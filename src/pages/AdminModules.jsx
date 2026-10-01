import { useCallback, useEffect, useState } from 'react';
import { Archive, ArchiveRestore, CalendarClock, Plus, RefreshCw, UserMinus, UserPlus, Users } from 'lucide-react';
import { useCoreData, dateLabel } from '../services/coreService.js';
import { useAdminAction, modulePath, rateLabel } from '../services/adminService.js';
import { authRequest } from '../services/authService.js';
import PageHeader from '../components/layout/PageHeader.jsx';
import { Card, CardHeader } from '../components/ui/Card.jsx';
import Button from '../components/ui/Button.jsx';
import Modal from '../components/ui/Modal.jsx';
import { EmptyState } from '../components/ui/States.jsx';
import { ActionNotice, RoleBadge, StateBadge } from '../components/admin/AdminUi.jsx';

const EXTENSIONS = [1, 3, 7, 14];

function CreateModule({ onCreated }) {
  const action = useAdminAction(onCreated);
  const [form, setForm] = useState({ code: '', name: '' });
  const set = (key, value) => setForm(old => ({ ...old, [key]: value }));
  return <Card className="mb-6">
    <CardHeader title="Create a module" description="The module opens today with a two-week feedback period in the active trimester."
      tooltip="Codes follow the INF2006 shape: two to six letters followed by three to six digits. A new module has no roster until you assign people." />
    <form className="px-5 py-4" onSubmit={async event => {
      event.preventDefault();
      if (await action.run('create', '/api/admin/modules', { code: form.code.trim(), name: form.name.trim() })) {
        setForm({ code: '', name: '' });
      }
    }}>
      <ActionNotice error={action.error} notice={action.notice} />
      <div className="mi-admin-form">
        <label htmlFor="code">Module code
          <input id="code" value={form.code} onChange={event => set('code', event.target.value)}
            placeholder="INF2006" required minLength={2} maxLength={16}
            className="w-full rounded-md border border-slate-300 bg-white p-3" />
        </label>
        <label htmlFor="name">Module name
          <input id="name" value={form.name} onChange={event => set('name', event.target.value)}
            placeholder="Cloud Computing and Big Data" required minLength={2} maxLength={120}
            className="w-full rounded-md border border-slate-300 bg-white p-3" />
        </label>
        <Button type="submit" icon={Plus} loading={action.pending === 'create'}>Create module</Button>
      </div>
    </form>
  </Card>;
}

// The roster lives in a modal: a cohort of fifty would otherwise stretch one
// card and break the surrounding grid.
function RosterModal({ module, open, onClose, onChange }) {
  const [roster, setRoster] = useState(null);
  const [email, setEmail] = useState('');
  const moduleId = module.module_id;

  const load = useCallback(async () => {
    try { setRoster((await authRequest(modulePath(moduleId, 'roster'))).roster); }
    catch { setRoster([]); }
  }, [moduleId]);
  const reload = useCallback(() => { load(); onChange(); }, [load, onChange]);
  const action = useAdminAction(reload);

  useEffect(() => { if (open) load(); }, [open, load]);

  const students = roster?.filter(person => person.role === 'student').length ?? 0;
  const staff = roster?.filter(person => person.role === 'staff').length ?? 0;

  return <Modal open={open} onClose={onClose}
    title={`Roster · ${module.code}`}
    description={roster ? `${students} student${students === 1 ? '' : 's'} and ${staff} lecturer${staff === 1 ? '' : 's'} assigned` : module.name}
    footer={<p className="mi-muted">Removing somebody withdraws the assignment only. Any feedback they already submitted stays in the record and stays anonymous.</p>}>
    <ActionNotice error={action.error} notice={action.notice} />
    <form className="mi-admin-form" onSubmit={async event => {
      event.preventDefault();
      if (await action.run('add', modulePath(moduleId, 'roster'), { email: email.trim(), action: 'add' })) setEmail('');
    }}>
      <label htmlFor={`assign-${moduleId}`}>Assign by email
        <input id={`assign-${moduleId}`} type="email" value={email} onChange={event => setEmail(event.target.value)}
          placeholder="name@sit.singaporetech.edu.sg" required
          className="w-full rounded-md border border-slate-300 bg-white p-3" />
      </label>
      <Button type="submit" variant="secondary" icon={UserPlus} loading={action.pending === 'add'}>Assign</Button>
    </form>
    <p className="mi-muted mt-2">The account must already be registered. Its role decides whether it joins as a student or a lecturer.</p>

    {roster === null && <p role="status" className="mt-4">Loading roster…</p>}
    {roster?.length === 0 && <p className="mi-muted mt-4">Nobody is assigned to {module.code} yet.</p>}
    {roster && roster.length > 0 && <div className="mt-4 max-h-[45vh] overflow-auto rounded-lg ring-1 ring-slate-200">
      {/* mi-analytics-table is unlayered CSS, so its margin beats a utility class. */}
      <table className="mi-analytics-table" style={{ marginTop: 0 }}>
        <caption className="sr-only">People assigned to {module.code}</caption>
        <thead className="sticky top-0 z-10"><tr>
          <th scope="col">Name</th><th scope="col">Email</th><th scope="col">Role</th><th scope="col">Action</th>
        </tr></thead>
        <tbody>{roster.map(person => <tr key={person.user_id}>
          <th scope="row">{person.name}</th>
          <td className="break-all">{person.email}</td>
          <td><RoleBadge role={person.role} /></td>
          <td><Button variant="ghost" size="sm" icon={UserMinus}
            loading={action.pending === person.user_id}
            onClick={() => action.run(person.user_id, modulePath(moduleId, 'roster'), { email: person.email, action: 'remove' })}>
            Remove
          </Button></td>
        </tr>)}</tbody>
      </table>
    </div>}
  </Modal>;
}

