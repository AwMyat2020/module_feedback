"""Local persistence boundary. No cloud credentials or integrations."""
import sqlite3
from contextlib import closing
from pathlib import Path


def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def initialise(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db, db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
          role TEXT NOT NULL CHECK(role IN ('student','staff')),
          salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
          token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
          expires INTEGER NOT NULL
        );
        ''')
        db.executescript('''
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
        ''')
