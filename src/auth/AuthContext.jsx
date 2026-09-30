import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { getCurrentUser, register as createAccount, signIn, signOut } from '../services/authService.js';
import { AuthContext } from './useAuth.js';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  useEffect(() => {
    let active = true;
    getCurrentUser().then(value => { if(active) setUser(value); })
      .catch(() => { if(active) setError('Cannot reach the local API. Start the Python server and refresh.'); })
      .finally(() => { if(active) setLoading(false); });
    return () => { active = false; };
  }, []);
  const login = useCallback(async (email, password) => {
    const value = await signIn(email, password); setUser(value); setError(''); return value;
  }, []);
  const register = useCallback(async (name, email, password) => {
    const value = await createAccount(name, email, password); setUser(value); setError(''); return value;
  }, []);
  const logout = useCallback(async () => {
    try { await signOut(); setUser(null); setError(''); navigate('/login', { replace:true }); }
    catch { setError('Sign out failed. Check the local API and try again.'); }
  }, [navigate]);
  const expire = useCallback(() => { setUser(null); navigate('/login', { replace:true }); }, [navigate]);
  const value = useMemo(() => ({ user, loading, error, login, register, logout, expire }), [user, loading, error, login, register, logout, expire]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
