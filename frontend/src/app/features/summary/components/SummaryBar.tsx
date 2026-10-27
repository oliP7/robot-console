import { useStatus } from '../../../core/store/hooks/useStatus';
import { useSummary } from '../../../core/store/hooks/useSummary';
import { segmentCounts } from '../utils/segments';
import { Kpi } from './Kpi';
import { ModeLegend } from './ModeLegend';
import { ModeStack } from './ModeStack';

export function SummaryBar() {
  const s = useSummary();
  const live = useStatus().state === 'live';
  const counts = segmentCounts(s);
  const total = s?.total ?? 0;
  return (
    <section className={`summary${live ? '' : ' is-stale'}`} aria-label="Robot summary">
      <div className="summary-head">
        <Kpi value={total.toLocaleString()} label="robots" />
        <Kpi value={(s?.online ?? 0).toLocaleString()} label="online" />
        <Kpi value={s?.avg_battery != null ? `${s.avg_battery.toFixed(1)}%` : '-'} label="avg battery" />
        <Kpi value={s?.low_battery ?? 0} label="below 20%" warn={(s?.low_battery ?? 0) > 0} />
        <Kpi value={`${(s?.ingest_per_s ?? 0).toLocaleString()}/s`} label="telemetry in" meta />
      </div>
      <ModeStack counts={counts} total={total} />
      <ModeLegend counts={counts} />
    </section>
  );
}
