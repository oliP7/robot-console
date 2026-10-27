import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { RobotStore } from './robot-store';
import type { Scheduler } from './scheduler';
import type { Robot } from '../../shared/models/robot';

/** Manual "animation frame": nothing is delivered until we call frame(). */
function manual() {
  let queued: (() => void)[] = [];
  const scheduler: Scheduler = (cb) => { queued.push(cb); };
  const frame = () => { const q = queued; queued = []; q.forEach((cb) => cb()); };
  return { scheduler, frame, pending: () => queued.length };
}

const robot = (id: string, over: Partial<Robot> = {}): Robot => ({
  id, battery: 50, charge: 'discharging', mode: 'idle', online: true, ts: '2026-01-01T00:00:00Z', ...over,
});

describe('index', () => {
  it('full index is sorted and de-duplicated', () => {
    const s = new RobotStore({ scheduler: manual().scheduler });
    s.applyFrame({ t: 'index', full: true, ids: ['c', 'a', 'b', 'a'] });
    expect(s.getIds()).toEqual(['a', 'b', 'c']);
  });

  it('diffs keep order and are idempotent', () => {
    const s = new RobotStore({ scheduler: manual().scheduler });
    s.applyFrame({ t: 'index', full: true, ids: ['b', 'd'] });
    s.applyFrame({ t: 'index', add: ['c', 'a', 'b'], rm: ['d', 'zz'] });
    expect(s.getIds()).toEqual(['a', 'b', 'c']);
    const before = s.getIds();
    s.applyFrame({ t: 'index', add: ['a'], rm: ['d'] }); // duplicate add, unknown rm
    expect(s.getIds()).toBe(before); // no change, same reference
  });

  it('large diffs take the sort path and stay correct', () => {
    const s = new RobotStore({ scheduler: manual().scheduler });
    const ids = Array.from({ length: 300 }, (_, i) => `r${String(i).padStart(4, '0')}`);
    s.applyFrame({ t: 'index', full: true, ids: ids.filter((_, i) => i % 2 === 0) });
    s.applyFrame({ t: 'index', add: ids.filter((_, i) => i % 2 === 1), rm: [] });
    expect(s.getIds()).toEqual(ids);
  });

  it('filter is case-insensitive and memoized', () => {
    const s = new RobotStore({ scheduler: manual().scheduler });
    s.applyFrame({ t: 'index', full: true, ids: ['r-ab1', 'r-cd2', 'r-AB3'] });
    s.setFilter(' AB ');
    expect(s.getIds()).toEqual(['r-AB3', 'r-ab1']);
    expect(s.getIds()).toBe(s.getIds());
  });

  it('ignores malformed frames', () => {
    const s = new RobotStore({ scheduler: manual().scheduler });
    s.applyFrame({ t: 'index', full: true, ids: [1, 2] } as never);
    s.applyFrame({ t: 'delta', robots: [{ id: 'x' }] } as never);
    s.applyFrame({ t: 'bogus' } as never);
    expect(s.getIds()).toEqual([]);
  });
});

