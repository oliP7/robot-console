import { useState, type FormEvent } from 'react';
import { errorMessage } from '../../../core/http/api-error';
import { verifyToken } from '../../../core/api/auth-api';

export function TokenGate({ onToken, reason }: { onToken: (t: string) => void; reason?: string }) {
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(reason ?? null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const token = value.trim();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      if (await verifyToken(token)) onToken(token);
      else setError('That token was not accepted.');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="gate">
      <form className="gate-card" onSubmit={submit}>
        <h1>Robot Console</h1>
        <p>This console requires an access token.</p>
        <label htmlFor="token">Access token</label>
        <input id="token" type="password" autoComplete="current-password" value={value}
               onChange={(e) => setValue(e.target.value)} autoFocus />
        {error ? <p className="gate-error" role="alert">{error}</p> : null}
        <button className="btn btn-primary" type="submit" disabled={busy || !value.trim()}>
          {busy ? 'Checking' : 'Sign in'}
        </button>
      </form>
    </main>
  );
}
