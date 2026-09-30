import json
import unittest
from contextlib import closing
import test_core
from analytics import aggregate, analytics_request, THEMES
from database import connect
from auth import AuthError


def response(theme='Workload',sentiment='positive',week=1,comment='Sample comment'):
    return dict(theme=theme,sentiment=sentiment,teaching_week=week,comment=comment)

class CalculationTests(unittest.TestCase):
    def test_module_and_filtered_threshold_boundaries(self):
        for count in [0,1,4]:
            result=aggregate([response()]*count)
            self.assertTrue(result['suppressed']);self.assertIsNone(result['total_responses'])
            for key in ['themes','weeks','comments','sentiment_percentages','selected_responses']:
                self.assertNotIn(key,result)
        self.assertFalse(aggregate([response()]*5)['suppressed'])
        result=aggregate([response()]*4+[response(theme='Assessment')]*6,{'theme':'Workload'})
        self.assertTrue(result['suppressed']);self.assertNotIn('comments',result)
    def test_correct_denominators_pending_and_sentiments(self):
        rows=[response()]*6+[response(theme='Assessment',sentiment='negative')]*6+[response(theme='Assessment',sentiment='neutral')]*6+[dict(comment='Pending')]*2
        result=aggregate(rows)
        self.assertEqual(result['total_responses'],20)
        self.assertEqual(result['analysed_responses'],18)
        self.assertEqual(result['sentiment_percentages'],dict(positive=33.3,neutral=33.3,negative=33.3))
        self.assertEqual(result['themes'][0]['mentions'],12)
        self.assertEqual(result['themes'][0]['response_percentage'],60)
        self.assertEqual(result['themes'][0]['sentiment_percentages']['negative'],50)
    def test_filters_combined_and_safe_comments(self):
        rows=[response()]*6+[response(week=2)]*6+[response(sentiment='negative')]*6
        result=aggregate(rows,dict(theme='Workload',sentiment='positive',teaching_week='2'))
        self.assertEqual(result['selected_responses'],6)
        self.assertEqual(result['weeks'][1]['total'],6)
        self.assertEqual(result['comments'],[dict(comment='Sample comment',theme='Workload',sentiment='positive',teaching_week=2)])
    def test_small_theme_week_and_comment_groups_suppressed(self):
        rows=[response()]*6+[response(theme='Assessment',week=2,comment='SECRET SMALL GROUP')]*4
        result=aggregate(rows)
        self.assertEqual(len(result['themes']),1)
        self.assertEqual(result['weeks'][1],dict(week=2,label='W2',suppressed=True,total=None))
        self.assertNotIn('SECRET SMALL GROUP',json.dumps(result))
        # Overall cohort is large but each detailed intersection is small.
        result=aggregate([response(week=i,comment='SMALL') for i in range(1,7)])
        self.assertFalse(result['suppressed']);self.assertEqual(result['comments'],[])
    def test_top_five_sorted_and_no_identity_projection(self):
        rows=[]
        for i,theme in enumerate(THEMES):
            rows += [dict(response(theme=theme),student_id='SECRET',email='SECRET',name='SECRET')]*(5+i)
        result=aggregate(rows)
        self.assertEqual(len(result['themes']),5)
        self.assertEqual(result['themes'][0]['theme'],'Others')
        self.assertNotIn('SECRET',json.dumps(result))
    def test_unanalysed_data_not_falsely_classified(self):
        result=aggregate([dict(comment='Unlabelled')]*20)
        self.assertTrue(result['suppressed']);self.assertNotIn('sentiment_percentages',result)

class AnalyticsAccessTests(unittest.TestCase):
    setUp=test_core.CoreTests.setUp
    tearDown=test_core.CoreTests.tearDown
    def test_access_and_filters(self):
        for user,url,status in [(self.student,'/api/staff/periods/a/analytics',403),
                                (self.staff,'/api/staff/periods/b/analytics',403),
                                (self.staff,'/api/staff/periods/missing/analytics',404),
                                (self.staff,'/api/staff/periods/a/analytics?theme=Invalid',400),
                                (self.staff,'/api/staff/periods/a/analytics?teaching_week=0',400),
                                (self.staff,'/api/staff/periods/a/analytics?sentiment=positive&sentiment=negative',400)]:
            with self.assertRaises(AuthError) as ctx: analytics_request(self.path,user,'GET',url)
            self.assertEqual(ctx.exception.status,status)
    def test_edit_invalidates_labels_delete_cascades(self):
        from core import execute
        def submit():
            key=execute(self.path,self.student,'POST','/api/student/periods/a/feedback',{'comment':'Original'},clock=lambda:1000)[1]['feedback']['id']
            with closing(connect(self.path)) as db,db:
                db.execute('INSERT INTO feedback_analysis VALUES (?,?,?,?,?,?,?)',(key,'positive',0.8,'Workload',0.9,1,'sample'))
            return key
        key=submit()
        execute(self.path,self.student,'POST',f'/api/student/periods/a/feedback/{key}/edit',{'comment':'Changed'},clock=lambda:1000)
        with closing(connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM feedback_analysis').fetchone()[0],0)
        execute(self.path,self.student,'POST',f'/api/student/periods/a/feedback/{key}/delete',{},clock=lambda:1000)
        key=submit()
        execute(self.path,self.student,'POST',f'/api/student/periods/a/feedback/{key}/delete',{},clock=lambda:1000)
        with closing(connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM feedback_analysis').fetchone()[0],0)
