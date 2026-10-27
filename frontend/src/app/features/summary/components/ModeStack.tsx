import { SEGMENTS, type SegmentCounts } from '../utils/segments';

/** Stacked bar: working / idle / error / offline, proportional to the counts. */
export function ModeStack({ counts, total }: { counts: SegmentCounts; total: number }) {
  return (
    <div className="stack" role="img"
         aria-label={SEGMENTS.map((g) => `${g.label} ${counts[g.key]}`).join(', ')}>
      {total === 0 ? <div className="stack-empty" /> : SEGMENTS.map((g) =>
        counts[g.key] > 0 ? (
          <div key={g.key} className={`stack-seg seg-${g.key}`}
               style={{ flexGrow: counts[g.key] }} title={`${g.label}: ${counts[g.key]}`} />
        ) : null)}
    </div>
  );
}
