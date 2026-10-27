import { useCallback, useSyncExternalStore } from 'react';
import type { RowSnapshot } from '../../../shared/models/row-snapshot';
import { useStore } from './useStore';

export function useRow(id: string): RowSnapshot {
  const store = useStore();
  // Stable callbacks, or React would resubscribe on every render.
  const subscribe = useCallback((cb: () => void) => store.subscribeRow(id, cb), [store, id]);
  const snapshot = useCallback(() => store.getRow(id), [store, id]);
  return useSyncExternalStore(subscribe, snapshot);
}
