import { SENTIMENT_META } from '../../utils/constants.js';

// Shared tooltip for the weekly charts.
export default function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const total = payload.reduce((sum, p) => sum + (p.value || 0), 0);
  return (
    <div className="rounded-lg bg-white px-3 py-2 text-xs shadow-lg ring-1 ring-slate-200">
      <p className="mb-1 font-semibold text-slate-900">{String(label).replace('W', 'Week ')}</p>
      {payload.map((p) => (
        <p key={p.dataKey} className="flex items-center justify-between gap-4 text-slate-600">
          <span className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full" style={{ background: p.color }} aria-hidden />
            {SENTIMENT_META[p.dataKey]?.label ?? p.name}
          </span>
          <span className="font-medium text-slate-900">{p.value ?? 0}</span>
        </p>
      ))}
      {payload.length > 1 && (
        <p className="mt-1 flex justify-between border-t border-slate-100 pt-1 font-medium text-slate-900">
          <span>Total</span>
          <span>{total}</span>
        </p>
      )}
    </div>
  );
}
