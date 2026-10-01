import json
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import connect, initialise
from admin import admin_request, NEGATIVE_ALERT_PERCENT
from core import execute
from auth import AuthError

FORBIDDEN_KEYS = {'comment', 'comments', 'sentiment', 'sentiment_score', 'sentiment_percentages',
                  'theme', 'themes', 'theme_confidence', 'feedback', 'student_id', 'rating', 'negative', 'analysed'}


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / 'admin.db')
        initialise(self.path)
        self.admin = dict(userId='a1', role='admin')
        self.student = dict(userId='s1', role='student')
        self.staff = dict(userId='t1', role='staff')
        self.now = 1_000_000
        with closing(connect(self.path)) as db, db:
            for key, role in [('a1', 'admin'), ('s1', 'student'), ('s2', 'student'), ('s3', 'student'),
                              ('s4', 'student'), ('s5', 'student'), ('s6', 'student'), ('t1', 'staff')]:
                db.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?)',
                           (key, 'Person ' + key, key + '@example.test', role, 'salt', 'hash', 0))
            db.execute("INSERT INTO trimesters VALUES ('current','Current'),('next','Next')")
            db.execute("INSERT INTO app_settings VALUES (1,'current')")
            db.execute("INSERT INTO modules (id,code,name,archived) VALUES ('m1','INF1001','Alpha',0),('m2','INF1002','Beta',0)")
            db.execute('INSERT INTO feedback_periods VALUES (?,?,?,?,?)', ('p1', 'm1', 'current', self.now - 100, self.now + 100))
            db.execute('INSERT INTO feedback_periods VALUES (?,?,?,?,?)', ('p2', 'm2', 'current', self.now - 500, self.now - 100))
            db.executemany('INSERT INTO student_modules VALUES (?,?,?)',
                           [(f's{n}', 'm1', 'current') for n in range(1, 7)])
            db.execute("INSERT INTO staff_modules VALUES ('t1','m1','current')")

    def tearDown(self):
        self.temp.cleanup()

    def call(self, route, user=None, body=None, method=None):
        return admin_request(self.path, user or self.admin, method or ('GET' if body is None else 'POST'),
                             route, body, clock=lambda: self.now)

    def rejected(self, status, **kwargs):
        with self.assertRaises(AuthError) as ctx:
            self.call(**kwargs)
        self.assertEqual(ctx.exception.status, status)

    def add_feedback(self, count, negative=0):
        with closing(connect(self.path)) as db, db:
            for n in range(1, count + 1):
                db.execute('INSERT INTO feedback VALUES (?,?,?,?,?,?,?)',
                           (f'f{n}', 'p1', f's{n}', 'Private comment ' + str(n), 3, self.now, self.now))
                db.execute('INSERT INTO feedback_analysis VALUES (?,?,?,?,?,?,?)',
                           (f'f{n}', 'negative' if n <= negative else 'positive',
                            -0.9 if n <= negative else 0.9, 'Workload', 0.8, 3, 'sample'))

    # --- role gate -------------------------------------------------------
    def test_student_and_staff_are_forbidden_on_every_admin_route(self):
        for route in ['/api/admin/overview', '/api/admin/modules', '/api/admin/users',
                      '/api/admin/health', '/api/admin/trimesters',
                      '/api/admin/modules/m1/roster', '/api/admin/modules/m1/reminders']:
            for user in (self.student, self.staff):
                self.rejected(403, route=route, user=user)

    def test_non_admin_routes_are_not_claimed(self):
        self.assertIsNone(self.call(route='/api/staff/dashboard'))
        self.assertIsNone(self.call(route='/api/student/dashboard'))

    def test_admin_cannot_reach_student_or_staff_core_routes(self):
        for route in ['/api/student/dashboard', '/api/staff/dashboard']:
            with self.assertRaises(AuthError) as ctx:
                execute(self.path, self.admin, 'GET', route, None, clock=lambda: self.now)
            self.assertEqual(ctx.exception.status, 403)

    # --- privacy ---------------------------------------------------------
    def test_no_admin_response_contains_feedback_text_scores_or_themes(self):
        self.add_feedback(6, negative=5)
        payloads = [self.call(route='/api/admin/overview')[1],
                    self.call(route='/api/admin/modules')[1],
                    self.call(route='/api/admin/users')[1],
                    self.call(route='/api/admin/health')[1],
                    self.call(route='/api/admin/modules/m1/roster')[1],
                    self.call(route='/api/admin/modules/m1/reminders', body={})[1]]
        for payload in payloads:
            serialised = json.dumps(payload)
            self.assertNotIn('Private comment', serialised)
            self.assertNotIn('Workload', serialised)
            self.assertNotIn('positive', serialised)
            self.assertNotIn('"negative"', serialised)
            self.walk(payload)

    def walk(self, node):
        if isinstance(node, dict):
            for key, value in node.items():
                self.assertNotIn(key, FORBIDDEN_KEYS, f'{key} must not reach an administrator')
                self.walk(value)
        elif isinstance(node, list):
            for item in node:
                self.walk(item)

    def test_roster_never_reveals_who_submitted(self):
        self.add_feedback(3)
        people = self.call(route='/api/admin/modules/m1/roster')[1]['roster']
        self.assertEqual(len(people), 7)
        for person in people:
            self.assertEqual(set(person), {'user_id', 'name', 'email', 'role'})

    def test_reminder_returns_only_a_recipient_count(self):
        self.add_feedback(4)
        status, payload = self.call(route='/api/admin/modules/m1/reminders', body={})
        self.assertEqual(status, 200)
        self.assertEqual(payload['recipients'], 2)
        self.assertEqual(payload['delivery'], 'mock')
        self.assertNotIn('students', payload)
        with closing(connect(self.path)) as db:
            row = db.execute('SELECT * FROM reminder_log').fetchone()
        self.assertEqual(row['recipients'], 2)
        self.assertEqual(set(row.keys()), {'id', 'period_id', 'sent_by', 'sent_at', 'recipients'})

    def test_reminder_is_refused_when_the_period_is_closed(self):
        self.rejected(409, route='/api/admin/modules/m2/reminders', body={})

    # --- anomaly flag ----------------------------------------------------
    def test_alert_requires_both_threshold_and_minimum_responses(self):
        self.add_feedback(4, negative=4)
        module = self.module('m1')
        self.assertFalse(module['alert']['requires_attention'])
        self.assertEqual(module['alert']['status'], 'Insufficient data')

    def test_alert_raised_only_above_the_percentage_threshold(self):
        self.add_feedback(6, negative=4)  # 66.7% negative, below 70
        self.assertEqual(self.module('m1')['alert']['status'], 'Normal')
        with closing(connect(self.path)) as db, db:
            db.execute("UPDATE feedback_analysis SET sentiment='negative' WHERE feedback_id='f5'")
        module = self.module('m1')  # 83.3% negative
        self.assertTrue(module['alert']['requires_attention'])
        self.assertEqual(module['alert']['status'], 'Requires Attention')
        self.assertEqual(module['alert']['threshold_percent'], NEGATIVE_ALERT_PERCENT)

    def module(self, module_id):
        modules = self.call(route='/api/admin/modules')[1]['modules']
        return next(m for m in modules if m['module_id'] == module_id)

    # --- metrics ---------------------------------------------------------
    def test_response_counts_and_rate(self):
        self.add_feedback(3)
        module = self.module('m1')
        self.assertEqual((module['roster_size'], module['responses'], module['outstanding']), (6, 3, 3))
        self.assertEqual(module['response_rate'], 50.0)
        self.assertEqual(module['period_state'], 'Open')
        self.assertEqual(module['lecturers'], ['Person t1'])

    def test_overview_summarises_only_live_modules(self):
        self.add_feedback(6, negative=6)
        self.call(route='/api/admin/modules/m2/archive', body={'archived': True})
        summary = self.call(route='/api/admin/overview')[1]['summary']
        self.assertEqual(summary['active_modules'], 1)
        self.assertEqual(summary['archived_modules'], 1)
        self.assertEqual(summary['modules_requiring_attention'], 1)

    # --- module and roster management ------------------------------------
    def test_create_module_validates_code_and_rejects_duplicates(self):
        status, payload = self.call(route='/api/admin/modules', body={'code': 'inf2006', 'name': 'Cloud Computing'})
        self.assertEqual(status, 201)
        self.assertEqual(payload['module']['code'], 'INF2006')
        self.rejected(409, route='/api/admin/modules', body={'code': 'INF2006', 'name': 'Duplicate'})
        self.rejected(400, route='/api/admin/modules', body={'code': 'NOPE', 'name': 'Bad code'})
        self.rejected(400, route='/api/admin/modules', body={'code': 'INF2007', 'name': 'x'})

    def test_archive_hides_the_module_from_student_dashboards(self):
        before = execute(self.path, self.student, 'GET', '/api/student/dashboard', None, clock=lambda: self.now)
        self.assertEqual(len(before[1]['modules']), 1)
        self.call(route='/api/admin/modules/m1/archive', body={'archived': True})
        after = execute(self.path, self.student, 'GET', '/api/student/dashboard', None, clock=lambda: self.now)
        self.assertEqual(after[1]['modules'], [])
        self.call(route='/api/admin/modules/m1/archive', body={'archived': False})
        restored = execute(self.path, self.student, 'GET', '/api/student/dashboard', None, clock=lambda: self.now)
        self.assertEqual(len(restored[1]['modules']), 1)

    def test_extend_deadline_reopens_a_closed_period(self):
        status, payload = self.call(route='/api/admin/modules/m2/deadline', body={'extend_days': 3})
        self.assertEqual(status, 200)
        self.assertEqual(payload['deadline'], self.now + 3 * 86400)
        self.assertEqual(payload['period_state'], 'Open')
        self.rejected(400, route='/api/admin/modules/m2/deadline', body={'extend_days': 0})
        self.rejected(400, route='/api/admin/modules/m2/deadline', body={'extend_days': 500})

    def test_extend_deadline_adds_to_a_future_deadline(self):
        payload = self.call(route='/api/admin/modules/m1/deadline', body={'extend_days': 2})[1]
        self.assertEqual(payload['deadline'], self.now + 100 + 2 * 86400)

    def test_roster_add_and_remove(self):
        self.call(route='/api/admin/modules/m1/roster', body={'email': 's1@example.test', 'action': 'remove'})
        self.assertEqual(self.module('m1')['roster_size'], 5)
        self.call(route='/api/admin/modules/m1/roster', body={'email': 'S1@example.test', 'action': 'add'})
        self.assertEqual(self.module('m1')['roster_size'], 6)
        self.rejected(404, route='/api/admin/modules/m1/roster', body={'email': 'ghost@example.test', 'action': 'add'})
        self.rejected(400, route='/api/admin/modules/m1/roster', body={'email': 'a1@example.test', 'action': 'add'})
        self.rejected(400, route='/api/admin/modules/m1/roster', body={'email': 's1@example.test', 'action': 'drop'})

    def test_removing_a_student_who_submitted_succeeds_and_keeps_the_feedback(self):
        self.add_feedback(1)
        status, _ = self.call(route='/api/admin/modules/m1/roster', body={'email': 's1@example.test', 'action': 'remove'})
        self.assertEqual(status, 200)
        with closing(connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM feedback').fetchone()[0], 1)

    # --- trimester control -----------------------------------------------
    def test_trimester_toggle_changes_every_dashboard(self):
        self.call(route='/api/admin/trimester', body={'trimester_id': 'next'})
        self.assertEqual(self.call(route='/api/admin/trimesters')[1]['current_trimester'], 'next')
        dashboard = execute(self.path, self.student, 'GET', '/api/student/dashboard', None, clock=lambda: self.now)
        self.assertEqual(dashboard[1]['trimester']['id'], 'next')
        self.assertEqual(dashboard[1]['modules'], [])
        self.rejected(404, route='/api/admin/trimester', body={'trimester_id': 'ghost'})

    def test_create_trimester(self):
        status, payload = self.call(route='/api/admin/trimesters', body={'name': 'AY2027/28 Trimester 2'})
        self.assertEqual(status, 201)
        self.assertIn(payload['trimester']['id'], [t['id'] for t in self.call(route='/api/admin/trimesters')[1]['trimesters']])

    # --- health and auditing ---------------------------------------------
    def test_health_reports_api_and_database(self):
        payload = self.call(route='/api/admin/health')[1]['health']
        self.assertEqual(payload['api']['status'], 'healthy')
        self.assertEqual(payload['database']['status'], 'healthy')
        self.assertTrue(payload['database']['trimester_configured'])
        self.assertGreaterEqual(payload['database']['users'], 8)

    def test_directory_lists_every_role(self):
        payload = self.call(route='/api/admin/users')[1]
        self.assertEqual(payload['counts'], {'student': 6, 'staff': 1, 'admin': 1})
        self.assertEqual(payload['total'], 8)

    def test_mutations_are_audited(self):
        self.call(route='/api/admin/modules/m1/archive', body={'archived': True})
        self.call(route='/api/admin/modules/m1/deadline', body={'extend_days': 1})
        with closing(connect(self.path)) as db:
            actions = [r['action'] for r in db.execute('SELECT action FROM admin_audit ORDER BY action')]
        self.assertEqual(actions, ['module.archive', 'period.deadline'])

    def test_unknown_admin_route_and_method(self):
        self.assertIsNone(self.call(route='/api/admin/nope'))
        self.rejected(405, route='/api/admin/users', method='DELETE')

    def test_unknown_route_is_unresolved_even_without_an_active_trimester(self):
        # Route resolution must not depend on configuration state, or an
        # unrecognised path reports the conflict of a path that exists.
        with closing(connect(self.path)) as db, db:
            db.execute('DELETE FROM app_settings')
        self.assertIsNone(self.call(route='/api/admin/nope'))
        self.rejected(409, route='/api/admin/overview')


class MigrationTests(unittest.TestCase):
    def test_legacy_database_gains_the_admin_role_and_archive_column(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'legacy.db')
            with closing(connect(path)) as db, db:
                db.executescript('''
                CREATE TABLE users (
                  id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
                  role TEXT NOT NULL CHECK(role IN ('student','staff')),
                  salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at INTEGER NOT NULL);
                CREATE TABLE sessions (
                  token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                  expires INTEGER NOT NULL);
                CREATE TABLE modules (id TEXT PRIMARY KEY, code TEXT NOT NULL, name TEXT NOT NULL);
                INSERT INTO users VALUES ('u1','Existing','u1@example.test','staff','salt','hash',1);
                INSERT INTO sessions VALUES ('hash','u1',9999999999);
                INSERT INTO modules VALUES ('m1','INF1001','Alpha');
                ''')
            initialise(path)
            with closing(connect(path)) as db, db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM users').fetchone()[0], 1)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT archived FROM modules WHERE id='m1'").fetchone()[0], 0)
                db.execute("UPDATE users SET role='admin' WHERE id='u1'")
                self.assertEqual(db.execute('SELECT role FROM users').fetchone()[0], 'admin')
                self.assertIsNone(db.execute('PRAGMA foreign_key_check').fetchone())
            initialise(path)  # second run must be a no-op


if __name__ == '__main__':
    unittest.main()
