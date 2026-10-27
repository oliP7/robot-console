import type { ServerConfig } from '../../shared/models/server-config';
import { api } from '../http/client';

export function fetchConfig(): Promise<ServerConfig> {
  return api.http.json<ServerConfig>('/api/config');
}
