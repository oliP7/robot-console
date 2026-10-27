import { useEffect } from 'react';
import { LiveConnection } from '../core/realtime/live-connection';
import { liveUrl } from '../core/realtime/live-url';
import type { RobotStore } from '../core/store/robot-store';

/** Keeps the live WebSocket open for the lifetime of the component. */
export function useLiveConnection(store: RobotStore, token: string | null): void {
  useEffect(() => {
    const conn = new LiveConnection({ url: liveUrl(), store, token });
    conn.start();
    return () => conn.stop();
  }, [store, token]);
}
