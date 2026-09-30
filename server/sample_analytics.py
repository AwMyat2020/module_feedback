"""Seed fictional feedback with fixed analysis labels. Never classifies user text."""
import os
import secrets
from pathlib import Path
from contextlib import closing
from database import connect
from sample_data import seed
from analytics import THEMES

def seed_analysis(path):
    seed(path)
    with closing(connect(path)) as db,db:
        period=db.execute("SELECT * FROM feedback_periods WHERE id='cloud-current'").fetchone()
        for theme_index,theme in enumerate(['Workload','Teaching Quality','Lab Instructions','Assessment','Learning Materials']):
            for week in range(1,4):
                sentiment=['positive','neutral','negative'][(theme_index+week)%3]
                texts={'positive':f'{theme} worked well and supported my learning.',
                       'neutral':f'{theme} was manageable, with some room for improvement.',
                       'negative':f'{theme} needs clearer expectations and more support.'}
                for number in range(6):
                    key=f'analysis-demo-{theme_index}-{week}-{number}'
                    # Non-login fixture user: random unusable password hash; no published credentials.
                    db.execute('INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?,?)',(key,'Synthetic respondent',key+'@sample.invalid','student',secrets.token_hex(16),'disabled-fixture',period['opens_at']))
                    db.execute('INSERT OR IGNORE INTO student_modules VALUES (?,?,?)',(key,'cloud',period['trimester_id']))
                    db.execute('INSERT OR IGNORE INTO feedback VALUES (?,?,?,?,?,?,?)',(key,period['id'],key,texts[sentiment]+f' Sample observation {number+1}.',None,period['opens_at'],period['opens_at']))
                    db.execute('INSERT OR IGNORE INTO feedback_analysis VALUES (?,?,?,?,?,?,?)',(key,sentiment,{'positive':0.8,'neutral':0,'negative':-0.8}[sentiment],theme,0.9,week,'sample'))
    print('90 fictional Cloud Computing responses with fixed sample labels ready. Existing feedback unchanged.')

if __name__=='__main__':
    seed_analysis(os.environ.get('MFI_DB_PATH',str(Path(__file__).parent/'local-data'/'auth.sqlite3')))
