import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router';
import { Eye, EyeOff, LockKeyhole } from 'lucide-react';
import { useAuth } from '../auth/useAuth.js';
import { AUTH_HOME as HOME_PATH_BY_ROLE } from '../auth/routePolicy.js';
import { isValidEmail } from '../utils/validation.js';
import Button from '../components/ui/Button.jsx';
import Logo from '../components/layout/Logo.jsx';

export default function LoginPage({ registration = false }) {
  const { user, loading, error: connectionError, login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [name, setName] = useState('');

  if (loading) return <p role="status" className="p-8">Checking your session…</p>;
  if (user) return <Navigate to={HOME_PATH_BY_ROLE[user.role]} replace />;

  const sessionExpired = location.state?.expired;

  const signInWith = async (emailValue, passwordValue) => {
    const nextErrors = {};
    if (!isValidEmail(emailValue.trim()) || !['sit.singaporetech.edu.sg','singaporetech.edu.sg'].includes(emailValue.trim().toLowerCase().split('@')[1])) nextErrors.email = 'Use @sit.singaporetech.edu.sg for students or @singaporetech.edu.sg for staff.';
    if (registration && (name.trim().length < 2 || name.trim().length > 60)) nextErrors.name = 'Display name must be 2–60 characters.';
    if (passwordValue.length < 12 || passwordValue.length > 128) nextErrors.password = 'Use a password of 12–128 characters.';
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    setSubmitting(true);
    try {
      const signedIn = registration ? await register(name.trim(), emailValue.trim(), passwordValue) : await login(emailValue.trim(), passwordValue);
      const from = location.state?.from;
      const home = HOME_PATH_BY_ROLE[signedIn.role];
      navigate(from && (from === home || from.startsWith(home + '/')) ? from : home, { replace: true });
    } catch (err) {
      setErrors({ form: err.message });
      setSubmitting(false);
    }
  };

  const onSubmit = (e) => {
    e.preventDefault();
    signInWith(email, password);
  };

  return (
    <div className="mi-shell">
      <header className="mi-header"><Logo /><span className="mi-badge">MODULE INSIGHT</span></header>
      <main className="mi-auth-main">
        <section className="mi-auth-card">
          <p className="mi-eyebrow">YOUR MODULE INSIGHT ACCOUNT</p>
          <h1>{registration ? 'Create your account' : 'Welcome back.'}</h1>
          <p className="mi-muted">{registration ? 'Use your institutional email to get started.' : 'Sign in to your student or staff dashboard.'}</p>
          {sessionExpired && (
            <p className="mt-4 rounded-lg bg-neutral-soft px-3 py-2 text-sm text-neutral-ink">Your session has expired. Please sign in again.</p>
          )}
          {(errors.form || connectionError) && (
            <p role="alert" className="mt-4 rounded-lg bg-negative-soft px-3 py-2 text-sm text-negative-ink">{errors.form || connectionError}</p>
          )}

          <form onSubmit={onSubmit} noValidate className="mt-6 space-y-4">
            {registration && <div><label htmlFor="display-name" className="mb-1.5 block text-sm font-medium text-slate-700">Display name</label><input id="display-name" autoComplete="nickname" maxLength={60} value={name} onChange={e => setName(e.target.value)} className="h-11 w-full rounded-lg px-3 text-sm ring-1 ring-slate-300" />{errors.name && <p role="alert" className="mt-1 text-xs text-negative-ink">{errors.name}</p>}</div>}
            <div>
              <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-slate-700">Email</label>
              <input
                id="email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                aria-invalid={Boolean(errors.email)}
                aria-describedby={errors.email ? 'email-error' : undefined}
                placeholder="name@sit.singaporetech.edu.sg"
                className="h-11 w-full rounded-lg px-3 text-sm ring-1 ring-slate-300 placeholder:text-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 aria-invalid:ring-negative"
              />
              {errors.email && <p id="email-error" className="mt-1 text-xs text-negative-ink">{errors.email}</p>}
            </div>

            <div>
              <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-slate-700">Password</label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete={registration ? 'new-password' : 'current-password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  aria-invalid={Boolean(errors.password)}
                  aria-describedby={errors.password ? 'password-error' : undefined}
                  className="h-11 w-full rounded-lg pl-3 pr-11 text-sm ring-1 ring-slate-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 aria-invalid:ring-negative"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1.5 text-slate-400 hover:text-slate-600"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="size-4" aria-hidden /> : <Eye className="size-4" aria-hidden />}
                </button>
              </div>
              {errors.password && <p id="password-error" className="mt-1 text-xs text-negative-ink">{errors.password}</p>}
            </div>

            <Button type="submit" size="lg" className="w-full" loading={submitting} icon={LockKeyhole}>
              {registration ? 'Create account' : 'Sign In'}
            </Button>
          </form>

          <p className="mt-6 text-sm text-slate-600">{registration ? 'Already registered? ' : 'New here? '}<Link className="font-semibold text-brand-700 underline" to={registration ? '/login' : '/register'} onClick={() => { setErrors({}); setPassword(''); }}>{registration ? 'Sign in' : 'Create an account'}</Link></p>
          <p className="mt-4 text-xs text-slate-500">Local project accounts only. Use a test password, not your university password. Institutional email ownership is not verified in this phase.</p>
        </section>
      </main>
      <footer className="mi-footer"><span>Module Insight / INF2006 prototype</span><span>Feedback supports your decision.</span></footer>
    </div>
  );
}
