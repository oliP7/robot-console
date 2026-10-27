// Wire protocol, mirrored from the backend.

export const MODES = ['idle', 'working', 'error'] as const;
export type Mode = (typeof MODES)[number];
export type Charge = 'charging' | 'discharging';

export interface Robot {
  id: string;
  battery: number;
  charge: Charge;
  mode: Mode;
  online: boolean;
  ts: string;
}
