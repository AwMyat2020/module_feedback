"""Local persistence boundary. No cloud credentials or integrations."""
import sqlite3
from contextlib import closing
from pathlib import Path

ACCOUNT_SCHEMA = '''
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL CHECK(role IN ('student','staff','admin')),
  salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
  expires INTEGER NOT NULL
);
'''

DOMAIN_SCHEMA = '''
CREATE TABLE IF NOT EXISTS trimesters (
  id TEXT PRIMARY KEY, name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS app_settings (
  id INTEGER PRIMARY KEY CHECK(id=1), current_trimester TEXT NOT NULL REFERENCES trimesters(id)
);
CREATE TABLE IF NOT EXISTS modules (
  id TEXT PRIMARY KEY, code TEXT NOT NULL, name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS student_modules (
  user_id TEXT NOT NULL REFERENCES users(id), module_id TEXT NOT NULL REFERENCES modules(id),
  trimester_id TEXT NOT NULL REFERENCES trimesters(id), PRIMARY KEY(user_id,module_id,trimester_id)
);
CREATE TABLE IF NOT EXISTS staff_modules (
  user_id TEXT NOT NULL REFERENCES users(id), module_id TEXT NOT NULL REFERENCES modules(id),
  trimester_id TEXT NOT NULL REFERENCES trimesters(id), PRIMARY KEY(user_id,module_id,trimester_id)
);
CREATE TABLE IF NOT EXISTS feedback_periods (
  id TEXT PRIMARY KEY, module_id TEXT NOT NULL REFERENCES modules(id),
  trimester_id TEXT NOT NULL REFERENCES trimesters(id), opens_at INTEGER NOT NULL,
  deadline INTEGER NOT NULL CHECK(deadline>opens_at), UNIQUE(module_id,trimester_id)
);
CREATE TABLE IF NOT EXISTS feedback (
  id TEXT PRIMARY KEY, period_id TEXT NOT NULL REFERENCES feedback_periods(id),
  student_id TEXT NOT NULL REFERENCES users(id), comment TEXT NOT NULL,
  rating INTEGER CHECK(rating IS NULL OR rating BETWEEN 1 AND 5),
  created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
  UNIQUE(student_id,period_id)
);
CREATE TABLE IF NOT EXISTS feedback_analysis (
  feedback_id TEXT PRIMARY KEY REFERENCES feedback(id) ON DELETE CASCADE,
  sentiment TEXT NOT NULL CHECK(sentiment IN ('positive','neutral','negative')),
  sentiment_score REAL NOT NULL CHECK(sentiment_score BETWEEN -1 AND 1),
  theme TEXT NOT NULL, theme_confidence REAL NOT NULL CHECK(theme_confidence BETWEEN 0 AND 1),
  teaching_week INTEGER NOT NULL CHECK(teaching_week BETWEEN 1 AND 14),
  source TEXT NOT NULL DEFAULT 'sample'
);
'''

# Reminder sends store a recipient COUNT only. Storing the addressed students
# would re-create, in the administrator's own audit trail, the submitted/not
# submitted split that the reminder feature exists to keep hidden.
ADMIN_SCHEMA = '''
CREATE TABLE IF NOT EXISTS reminder_log (
  id TEXT PRIMARY KEY, period_id TEXT NOT NULL REFERENCES feedback_periods(id),
  sent_by TEXT NOT NULL REFERENCES users(id), sent_at INTEGER NOT NULL,
  recipients INTEGER NOT NULL CHECK(recipients>=0)
);
CREATE TABLE IF NOT EXISTS admin_audit (
  id TEXT PRIMARY KEY, actor_id TEXT NOT NULL REFERENCES users(id),
  action TEXT NOT NULL, target TEXT NOT NULL, detail TEXT NOT NULL, created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS reminder_log_period ON reminder_log(period_id, sent_at);
CREATE INDEX IF NOT EXISTS admin_audit_time ON admin_audit(created_at);
'''


def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def widen_user_roles(db):
    """Admit the 'admin' role on databases created before it existed.

    SQLite cannot ALTER a CHECK constraint, so the documented rebuild is the
    only route: copy into a new table, drop the old one, rename. Foreign keys
    are suspended for the swap because every dependent table references users.
    """
    row = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
    if row is None or "'admin'" in row['sql']:
        return
    db.execute('PRAGMA foreign_keys=OFF')
    try:
        with db:
            db.executescript('''
            CREATE TABLE users_rebuilt (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
              role TEXT NOT NULL CHECK(role IN ('student','staff','admin')),
              salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at INTEGER NOT NULL
            );
            INSERT INTO users_rebuilt SELECT id,name,email,role,salt,password_hash,created_at FROM users;
            DROP TABLE users;
            ALTER TABLE users_rebuilt RENAME TO users;
            ''')
        if db.execute('PRAGMA foreign_key_check').fetchone() is not None:
            raise RuntimeError('Role migration left orphaned rows; the database was not changed.')
    finally:
        db.execute('PRAGMA foreign_keys=ON')


def add_module_columns(db):
    """Archiving is additive, so a plain ADD COLUMN is enough here."""
    columns = {row['name'] for row in db.execute('PRAGMA table_info(modules)')}
    if 'archived' not in columns:
        db.execute('ALTER TABLE modules ADD COLUMN archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1))')


def initialise(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db:
        with db:
            db.executescript(ACCOUNT_SCHEMA)
            db.executescript(DOMAIN_SCHEMA)
        # Migrations run between the base schema and the tables that depend on it.
        widen_user_roles(db)
        with db:
            add_module_columns(db)
            db.executescript(ADMIN_SCHEMA)
