export type ConnState = 'connecting' | 'live' | 'stale' | 'reconnecting' | 'unauthorized';

export interface ConnStatus {
  state: ConnState;
  /** epoch ms of the next reconnect attempt, when state is "reconnecting" */
  retryAt?: number;
}
