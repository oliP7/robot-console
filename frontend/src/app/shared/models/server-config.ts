import type { Mode } from './robot';

/** GET /api/config */
export interface ServerConfig {
  auth_required: boolean;
  modes: Mode[];
  max_watch: number;
  flush_ms: number;
}
