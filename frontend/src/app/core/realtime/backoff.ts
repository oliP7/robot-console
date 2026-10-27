import type { BackoffOptions } from '../../shared/models/backoff-options';
import { DEFAULT_BACKOFF } from '../config/constants';

/**
 * Exponential backoff with "full jitter": a uniform delay between minMs and
 * min(cap, base * 2^attempt). Jitter spreads reconnects after a server restart
 * so that thousands of clients do not stampede it at the same instant.
 */
export function backoffDelay(attempt: number, opts: BackoffOptions = DEFAULT_BACKOFF,
                             random: () => number = Math.random): number {
  const ceiling = Math.min(opts.capMs, opts.baseMs * 2 ** Math.min(attempt, 30));
  return Math.round(opts.minMs + random() * Math.max(0, ceiling - opts.minMs));
}
