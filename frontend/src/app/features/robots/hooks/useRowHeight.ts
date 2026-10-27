import { useEffect, useState } from 'react';
import { DESKTOP_ROW, MOBILE_QUERY, MOBILE_ROW } from '../../../core/config/constants';

/** Fixed row height per layout: desktop table rows, or stacked cards on phones. */
export function useRowHeight(): number {
  const query = typeof window !== 'undefined' ? window.matchMedia(MOBILE_QUERY) : null;
  const [mobile, setMobile] = useState(() => query?.matches ?? false);
  useEffect(() => {
    if (!query) return;
    const onChange = () => setMobile(query.matches);
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, [query]);
  return mobile ? MOBILE_ROW : DESKTOP_ROW;
}
