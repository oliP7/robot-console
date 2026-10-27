import { useContext } from 'react';
import type { RobotStore } from '../robot-store';
import { StoreContext } from './store-context';

export function useStore(): RobotStore {
  const store = useContext(StoreContext);
  if (!store) throw new Error('StoreContext missing');
  return store;
}
