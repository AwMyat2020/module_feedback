import { useCallback, useState } from 'react';
import { useAuth } from '../auth/useAuth.js';
import { authRequest } from './authService.js';

// Administrator mutations all POST to /api/admin/*. A single pending key lets
// one row's button show progress without disabling the rest of the table.
export function useAdminAction(onSuccess) {
  const { expire } = useAuth();
  const [pending, setPending] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const run = useCallback(async (key, path, body = {}) => {
    setPending(key); setError(''); setNotice('');
    try {
      const data = await authRequest(path, body);
      setNotice(data.message || 'Change saved.');
      onSuccess?.(data);
      return data;
    } catch (failure) {
      if (failure.status === 401) expire(); else setError(failure.message);
      return null;
    } finally {
      setPending('');
    }
  }, [expire, onSuccess]);
  const clear = useCallback(() => { setError(''); setNotice(''); }, []);
  return { run, pending, error, notice, clear };
}

export function modulePath(moduleId, action) {
  return `/api/admin/modules/${encodeURIComponent(moduleId)}${action ? `/${action}` : ''}`;
}

// A module with no roster has no meaningful rate; the API sends null for it.
export function rateLabel(value) {
  return value === null || value === undefined ? '—' : `${value}%`;
}

export const ROLE_LABEL = { student: 'Student', staff: 'Staff', admin: 'Administrator' };
