import test from 'node:test';
import assert from 'node:assert/strict';
import { routeDecision, AUTH_HOME } from '../src/auth/routePolicy.js';
test('unauthenticated visitor is sent to login for protected routes', () => {
  assert.equal(routeDecision(null), 'login');
  assert.equal(routeDecision(null, ['staff']), 'login');
  assert.equal(routeDecision(null, ['admin']), 'login');
});
test('student denied staff route, staff denied student route', () => {
  assert.equal(routeDecision({role:'student'}, ['staff']), 'forbidden');
  assert.equal(routeDecision({role:'staff'}, ['student']), 'forbidden');
  assert.equal(routeDecision({role:'staff'}, ['staff']), 'allow');
  assert.equal(routeDecision({role:'student'}, ['student']), 'allow');
});
test('admin area is closed to student and staff', () => {
  assert.equal(routeDecision({role:'student'}, ['admin']), 'forbidden');
  assert.equal(routeDecision({role:'staff'}, ['admin']), 'forbidden');
  assert.equal(routeDecision({role:'admin'}, ['admin']), 'allow');
});
test('admin is not granted the student or staff areas', () => {
  assert.equal(routeDecision({role:'admin'}, ['student']), 'forbidden');
  assert.equal(routeDecision({role:'admin'}, ['staff']), 'forbidden');
});
test('stored role determines dashboard destination', () => {
  assert.equal(AUTH_HOME.student, '/student'); assert.equal(AUTH_HOME.staff, '/staff');
  assert.equal(AUTH_HOME.admin, '/admin');
});
