import type { Pending } from '../../../shared/models/pending-command';

export function pendingText(p: Pending): string {
  if (p.phase === 'failed' || p.phase === 'unconfirmed') return p.message ?? 'Failed';
  const what = p.cmd.cmd === 'set_mode' ? `mode ${p.cmd.value}` : p.cmd.cmd === 'kick' ? 'kick' : 'charge toggle';
  return p.phase === 'sending' ? `Sending ${what}` : `Waiting for robot: ${what}`;
}

export function timeOf(ts: string): string {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? '-' : d.toLocaleTimeString([], { hour12: false });
}
