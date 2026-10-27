import type { Summary } from '../../../shared/models/summary';

export const SEGMENTS = [
  { key: 'working', label: 'Working' },
  { key: 'idle', label: 'Idle' },
  { key: 'error', label: 'Error' },
  { key: 'offline', label: 'Offline' },
] as const;

export type SegmentKey = (typeof SEGMENTS)[number]['key'];
export type SegmentCounts = Record<SegmentKey, number>;

export function segmentCounts(s: Summary | null): SegmentCounts {
  return {
    working: s?.modes.working ?? 0,
    idle: s?.modes.idle ?? 0,
    error: s?.modes.error ?? 0,
    offline: s?.offline ?? 0,
  };
}
