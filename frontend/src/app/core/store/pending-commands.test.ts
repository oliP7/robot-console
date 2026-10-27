import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Robot } from '../../shared/models/robot';
import { PendingCommands } from './pending-commands';

const robot = (over: Partial<Robot> = {}): Robot => ({
  id: 'a', battery: 50, charge: 'discharging', mode: 'idle', online: true, ts: '', ...over,
});

describe('PendingCommands', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it('resolves on confirming telemetry and reports the release', () => {
    const events = { changed: vi.fn(), released: vi.fn() };
    const p = new PendingCommands(events, 1000, 500);
    p.begin('a', { cmd: 'set_mode', value: 'working' }, robot());
    p.observe(robot({ battery: 49 }));
    expect(p.get('a')?.phase).toBe('sending');
    p.observe(robot({ mode: 'working' }));
    expect(p.get('a')).toBeUndefined();
    expect(events.released).toHaveBeenCalledTimes(1);
  });

  it('dispose cancels timers', () => {
    const p = new PendingCommands({ changed: vi.fn(), released: vi.fn() }, 1000, 500);
    p.begin('a', { cmd: 'kick' }, robot());
    p.published('a');
    p.dispose();
    vi.advanceTimersByTime(5000);
    expect(p.get('a')?.phase).toBe('awaiting');
  });
});
