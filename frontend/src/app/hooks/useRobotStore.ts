import { useEffect, useMemo } from 'react';
import { RobotStore } from '../core/store/robot-store';

/** One store per dashboard mount, disposed on unmount. */
export function useRobotStore(): RobotStore {
  const store = useMemo(() => new RobotStore(), []);
  useEffect(() => () => store.dispose(), [store]);
  return store;
}
