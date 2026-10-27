import { describe, expect, it } from 'vitest';
import { RobotIndex } from './robot-index';

describe('RobotIndex', () => {
  it('patch reports only ids that were actually removed', () => {
    const ix = new RobotIndex();
    ix.replace(['a', 'b']);
    expect(ix.patch(['c'], ['b', 'zz'])).toEqual(['b']);
    expect(ix.getIds()).toEqual(['a', 'c']);
    expect(ix.patch(['a'], ['zz'])).toBeNull(); // nothing changed
  });

  it('setFilter normalizes and reports changes', () => {
    const ix = new RobotIndex();
    ix.replace(['r-A', 'r-b']);
    expect(ix.setFilter(' A ')).toBe(true);
    expect(ix.setFilter('a')).toBe(false);
    expect(ix.getIds()).toEqual(['r-A']);
    expect(ix.total).toBe(2);
  });
});
