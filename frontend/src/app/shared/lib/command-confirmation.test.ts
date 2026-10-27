import { describe, expect, it } from 'vitest';
import { confirms, isNoop } from './command-confirmation';
import type { Robot } from '../models/robot';

const r = (over: Partial<Robot> = {}): Robot => ({
  id: 'a', battery: 50, charge: 'discharging', mode: 'idle', online: true, ts: '', ...over,
});

describe('confirms', () => {
  it('set_mode needs the target mode', () => {
    expect(confirms({ cmd: 'set_mode', value: 'working' }, r(), r({ mode: 'working' }))).toBe(true);
    expect(confirms({ cmd: 'set_mode', value: 'working' }, r(), r())).toBe(false);
  });
  it('toggle_charge needs a flip', () => {
    expect(confirms({ cmd: 'toggle_charge' }, r(), r({ charge: 'charging' }))).toBe(true);
    expect(confirms({ cmd: 'toggle_charge' }, r(), r())).toBe(false);
  });
  it('kick is not fooled by charging drift', () => {
    expect(confirms({ cmd: 'kick' }, r({ battery: 50 }), r({ battery: 51.2 }))).toBe(false);
    expect(confirms({ cmd: 'kick' }, r({ battery: 50 }), r({ battery: 54.6 }))).toBe(true);
    expect(confirms({ cmd: 'kick' }, r({ battery: 98 }), r({ battery: 100 }))).toBe(true);
  });
  it('no-ops are detected', () => {
    expect(isNoop({ cmd: 'set_mode', value: 'idle' }, r())).toBe(true);
    expect(isNoop({ cmd: 'kick' }, r({ battery: 100 }))).toBe(true);
    expect(isNoop({ cmd: 'toggle_charge' }, r())).toBe(false);
  });
});
