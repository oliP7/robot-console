import { memo } from 'react';

const level = (pct: number) => (pct < 20 ? 'low' : pct < 50 ? 'mid' : 'high');

export const BatteryGauge = memo(function BatteryGauge({ pct, charging }: { pct: number; charging: boolean }) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <div className="battery" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={clamped}
         aria-label={`Battery ${clamped.toFixed(1)} percent${charging ? ', charging' : ''}`}>
      <div className="battery-shell">
        <div className={`battery-fill ${level(clamped)}`} style={{ width: `${clamped}%` }} />
      </div>
      <span className="battery-num">{clamped.toFixed(1)}%</span>
    </div>
  );
});
