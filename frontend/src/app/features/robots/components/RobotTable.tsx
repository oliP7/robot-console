import { useEffect } from 'react';
import type { Command } from '../../../shared/models/command';
import { useIds } from '../../../core/store/hooks/useIds';
import { useStore } from '../../../core/store/hooks/useStore';
import { useTotal } from '../../../core/store/hooks/useTotal';
import { useRowHeight } from '../hooks/useRowHeight';
import { useVirtualWindow } from '../hooks/useVirtualWindow';
import { RobotRow } from './RobotRow';
import { RobotTableHeader } from './RobotTableHeader';

/**
 * Virtualized table: only the rows in (or near) the viewport are mounted,
 * and only those ids are watched on the server.
 */
export function RobotTable({ onCommand }: { onCommand: (id: string, cmd: Command) => void }) {
  const store = useStore();
  const ids = useIds();
  const total = useTotal();
  const rowH = useRowHeight();
  const { viewportRef, onScroll, start, end } = useVirtualWindow(ids.length, rowH);

  // Tell the store (and through it the server) which robots are on screen.
  useEffect(() => {
    store.setView(ids.slice(start, end));
  }, [store, ids, start, end]);

  const rows = [];
  for (let i = start; i < end; i++) {
    const id = ids[i] as string;
    rows.push(<RobotRow key={id} id={id} index={i} top={i * rowH} height={rowH} onCommand={onCommand} />);
  }

  return (
    <div className="table" role="table" aria-label="Robots" aria-rowcount={ids.length + 1}>
      <RobotTableHeader />
      <div className="viewport" ref={viewportRef} onScroll={onScroll} role="rowgroup" tabIndex={0}>
        {ids.length === 0 ? (
          <p className="empty">{total === 0 ? 'Waiting for robots to report.' : 'No robot id matches the search.'}</p>
        ) : (
          <div className="spacer" style={{ height: ids.length * rowH }}>{rows}</div>
        )}
      </div>
    </div>
  );
}
