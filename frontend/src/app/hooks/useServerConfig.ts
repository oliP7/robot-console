import { useEffect, useState } from 'react';
import { errorMessage } from '../core/http/api-error';
import { fetchConfig } from '../core/api/config-api';
import { CONFIG_RETRY_MAX_MS } from '../core/config/constants';
import type { ServerConfig } from '../shared/models/server-config';

/** Loads /api/config, retrying with exponential backoff until the server answers. */
export function useServerConfig(): { config: ServerConfig | null; error: string | null } {
  const [config, setConfig] = useState<ServerConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const load = (attempt: number) => {
      fetchConfig()
        .then((c) => !cancelled && (setConfig(c), setError(null)))
        .catch((err: unknown) => {
          if (cancelled) return;
          setError(errorMessage(err));
          timer = setTimeout(() => load(attempt + 1), Math.min(CONFIG_RETRY_MAX_MS, 1000 * 2 ** attempt));
        });
    };
    load(0);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  return { config, error };
}
