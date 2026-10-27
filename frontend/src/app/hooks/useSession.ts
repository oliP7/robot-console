import { useCallback, useEffect, useState } from 'react';
import { onUnauthorized } from '../core/http/client';
import { tokenStorage } from '../core/auth/token-storage';

export interface Session {
  token: string | null;
  /** why the user was signed out, shown on the token gate */
  reason: string | undefined;
  signIn: (token: string) => void;
  signOut: (reason?: string) => void;
}

/**
 * The access token and the sign-in / sign-out transitions. Any HTTP 401 (via
 * the unauthorized interceptor) signs the user out, in one place.
 */
export function useSession(): Session {
  const [token, setToken] = useState<string | null>(() => tokenStorage.get());
  const [reason, setReason] = useState<string | undefined>();

  const signIn = useCallback((t: string) => {
    tokenStorage.set(t);
    setToken(t);
    setReason(undefined);
  }, []);

  const signOut = useCallback((why?: string) => {
    tokenStorage.set(null);
    setToken(null);
    setReason(why);
  }, []);

  useEffect(() => onUnauthorized(() => signOut('Your session expired.')), [signOut]);

  return { token, reason, signIn, signOut };
}
