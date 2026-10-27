import type { Command } from './command';
import type { Robot } from './robot';

export type PendingPhase = 'sending' | 'awaiting' | 'failed' | 'unconfirmed';

/** A command in flight. A UI hint only: it never changes the robot's state. */
export interface Pending {
  cmd: Command;
  phase: PendingPhase;
  /** the last state this client saw when the command was issued */
  before?: Robot;
  message?: string;
}
