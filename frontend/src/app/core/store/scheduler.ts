/** Runs `flush` later. The store batches notifications through it. */
export type Scheduler = (flush: () => void) => void;

/** One flush per animation frame; a background tab does no rendering work at all. */
export const rafScheduler: Scheduler = (cb) => {
  if (typeof requestAnimationFrame === 'function') requestAnimationFrame(() => cb());
  else setTimeout(cb, 16);
};
