import { useSyncExternalStore } from 'react';
import type { ConnStatus } from '../../../shared/models/connection-status';
import { useStore } from './useStore';

export function useStatus(): ConnStatus {
  const store = useStore();
  return useSyncExternalStore(store.subStatus, store.getStatus);
}
