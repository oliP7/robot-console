import { useState } from 'react';
import { useIds } from '../../../core/store/hooks/useIds';
import { useStore } from '../../../core/store/hooks/useStore';
import { useTotal } from '../../../core/store/hooks/useTotal';

export function SearchToolbar() {
  const store = useStore();
  const shown = useIds().length;
  const total = useTotal();
  const [q, setQ] = useState(store.getFilter());
  return (
    <div className="toolbar">
      <label className="search">
        <span className="sr-only">Search robots by id</span>
        <input type="search" placeholder="Search by robot id" value={q} spellCheck={false}
               onChange={(e) => { setQ(e.target.value); store.setFilter(e.target.value); }} />
      </label>
      <span className="count" aria-live="polite">
        {shown === total ? `${total.toLocaleString()} robots` : `${shown.toLocaleString()} of ${total.toLocaleString()}`}
      </span>
    </div>
  );
}
