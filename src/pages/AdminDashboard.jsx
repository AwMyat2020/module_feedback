import { useCallback, useState } from 'react';
import { Bell, RefreshCw, TriangleAlert } from 'lucide-react';
import { useAuth } from '../auth/useAuth.js';
import { useCoreData, dateLabel } from '../services/coreService.js';
import { useAdminAction, modulePath, rateLabel } from '../services/adminService.js';
import PageHeader from '../components/layout/PageHeader.jsx';
import { Card, CardHeader } from '../components/ui/Card.jsx';
import Button from '../components/ui/Button.jsx';
import { EmptyState } from '../components/ui/States.jsx';
import { ActionNotice, AlertBadge, MetricTile, StateBadge } from '../components/admin/AdminUi.jsx';

function TrimesterControl({ onChange }) {
  const { data, error, refresh } = useCoreData('/api/admin/trimesters');
  const reload = useCallback(() => { refresh(); onChange(); }, [refresh, onChange]);
  const action = useAdminAction(reload);
  const [selected, setSelected] = useState('');
  const [name, setName] = useState('');
  const current = data?.current_trimester;
  const choice = selected || current || '';
  return <Card>
    <CardHeader title="Active trimester" tooltip="Every student and staff dashboard reads from the active trimester. Changing it switches the whole application at once."
      description="Global toggle. Student and staff dashboards follow this setting immediately." />
    <div className="px-5 py-4">
      <ActionNotice error={action.error || error} notice={action.notice} />
      <div className="mi-admin-form">
        <label htmlFor="trimester">Trimester
          <select id="trimester" value={choice} onChange={event => setSelected(event.target.value)}
            className="w-full rounded-md border border-slate-300 bg-white p-3">
            {(data?.trimesters || []).map(term => <option key={term.id} value={term.id}>{term.name}</option>)}
          </select>
        </label>
        <Button onClick={() => action.run('activate', '/api/admin/trimester', { trimester_id: choice })}
          loading={action.pending === 'activate'} disabled={!choice || choice === current}>
          {choice && choice === current ? 'Already active' : 'Set as active'}
        </Button>
      </div>
      <form className="mi-admin-form mt-5 border-t border-slate-100 pt-5" onSubmit={async event => {
        event.preventDefault();
        if (await action.run('create', '/api/admin/trimesters', { name: name.trim() })) setName('');
      }}>
        <label htmlFor="trimester-name">Add a trimester
          <input id="trimester-name" value={name} onChange={event => setName(event.target.value)}
            placeholder="AY2027/28 · Trimester 1" minLength={2} maxLength={80} required
            className="w-full rounded-md border border-slate-300 bg-white p-3" />
        </label>
        <Button type="submit" variant="secondary" loading={action.pending === 'create'}>Create trimester</Button>
      </form>
    </div>
  </Card>;
}

