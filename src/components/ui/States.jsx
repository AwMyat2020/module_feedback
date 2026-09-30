import { CloudOff, Inbox, RefreshCw } from 'lucide-react';
import Button from './Button.jsx';

export function EmptyState({ icon: Icon = Inbox, title, message, action }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="rounded-full bg-slate-100 p-3">
        <Icon className="size-6 text-slate-500" aria-hidden />
      </div>
      <h3 className="mt-4 text-base font-semibold text-slate-900">{title}</h3>
      {message && <p className="mt-1 max-w-md text-sm text-slate-500">{message}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ title = 'Unable to load feedback.', error, onRetry }) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center rounded-xl bg-white px-6 py-12 text-center ring-1 ring-slate-200">
      <div className="rounded-full bg-negative-soft p-3">
        <CloudOff className="size-6 text-negative-ink" aria-hidden />
      </div>
      <h3 className="mt-4 text-base font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 max-w-md text-sm text-slate-500">
        {error?.message || 'Something went wrong while contacting the server.'}
        {error?.status ? <span className="text-slate-400"> (HTTP {error.status})</span> : null}
      </p>
      {onRetry && (
        <Button variant="secondary" icon={RefreshCw} className="mt-5" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}
