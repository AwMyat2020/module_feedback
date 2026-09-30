import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../auth/useAuth.js';
import { authRequest } from '../services/authService.js';

export function useCoreData(path) {
  const { expire } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const refresh = useCallback(() => setRevision(n => n + 1), []);
  useEffect(() => {
    let active = true;
    setData(null); setError('');
    authRequest(path).then(value => { if (active) setData(value); })
      .catch(e => { if (active) { if (e.status === 401) expire(); else setError(e.message); } });
    return () => { active = false; };
  }, [path, revision, expire]);
  return { data, error, refresh };
}

export function dateLabel(seconds) {
  return new Date(seconds * 1000).toLocaleString('en-SG', { timeZone: 'Asia/Singapore', dateStyle: 'medium', timeStyle: 'short' }) + ' SGT';
}
