import type { ReactNode } from 'react';
import type { RobotStore } from '../core/store/robot-store';
import { StoreContext } from '../core/store/hooks/store-context';

export function StoreProvider({ store, children }: { store: RobotStore; children: ReactNode }) {
  return <StoreContext.Provider value={store}>{children}</StoreContext.Provider>;
}
