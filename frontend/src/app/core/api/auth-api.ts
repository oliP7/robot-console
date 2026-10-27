import { ApiError } from '../http/api-error';
import { api } from '../http/client';

/** Checks a candidate token without side effects: a 401 means "wrong token", not "sign out". */
export async function verifyToken(token: string): Promise<boolean> {
  try {
    await api.http.send('/api/robots?limit=1', { headers: { Authorization: `Bearer ${token}` } },
      { skipUnauthorizedHandler: true });
    return true;
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return false;
    throw err;
  }
}
