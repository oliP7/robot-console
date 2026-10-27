import { SEGMENTS, type SegmentCounts } from '../utils/segments';

export function ModeLegend({ counts }: { counts: SegmentCounts }) {
  return (
    <ul className="legend">
      {SEGMENTS.map((g) => (
        <li key={g.key}>
          <span className={`swatch seg-${g.key}`} aria-hidden="true" />
          {g.label} <b>{counts[g.key].toLocaleString()}</b>
        </li>
      ))}
    </ul>
  );
}
