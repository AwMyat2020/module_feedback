import { lazy, Suspense, useState } from 'react';
import { useParams } from 'react-router';
import { useAuth } from '../auth/useAuth.js';
import { authRequest } from '../services/authService.js';
import { useCoreData, dateLabel } from '../services/coreService.js';
import PageHeader from '../components/layout/PageHeader.jsx';
import { Card } from '../components/ui/Card.jsx';
import Button from '../components/ui/Button.jsx';
const StaffAnalytics = lazy(() => import('./StaffAnalytics.jsx'));

function StudentFeedback({ module, refresh }) {
  const { expire } = useAuth();
  const [comment, setComment] = useState(module.feedback?.comment || '');
  const [rating, setRating] = useState(module.feedback?.rating ?? '');
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const feedback = module.feedback;
  async function mutate(action) {
    setBusy(true); setError('');
    try {
      const suffix = action === 'submit' ? '' : `/${feedback.id}/${action}`;
      await authRequest(`/api/student/periods/${module.id}/feedback${suffix}`, action === 'delete' ? {} : { comment, rating: rating === '' ? null : Number(rating) });
      refresh();
    } catch (e) { if (e.status === 401) expire(); else setError(e.message); }
    finally { setBusy(false); }
  }
  return <Card className="p-6">
    <h2 className="text-xl font-semibold mb-3">Your feedback</h2>
    {error && <p role="alert" className="mi-error">{error} Use Refresh above to check the latest state.</p>}
    {feedback && !editing && <><p className="mi-feedback-text">{feedback.comment}</p><p className="mi-muted mt-3">Rating: {feedback.rating ?? 'Not provided'}{feedback.rating !== null && ' / 5'}</p></>}
    {!module.can_write && <p role="status" className="mi-muted mt-4">{module.period_state === 'Upcoming' ? 'Feedback has not opened yet.' : feedback ? 'The deadline has passed. Your feedback is read-only.' : 'The deadline has passed. No feedback was submitted.'}</p>}
    {module.can_write && feedback && !editing && <div className="mi-actions"><Button onClick={() => setEditing(true)} disabled={busy}>Edit feedback</Button><Button variant="secondary" onClick={() => setConfirmDelete(true)} disabled={busy}>Delete feedback</Button></div>}
    {confirmDelete && <div className="mi-confirm" role="group" aria-label="Confirm deletion"><p>Delete your feedback? You can submit again before the deadline.</p><div className="mi-actions"><Button onClick={() => mutate('delete')} loading={busy}>Confirm delete</Button><Button variant="secondary" onClick={() => setConfirmDelete(false)} disabled={busy}>Keep feedback</Button></div></div>}
    {module.can_write && (!feedback || editing) && <form onSubmit={e => { e.preventDefault(); mutate(feedback ? 'edit' : 'submit'); }} className="mi-feedback-form">
      <p className="mi-muted">Staff see your comment and optional rating without your account details. Avoid including your name, student ID or other identifying details in your comment.</p>
      <label htmlFor="feedback-comment">Written feedback <span className="mi-muted">(required)</span></label>
      <textarea id="feedback-comment" value={comment} onChange={e => setComment(e.target.value)} required maxLength={2000} rows={6} disabled={busy} />
      <label htmlFor="feedback-rating">Rating <span className="mi-muted">(optional)</span></label>
      <select id="feedback-rating" value={rating} onChange={e => setRating(e.target.value)} disabled={busy}><option value="">No rating</option>{[1,2,3,4,5].map(n => <option key={n} value={n}>{n} / 5</option>)}</select>
      <div className="mi-actions"><Button type="submit" loading={busy}>{feedback ? 'Save changes' : 'Submit feedback'}</Button>{editing && <Button variant="secondary" disabled={busy} onClick={() => { setEditing(false);setComment(feedback.comment);setRating(feedback.rating ?? ''); }}>Cancel</Button>}</div>
    </form>}
  </Card>;
}

export default function ModuleFeedbackPage() {
  const { periodId } = useParams();
  const { user } = useAuth();
  const { data, error, refresh } = useCoreData(`/api/${user.role}/periods/${encodeURIComponent(periodId)}`);
  const module = data?.module;
  return <>
    <PageHeader title={module ? `${module.code} · ${module.name}` : 'Module feedback'} breadcrumbs={[{label:'Dashboard',to:`/${user.role}`},{label:'Module feedback'}]} actions={<Button variant="secondary" onClick={refresh}>Refresh</Button>} />
    {error && <p role="alert" className="mi-error">{error}</p>}
    {!data && !error && <p role="status">Loading module…</p>}
    {module && <>
      <Card className="p-6 mb-6"><p className="mi-term">{module.trimester}</p><p className="mi-muted">{module.lecturers.join(', ') || 'Lecturer not assigned'}</p><dl className="mi-dates"><div><dt>Feedback opens</dt><dd>{dateLabel(module.opens_at)}</dd></div><div><dt>Deadline</dt><dd>{dateLabel(module.deadline)}</dd></div></dl><span className="mi-status">{module.status || module.period_state}</span><span className="mi-muted ml-3">Period: {module.period_state}</span></Card>
      {user.role === 'student' ? <StudentFeedback key={module.id} module={module} refresh={refresh} /> : <Suspense fallback={<p role="status">Loading analytics…</p>}><StaffAnalytics key={module.id} periodId={module.id} /></Suspense>}
    </>}
  </>;
}