function ModuleCard({ module, onChange, onArchived }) {
  const action = useAdminAction(onChange);
  const [days, setDays] = useState(3);
  const [rosterOpen, setRosterOpen] = useState(false);

  async function toggleArchive() {
    const archived = !module.archived;
    const result = await action.run('archive', modulePath(module.module_id, 'archive'), { archived });
    // Keep a module on screen the moment it is archived, so the restore control
    // is where the administrator is already looking.
    if (result && archived) onArchived();
  }

  return <Card className={`p-6 transition-opacity ${module.archived ? 'bg-slate-50 opacity-75 hover:opacity-100 focus-within:opacity-100' : ''}`}>
    <div className="mi-card-top">
      <span>{module.code}</span>
      {module.archived
        ? <span className="mi-badge-pill bg-slate-200 text-slate-700">Archived</span>
        : <StateBadge state={module.period_state} />}
    </div>
    <h2 className="mt-4 mb-2 text-xl font-semibold">{module.name}</h2>
    <p className="mi-muted">{module.lecturers.join(', ') || 'Lecturer not assigned'}</p>
    {module.archived && <p className="mi-muted mt-2">Hidden from student and staff dashboards. Restore it to bring it back.</p>}

    <dl className="mi-dates">
      <div><dt>Enrolled students</dt><dd>{module.roster_size}</dd></div>
      <div><dt>Responses</dt><dd>{module.responses} ({rateLabel(module.response_rate)})</dd></div>
      <div><dt>Feedback opens</dt><dd>{module.opens_at ? dateLabel(module.opens_at) : 'Not scheduled'}</dd></div>
      <div><dt>Deadline</dt><dd>{module.deadline ? dateLabel(module.deadline) : 'Not scheduled'}</dd></div>
    </dl>

    <ActionNotice error={action.error} notice={action.notice} />

    {module.period_id && !module.archived && <div className="mi-admin-row">
      <label htmlFor={`days-${module.module_id}`} className="text-sm font-semibold">Extend deadline</label>
      <select id={`days-${module.module_id}`} value={days} onChange={event => setDays(Number(event.target.value))}
        className="rounded-md border border-slate-300 bg-white p-2 text-sm">
        {EXTENSIONS.map(value => <option key={value} value={value}>{value} day{value > 1 ? 's' : ''}</option>)}
      </select>
      <Button variant="subtle" size="sm" icon={CalendarClock}
        loading={action.pending === 'deadline'}
        onClick={() => action.run('deadline', modulePath(module.module_id, 'deadline'), { extend_days: days })}>
        Extend
      </Button>
    </div>}

    <div className="mi-actions">
      <Button variant="secondary" size="sm" icon={Users} onClick={() => setRosterOpen(true)}>Manage roster</Button>
      <Button variant={module.archived ? 'primary' : 'secondary'} size="sm"
        icon={module.archived ? ArchiveRestore : Archive}
        loading={action.pending === 'archive'} onClick={toggleArchive}>
        {module.archived ? 'Restore module' : 'Archive module'}
      </Button>
    </div>

    <RosterModal module={module} open={rosterOpen} onClose={() => setRosterOpen(false)} onChange={onChange} />
  </Card>;
}

export default function AdminModules() {
  const { data, error, refresh } = useCoreData('/api/admin/modules');
  const modules = data?.modules || [];
  const [showArchived, setShowArchived] = useState(false);
  const visible = showArchived ? modules : modules.filter(module => !module.archived);
  const archivedCount = modules.filter(module => module.archived).length;

  return <>
    <PageHeader title="Modules & Rosters" subtitle="Create modules, manage assignments and control feedback deadlines."
      breadcrumbs={[{ label: 'Administration', to: '/admin' }, { label: 'Modules & Rosters' }]}
      actions={<Button variant="secondary" icon={RefreshCw} onClick={refresh}>Refresh</Button>} />
    {error && <p role="alert" className="mi-error">{error}</p>}
    {!data && !error && <p role="status">Loading modules…</p>}

    {data && <>
      <p className="mi-term">{data.trimester?.name || 'No current trimester configured'}</p>
      <p className="mi-muted mb-6">Changes apply to the active trimester. Rosters show who is assigned, never who has responded.</p>

      <CreateModule onCreated={refresh} />

      {/* Always rendered, so archiving never looks like a one-way door. */}
      <label className="mi-admin-row mb-4 cursor-pointer text-sm font-medium text-slate-700">
        <input type="checkbox" checked={showArchived} onChange={event => setShowArchived(event.target.checked)}
          className="size-4 rounded border-slate-300 accent-brand-700" />
        Show archived modules
        <span className="mi-muted">({archivedCount} archived)</span>
      </label>

      {visible.length === 0
        ? <Card className="p-6"><EmptyState title={archivedCount && !showArchived ? 'No active modules' : 'No modules yet'}
            message={archivedCount && !showArchived
              ? `Every module is archived. Tick "Show archived modules" to restore one.`
              : 'Create the first module for this trimester using the form above.'} /></Card>
        : <div className="mi-module-grid">
          {visible.map(module => <ModuleCard key={module.module_id} module={module}
            onChange={refresh} onArchived={() => setShowArchived(true)} />)}
        </div>}
    </>}
  </>;
}