export default function AdminDashboard() {
  const { user, error: sessionError } = useAuth();
  const { data, error, refresh } = useCoreData('/api/admin/overview');
  const action = useAdminAction(refresh);
  const summary = data?.summary;
  const live = (data?.modules || []).filter(module => !module.archived);
  const flagged = live.filter(module => module.alert.requires_attention);

  return <>
    <PageHeader title="Admin Dashboard" subtitle={`Welcome, ${user.name}`}
      breadcrumbs={[{ label: 'Administration' }, { label: 'Overview' }]}
      actions={<Button variant="secondary" icon={RefreshCw} onClick={refresh}>Refresh</Button>} />
    {(error || sessionError) && <p role="alert" className="mi-error">{error || sessionError}</p>}
    {!data && !error && <p role="status">Loading administration overview…</p>}

    <p className="mi-term">{data?.trimester?.name || 'No current trimester configured'}</p>
    <p className="mi-muted mb-6">
      Participation and module-level alerts only. Feedback text, individual sentiment scores and themes are never sent to this dashboard.
    </p>

    {data && <>
      <div className="mi-admin-grid">
        <MetricTile label="Active modules" value={summary.active_modules}
          hint={summary.archived_modules ? `${summary.archived_modules} archived` : 'None archived'} />
        <MetricTile label="Responses" value={summary.responses}
          hint={`of ${summary.expected_responses} enrolled students`} />
        <MetricTile label="Response rate" value={rateLabel(summary.response_rate)}
          tooltip="Submitted responses as a share of enrolled students across every active module in this trimester." />
        <MetricTile label="Requires attention" value={summary.modules_requiring_attention}
          tone={summary.modules_requiring_attention ? 'text-negative-ink' : 'text-slate-900'}
          tooltip="Modules where aggregate negative sentiment passed the alert threshold. The underlying scores and comments stay hidden." />
      </div>

      {flagged.length > 0 && <Card className="mb-6">
        <CardHeader title="AI anomaly alerts"
          description="Aggregate module-level warnings. No individual score, comment or theme is available here."
          tooltip="Raised only when a module passes the negative-sentiment threshold and has enough analysed responses that the flag cannot identify anyone." />
        <div className="divide-y divide-slate-100">
          {flagged.map(module => <div key={module.module_id} className="flex items-start gap-3 px-5 py-4">
            <span className="mt-0.5 rounded-full bg-negative-soft p-2 text-negative-ink"><TriangleAlert className="size-4" aria-hidden /></span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-900">{module.code} · {module.name}</p>
              <p className="mi-muted">{module.alert.explanation}</p>
            </div>
          </div>)}
        </div>
      </Card>}
    </>}

    {/* Outside the data guard: /api/admin/overview returns 409 when no trimester
        is set, and this control is the only way to fix that. */}
    <TrimesterControl onChange={refresh} />

    {data && <>
      <Card className="mt-6">
        <CardHeader title="Participation metrics" description="Response counts per module for the active trimester."
          tooltip="A reminder emails only the students who have not submitted. The list of recipients is resolved inside the database and is never shown to an administrator."
          actions={<Button variant="secondary" size="sm" icon={RefreshCw} onClick={refresh}>Refresh</Button>} />
        <div className="px-5 py-4">
          <ActionNotice error={action.error} notice={action.notice} />
          {live.length === 0
            ? <EmptyState title="No active modules" message="Create a module to start collecting feedback for this trimester."
                action={<Button to="/admin/modules">Manage modules</Button>} />
            : <div className="overflow-x-auto">
              <table className="mi-analytics-table">
                <caption className="sr-only">Response counts and aggregate alert state for each active module</caption>
                <thead><tr>
                  <th scope="col">Module</th><th scope="col">Period</th><th scope="col">Responses</th>
                  <th scope="col">Rate</th><th scope="col">Outstanding</th><th scope="col">Alert</th><th scope="col">Reminder</th>
                </tr></thead>
                <tbody>{live.map(module => <tr key={module.module_id}>
                  <th scope="row"><span className="block font-semibold">{module.code}</span><span className="mi-muted">{module.name}</span></th>
                  <td><StateBadge state={module.period_state} />
                    {module.deadline && <span className="mi-muted mt-1 block">Due {dateLabel(module.deadline)}</span>}</td>
                  <td>{module.responses} / {module.roster_size}</td>
                  <td>{rateLabel(module.response_rate)}</td>
                  <td>{module.outstanding}</td>
                  <td><AlertBadge alert={module.alert} /></td>
                  <td>
                    <Button variant="secondary" size="sm" icon={Bell}
                      disabled={module.period_state !== 'Open'}
                      loading={action.pending === module.module_id}
                      onClick={() => action.run(module.module_id, modulePath(module.module_id, 'reminders'))}>
                      Send reminder
                    </Button>
                    <span className="mi-muted mt-1 block">
                      {module.period_state !== 'Open' ? 'Period is not open'
                        : module.last_reminder ? `Last sent ${dateLabel(module.last_reminder)}` : 'Not sent yet'}
                    </span>
                  </td>
                </tr>)}</tbody>
              </table>
            </div>}
        </div>
      </Card>
    </>}
  </>;
}
