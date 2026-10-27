import { confirms } from '../../shared/lib/command-confirmation';
import type { Command } from '../../shared/models/command';
import type { Pending } from '../../shared/models/pending-command';
import type { Robot } from '../../shared/models/robot';

export interface PendingEvents {
  /** the pending state of this row changed */
  changed(id: string): void;
  /** a command finished, so its robot may no longer need watching */
  released(): void;
}

/**
 * Commands in flight and their timers. Pending is a UI hint only, never a fake
 * state: it is resolved by the robot's own telemetry, by an error, or by timeout.
 */
export class PendingCommands {
  private pending = new Map<string, Pending>();
  private timers = new Map<string, ReturnType<typeof setTimeout>>();

  constructor(
    private readonly events: PendingEvents,
    private readonly confirmTimeoutMs: number,
    private readonly messageMs: number,
  ) {}

  get(id: string): Pending | undefined {
    return this.pending.get(id);
  }

  ids(): Iterable<string> {
    return this.pending.keys();
  }

  begin(id: string, cmd: Command, before: Robot | undefined): void {
    this.set(id, { cmd, phase: 'sending', before });
  }

  published(id: string): void {
    const p = this.pending.get(id);
    if (!p || p.phase !== 'sending') return; // already confirmed by telemetry
    this.set(id, { ...p, phase: 'awaiting' });
    this.arm(id, this.confirmTimeoutMs, () =>
      this.flashMessage(id, 'unconfirmed', 'The robot has not reported the change yet.'));
  }

  failed(id: string, message: string): void {
    if (!this.pending.has(id)) return;
    this.flashMessage(id, 'failed', message);
  }

  /** New telemetry for a robot: resolves its command if the robot now reports the change. */
  observe(robot: Robot): void {
    const p = this.pending.get(robot.id);
    if (p && (p.phase === 'sending' || p.phase === 'awaiting') && confirms(p.cmd, p.before, robot)) {
      this.clear(robot.id);
    }
  }

  clear(id: string): void {
    const t = this.timers.get(id);
    if (t !== undefined) clearTimeout(t);
    this.timers.delete(id);
    if (this.pending.delete(id)) {
      this.events.changed(id);
      this.events.released();
    }
  }

  dispose(): void {
    for (const t of this.timers.values()) clearTimeout(t);
    this.timers.clear();
  }

  private set(id: string, p: Pending): void {
    this.pending.set(id, p);
    this.events.changed(id);
  }

  private flashMessage(id: string, phase: 'failed' | 'unconfirmed', message: string): void {
    const p = this.pending.get(id);
    if (!p) return;
    this.set(id, { ...p, phase, message });
    this.arm(id, this.messageMs, () => this.clear(id));
  }

  private arm(id: string, ms: number, fn: () => void): void {
    const old = this.timers.get(id);
    if (old !== undefined) clearTimeout(old);
    this.timers.set(id, setTimeout(() => {
      this.timers.delete(id);
      fn();
    }, ms));
  }
}
