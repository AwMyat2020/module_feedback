import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from database import connect, initialise
from core import execute
from auth import AuthError

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=str(Path(self.temp.name)/'core.db')
        initialise(self.path)
        self.student=dict(userId='s1',role='student')
        self.other=dict(userId='s2',role='student')
        self.staff=dict(userId='t1',role='staff')
        self.now=1000
        with closing(connect(self.path)) as db,db:
            for key,role in [('s1','student'),('s2','student'),('t1','staff'),('t2','staff')]:
                db.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?)',(key,'Private '+key,key+'@example.test',role,'salt','hash',0))
            db.execute("INSERT INTO trimesters VALUES ('current','Current'),('old','Old')")
            db.execute("INSERT INTO app_settings VALUES (1,'current')")
            for key in ['a','b']:
                db.execute('INSERT INTO modules VALUES (?,?,?)',(key,'INF'+key,'Module '+key))
                db.execute('INSERT INTO feedback_periods VALUES (?,?,?,?,?)',(key,key,'current',900,1100))
            db.execute("INSERT INTO feedback_periods VALUES ('old','a','old',100,200)")
            db.executemany('INSERT INTO student_modules VALUES (?,?,?)',[('s1','a','current'),('s2','b','current'),('s1','a','old')])
            db.executemany('INSERT INTO staff_modules VALUES (?,?,?)',[('t1','a','current'),('t2','b','current')])
    def tearDown(self): self.temp.cleanup()
    def call(self,user=None,route='/api/student/periods/a',body=None):
        return execute(self.path,user or self.student,'GET' if body is None else 'POST',route,body,clock=lambda:self.now)
    def submit(self):
        return self.call(route='/api/student/periods/a/feedback',body=dict(comment='Useful weekly labs.',rating=4))[1]['feedback']['id']
    def rejected(self,status,**kwargs):
        with self.assertRaises(AuthError) as ctx: self.call(**kwargs)
        self.assertEqual(ctx.exception.status,status)
    def test_student_sees_only_current_assigned_modules(self):
        data=self.call(route='/api/student/dashboard')[1]
        self.assertEqual([r['id'] for r in data['modules']],['a'])
    def test_staff_sees_only_assigned_modules(self):
        self.assertEqual([r['id'] for r in self.call(self.staff,'/api/staff/dashboard')[1]['modules']],['a'])
    def test_unassigned_and_missing_denied(self):
        self.rejected(403,route='/api/student/periods/b')
        self.rejected(403,user=self.staff,route='/api/staff/periods/b')
        self.rejected(403,route='/api/student/periods/b/feedback',body={'comment':'No'})
        self.rejected(404,route='/api/student/periods/missing')
    def test_valid_submission_and_duplicate(self):
        self.submit()
        self.assertEqual(self.call()[1]['module']['feedback']['rating'],4)
        self.rejected(409,route='/api/student/periods/a/feedback',body={'comment':'Again'})
    def test_edit_before_deadline(self):
        key=self.submit()
        self.call(route=f'/api/student/periods/a/feedback/{key}/edit',body={'comment':'Edited','rating':None})
        self.assertEqual(self.call()[1]['module']['feedback']['comment'],'Edited')
    def test_delete_before_deadline_and_resubmit(self):
        key=self.submit(); url=f'/api/student/periods/a/feedback/{key}/delete'
        self.call(route=url,body={})
        self.rejected(404,route=url,body={})
        new=self.submit()
        self.assertNotEqual(key,new)
        self.rejected(404,route=url,body={})
    def test_edit_at_deadline_rejected(self):
        key=self.submit();self.now=1100
        self.rejected(409,route=f'/api/student/periods/a/feedback/{key}/edit',body={'comment':'Late'})
        self.assertEqual(self.call()[1]['module']['feedback']['comment'],'Useful weekly labs.')
    def test_delete_after_deadline_rejected(self):
        key=self.submit();self.now=1101
        self.rejected(409,route=f'/api/student/periods/a/feedback/{key}/delete',body={})
    def test_late_and_early_submission_rejected(self):
        for now in [899,1100,1200]:
            self.now=now
            self.rejected(409,route='/api/student/periods/a/feedback',body={'comment':'No'})
    def test_staff_response_identity_allowlist(self):
        self.submit()
        result=self.call(self.staff,'/api/staff/periods/a')[1]['module']['feedback']
        self.assertEqual(result,[])  # Raw staff list cannot bypass analytics privacy.
    def test_invalid_rating_and_empty_text(self):
        for rating in [0,6,1.5,True,'4']:
            self.rejected(400,route='/api/student/periods/a/feedback',body={'comment':'Text','rating':rating})
        for text in ['', '   ',None,'x'*2001]:
            self.rejected(400,route='/api/student/periods/a/feedback',body={'comment':text})
    def test_staff_cannot_submit_and_cross_student_ownership(self):
        key=self.submit()
        self.rejected(403,user=self.staff,route='/api/student/periods/a/feedback',body={'comment':'No'})
        self.rejected(403,user=self.staff,route='/api/staff/periods/a/feedback',body={'comment':'No'})
        with closing(connect(self.path)) as db,db:
            db.execute("INSERT INTO student_modules VALUES ('s2','a','current')")
        self.rejected(404,user=self.other,route=f'/api/student/periods/a/feedback/{key}/edit',body={'comment':'No'})
        self.rejected(404,user=self.other,route=f'/api/student/periods/a/feedback/{key}/delete',body={})
    def test_statuses_and_optional_rating(self):
        self.assertEqual(self.call()[1]['module']['status'],'Feedback Open')
        self.now=899;self.assertEqual(self.call()[1]['module']['status'],'Closed')
        self.now=1100;self.assertEqual(self.call()[1]['module']['status'],'Not Submitted')
        self.now=1000
        self.call(route='/api/student/periods/a/feedback',body={'comment':'Optional rating'})
        self.now=1100
        self.assertEqual(self.call()[1]['module']['status'],'Submitted')
        self.assertFalse(self.call()[1]['module']['can_write'])

    def test_concurrent_duplicate_requests_have_one_winner(self):
        def submit_one(_):
            try:
                return self.call(route='/api/student/periods/a/feedback',body={'comment':'Concurrent'})[0]
            except AuthError as error:
                return error.status
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(submit_one,range(2))),[201,409])
