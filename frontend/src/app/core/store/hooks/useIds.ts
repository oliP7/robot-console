import { useSyncExternalStore } from 'react';
import { useStore } from './useStore';

export function useIds(): string[] {
  const store = useStore();
  return useSyncExternalStore(store.subIndex, store.getIds);
}
