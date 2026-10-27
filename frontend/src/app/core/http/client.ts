import { tokenStorage } from '../auth/token-storage';
import { HttpClient, type FetchLike } from './http-client';
import { createAuthInterceptor, type TokenProvider } from './interceptors/auth-interceptor';
import { errorInterceptor } from './interceptors/error-interceptor';
import { UnauthorizedInterceptor } from './interceptors/unauthorized-interceptor';

export interface ApiClient {
  http: HttpClient;
  unauthorized: UnauthorizedInterceptor;
}

/** Wires the interceptor chain. Exposed as a factory so tests can inject a fake fetch. */
export function createApiClient(fetchImpl?: FetchLike, getToken: TokenProvider = () => tokenStorage.get()): ApiClient {
  const http = new HttpClient(fetchImpl);
  const unauthorized = new UnauthorizedInterceptor();
  http.useRequest(createAuthInterceptor(getToken));
  http.useError(errorInterceptor); // first: normalize, so later interceptors see final errors
  http.useError(unauthorized.intercept);
  return { http, unauthorized };
}

/** The shared instance used by every API module. */
export const api = createApiClient();

export const onUnauthorized = (handler: () => void): (() => void) => api.unauthorized.onUnauthorized(handler);
