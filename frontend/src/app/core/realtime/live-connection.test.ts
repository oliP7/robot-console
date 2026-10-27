import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { LiveConnection } from './live-connection';
import { RobotStore } from '../store/robot-store';

class FakeWS {
  static all: FakeWS[] = [];
  readyState = 0;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: ((e: { code: number }) => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;
  constructor(public url: string) { FakeWS.all.push(this); }
  send(d: string) { this.sent.push(d); }
  close() { this.closed = true; }
  // test helpers
  open() { this.readyState = 1; this.onopen?.(); }
  recv(frame: object) { this.onmessage?.({ data: JSON.stringify(frame) }); }
  serverClose(code: number) { this.readyState = 3; this.onclose?.({ code }); }
}

function setup(token: string | null = null) {
  const store = new RobotStore({ scheduler: (cb) => cb() });
  const conn = new LiveConnection({
    url: 'ws://x/ws', store, token, staleMs: 1000, viewDebounceMs: 10,
    backoff: { baseMs: 100, capMs: 1000, minMs: 100 }, random: () => 0,
    WebSocketImpl: FakeWS as unknown as typeof WebSocket, now: () => Date.now(),
  });
  return { store, conn };
}

describe('LiveConnection', () => {
  beforeEach(() => { vi.useFakeTimers(); FakeWS.all = []; });
  afterEach(() => { vi.useRealTimers(); });

  it('authenticates first, then sends the viewport after hello', () => {
    const { store, conn } = setup('tok');
    store.setView(['a']);
    conn.start();
    const ws = FakeWS.all[0]!;
    ws.open();
    expect(JSON.parse(ws.sent[0]!)).toEqual({ t: 'auth', token: 'tok' });
    ws.recv({ t: 'hello', modes: [], max_watch: 400 });
    expect(store.getStatus().state).toBe('live');
    expect(JSON.parse(ws.sent[1]!)).toEqual({ t: 'view', ids: ['a'] });
    conn.stop();
  });

  it('reconnects with backoff and re-sends the viewport', () => {
    const { store, conn } = setup();
    conn.start();
    FakeWS.all[0]!.open();
    FakeWS.all[0]!.recv({ t: 'hello' });
    store.setView(['b']);
    vi.advanceTimersByTime(20);
    FakeWS.all[0]!.serverClose(1006);
    expect(store.getStatus().state).toBe('reconnecting');
    vi.advanceTimersByTime(100);
    expect(FakeWS.all).toHaveLength(2);
    const ws2 = FakeWS.all[1]!;
    ws2.open();
    ws2.recv({ t: 'hello' });
    expect(JSON.parse(ws2.sent.at(-1)!)).toEqual({ t: 'view', ids: ['b'] });
    conn.stop();
  });

  it('marks a silent link stale, then replaces it', () => {
    const { store, conn } = setup();
    conn.start();
    FakeWS.all[0]!.open();
    FakeWS.all[0]!.recv({ t: 'hello' });
    vi.advanceTimersByTime(1500);
    expect(store.getStatus().state).toBe('stale');
    vi.advanceTimersByTime(1000);
    expect(FakeWS.all[0]!.closed).toBe(true);
    vi.advanceTimersByTime(200);
    expect(FakeWS.all.length).toBe(2);
    conn.stop();
  });

  it('stops retrying when the server rejects the token', () => {
    const { store, conn } = setup('bad');
    conn.start();
    FakeWS.all[0]!.open();
    FakeWS.all[0]!.serverClose(4401);
    expect(store.getStatus().state).toBe('unauthorized');
    vi.advanceTimersByTime(60_000);
    expect(FakeWS.all).toHaveLength(1);
    conn.stop();
  });

  it('survives garbage frames', () => {
    const { store, conn } = setup();
    conn.start();
    const ws = FakeWS.all[0]!;
    ws.open();
    ws.onmessage?.({ data: '{not json' });
    ws.onmessage?.({ data: 'null' });
    ws.recv({ t: 'hello' });
    expect(store.getStatus().state).toBe('live');
    conn.stop();
  });
});
