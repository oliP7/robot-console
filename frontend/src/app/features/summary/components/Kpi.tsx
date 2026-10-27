export function Kpi({ value, label, warn = false, meta = false }:
  { value: string | number; label: string; warn?: boolean; meta?: boolean }) {
  return (
    <div className={`kpi${meta ? ' kpi-meta' : ''}`}>
      <span className={`kpi-num${warn ? ' warn' : ''}`}>{value}</span>
      <span className="kpi-label">{label}</span>
    </div>
  );
}
