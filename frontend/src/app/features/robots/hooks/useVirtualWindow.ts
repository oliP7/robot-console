import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from 'react';
import { OVERSCAN } from '../../../core/config/constants';

export interface VirtualWindow {
  viewportRef: RefObject<HTMLDivElement | null>;
  onScroll: () => void;
  /** first row to mount (inclusive) */
  start: number;
  /** last row to mount (exclusive) */
  end: number;
}

/**
 * Hand-rolled windowing over fixed-height rows: only the rows in (or near) the
 * viewport are mounted. Cost per frame is O(visible rows), independent of count.
 */
export function useVirtualWindow(count: number, rowHeight: number, overscan = OVERSCAN): VirtualWindow {
  const viewportRef = useRef<HTMLDivElement>(null);
  const frame = useRef(0);
  const [scrollTop, setScrollTop] = useState(0);
  const [height, setHeight] = useState(600);

  useLayoutEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    setHeight(el.clientHeight);
    const ro = new ResizeObserver(() => setHeight(el.clientHeight));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => () => cancelAnimationFrame(frame.current), []);

  // At most one state update per animation frame while scrolling.
  const onScroll = () => {
    if (frame.current) return;
    frame.current = requestAnimationFrame(() => {
      frame.current = 0;
      if (viewportRef.current) setScrollTop(viewportRef.current.scrollTop);
    });
  };

  const start = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
  const end = Math.min(count, Math.ceil((scrollTop + height) / rowHeight) + overscan);
  return { viewportRef, onScroll, start, end };
}
