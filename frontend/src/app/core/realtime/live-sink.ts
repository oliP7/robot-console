import type { ConnStatus } from '../../shared/models/connection-status';
import type { ServerFrame } from '../../shared/models/server-frame';

/**
 * What the connection needs from the app state. The connection depends on this
 * interface, not on RobotStore, so either side can change independently.
 */
export interface LiveSink {
  /** Called with a function that tells the server what we watch. */
  onViewChange(fn: ((ids: string[]) => void) | null): void;
  getWatch(): string[];
  getStatus(): ConnStatus;
  setStatus(status: ConnStatus): void;
  applyFrame(frame: ServerFrame): void;
}
