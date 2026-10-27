import { ConnectionBadge } from '../features/connection/components/ConnectionBadge';

export function AppHeader() {
  return (
    <header className="top">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true" />
        <h1>Robot Console</h1>
      </div>
      <ConnectionBadge />
    </header>
  );
}
