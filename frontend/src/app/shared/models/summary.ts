import type { Mode } from './robot';

export interface Summary {
  total: number;
  online: number;
  offline: number;
  modes: Record<Mode, number>;
  charging: number;
  discharging: number;
  avg_battery: number | null;
  low_battery: number;
  ingest_per_s: number;
  lag_ms: number;
  clients: number;
  server_ts: number;
}
