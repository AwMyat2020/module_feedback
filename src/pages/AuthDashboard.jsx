import { useAuth } from '../auth/useAuth.js';
import { useCoreData, dateLabel } from '../services/coreService.js';
import PageHeader from '../components/layout/PageHeader.jsx';
import { Card } from '../components/ui/Card.jsx';
import Button from '../components/ui/Button.jsx';

export default function AuthDashboard() {
  const { user, error: sessionError } = useAuth();
  const { data, error, refresh } = useCoreData(`/api/${user.role}/dashboard`);
  return <>
    <PageHeader title={user.role === 'staff' ? 'Staff Dashboard' : 'Student Dashboard'} subtitle={`Welcome, ${user.name}`} actions={<Button variant="secondary" onClick={refresh}>Refresh</Button>} />
    {(error || sessionError) && <p role="alert" className="mi-error">{error || sessionError}</p>}
    {!data && !error && <p role="status">Loading your modules…</p>}
    {data && <>
      <p className="mi-term">{data.trimester?.name || 'No current trimester configured'}</p>
      <p className="mi-muted mb-6">{user.role === 'student' ? 'Your enrolled modules and feedback periods.' : 'Your teaching modules. Student identity is excluded from staff feedback responses.'}</p>
      {data.modules.length === 0 && <Card className="p-6"><h2 className="font-semibold">No assigned modules</h2><p className="mi-muted mt-2">Your account is ready. Modules must be assigned by the local project administrator.</p></Card>}
      <div className="mi-module-grid">{data.modules.map(module => <Card key={module.id} className="p-6">
        <div className="mi-card-top"><span>{module.code}</span><span className="mi-status">{module.status || module.period_state}</span></div>
        <h2 className="text-xl font-semibold mt-4 mb-2">{module.name}</h2>
        <p className="mi-muted">{module.lecturers.join(', ') || 'Lecturer not assigned'}</p>
        <dl className="mi-dates"><div><dt>Trimester</dt><dd>{module.trimester}</dd></div><div><dt>Feedback opens</dt><dd>{dateLabel(module.opens_at)}</dd></div><div><dt>Deadline</dt><dd>{dateLabel(module.deadline)}</dd></div></dl>
        <p className="mi-muted mb-4">Period: {module.period_state}</p>
        <Button to={`/${user.role}/periods/${module.id}`} variant="subtle">{user.role === 'staff' ? 'View analytics' : module.feedback ? 'View your feedback' : 'Open module'}</Button>
      </Card>)}</div>
    </>}
  </>;
}
