import { CONFIRM_TIMEOUT_MS, MESSAGE_MS } from '../config/constants';
import type { Command } from '../../shared/models/command';
import type { ConnStatus } from '../../shared/models/connection-status';
import type { Robot } from '../../shared/models/robot';
import type { RowSnapshot } from '../../shared/models/row-snapshot';
import type { ServerFrame } from '../../shared/models/server-frame';
import type { Summary } from '../../shared/models/summary';
import { RobotIndex } from './robot-index';
import { isRobot, isStringArray } from './guards';
import { Notifier, type Listener } from './notifier';
import { PendingCommands } from './pending-commands';
import { rafScheduler, type Scheduler } from './scheduler';
import { WatchSet } from './watch-set';

/**
 * External store for the live robot state, read through useSyncExternalStore.
 * A facade: it routes server frames and UI inputs to the parts that own them
 * (index, watch set, pending commands, notifier).
 *
 * - Per-row subscriptions: a telemetry delta for robot X notifies only the row
 *   component that renders X, never the whole table.
 * - Notifications are batched per animation frame: 50 deltas in one frame cost
 *   one render pass, and a background tab does no rendering work at all.
 * - Snapshots are immutable and reference-stable until they change, which is
 *   what useSyncExternalStore requires.
 * - Memory is bounded by the viewport: robot details are kept only for watched
 *   ids (visible rows plus robots with a command in flight).
 */

type Topic = 'index' | 'summary' | 'status';

export interface StoreOptions {
  scheduler?: Scheduler;
  /** how long to wait for the robot to report the change */
  confirmTimeoutMs?: number;
  /** how long a failure message stays on the row */
  messageMs?: number;
}

const EMPTY_ROW: RowSnapshot = Object.freeze({});

export class RobotStore {
  private readonly index = new RobotIndex();
  private readonly watch = new WatchSet();
  private readonly robots = new Map<string, Robot>();
  private readonly rowCache = new Map<string, RowSnapshot>();
  private readonly notifier: Notifier<Topic>;
  private readonly pending: PendingCommands;
  private visible: string[] = [];
  private summary: Summary | null = null;
  private status: ConnStatus = { state: 'connecting' };
  private viewListener: ((ids: string[]) => void) | null = null;

  constructor(opts: StoreOptions = {}) {
    this.notifier = new Notifier<Topic>(opts.scheduler ?? rafScheduler);
    this.pending = new PendingCommands(
      { changed: (id) => this.markRow(id), released: () => this.recomputeWatch() },
      opts.confirmTimeoutMs ?? CONFIRM_TIMEOUT_MS,
      opts.messageMs ?? MESSAGE_MS,
    );
  }

  // ---- subscriptions (for useSyncExternalStore) ----------------------------
  subscribeRow = (id: string, cb: Listener): (() => void) => this.notifier.subscribeRow(id, cb);
  subscribe = (topic: Topic, cb: Listener): (() => void) => this.notifier.subscribe(topic, cb);

  // Pre-bound, reference-stable subscribe functions for the hooks.
  subIndex = (cb: Listener) => this.subscribe('index', cb);
  subSummary = (cb: Listener) => this.subscribe('summary', cb);
  subStatus = (cb: Listener) => this.subscribe('status', cb);

  getRow = (id: string): RowSnapshot => {
    let snap = this.rowCache.get(id);
    if (!snap) {
      const robot = this.robots.get(id);
      const pending = this.pending.get(id);
      snap = robot || pending ? { robot, pending } : EMPTY_ROW;
      this.rowCache.set(id, snap);
    }
    return snap;
  };

  /** Sorted ids matching the current filter. Same array until something changes. */
  getIds = (): string[] => this.index.getIds();
  getTotal = (): number => this.index.total;
  getSummary = (): Summary | null => this.summary;
  getStatus = (): ConnStatus => this.status;
  getFilter = (): string => this.index.getFilter();
  getWatch = (): string[] => this.watch.toArray();

  // ---- inputs ------------------------------------------------------------
  setFilter(q: string): void {
    if (this.index.setFilter(q)) this.notifier.notifyTopic('index');
  }

  setStatus(status: ConnStatus): void {
    if (status.state === this.status.state && status.retryAt === this.status.retryAt) return;
    this.status = status;
    this.notifier.notifyTopic('status');
  }

  /** Called by the connection with a function that tells the server what we watch. */
  onViewChange(fn: ((ids: string[]) => void) | null): void {
    this.viewListener = fn;
  }

  /** The rows currently on screen. Robots with a command in flight stay watched. */
  setView(visible: string[]): void {
    this.visible = visible;
    this.recomputeWatch();
  }

  applyFrame(f: ServerFrame): void {
    switch (f.t) {
      case 'index':
        if (f.full) {
          if (isStringArray(f.ids)) this.replaceIndex(f.ids);
        } else if (isStringArray(f.add) && isStringArray(f.rm)) {
          this.patchIndex(f.add, f.rm);
        }
        break;
      case 'delta':
        if (Array.isArray(f.robots)) for (const r of f.robots) this.applyRobot(r);
        break;
      case 'summary':
        this.summary = f;
        this.notifier.notifyTopic('summary');
        break;
      default:
        break; // "hello" and unknown frames carry nothing for the store
    }
  }

  // ---- commands (pending is a UI hint only, never a fake state) -------------
  beginCommand(id: string, cmd: Command): void {
    this.pending.begin(id, cmd, this.robots.get(id));
    this.recomputeWatch();
  }

  commandPublished(id: string): void {
    this.pending.published(id);
  }

  commandFailed(id: string, message: string): void {
    this.pending.failed(id, message);
  }

  /** Free timers. The store is not usable afterwards. */
  dispose(): void {
    this.pending.dispose();
    this.viewListener = null;
  }

  // ---- internals ---------------------------------------------------------
  private applyRobot(raw: unknown): void {
    if (!isRobot(raw) || !this.watch.has(raw.id)) return; // not ours to keep
    this.robots.set(raw.id, raw);
    this.pending.observe(raw);
    this.markRow(raw.id);
  }

  private replaceIndex(ids: string[]): void {
    this.index.replace(ids);
    for (const id of [...this.robots.keys()]) if (!this.index.has(id)) this.forget(id);
    this.notifier.notifyTopic('index');
  }

  private patchIndex(add: string[], rm: string[]): void {
    const removed = this.index.patch(add, rm);
    if (removed === null) return;
    for (const id of removed) this.forget(id);
    this.notifier.notifyTopic('index');
  }

  private forget(id: string): void {
    this.robots.delete(id);
    this.pending.clear(id);
    this.markRow(id);
  }

  private recomputeWatch(): void {
    if (!this.watch.update(this.visible, this.pending.ids())) return;
    for (const id of [...this.robots.keys()]) {
      if (!this.watch.has(id)) {
        this.robots.delete(id); // bounded memory: unwatched rows are re-fetched on demand
        this.markRow(id);
      }
    }
    this.viewListener?.(this.watch.toArray());
  }

  private markRow(id: string): void {
    this.rowCache.delete(id);
    this.notifier.notifyRow(id);
  }
}
