import { FileQuestionMark, ShieldAlert } from 'lucide-react';
import { useAuth } from '../../auth/useAuth.js';
import { AUTH_HOME } from '../../auth/routePolicy.js';
import Button from './Button.jsx';
import { ErrorState } from './States.jsx';

function StatusView({ code, icon: Icon, tone, title, message }) {
  const { user } = useAuth();
  const home = user ? AUTH_HOME[user.role] : '/login';
  return (
    <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
      <div className={`rounded-full p-4 ${tone}`}>
        <Icon className="size-8" aria-hidden />
      </div>
      <p className="mt-6 text-sm font-semibold uppercase tracking-wider text-slate-400">Error {code}</p>
      <h1 className="mt-1 text-2xl font-semibold text-slate-900">{title}</h1>
      <p className="mt-2 max-w-md text-sm text-slate-500">{message}</p>
      <Button to={home} variant="secondary" className="mt-6">Back to dashboard</Button>
    </div>
  );
}

export function ForbiddenView({
  title = '403 – You do not have permission to access this module.',
  message = 'This module is not assigned to your account.',
}) {
  return (
    <StatusView
      code={403}
      icon={ShieldAlert}
      tone="bg-negative-soft text-negative-ink"
      title={title}
      message={`${message} If you believe this is a mistake, contact your faculty administrator.`}
    />
  );
}

export function NotFoundView({ message = 'The page or module you are looking for does not exist.' }) {
  return (
    <StatusView code={404} icon={FileQuestionMark} tone="bg-slate-100 text-slate-500" title="Page not found" message={message} />
  );
}

// Maps an API failure to the right view: 403 and 404 get their own pages,
// anything else is a retryable error.
export function ApiErrorView({ error, onRetry, title }) {
  if (error?.status === 403) return <ForbiddenView />;
  if (error?.status === 404) return <NotFoundView message={error.message} />;
  return <ErrorState title={title} error={error} onRetry={onRetry} />;
}
