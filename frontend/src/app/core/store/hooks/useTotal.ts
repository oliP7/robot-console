import { useSyncExternalStore } from 'react';
import { useStore } from './useStore';

export function useTotal(): number {
  const store = useStore();
  return useSyncExternalStore(store.subIndex, store.getTotal);
}
