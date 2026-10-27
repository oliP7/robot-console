import { useEffect } from 'react';
import { useStatus } from '../../../core/store/hooks/useStatus';

/** Signs out when the live channel rejects the token (WebSocket close 4401). */
export function AuthWatch({ onUnauthorized }: { onUnauthorized: (reason?: string) => void }) {
  const status = useStatus();
  useEffect(() => {
    if (status.state === 'unauthorized') onUnauthorized('The server rejected the token.');
  }, [status.state, onUnauthorized]);
  return null;
}
