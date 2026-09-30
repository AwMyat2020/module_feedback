// Local server is authoritative. No demo tokens or user records in localStorage.
export async function authRequest(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json', 'X-Requested-With': 'ModuleFeedbackInsight' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const data = await response.json().catch(() => ({ message: 'Local API unavailable. Start the Python server.' }));
  if (!response.ok) {
    const error = new Error(data.message || 'Request failed.');
    error.status = response.status;
    throw error;
  }
  return data;
}
export const signIn = async (email, password) => (await authRequest('/api/auth/login', { email, password })).user;
export const register = async (name, email, password) => (await authRequest('/api/auth/register', { name, email, password })).user;
export const signOut = () => authRequest('/api/auth/logout', {});
export async function getCurrentUser() {
  try { return (await authRequest('/api/auth/me')).user; }
  catch (error) { if (error.status === 401) return null; throw error; }
}
