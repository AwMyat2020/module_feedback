import { createContext, useContext } from 'react';

// Kept apart from AuthProvider so React Fast Refresh can hot-swap the
// provider without re-creating the context (which would orphan consumers).
export const AuthContext = createContext(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
