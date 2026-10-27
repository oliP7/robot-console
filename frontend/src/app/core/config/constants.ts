import type { BackoffOptions } from '../../shared/models/backoff-options';

// ---- HTTP -------------------------------------------------------------------
export const REQUEST_TIMEOUT_MS = 8000;
/** Ceiling for the boot-time /api/config retry (exponential from 1 s). */
export const CONFIG_RETRY_MAX_MS = 10_000;

// ---- session ----------------------------------------------------------------
export const TOKEN_STORAGE_KEY = 'robot-console-token';

// ---- live connection --------------------------------------------------------
export const DEFAULT_BACKOFF: BackoffOptions = { baseMs: 500, capMs: 15_000, minMs: 250 };
/** No frame for this long means the link is dead even if TCP says otherwise. */
export const STALE_MS = 5000;
/** Delay before telling the server about a new viewport (scroll debounce). */
export const VIEW_DEBOUNCE_MS = 40;
/** WebSocket close code the server uses for a rejected token. */
export const CLOSE_UNAUTHORIZED = 4401;
export const MAX_FRAME_CHARS = 8 * 1024 * 1024;

// ---- store ------------------------------------------------------------------
/** How long to wait for the robot to report the change. */
export const CONFIRM_TIMEOUT_MS = 6000;
/** How long a failure message stays on the row. */
export const MESSAGE_MS = 4000;
/** Upper bound on index size accepted from the server. */
export const MAX_INDEX = 500_000;

// ---- robot table ------------------------------------------------------------
export const DESKTOP_ROW = 56;
export const MOBILE_ROW = 156;
export const MOBILE_QUERY = '(max-width: 760px)';
export const OVERSCAN = 6;
