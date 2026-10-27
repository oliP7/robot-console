import type { Pending } from '../../../shared/models/pending-command';
import { pendingText } from '../utils/format';

/** The line under the actions while a command is in flight or just failed. */
export function PendingStatus({ pending }: { pending: Pending }) {
  const busy = pending.phase === 'sending' || pending.phase === 'awaiting';
  return (
    <div className={`pending phase-${pending.phase}`} role="status">
      {busy ? <span className="spinner" aria-hidden="true" /> : null}
      {pendingText(pending)}
    </div>
  );
}
