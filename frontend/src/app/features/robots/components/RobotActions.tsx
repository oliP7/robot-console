import { type Command } from '../../../shared/models/command';
import { MODES, type Robot } from '../../../shared/models/robot';

export interface RobotActionsProps {
  id: string;
  robot: Robot | undefined;
  disabled: boolean;
  onSend: (cmd: Command) => void;
}

export function RobotActions({ id, robot, disabled, onSend }: RobotActionsProps) {
  return (
    <div className="actions">
      <button type="button" className="btn" disabled={disabled}
              onClick={() => onSend({ cmd: 'toggle_charge' })}
              aria-label={`Toggle charging for ${id}`}>
        {robot?.charge === 'charging' ? 'Stop charge' : 'Charge'}
      </button>
      <div className="seg" role="group" aria-label={`Set mode for ${id}`}>
        {MODES.map((m) => (
          <button key={m} type="button"
                  className={`seg-btn${robot?.mode === m ? ' is-active' : ''}`}
                  aria-pressed={robot?.mode === m}
                  disabled={disabled || robot?.mode === m}
                  onClick={() => onSend({ cmd: 'set_mode', value: m })}>
            {m}
          </button>
        ))}
      </div>
      <button type="button" className="btn btn-ghost"
              disabled={disabled || (robot?.battery ?? 0) >= 100}
              onClick={() => onSend({ cmd: 'kick' })}
              title="Battery +5%" aria-label={`Kick ${id}: battery plus 5 percent`}>
        Kick
      </button>
    </div>
  );
}
