// Pure route decision, shared by React guard and automated tests.
export function routeDecision(user, roles) {
  if (!user) return 'login';
  if (roles && !roles.includes(user.role)) return 'forbidden';
  return 'allow';
}
export const AUTH_HOME = { student: '/student', staff: '/staff' };
