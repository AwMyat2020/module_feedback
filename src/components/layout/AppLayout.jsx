import { Outlet, NavLink } from 'react-router';
import { useAuth } from '../../auth/useAuth.js';
import Logo from './Logo.jsx';
export default function AppLayout() {
  const { user, logout } = useAuth();
  return <div className="mi-shell">
    <a href="#main" className="sr-only focus:not-sr-only">Skip to content</a>
    <header className="mi-header"><Logo />
      <nav className="mi-nav" aria-label="Main navigation"><NavLink to={user.role === 'staff' ? '/staff' : '/student'}>{user.role === 'staff' ? 'Staff Dashboard' : 'Student Dashboard'}</NavLink></nav>
      <div className="mi-account"><span>{user.name}</span><button onClick={logout} className="mi-secondary">Sign out</button></div>
    </header>
    <main id="main" className="mi-main"><Outlet /></main>
    <footer className="mi-footer"><span>Module Insight / INF2006 prototype</span><span>Feedback supports your decision.</span></footer>
  </div>;
}
