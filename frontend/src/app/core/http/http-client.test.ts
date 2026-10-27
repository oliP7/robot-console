import { describe, expect, it, vi } from 'vitest';
import { ApiError } from './api-error';
import { createApiClient } from './client';
import type { FetchLike } from './http-client';

/** Fake fetch: answers with a fixed status and records what it was sent. */
function answering(status: number, body: unknown = {}) {
  const calls: { url: string; init: RequestInit }[] = [];
  const fetchImpl: FetchLike = async (url, init) => {
    calls.push({ url, init });
    return new Response(JSON.stringify(body), { status });
  };
  return { fetchImpl, calls };
}

async function caught(p: Promise<unknown>): Promise<ApiError> {
  try {
    await p;
  } catch (err) {
    expect(err).toBeInstanceOf(ApiError);
    return err as ApiError;
  }
  throw new Error('expected a rejection');
}

describe('error interceptor', () => {
  it.each([
    [404, 'Not found.'],
    [422, 'Request rejected as invalid.'],
    [429, 'Too many requests. Try again in a moment.'],
    [503, 'Service unavailable. Try again in a moment.'],
    [418, 'Request failed (HTTP 418).'],
  ])('maps HTTP %i to a user message', async (status, message) => {
    const { http } = createApiClient(answering(status).fetchImpl, () => null);
    const err = await caught(http.send('/x'));
    expect(err).toMatchObject({ status, kind: 'http', message });
  });

  it('prefers endpoint-specific wording from the request', async () => {
    const { http } = createApiClient(answering(503).fetchImpl, () => null);
    const err = await caught(http.send('/x', {}, { messages: { 503: 'Broker unavailable. Command not sent.' } }));
    expect(err.message).toBe('Broker unavailable. Command not sent.');
  });

  it('enforces an expected status', async () => {
    const { http } = createApiClient(answering(200).fetchImpl, () => null);
    const err = await caught(http.send('/x', {}, { expect: 202 }));
    expect(err.status).toBe(200);
  });

  it('normalizes network errors', async () => {
    const { http } = createApiClient(async () => { throw new TypeError('Failed to fetch'); }, () => null);
    const err = await caught(http.send('/x'));
    expect(err).toMatchObject({ status: 0, kind: 'network', message: 'Network error. Is the server reachable?' });
  });

  it('normalizes timeouts', async () => {
    const hang: FetchLike = (_url, init) => new Promise((_, reject) => {
      init.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
    });
    const { http } = createApiClient(hang, () => null);
    const err = await caught(http.send('/x', {}, { timeoutMs: 5 }));
    expect(err).toMatchObject({ status: 0, kind: 'timeout', message: 'Request timed out.' });
  });

  it('normalizes an unparsable body', async () => {
    const bad: FetchLike = async () => new Response('not json', { status: 200 });
    const { http } = createApiClient(bad, () => null);
    const err = await caught(http.json('/x'));
    expect(err.kind).toBe('parse');
  });
});

describe('unauthorized interceptor', () => {
  it('calls the registered handler on 401', async () => {
    const { http, unauthorized } = createApiClient(answering(401).fetchImpl, () => null);
    const handler = vi.fn();
    unauthorized.onUnauthorized(handler);
    const err = await caught(http.send('/x'));
    expect(handler).toHaveBeenCalledTimes(1);
    expect(err.message).toBe('Not authorised. Please sign in again.');
  });

  it('respects the per-request opt-out', async () => {
    const { http, unauthorized } = createApiClient(answering(401).fetchImpl, () => null);
    const handler = vi.fn();
    unauthorized.onUnauthorized(handler);
    await caught(http.send('/x', {}, { skipUnauthorizedHandler: true }));
    expect(handler).not.toHaveBeenCalled();
  });

  it('does not fire for other statuses or after unregistering', async () => {
    const handler = vi.fn();
    const a = createApiClient(answering(403).fetchImpl, () => null);
    a.unauthorized.onUnauthorized(handler);
    await caught(a.http.send('/x'));
    const b = createApiClient(answering(401).fetchImpl, () => null);
    b.unauthorized.onUnauthorized(handler)();
    await caught(b.http.send('/x'));
    expect(handler).not.toHaveBeenCalled();
  });
});

describe('auth interceptor', () => {
  it('adds the bearer token and same-origin credentials', async () => {
    const f = answering(200);
    const { http } = createApiClient(f.fetchImpl, () => 'tok');
    await http.send('/x');
    const init = f.calls[0]!.init;
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer tok');
    expect(init.credentials).toBe('same-origin');
  });

  it('keeps an explicit Authorization header and sends none without a token', async () => {
    const f = answering(200);
    const { http } = createApiClient(f.fetchImpl, () => 'stored');
    await http.send('/x', { headers: { Authorization: 'Bearer candidate' } });
    expect(new Headers(f.calls[0]!.init.headers).get('Authorization')).toBe('Bearer candidate');
    const g = answering(200);
    await createApiClient(g.fetchImpl, () => null).http.send('/x');
    expect(new Headers(g.calls[0]!.init.headers).has('Authorization')).toBe(false);
  });
});
