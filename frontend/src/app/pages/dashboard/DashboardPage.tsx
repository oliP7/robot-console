import { AuthWatch } from '../../features/auth/components/AuthWatch';
import { RobotTable } from '../../features/robots/components/RobotTable';
import { SearchToolbar } from '../../features/robots/components/SearchToolbar';
import { SummaryBar } from '../../features/summary/components/SummaryBar';
import { AppHeader } from '../../layout/AppHeader';
import { useCommandSender } from '../../hooks/useCommandSender';
import { useRobotStore } from '../../hooks/useRobotStore';
import { useLiveConnection } from '../../hooks/useLiveConnection';
import { StoreProvider } from '../../providers/StoreProvider';

export interface DashboardPageProps {
  token: string | null;
  onUnauthorized: (reason?: string) => void;
}

/** Composition only: wires the store, the live link and the command path to the features. */
export function DashboardPage({ token, onUnauthorized }: DashboardPageProps) {
  const store = useRobotStore();
  useLiveConnection(store, token);
  const onCommand = useCommandSender(store);

  return (
    <StoreProvider store={store}>
      <AuthWatch onUnauthorized={onUnauthorized} />
      <div className="app">
        <AppHeader />
        <SummaryBar />
        <SearchToolbar />
        <RobotTable onCommand={onCommand} />
      </div>
    </StoreProvider>
  );
}
