"""Assignment and feedback rules. Every operation resolves the authenticated user."""
import re
import secrets
import time
from contextlib import closing
from auth import AuthError
from database import connect


def period_for(db, user, period_id):
    row = db.execute('''SELECT p.*, m.code, m.name, t.name AS trimester
        FROM feedback_periods p JOIN modules m ON m.id=p.module_id
        JOIN trimesters t ON t.id=p.trimester_id WHERE p.id=?''', (period_id,)).fetchone()
    if row is None:
        raise AuthError(404, 'Module or feedback period not found.')
    table = 'student_modules' if user['role'] == 'student' else 'staff_modules'
    assigned = db.execute(f'SELECT 1 FROM {table} WHERE user_id=? AND module_id=? AND trimester_id=?',
                          (user['userId'], row['module_id'], row['trimester_id'])).fetchone()
    if not assigned:
        raise AuthError(403, 'You are not assigned to this module.')
    return row


def own_feedback(db, user, period_id):
    row = db.execute('SELECT id,comment,rating,updated_at FROM feedback WHERE period_id=? AND student_id=?',
                     (period_id, user['userId'])).fetchone()
    return dict(row) if row else None


def describe(db, row, user, now):
    result = dict(row)
    result['lecturers'] = [r['name'] for r in db.execute('''SELECT u.name FROM staff_modules a
        JOIN users u ON u.id=a.user_id WHERE a.module_id=? AND a.trimester_id=? ORDER BY u.name''',
        (row['module_id'], row['trimester_id']))]
    result['period_state'] = 'Open' if row['opens_at'] <= now < row['deadline'] else ('Upcoming' if now < row['opens_at'] else 'Closed')
    result['can_write'] = user['role'] == 'student' and result['period_state'] == 'Open'
    if user['role'] == 'student':
        result['feedback'] = own_feedback(db, user, row['id'])
        result['status'] = ('Submitted' if result['feedback'] else 'Feedback Open' if result['period_state'] == 'Open'
                            else 'Not Submitted' if now >= row['deadline'] else 'Closed')
    return result


def execute(path, user, method, route, body=None, clock=time.time):
    """Return HTTP status and payload. None means this is not a core route."""
    match = re.fullmatch(r'/api/(student|staff)/periods/([^/]+)(?:/feedback(?:/([^/]+)/(edit|delete))?)?', route)
    dashboard = re.fullmatch(r'/api/(student|staff)/dashboard', route)
    if not match and not dashboard:
        return None
    role = (match or dashboard)[1]
    if user['role'] != role:
        raise AuthError(403, f'{role.capitalize()} access is required.')
    with closing(connect(path)) as db, db:
        # Serialise writes before reading ownership/deadlines and checking uniqueness.
        # The timestamp is taken after acquiring the lock, not when a request starts.
        if method != 'GET':
            db.execute('BEGIN IMMEDIATE')
        now = int(clock())
        if dashboard:
            if method != 'GET':
                raise AuthError(405, 'Method not allowed.')
            term = db.execute('SELECT t.* FROM app_settings s JOIN trimesters t ON t.id=s.current_trimester WHERE s.id=1').fetchone()
            periods = []
            if term:
                table = 'student_modules' if role == 'student' else 'staff_modules'
                # Archived modules stay in the record for the administrator but
                # drop off student and staff dashboards.
                rows = db.execute(f'''SELECT p.id FROM feedback_periods p JOIN {table} a
                    ON a.module_id=p.module_id AND a.trimester_id=p.trimester_id
                    JOIN modules m ON m.id=p.module_id
                    WHERE a.user_id=? AND p.trimester_id=? AND m.archived=0 ORDER BY p.id''',
                    (user['userId'], term['id'])).fetchall()
                periods = [describe(db, period_for(db, user, r['id']), user, now) for r in rows]
            return 200, {'trimester': dict(term) if term else None, 'modules': periods}
        period_id, feedback_id, action = match[2], match[3], match[4]
        row = period_for(db, user, period_id)
        if method == 'GET' and not route.endswith('/feedback') and not action:
            result = describe(db, row, user, now)
            if role == 'staff':
                # Raw staff feedback is no longer exposed: analytics applies privacy checks.
                result['feedback'] = []
                result['feedback_notice'] = 'Use the privacy-protected analytics view.'
            return 200, {'module': result}
        if role != 'student':
            raise AuthError(403, 'Only enrolled students can change feedback.')
        if method != 'POST' or (not action and not route.endswith('/feedback')):
            raise AuthError(405, 'Method not allowed.')
        existing = own_feedback(db, user, period_id)
        if action and (not existing or existing['id'] != feedback_id):
            raise AuthError(404, 'Feedback not found or already deleted. Refresh the page.')
        if not row['opens_at'] <= now < row['deadline']:
            raise AuthError(409, 'Feedback is closed. Changes are allowed only between the open date and deadline.')
        if not action and existing:
            raise AuthError(409, 'You have already submitted feedback for this period.')
        if action == 'delete':
            db.execute('DELETE FROM feedback WHERE id=? AND student_id=?', (feedback_id, user['userId']))
            return 200, {'message': 'Feedback deleted.'}
        comment, rating = (body or {}).get('comment'), (body or {}).get('rating')
        if not isinstance(comment, str) or not 1 <= len(comment.strip()) <= 2000:
            raise AuthError(400, 'Write feedback between 1 and 2,000 characters.')
        if rating is not None and (type(rating) is not int or not 1 <= rating <= 5):
            raise AuthError(400, 'Rating must be a whole number from 1 to 5, or omitted.')
        if action == 'edit':
            # A previously populated label must not describe a changed comment.
            db.execute('DELETE FROM feedback_analysis WHERE feedback_id=?', (feedback_id,))
            db.execute('UPDATE feedback SET comment=?,rating=?,updated_at=? WHERE id=? AND student_id=?',
                       (comment.strip(), rating, now, feedback_id, user['userId']))
        else:
            db.execute('INSERT INTO feedback VALUES (?,?,?,?,?,?,?)',
                       (secrets.token_hex(16), period_id, user['userId'], comment.strip(), rating, now, now))
        return (200 if action else 201), {'feedback': own_feedback(db, user, period_id)}
