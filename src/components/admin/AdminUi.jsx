import { CircleCheck, CircleDashed, TriangleAlert } from 'lucide-react';
import { Card } from '../ui/Card.jsx';
import InfoTooltip from '../ui/InfoTooltip.jsx';
import { ROLE_LABEL } from '../../services/adminService.js';

// The administrator sees an aggregate state, never a score. Colour is always
// paired with the text label, matching the sentiment palette rules.
const ALERT_TONE = {
  'Requires Attention': { tone: 'bg-negative-soft text-negative-ink', icon: TriangleAlert },
  Normal: { tone: 'bg-positive-soft text-positive-ink', icon: CircleCheck },
  'Insufficient data': { tone: 'bg-slate-100 text-slate-600', icon: CircleDashed },
};

export function AlertBadge({ alert }) {
  const { tone, icon: Icon } = ALERT_TONE[alert.status] || ALERT_TONE['Insufficient data'];
  return (
    <span className={`mi-badge-pill ${tone}`}>
      <Icon className="size-3.5" aria-hidden />
      {alert.status}
    </span>
  );
}

const STATE_TONE = {
  Open: 'bg-positive-soft text-positive-ink',
  Upcoming: 'bg-neutral-soft text-neutral-ink',
  Closed: 'bg-slate-100 text-slate-600',
  'Not scheduled': 'bg-slate-100 text-slate-600',
};

export function StateBadge({ state }) {
  return <span className={`mi-badge-pill ${STATE_TONE[state] || STATE_TONE.Closed}`}>{state}</span>;
}

const ROLE_TONE = {
  student: 'bg-brand-50 text-brand-700',
  staff: 'bg-neutral-soft text-neutral-ink',
  admin: 'bg-navy-900 text-white',
};

export function RoleBadge({ role }) {
  return <span className={`mi-badge-pill ${ROLE_TONE[role] || ROLE_TONE.student}`}>{ROLE_LABEL[role] || role}</span>;
}

export function MetricTile({ label, value, hint, tooltip, tone = 'text-slate-900' }) {
  return (
    <Card className="p-6">
      <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-500">
        {label}
        {tooltip && <InfoTooltip text={tooltip} />}
      </h3>
      <p className={`mt-2 text-3xl font-semibold ${tone}`}>{value}</p>
      {hint && <p className="mi-muted mt-1">{hint}</p>}
    </Card>
  );
}

// Inline result banner for an administrator action, reusing the mi-error panel
// for failures so every page reports problems the same way.
export function ActionNotice({ error, notice }) {
  if (error) return <p role="alert" className="mi-error">{error}</p>;
  if (notice) return <p role="status" className="mb-4 rounded-lg bg-positive-soft px-4 py-3 text-sm text-positive-ink">{notice}</p>;
  return null;
}
