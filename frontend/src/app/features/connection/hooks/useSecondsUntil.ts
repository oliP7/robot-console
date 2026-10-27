import { useEffect, useState } from 'react';

/**
 * Whole seconds until `deadline` (epoch ms), refreshed once a second while a
 * deadline is set. The clock is read in effects, never during render, so
 * rendering stays pure.
 */
export function useSecondsUntil(deadline: number | undefined): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!deadline) return;
    const update = () => setNow(Date.now());
    const first = setTimeout(update, 0); // fresh clock for a new deadline
    const every = setInterval(update, 1000);
    return () => {
      clearTimeout(first);
      clearInterval(every);
    };
  }, [deadline]);
  return deadline ? Math.max(0, Math.ceil((deadline - now) / 1000)) : 0;
}