describe('rows and notifications', () => {
  it('keeps only watched robots and evicts on unwatch', () => {
    const s = new RobotStore({ scheduler: manual().scheduler });
    s.setView(['a']);
    s.applyFrame({ t: 'delta', robots: [robot('a'), robot('b')] });
    expect(s.getRow('a').robot?.id).toBe('a');
    expect(s.getRow('b').robot).toBeUndefined(); // not watched
    s.setView(['b']);
    expect(s.getRow('a').robot).toBeUndefined(); // evicted
  });

  it('notifies only the subscribed row, once per frame (rAF batching)', () => {
    const m = manual();
    const s = new RobotStore({ scheduler: m.scheduler });
    s.setView(['a', 'b']);
    const a = vi.fn();
    const b = vi.fn();
    s.subscribeRow('a', a);
    s.subscribeRow('b', b);
    for (let i = 0; i < 20; i++) s.applyFrame({ t: 'delta', robots: [robot('a', { battery: i })] });
    expect(a).not.toHaveBeenCalled(); // nothing until the frame
    expect(m.pending()).toBe(1); // one frame scheduled for 20 updates
    m.frame();
    expect(a).toHaveBeenCalledTimes(1);
    expect(b).not.toHaveBeenCalled();
    expect(s.getRow('a').robot?.battery).toBe(19); // latest wins
  });

  it('row snapshots are reference-stable until the row changes', () => {
    const s = new RobotStore({ scheduler: manual().scheduler });
    s.setView(['a', 'b']);
    s.applyFrame({ t: 'delta', robots: [robot('a'), robot('b')] });
    const snap = s.getRow('a');
    s.applyFrame({ t: 'delta', robots: [robot('b', { battery: 1 })] });
    expect(s.getRow('a')).toBe(snap);
    s.applyFrame({ t: 'delta', robots: [robot('a', { battery: 1 })] });
    expect(s.getRow('a')).not.toBe(snap);
  });

  it('unsubscribe stops notifications', () => {
    const m = manual();
    const s = new RobotStore({ scheduler: m.scheduler });
    s.setView(['a']);
    const cb = vi.fn();
    const off = s.subscribeRow('a', cb);
    off();
    s.applyFrame({ t: 'delta', robots: [robot('a')] });
    m.frame();
    expect(cb).not.toHaveBeenCalled();
  });

  it('removal from the index forgets the robot', () => {
    const s = new RobotStore({ scheduler: manual().scheduler });
    s.applyFrame({ t: 'index', full: true, ids: ['a'] });
    s.setView(['a']);
    s.applyFrame({ t: 'delta', robots: [robot('a')] });
    s.applyFrame({ t: 'index', add: [], rm: ['a'] });
    expect(s.getRow('a').robot).toBeUndefined();
  });

  it('reports view changes only when the watched set changes', () => {
    const s = new RobotStore({ scheduler: manual().scheduler });
    const views: string[][] = [];
    s.onViewChange((ids) => views.push(ids));
    s.setView(['a', 'b']);
    s.setView(['b', 'a']);
    s.setView(['c']);
    expect(views).toEqual([['a', 'b'], ['c']]);
  });
});

describe('pending commands', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  function ready() {
    const s = new RobotStore({ scheduler: manual().scheduler, confirmTimeoutMs: 1000, messageMs: 500 });
    s.setView(['a']);
    s.applyFrame({ t: 'delta', robots: [robot('a', { mode: 'idle' })] });
    return s;
  }

  it('never changes robot state locally: only telemetry resolves a command', () => {
    const s = ready();
    s.beginCommand('a', { cmd: 'set_mode', value: 'working' });
    s.commandPublished('a');
    expect(s.getRow('a').robot?.mode).toBe('idle'); // no optimistic update
    expect(s.getRow('a').pending?.phase).toBe('awaiting');
    s.applyFrame({ t: 'delta', robots: [robot('a', { mode: 'idle', battery: 49 })] }); // unrelated drift
    expect(s.getRow('a').pending?.phase).toBe('awaiting');
    s.applyFrame({ t: 'delta', robots: [robot('a', { mode: 'working' })] });
    expect(s.getRow('a').pending).toBeUndefined();
    expect(s.getRow('a').robot?.mode).toBe('working');
  });

  it('telemetry can confirm before the HTTP 202 arrives', () => {
    const s = ready();
    s.beginCommand('a', { cmd: 'toggle_charge' });
    s.applyFrame({ t: 'delta', robots: [robot('a', { charge: 'charging' })] });
    expect(s.getRow('a').pending).toBeUndefined();
    s.commandPublished('a'); // late 202 must not resurrect the pending state
    expect(s.getRow('a').pending).toBeUndefined();
  });

  it('times out to "unconfirmed" and then clears', () => {
    const s = ready();
    s.beginCommand('a', { cmd: 'kick' });
    s.commandPublished('a');
    vi.advanceTimersByTime(1001);
    expect(s.getRow('a').pending?.phase).toBe('unconfirmed');
    vi.advanceTimersByTime(501);
    expect(s.getRow('a').pending).toBeUndefined();
  });

  it('shows HTTP failures then clears them', () => {
    const s = ready();
    s.beginCommand('a', { cmd: 'kick' });
    s.commandFailed('a', 'Robot is offline.');
    expect(s.getRow('a').pending).toMatchObject({ phase: 'failed', message: 'Robot is offline.' });
    vi.advanceTimersByTime(501);
    expect(s.getRow('a').pending).toBeUndefined();
  });

  it('a robot with a command in flight stays watched after scrolling away', () => {
    const s = ready();
    const views: string[][] = [];
    s.onViewChange((ids) => views.push(ids));
    s.beginCommand('a', { cmd: 'set_mode', value: 'error' });
    s.setView(['z']);
    expect(views.at(-1)?.sort()).toEqual(['a', 'z']);
    s.applyFrame({ t: 'delta', robots: [robot('a', { mode: 'error' })] });
    expect(views.at(-1)).toEqual(['z']); // released once confirmed
  });
});
