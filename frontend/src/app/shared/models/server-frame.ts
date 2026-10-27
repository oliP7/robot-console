import type { Mode, Robot } from './robot';
import type { Summary } from './summary';

// Index ops are idempotent set operations: an "add" for a known id or an "rm"
// for an unknown id is legal and must be a no-op.
export type ServerFrame =
  | { t: 'hello'; modes: Mode[]; max_watch: number }
  | { t: 'index'; full: true; ids: string[] }
  | { t: 'index'; full?: false; add: string[]; rm: string[] }
  | { t: 'delta'; robots: Robot[] }
  | ({ t: 'summary' } & Summary);
