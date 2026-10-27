import type { Scheduler } from './scheduler';

export type Listener = () => void;

/**
 * Listener registry with batched delivery. Per-row listeners mean a change to
 * robot X notifies only the component that renders X. All notifications raised
 * before the scheduled flush are delivered once, together.
 */
export class Notifier<Topic extends string> {
  private rowListeners = new Map<string, Set<Listener>>();
  private topicListeners = new Map<Topic, Set<Listener>>();
  private dirtyRows = new Set<string>();
  private dirtyTopics = new Set<Topic>();
  private scheduled = false;

  constructor(private readonly schedule: Scheduler) {}

  subscribeRow(id: string, cb: Listener): () => void {
    return add(this.rowListeners, id, cb);
  }

  subscribe(topic: Topic, cb: Listener): () => void {
    return add(this.topicListeners, topic, cb);
  }

  /** Rows nobody renders cost nothing. */
  notifyRow(id: string): void {
    if (!this.rowListeners.has(id)) return;
    this.dirtyRows.add(id);
    this.requestFlush();
  }

  notifyTopic(topic: Topic): void {
    this.dirtyTopics.add(topic);
    this.requestFlush();
  }

  private requestFlush(): void {
    if (this.scheduled) return;
    this.scheduled = true;
    this.schedule(this.flush);
  }

  private flush = (): void => {
    this.scheduled = false;
    const rows = this.dirtyRows;
    const topics = this.dirtyTopics;
    this.dirtyRows = new Set();
    this.dirtyTopics = new Set();
    for (const id of rows) this.rowListeners.get(id)?.forEach((cb) => cb());
    for (const t of topics) this.topicListeners.get(t)?.forEach((cb) => cb());
  };
}

function add<K>(map: Map<K, Set<Listener>>, key: K, cb: Listener): () => void {
  let set = map.get(key);
  if (!set) map.set(key, (set = new Set()));
  set.add(cb);
  return () => {
    set.delete(cb);
    if (set.size === 0) map.delete(key);
  };
}
