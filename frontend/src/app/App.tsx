import { TokenGate } from './features/auth/components/TokenGate';
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { useServerConfig } from './hooks/useServerConfig';
import { useSession } from './hooks/useSession';

/** Boot (load /api/config) and the auth gate. Everything else lives in the pages. */
export function App() {
  const { config, error } = useServerConfig();
  const session = useSession();

  if (!config) {
    return <main className="boot">{error ? `${error} Retrying.` : 'Loading.'}</main>;
  }
  if (config.auth_required && !session.token) {
    return <TokenGate reason={session.reason} onToken={session.signIn} />;
  }
  const token = config.auth_required ? session.token : null;
  return <DashboardPage key={token ?? 'open'} token={token} onUnauthorized={session.signOut} />;
}
