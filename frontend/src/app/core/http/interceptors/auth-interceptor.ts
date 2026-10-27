import type { RequestInterceptor } from '../http-client';

export type TokenProvider = () => string | null;

/** Adds the bearer token, unless the request already carries its own Authorization header. */
export function createAuthInterceptor(getToken: TokenProvider): RequestInterceptor {
  return (req) => {
    const token = getToken();
    if (token && !req.headers.has('Authorization')) req.headers.set('Authorization', `Bearer ${token}`);
    return req;
  };
}
