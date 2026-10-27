import { CLOSE_UNAUTHORIZED, DEFAULT_BACKOFF, STALE_MS, VIEW_DEBOUNCE_MS } from '../config/constants';
import type { BackoffOptions } from '../../shared/models/backoff-options';
import { backoffDelay } from './backoff';
import { parseFrame } from './frame-parser';
import type { LiveSink } from './live-sink';

export interface ConnectionOptions {
  url: string;
  store: LiveSink;
  token?: string | null;
  /** no frame for this long means the link is dead even if TCP says otherwise */
  staleMs?: number;
  backoff?: BackoffOptions;
  /** delay before telling the server about a new viewport (scroll debounce) */
  viewDebounceMs?: number;
  WebSocketImpl?: typeof WebSocket;
  random?: () => number;
  now?: () => number;
}

/**
 * The live link. Read-only: the server pushes, the client only says which rows
 * it is looking at. Commands go over REST (see api/commands-api.ts).
 *
 * - reconnects with exponential backoff and full jitter
 * - detects a stale link (the server sends a summary every second, so a few
 *   seconds of silence means the connection is dead) and replaces it
 * - re-sends the current viewport after every reconnect
 */
export class LiveConnection {
  private ws: WebSocket | null = null;
  private attempt = 0;
  private stopped = true;
  private ready = false; // "hello" received on the current socket
  private lastFrameAt = 0;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private watchdog: ReturnType<typeof setInterval> | null = null;
  private viewTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly o: Required<Omit<ConnectionOptions, 'token'>> & { token: string | null };

  constructor(opts: ConnectionOptions) {
    this.o = {
      staleMs: STALE_MS,
      backoff: DEFAULT_BACKOFF,
      viewDebounceMs: VIEW_DEBOUNCE_MS,
      WebSocketImpl: globalThis.WebSocket,
      random: Math.random,
      now: Date.now,
      ...opts,
      token: opts.token ?? null,
    };
  }

  start(): void {
    if (!this.stopped) return;
    this.stopped = false;
    this.o.store.onViewChange(() => this.scheduleView());
    this.watchdog = setInterval(() => this.checkStale(), Math.min(1000, this.o.staleMs / 2));
    if (typeof window !== 'undefined') window.addEventListener('online', this.onOnline);
    this.connect();
  }

  stop(): void {
    this.stopped = true;
    this.o.store.onViewChange(null);
    if (this.retryTimer) clearTimeout(this.retryTimer);
    if (this.viewTimer) clearTimeout(this.viewTimer);
    if (this.watchdog) clearInterval(this.watchdog);
    this.retryTimer = this.viewTimer = this.watchdog = null;
    if (typeof window !== 'undefined') window.removeEventListener('online', this.onOnline);
    this.drop();
  }

  private connect(): void {
    if (this.stopped) return;
    this.retryTimer = null;
    this.o.store.setStatus({ state: this.attempt === 0 ? 'connecting' : 'reconnecting' });
    let ws: WebSocket;
    try {
      ws = new this.o.WebSocketImpl(this.o.url);
    } catch {
      this.scheduleRetry();
      return;
    }
    this.ws = ws;
    this.ready = false;
    this.lastFrameAt = this.o.now();
    ws.onopen = () => {
      if (this.o.token) ws.send(JSON.stringify({ t: 'auth', token: this.o.token }));
    };
    ws.onmessage = (ev: MessageEvent) => this.onFrame(ev.data);
    ws.onclose = (ev: CloseEvent) => {
      if (this.ws !== ws) return; // an old socket we already replaced
      this.ws = null;
      this.ready = false;
      if (ev.code === CLOSE_UNAUTHORIZED) {
        this.stopped = true; // retrying with the same token cannot succeed
        this.o.store.setStatus({ state: 'unauthorized' });
        return;
      }
      this.scheduleRetry();
    };
    ws.onerror = () => {
      /* a close event always follows; handled there */
    };
  }

  private onFrame(data: unknown): void {
    this.lastFrameAt = this.o.now();
    const frame = parseFrame(data);
    if (!frame) return;
    if (frame.t === 'hello') {
      this.ready = true;
      this.attempt = 0;
      this.o.store.setStatus({ state: 'live' });
      this.sendView(); // the server forgets our viewport on every new socket
      return;
    }
    if (this.o.store.getStatus().state === 'stale') this.o.store.setStatus({ state: 'live' });
    this.o.store.applyFrame(frame);
  }

  private checkStale(): void {
    if (!this.ws) return;
    const silent = this.o.now() - this.lastFrameAt;
    if (silent > this.o.staleMs * 2) {
      // Dead link: do not wait for TCP to notice (that can take minutes).
      this.drop();
      this.scheduleRetry();
    } else if (silent > this.o.staleMs && this.ready) {
      this.o.store.setStatus({ state: 'stale' });
    }
  }

  private drop(): void {
    const ws = this.ws;
    this.ws = null;
    this.ready = false;
    if (!ws) return;
    ws.onopen = ws.onmessage = ws.onclose = ws.onerror = null;
    try {
      ws.close();
    } catch {
      /* already closed */
    }
  }

  private scheduleRetry(): void {
    if (this.stopped || this.retryTimer) return;
    const delay = backoffDelay(this.attempt++, this.o.backoff, this.o.random);
    this.o.store.setStatus({ state: 'reconnecting', retryAt: this.o.now() + delay });
    this.retryTimer = setTimeout(() => this.connect(), delay);
  }

  private onOnline = (): void => {
    // The network came back: try now instead of waiting out the backoff.
    if (this.stopped || this.ws) return;
    if (this.retryTimer) clearTimeout(this.retryTimer);
    this.retryTimer = null;
    this.attempt = 0;
    this.connect();
  };

  private scheduleView(): void {
    if (this.viewTimer) return;
    this.viewTimer = setTimeout(() => {
      this.viewTimer = null;
      this.sendView();
    }, this.o.viewDebounceMs);
  }

  private sendView(): void {
    const ws = this.ws;
    if (!ws || !this.ready || ws.readyState !== 1 /* OPEN */) return;
    try {
      ws.send(JSON.stringify({ t: 'view', ids: this.o.store.getWatch() }));
    } catch {
      /* the close handler will reconnect and re-send */
    }
  }
}
