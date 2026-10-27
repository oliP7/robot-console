import { describe, expect, it, vi } from 'vitest';
import { Notifier } from './notifier';

describe('Notifier', () => {
  it('batches until the scheduled flush and skips rows nobody renders', () => {
    const queued: (() => void)[] = [];
    const n = new Notifier<'index'>((cb) => { queued.push(cb); });
    const row = vi.fn();
    const topic = vi.fn();
    n.subscribeRow('a', row);
    n.subscribe('index', topic);
    n.notifyRow('a');
    n.notifyRow('a');
    n.notifyRow('nobody');
    n.notifyTopic('index');
    expect(queued).toHaveLength(1);
    queued[0]!();
    expect(row).toHaveBeenCalledTimes(1);
    expect(topic).toHaveBeenCalledTimes(1);
  });
});
