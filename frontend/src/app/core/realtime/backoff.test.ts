import { describe, expect, it } from 'vitest';
import { backoffDelay } from './backoff';

describe('backoffDelay', () => {
  const opts = { baseMs: 500, capMs: 15_000, minMs: 250 };
  it('grows exponentially up to the cap', () => {
    expect(backoffDelay(0, opts, () => 1)).toBe(500);
    expect(backoffDelay(3, opts, () => 1)).toBe(4000);
    expect(backoffDelay(50, opts, () => 1)).toBe(15_000);
  });
  it('is jittered over the whole range and never below the floor', () => {
    expect(backoffDelay(5, opts, () => 0)).toBe(250);
    const samples = Array.from({ length: 200 }, () => backoffDelay(5, opts));
    expect(Math.min(...samples)).toBeGreaterThanOrEqual(250);
    expect(Math.max(...samples)).toBeLessThanOrEqual(15_000);
    expect(new Set(samples).size).toBeGreaterThan(50); // actually spread out
  });
});
