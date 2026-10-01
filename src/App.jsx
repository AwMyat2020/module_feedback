import { Navigate, Route, Routes } from 'react-router';
import { useAuth } from './auth/useAuth.js';
import RequireRole from './auth/RequireRole.jsx';
import AppLayout from './components/layout/AppLayout.jsx';
import { AUTH_HOME } from './auth/routePolicy.js';
import LoginPage from './pages/LoginPage.jsx';
import AuthDashboard from './pages/AuthDashboard.jsx';
import ModuleFeedbackPage from './pages/ModuleFeedbackPage.jsx';
import AdminDashboard from './pages/AdminDashboard.jsx';
import AdminModules from './pages/AdminModules.jsx';
import AdminUsers from './pages/AdminUsers.jsx';
import NotFoundPage from './pages/NotFoundPage.jsx';

function Home() {
  const { user, loading } = useAuth();
  if(loading) return <p role="status" className="p-8">Checking your session…</p>;
  return <Navigate to={user ? AUTH_HOME[user.role] : '/login'} replace />;
}
export default function App() {
  return <Routes>
    <Route path="/" element={<Home />} />
    <Route path="/login" element={<LoginPage />} />
    <Route path="/register" element={<LoginPage registration />} />
    <Route element={<RequireRole />}><Route element={<AppLayout />}>
      <Route element={<RequireRole roles={['student']} />}>
        <Route path="/student" element={<AuthDashboard />} />
        <Route path="/student/periods/:periodId" element={<ModuleFeedbackPage />} />
        <Route path="/student/*" element={<NotFoundPage />} />
      </Route>
      <Route element={<RequireRole roles={['staff']} />}>
        <Route path="/staff" element={<AuthDashboard />} />
        <Route path="/staff/periods/:periodId" element={<ModuleFeedbackPage />} />
        <Route path="/staff/*" element={<NotFoundPage />} />
        <Route path="/lecturer" element={<Navigate to="/staff" replace />} />
        <Route path="/lecturer/*" element={<NotFoundPage />} />
      </Route>
      <Route element={<RequireRole roles={['admin']} />}>
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/admin/modules" element={<AdminModules />} />
        <Route path="/admin/users" element={<AdminUsers />} />
        <Route path="/admin/*" element={<NotFoundPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Route></Route>
  </Routes>;
}
