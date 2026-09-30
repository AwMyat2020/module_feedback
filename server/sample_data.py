"""Explicit local sample setup; never resets passwords, feedback or existing dates."""
import argparse
import getpass
import os
import time
from contextlib import closing
from pathlib import Path
from auth import authenticate_account
from database import connect, initialise

ACCOUNTS = [
    ('demo.student@sit.singaporetech.edu.sg', 'Jamie Tan', ['cloud','database','security']),
    ('demo.other@sit.singaporetech.edu.sg', 'Alex Lim', ['software']),
    ('demo.staff@singaporetech.edu.sg', 'Dr Lee (Sample)', ['cloud','database','security']),
    ('demo.other@singaporetech.edu.sg', 'Dr Wong (Sample)', ['software']),
]

def seed(path):
    initialise(path)
    with closing(connect(path)) as db:
        missing = any(not db.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone() for email,_,_ in ACCOUNTS)
    password = None
    if missing:
        password = os.environ.get('MFI_DEMO_PASSWORD') or getpass.getpass('Choose a local sample-account password (12-128 characters): ')
        if not 12 <= len(password) <= 128:
            raise SystemExit('Sample password must be 12-128 characters. Nothing was seeded.')
    now = int(time.time())
    term = 'sample-current'
    with closing(connect(path)) as db, db:
        db.execute('INSERT OR IGNORE INTO trimesters VALUES (?,?)', (term, 'AY2026/27 · Trimester 1 (sample)'))
        db.execute('INSERT OR IGNORE INTO app_settings VALUES (1,?)', (term,))
        for key, code, name, opens, deadline in [
            ('cloud','INF2006','Cloud Computing', now-86400, now+14*86400),
            ('database','INF2003','Database Systems',now-14*86400,now-86400),
            ('security','INF2008','Information Security',now+7*86400,now+21*86400),
            ('software','INF2002','Software Engineering',now-86400,now+14*86400),
        ]:
            db.execute('INSERT OR IGNORE INTO modules VALUES (?,?,?)',(key,code,name))
            db.execute('INSERT OR IGNORE INTO feedback_periods VALUES (?,?,?,?,?)',(key+'-current',key,term,opens,deadline))
    for email,name,modules in ACCOUNTS:
        with closing(connect(path)) as db:
            row = db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        if row is None:
            user = authenticate_account(path,'register',dict(email=email,name=name,password=password))
        else:
            user = dict(userId=row['id'],role=row['role'])
        assign(path,email,modules)
    print('Sample accounts and assignments ready. Existing accounts, feedback and dates preserved.')


def assign(path, email, modules):
    with closing(connect(path)) as db, db:
        user = db.execute('SELECT * FROM users WHERE email=?',(email.strip().lower(),)).fetchone()
        term = db.execute('SELECT current_trimester FROM app_settings WHERE id=1').fetchone()
        if not user or not term:
            raise SystemExit('Register the account first and run sample setup.')
        table = 'student_modules' if user['role']=='student' else 'staff_modules'
        for module in modules:
            if not db.execute('SELECT 1 FROM feedback_periods WHERE module_id=? AND trimester_id=?',(module,term[0])).fetchone():
                raise SystemExit('Unknown module in current trimester: '+module)
        for module in modules:
            db.execute(f'INSERT OR IGNORE INTO {table} VALUES (?,?,?)',(user['id'],module,term[0]))

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assign-email')
    parser.add_argument('--modules',nargs='+',choices=['cloud','database','security','software'])
    args=parser.parse_args()
    path=os.environ.get('MFI_DB_PATH',str(Path(__file__).parent/'local-data'/'auth.sqlite3'))
    if args.assign_email:
        if not args.modules: parser.error('--modules is required with --assign-email')
        assign(path,args.assign_email,args.modules)
        print('Assignments added.')
    else: seed(path)
