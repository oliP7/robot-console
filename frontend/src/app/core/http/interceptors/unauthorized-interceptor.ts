import type { ErrorInterceptor } from '../http-client';

export type UnauthorizedHandler = () => void;

/**
 * Turns any 401 into one app-wide reaction (sign out), so no call site checks
 * for 401 itself. Requests that expect a 401 opt out with skipUnauthorizedHandler.
 */
export class UnauthorizedInterceptor {
  private handler: UnauthorizedHandler | null = null;

  /** Registers the handler; returns a function that unregisters it. */
  onUnauthorized(handler: UnauthorizedHandler): () => void {
    this.handler = handler;
    return () => {
      if (this.handler === handler) this.handler = null;
    };
  }

  readonly intercept: ErrorInterceptor = (err, req) => {
    if (err.status === 401 && !req.meta.skipUnauthorizedHandler) this.handler?.();
    return err;
  };
}
