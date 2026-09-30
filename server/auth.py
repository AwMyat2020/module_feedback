"""Authentication rules; roles always come from exact institutional domains."""
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from contextlib import closing
from database import connect

DOMAIN_MESSAGE = 'Use @sit.singaporetech.edu.sg for students or @singaporetech.edu.sg for staff.'
DOMAINS = {'sit.singaporetech.edu.sg': 'student', 'singaporetech.edu.sg': 'staff'}


class AuthError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def email_role(value):
    if not isinstance(value, str):
        raise AuthError(400, DOMAIN_MESSAGE)
    email = value.strip().lower()
    if len(email) > 254 or not re.fullmatch(r'[a-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[^@\s]+', email):
        raise AuthError(400, DOMAIN_MESSAGE)
    role = DOMAINS.get(email.split('@')[1])
    if not role:
        raise AuthError(400, DOMAIN_MESSAGE)
    return email, role


def digest(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600_000).hex()


def public_user(row):
    return dict(userId=row['id'], name=row['name'], email=row['email'], role=row['role'])


def authenticate_account(path, action, body):
    email, role = email_role(body.get('email'))
    password = body.get('password')
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise AuthError(400, 'Use a password of 12–128 characters.')
    with closing(connect(path)) as db, db:
        if action == 'register':
            name = body.get('name')
            if not isinstance(name, str) or not 2 <= len(name.strip()) <= 60:
                raise AuthError(400, 'Display name must be 2–60 characters.')
            salt = secrets.token_hex(16)
            try:
                db.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?)',
                    (secrets.token_hex(16), name.strip(), email, role, salt, digest(password, salt), int(time.time())))
            except sqlite3.IntegrityError:
                raise AuthError(409, 'An account already uses this email. Please sign in.')
        row = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        if action == 'login':
            calculated = digest(password, row['salt'] if row else '00' * 16)
            if row is None or not hmac.compare_digest(calculated, row['password_hash']):
                raise AuthError(401, 'Email or password is incorrect.')
        return public_user(row)


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def new_session(path, user_id, old_token=''):
    token = secrets.token_urlsafe(32)
    with closing(connect(path)) as db, db:
        db.execute('DELETE FROM sessions WHERE expires<=? OR token_hash=?', (int(time.time()), token_hash(old_token)))
        db.execute('INSERT INTO sessions VALUES (?,?,?)', (token_hash(token), user_id, int(time.time()) + 8*3600))
    return token


def session_user(path, token):
    with closing(connect(path)) as db:
        row = db.execute('SELECT users.* FROM sessions JOIN users ON users.id=sessions.user_id WHERE token_hash=? AND expires>?',
                         (token_hash(token), int(time.time()))).fetchone()
        return public_user(row) if row else None


def revoke_session(path, token):
    with closing(connect(path)) as db, db:
        db.execute('DELETE FROM sessions WHERE token_hash=?', (token_hash(token),))
