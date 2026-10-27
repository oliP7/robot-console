import type { Mode } from './robot';

export type Command =
  | { cmd: 'toggle_charge' }
  | { cmd: 'kick' }
  | { cmd: 'set_mode'; value: Mode };
