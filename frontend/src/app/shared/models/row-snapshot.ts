import type { Pending } from './pending-command';
import type { Robot } from './robot';

export interface RowSnapshot {
  robot?: Robot;
  pending?: Pending;
}
