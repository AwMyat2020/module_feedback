import http.client
import json
import sys
import tempfile
import threading
import unittest
import time
import secrets
from contextlib import closing
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import make_server
from database import connect


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name)/'test.sqlite3')
        self.server = make_server(self.path, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.cookie = ''
        self.password = secrets.token_urlsafe(24)

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.temp.cleanup()

    def request(self, path, body=None, **headers):
        client = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        all_headers = {'Cookie':self.cookie, 'Content-Type':'application/json', 'X-Requested-With':'ModuleFeedbackInsight', **headers}
        client.request('GET' if body is None else 'POST', path, None if body is None else json.dumps(body), all_headers)
        response = client.getresponse()
        cookie = response.getheader('Set-Cookie')
        if cookie is not None: self.cookie = cookie.split(';')[0]
        result = response.status, json.loads(response.read()), cookie
        client.close()
        return result

    def register(self, email, **extra):
        return self.request('/api/auth/register',dict(name='Test Account',email=email,password=self.password,**extra))

    def test_valid_student_registration_persists_role_and_hash(self):
        status, data, cookie = self.register('  Student@SIT.Singaporetech.edu.sg ', role='staff')
        self.assertEqual(status,201); self.assertEqual(data['user']['role'],'student')
        self.assertIn('HttpOnly',cookie); self.assertIn('SameSite=Strict',cookie)
        with closing(connect(self.path)) as db:
            row=db.execute('SELECT * FROM users').fetchone()
            self.assertEqual(row['role'],'student')
            self.assertNotEqual(row['password_hash'],self.password)
        self.assertNotIn('password_hash',data['user'])

    def test_valid_staff_registration(self):
        status,data,_=self.register('lecturer@singaporetech.edu.sg')
        self.assertEqual(status,201);self.assertEqual(data['user']['role'],'staff')
        self.assertEqual(self.request('/api/staff/dashboard')[0],200)

    def test_other_and_lookalike_domains_rejected(self):
        for email in ['person@gmail.com','a@evilsingaporetech.edu.sg','a@singaporetech.edu.sg.evil.com','a@sub.sit.singaporetech.edu.sg','a@@singaporetech.edu.sg']:
            status,data,_=self.register(email)
            self.assertEqual(status,400);self.assertIn('@sit.singaporetech.edu.sg',data['message'])

    def test_student_denied_staff_api_and_staff_denied_student_actions(self):
        self.register('student@sit.singaporetech.edu.sg')
        self.assertEqual(self.request('/api/staff/dashboard')[0],403)
        self.request('/api/auth/logout',{})
        self.register('staff@singaporetech.edu.sg')
        self.assertEqual(self.request('/api/student/dashboard')[0],403)
        self.assertEqual(self.request('/api/feedback',{})[0],403)

    def test_unauthenticated_request_denied_and_fake_token_ignored(self):
        self.assertEqual(self.request('/api/student/dashboard')[0],401)
        self.cookie='mfi_session=pretend-staff'
        self.assertEqual(self.request('/api/staff/dashboard')[0],401)

    def test_login_duplicate_logout_and_revocation(self):
        self.register('student@sit.singaporetech.edu.sg')
        old_cookie=self.cookie
        self.assertEqual(self.register('STUDENT@sit.singaporetech.edu.sg')[0],409)
        self.request('/api/auth/logout',{})
        self.cookie=old_cookie
        self.assertEqual(self.request('/api/auth/me')[0],401)
        self.assertEqual(self.request('/api/auth/login',dict(email='student@sit.singaporetech.edu.sg',password=secrets.token_urlsafe(24)))[0],401)
        self.assertEqual(self.request('/api/auth/login',dict(email='student@sit.singaporetech.edu.sg',password=self.password))[0],200)
        self.assertEqual(self.request('/api/auth/me')[1]['user']['role'],'student')

    def test_cross_origin_mutation_rejected(self):
        status,_,_=self.request('/api/auth/register',dict(name='Test',email='a@singaporetech.edu.sg',password=self.password),Origin='https://evil.example')
        self.assertEqual(status,403)

    def test_core_http_routes_submission_and_staff_projection(self):
        student=self.register('core@sit.singaporetech.edu.sg')[1]['user']['userId']
        now=int(time.time())
        with closing(connect(self.path)) as db,db:
            db.execute("INSERT INTO trimesters VALUES ('t','Current')")
            db.execute("INSERT INTO app_settings VALUES (1,'t')")
            db.execute("INSERT INTO modules (id,code,name) VALUES ('m','INF2006','Cloud Computing')")
            db.execute('INSERT INTO feedback_periods VALUES (?,?,?,?,?)',('p','m','t',now-60,now+60))
            db.execute('INSERT INTO student_modules VALUES (?,?,?)',(student,'m','t'))
        self.assertEqual(len(self.request('/api/student/dashboard')[1]['modules']),1)
        status,data,_=self.request('/api/student/periods/p/feedback',{'comment':'HTTP test','rating':5})
        self.assertEqual(status,201)
        key=data['feedback']['id']
        self.assertEqual(self.request(f'/api/student/periods/p/feedback/{key}/edit',{'comment':'Updated'})[0],200)
        staff=self.register('core@singaporetech.edu.sg')[1]['user']['userId']
        self.assertEqual(self.request('/api/staff/periods/p')[0],403)
        with closing(connect(self.path)) as db,db:
            db.execute('INSERT INTO staff_modules VALUES (?,?,?)',(staff,'m','t'))
        self.assertEqual(self.request('/api/staff/periods/p')[1]['module']['feedback'],[])
        analytics=self.request('/api/staff/periods/p/analytics')[1]['analytics']
        self.assertTrue(analytics['suppressed']);self.assertNotIn('comments',analytics)
        self.request('/api/auth/logout',{})
        self.assertEqual(self.request('/api/student/periods/p/feedback',{'comment':'Anonymous'})[0],401)

if __name__=='__main__': unittest.main()
