import { Outlet, NavLink } from 'react-router';
import { useAuth } from '../../auth/useAuth.js';
import Logo from './Logo.jsx';

// Navigation is driven by the signed-in role. The administrator area is the
// only one with more than a single destination.
const NAV = {
  student: [['/student', 'Student Dashboard']],
  staff: [['/staff', 'Staff Dashboard']],
  admin: [['/admin', 'Overview'], ['/admin/modules', 'Modules & Rosters'], ['/admin/users', 'User Directory']],
};

export default function AppLayout() {
  const { user, logout } = useAuth();
  return <div className="mi-shell">
    <a href="#main" className="sr-only focus:not-sr-only">Skip to content</a>
    <header className="mi-header"><Logo />
      <nav className="mi-nav" aria-label="Main navigation">{(NAV[user.role] || []).map(([to, label]) =>
        <NavLink key={to} to={to} end={to === '/admin'}>{label}</NavLink>)}</nav>
      <div className="mi-account"><span>{user.name}</span><button onClick={logout} className="mi-secondary">Sign out</button></div>
    </header>
    <main id="main" className="mi-main"><Outlet /></main>
    <footer className="mi-footer"><span>Module Insight / INF2006 prototype</span><span>Feedback supports your decision.</span></footer>
  </div>;
}
