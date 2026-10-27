import { useCallback } from 'react';
import { errorMessage } from '../core/http/api-error';
import { postCommand } from '../core/api/commands-api';
import type { Command } from '../shared/models/command';
import type { RobotStore } from '../core/store/robot-store';

/**
 * REST command with a pending hint on the row. Errors are already normalized
 * (and a 401 already handled) by the HTTP interceptors.
 */
export function useCommandSender(store: RobotStore): (id: string, cmd: Command) => void {
  return useCallback((id: string, cmd: Command) => {
    store.beginCommand(id, cmd);
    postCommand(id, cmd)
      .then(() => store.commandPublished(id))
      .catch((err: unknown) => store.commandFailed(id, errorMessage(err)));
  }, [store]);
}
