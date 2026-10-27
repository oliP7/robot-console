import { MAX_FRAME_CHARS } from '../config/constants';
import type { ServerFrame } from '../../shared/models/server-frame';

/** Raw socket data to a frame, or null. A garbled frame is ignored rather than killing the session. */
export function parseFrame(data: unknown): ServerFrame | null {
  if (typeof data !== 'string' || data.length > MAX_FRAME_CHARS) return null;
  let frame: unknown;
  try {
    frame = JSON.parse(data);
  } catch {
    return null;
  }
  return typeof frame === 'object' && frame !== null ? (frame as ServerFrame) : null;
}
