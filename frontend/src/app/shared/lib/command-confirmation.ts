import type { Command } from '../models/command';
import type { Robot } from '../models/robot';

/**
 * Did this telemetry confirm the command? robot.py has no acknowledgement
 * channel and does not echo a command id, so confirmation is inferred from the
 * state the robot itself reports. The UI never applies the change on its own.
 *
 * `before` is the last state this client saw when the command was issued.
 */
export function confirms(cmd: Command, before: Robot | undefined, now: Robot): boolean {
  switch (cmd.cmd) {
    case 'set_mode':
      return now.mode === cmd.value;
    case 'toggle_charge':
      return before === undefined || now.charge !== before.charge;
    case 'kick':
      // kick adds +5. Charging drift is at most +1.2 per tick, so require +4
      // (a capped battery at 100 also counts).
      return before === undefined || now.battery >= Math.min(100, before.battery + 4);
  }
}

/** A command that cannot change anything is not offered (no confirmation would come). */
export function isNoop(cmd: Command, robot: Robot | undefined): boolean {
  if (!robot) return false;
  if (cmd.cmd === 'set_mode') return robot.mode === cmd.value;
  if (cmd.cmd === 'kick') return robot.battery >= 100;
  return false;
}
