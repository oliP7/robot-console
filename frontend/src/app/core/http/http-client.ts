import { REQUEST_TIMEOUT_MS } from '../config/constants';
import { ApiError } from './api-error';

/** Per-request options read by the client and its interceptors. */
export interface RequestMeta {
  timeoutMs?: number;
  /** succeed only on this status (default: any 2xx) */
  expect?: number;
  /** a 401 is an expected answer here, not a reason to sign the user out */
  skipUnauthorizedHandler?: boolean;
  /** endpoint-specific wording for some statuses, applied by the error interceptor */
  messages?: Readonly<Record<number, string>>;
}

export interface HttpRequest {
  url: string;
  init: RequestInit;
  headers: Headers;
  meta: RequestMeta;
}

export type RequestInterceptor = (req: HttpRequest) => HttpRequest;
export type ResponseInterceptor = (res: Response, req: HttpRequest) => Response | Promise<Response>;
/** Sees every failure. Returns the error to throw (possibly a rewritten one). */
export type ErrorInterceptor = (err: ApiError, req: HttpRequest) => ApiError;

export type FetchLike = (input: string, init: RequestInit) => Promise<Response>;

/**
 * fetch with a timeout, same-origin credentials and an interceptor chain.
 * Every failure (HTTP status, timeout, network, unparsable body) leaves as an
 * ApiError that has been through the error interceptors, so call sites never
 * interpret status codes themselves.
 */
export class HttpClient {
  private readonly requestInterceptors: RequestInterceptor[] = [];
  private readonly responseInterceptors: ResponseInterceptor[] = [];
  private readonly errorInterceptors: ErrorInterceptor[] = [];

  constructor(private readonly fetchImpl: FetchLike = (input, init) => fetch(input, init)) {}

  useRequest(i: RequestInterceptor): () => void {
    return register(this.requestInterceptors, i);
  }

  useResponse(i: ResponseInterceptor): () => void {
    return register(this.responseInterceptors, i);
  }

  useError(i: ErrorInterceptor): () => void {
    return register(this.errorInterceptors, i);
  }

  async send(url: string, init: RequestInit = {}, meta: RequestMeta = {}): Promise<Response> {
    let req: HttpRequest = { url, init, headers: new Headers(init.headers), meta };
    for (const i of this.requestInterceptors) req = i(req);

    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), req.meta.timeoutMs ?? REQUEST_TIMEOUT_MS);
    let res: Response;
    try {
      res = await this.fetchImpl(req.url, {
        ...req.init, headers: req.headers, signal: ctrl.signal, credentials: 'same-origin',
      });
    } catch (err) {
      const aborted = err instanceof DOMException && err.name === 'AbortError';
      throw this.fail(new ApiError(0, aborted ? 'timeout' : 'network'), req);
    } finally {
      clearTimeout(timer);
    }

    for (const i of this.responseInterceptors) res = await i(res, req);
    const ok = req.meta.expect === undefined ? res.ok : res.status === req.meta.expect;
    if (!ok) throw this.fail(new ApiError(res.status, 'http'), req);
    return res;
  }

  async json<T>(url: string, init: RequestInit = {}, meta: RequestMeta = {}): Promise<T> {
    const res = await this.send(url, init, meta);
    try {
      return (await res.json()) as T;
    } catch {
      throw this.fail(new ApiError(res.status, 'parse'), { url, init, headers: new Headers(init.headers), meta });
    }
  }

  private fail(err: ApiError, req: HttpRequest): ApiError {
    return this.errorInterceptors.reduce((e, i) => i(e, req), err);
  }
}

function register<T>(list: T[], item: T): () => void {
  list.push(item);
  return () => {
    const at = list.indexOf(item);
    if (at >= 0) list.splice(at, 1);
  };
}
