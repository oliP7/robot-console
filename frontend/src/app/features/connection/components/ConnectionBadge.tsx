import { useStatus } from '../../../core/store/hooks/useStatus';
import { useSecondsUntil } from '../hooks/useSecondsUntil';

const LABEL = {
  connecting: 'Connecting',
  live: 'Live',
  stale: 'Stale',
  reconnecting: 'Reconnecting',
  unauthorized: 'Signed out',
} as const;

export function ConnectionBadge() {
  const status = useStatus();
  // Ticks once a second only while a reconnect countdown is visible.
  const secs = useSecondsUntil(status.state === 'reconnecting' ? status.retryAt : undefined);
  return (
    <span className={`conn conn-${status.state}`} role="status" aria-live="polite">
      <span className="conn-dot" aria-hidden="true" />
      {LABEL[status.state]}
      {status.state === 'reconnecting' && secs > 0 ? ` in ${secs}s` : ''}
    </span>
  );
}
