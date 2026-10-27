/** Reconnect delay bounds for exponential backoff with full jitter. */
export interface BackoffOptions {
  baseMs: number;
  capMs: number;
  minMs: number;
}
