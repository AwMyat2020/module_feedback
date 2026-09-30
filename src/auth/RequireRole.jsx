import { Navigate, Outlet, useLocation } from 'react-router';
import { useAuth } from './useAuth.js';
import { routeDecision } from './routePolicy.js';
import ForbiddenPage from '../pages/ForbiddenPage.jsx';

export default function RequireRole({ roles }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <p role="status" className="p-8">Checking your session…</p>;
  const decision = routeDecision(user, roles);
  if (decision === 'login') return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (decision === 'forbidden') return <ForbiddenPage title="403 – You do not have permission to access this page." message="Your account role does not have access to this area." />;
  return <Outlet />;
}
