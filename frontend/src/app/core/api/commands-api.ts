import type { Command } from '../../shared/models/command';
import { api } from '../http/client';

/** What each status means for a command, as the backend documents it. */
const COMMAND_MESSAGES: Readonly<Record<number, string>> = {
  404: 'Unknown robot.',
  409: 'Robot is offline.',
  422: 'Command rejected as invalid.',
  429: 'Too many commands. Try again in a moment.',
  503: 'Broker unavailable. Command not sent.',
};

/** Resolves when the broker accepted the command (HTTP 202). Not when the robot executed it. */
export async function postCommand(robotId: string, cmd: Command): Promise<void> {
  await api.http.send(`/api/robots/${encodeURIComponent(robotId)}/commands`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cmd),
  }, { expect: 202, messages: COMMAND_MESSAGES });
}
