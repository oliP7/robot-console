import { useSyncExternalStore } from 'react';
import type { Summary } from '../../../shared/models/summary';
import { useStore } from './useStore';

export function useSummary(): Summary | null {
  const store = useStore();
  return useSyncExternalStore(store.subSummary, store.getSummary);
}
