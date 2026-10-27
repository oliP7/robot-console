import { createContext } from 'react';
import type { RobotStore } from '../robot-store';

export const StoreContext = createContext<RobotStore | null>(null);
