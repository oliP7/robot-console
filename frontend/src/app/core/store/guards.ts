import { MAX_INDEX } from '../config/constants';
import type { Robot } from '../../shared/models/robot';

// Frames come from the network: validate shape before trusting them.

export function isRobot(x: unknown): x is Robot {
  if (typeof x !== 'object' || x === null) return false;
  const r = x as Record<string, unknown>;
  return typeof r.id === 'string' && typeof r.battery === 'number' && typeof r.charge === 'string'
    && typeof r.mode === 'string' && typeof r.online === 'boolean';
}

export const isStringArray = (x: unknown): x is string[] =>
  Array.isArray(x) && x.length <= MAX_INDEX && x.every((v) => typeof v === 'string');
