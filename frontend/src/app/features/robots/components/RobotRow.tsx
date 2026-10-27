import { memo } from 'react';
import { isNoop } from '../../../shared/lib/command-confirmation';
import type { Command } from '../../../shared/models/command';
import { useRow } from '../../../core/store/hooks/useRow';
import { timeOf } from '../utils/format';
import { BatteryGauge } from './BatteryGauge';
import { PendingStatus } from './PendingStatus';
import { RobotActions } from './RobotActions';

export interface RowProps {
  id: string;
  index: number;
  top: number;
  height: number;
  onCommand: (id: string, cmd: Command) => void;
}

/**
 * One row. Memoized and subscribed to its own robot only, so a telemetry
 * update re-renders exactly one row, and scrolling re-renders only new rows.
 */
export const RobotRow = memo(function RobotRow({ id, index, top, height, onCommand }: RowProps) {
  const { robot, pending } = useRow(id);
  const busy = pending?.phase === 'sending' || pending?.phase === 'awaiting';
  const disabled = !robot || !robot.online || busy;
  const send = (cmd: Command) => {
    if (!disabled && !isNoop(cmd, robot)) onCommand(id, cmd);
  };
  const online = robot?.online ?? false;

  return (
    <div className={`row${robot ? '' : ' is-loading'}${online ? '' : ' is-offline'}`} role="row"
         aria-rowindex={index + 2} style={{ transform: `translateY(${top}px)`, height }}>
      <div className="cell c-id" role="cell">
        <span className={`dot ${robot ? (online ? 'on' : 'off') : ''}`}
              aria-label={robot ? (online ? 'online' : 'offline') : 'loading'} />
        <span className="rid">{id}</span>
      </div>
      <div className="cell c-battery" role="cell">
        {robot ? <BatteryGauge pct={robot.battery} charging={robot.charge === 'charging'} /> : <span className="skeleton" />}
      </div>
      <div className="cell c-charge" role="cell">
        {robot ? (
          <span className={`chip charge-${robot.charge}`}>
            {robot.charge === 'charging' ? '↯ charging' : 'discharging'}
          </span>
        ) : <span className="skeleton short" />}
      </div>
      <div className="cell c-mode" role="cell">
        {robot ? <span className={`chip mode-${robot.mode}`}>{robot.mode}</span> : <span className="skeleton short" />}
      </div>
      <div className="cell c-seen" role="cell">{robot ? timeOf(robot.ts) : ''}</div>
      <div className="cell c-actions" role="cell">
        <RobotActions id={id} robot={robot} disabled={disabled} onSend={send} />
        {pending ? <PendingStatus pending={pending} /> : null}
      </div>
    </div>
  );
});
