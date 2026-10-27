export type ApiErrorKind = 'http' | 'timeout' | 'network' | 'parse';

/** The only error type the HTTP layer throws. `message` is ready to show to a user. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly kind: ApiErrorKind,
    message = status ? `HTTP ${status}` : kind,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/** Message for any caught value. The HTTP layer always throws ApiError; this covers bugs. */
export function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : 'Unexpected error.';
}
