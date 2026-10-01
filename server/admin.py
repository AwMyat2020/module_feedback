"""Administrator operations: modules, rosters, trimesters, deadlines, reminders.

Privacy boundary. Nothing in this module may return feedback text, an
individual sentiment score, a theme, or the identity of a respondent. An
administrator is limited to module metadata, rosters, response counts and a
module-level aggregate alert flag. The queries below select counts rather than
rows wherever a row set would contain a respondent, so a later change to a
response shape cannot accidentally widen what is exposed.
"""
import re
import secrets
import time
from contextlib import closing
from urllib.parse import urlsplit
from auth import AuthError
from analytics import THRESHOLD
from database import connect

# A module is flagged only when negative sentiment dominates AND enough
# responses exist that the flag cannot single anybody out.
NEGATIVE_ALERT_PERCENT = 70.0
MAX_EXTENSION_DAYS = 90
CODE = re.compile(r'[A-Za-z]{2,6}[0-9]{3,6}')
MODULE_ACTION = re.compile(r'/api/admin/modules/([^/]+)/(archive|deadline|roster|reminders)')


def text(body, key, low, high, label):
    value = (body or {}).get(key)
    if not isinstance(value, str) or not low <= len(value.strip()) <= high:
        raise AuthError(400, f'{label} must be {low} to {high} characters.')
    return value.strip()


def whole(body, key, low, high, label):
    value = (body or {}).get(key)
    if type(value) is not int or not low <= value <= high:
        raise AuthError(400, f'{label} must be a whole number from {low} to {high}.')
    return value


def flag(body, key, label):
    value = (body or {}).get(key)
    if type(value) is not bool:
        raise AuthError(400, f'{label} must be true or false.')
    return value


def audit(db, user, action, target, detail, now):
    db.execute('INSERT INTO admin_audit VALUES (?,?,?,?,?,?)',
               (secrets.token_hex(16), user['userId'], action, target, detail, now))


def state_of(row, now):
    return 'Open' if row['opens_at'] <= now < row['deadline'] else ('Upcoming' if now < row['opens_at'] else 'Closed')


def active_trimester(db):
    row = db.execute('''SELECT t.* FROM app_settings s JOIN trimesters t
        ON t.id=s.current_trimester WHERE s.id=1''').fetchone()
    if row is None:
        raise AuthError(409, 'No active trimester is configured. Create one first.')
    return row


def alert_for(analysed, negative):
    """Aggregate only. The caller must never pass the negative count onward."""
    base = {'threshold_percent': NEGATIVE_ALERT_PERCENT, 'minimum_responses': THRESHOLD}
    if analysed < THRESHOLD:
        return {**base, 'requires_attention': False, 'status': 'Insufficient data',
                'explanation': f'Fewer than {THRESHOLD} analysed responses, so no module-level flag is produced.'}
    if 100 * negative / analysed > NEGATIVE_ALERT_PERCENT:
        return {**base, 'requires_attention': True, 'status': 'Requires Attention',
                'explanation': f'Aggregate negative sentiment exceeds {NEGATIVE_ALERT_PERCENT:.0f}% of analysed responses for this module.'}
    return {**base, 'requires_attention': False, 'status': 'Normal',
            'explanation': f'Aggregate negative sentiment is at or below {NEGATIVE_ALERT_PERCENT:.0f}%.'}


def module_in(db, module_id):
    row = db.execute('SELECT * FROM modules WHERE id=?', (module_id,)).fetchone()
    if row is None:
        raise AuthError(404, 'Module not found.')
    return row


def period_in(db, module_id, trimester_id):
    row = db.execute('SELECT * FROM feedback_periods WHERE module_id=? AND trimester_id=?',
                     (module_id, trimester_id)).fetchone()
    if row is None:
        raise AuthError(404, 'This module has no feedback period in the active trimester.')
    return row


def module_metrics(db, term_id, now):
    """Per-module counts and the aggregate alert, for one trimester."""
    rows = db.execute('''SELECT m.id, m.code, m.name, m.archived,
          p.id AS period_id, p.opens_at, p.deadline,
          (SELECT COUNT(*) FROM student_modules sm WHERE sm.module_id=m.id AND sm.trimester_id=?) AS roster_size,
          (SELECT COUNT(*) FROM feedback f WHERE f.period_id=p.id) AS responses,
          (SELECT COUNT(*) FROM feedback f JOIN feedback_analysis a ON a.feedback_id=f.id
             WHERE f.period_id=p.id) AS analysed,
          (SELECT COUNT(*) FROM feedback f JOIN feedback_analysis a ON a.feedback_id=f.id
             WHERE f.period_id=p.id AND a.sentiment='negative') AS negative,
          (SELECT MAX(sent_at) FROM reminder_log r WHERE r.period_id=p.id) AS last_reminder
        FROM modules m LEFT JOIN feedback_periods p
          ON p.module_id=m.id AND p.trimester_id=?
        ORDER BY m.code''', (term_id, term_id)).fetchall()
    result = []
    for row in rows:
        lecturers = [r['name'] for r in db.execute('''SELECT u.name FROM staff_modules a
            JOIN users u ON u.id=a.user_id WHERE a.module_id=? AND a.trimester_id=? ORDER BY u.name''',
            (row['id'], term_id))]
        responses = row['responses'] or 0
        roster = row['roster_size'] or 0
        # 'analysed' and 'negative' stay local: only the derived flag is published.
        result.append({
            'module_id': row['id'], 'code': row['code'], 'name': row['name'],
            'archived': bool(row['archived']), 'lecturers': lecturers,
            'period_id': row['period_id'], 'opens_at': row['opens_at'], 'deadline': row['deadline'],
            'period_state': state_of(row, now) if row['period_id'] else 'Not scheduled',
            'roster_size': roster, 'responses': responses, 'outstanding': max(roster - responses, 0),
            'response_rate': round(100 * responses / roster, 1) if roster else None,
            'last_reminder': row['last_reminder'],
            'alert': alert_for(row['analysed'] or 0, row['negative'] or 0),
        })
    return result


def health(path, now):
    started = time.perf_counter()
    try:
        with closing(connect(path)) as db:
            users = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            modules = db.execute('SELECT COUNT(*) FROM modules').fetchone()[0]
            configured = db.execute('SELECT COUNT(*) FROM app_settings WHERE id=1').fetchone()[0]
        database = {'status': 'healthy', 'latency_ms': round((time.perf_counter() - started) * 1000, 1),
                    'users': users, 'modules': modules, 'trimester_configured': bool(configured)}
    except Exception:
        # The reason is withheld on purpose: a file path or driver string in an
        # error message is more use to an attacker than to an administrator.
        database = {'status': 'unavailable', 'latency_ms': None, 'users': None, 'modules': None,
                    'trimester_configured': False}
    return 200, {'health': {'checked_at': now,
                            'api': {'status': 'healthy', 'detail': 'Loopback API responded to this request.'},
                            'database': database}}


def create_module(db, user, body, term, now):
    code = text(body, 'code', 2, 16, 'Module code').upper()
    if not CODE.fullmatch(code):
        raise AuthError(400, 'Module code must look like INF2006: two to six letters followed by three to six digits.')
    name = text(body, 'name', 2, 120, 'Module name')
    if db.execute('SELECT 1 FROM modules WHERE code=? COLLATE NOCASE', (code,)).fetchone():
        raise AuthError(409, 'A module already uses this code.')
    opens_at = body.get('opens_at', now)
    deadline = body.get('deadline', now + 14 * 86400)
    if type(opens_at) is not int or type(deadline) is not int or not 0 < opens_at < deadline:
        raise AuthError(400, 'Provide opens_at and deadline as whole seconds, with the deadline after the opening.')
    if deadline - opens_at > 365 * 86400:
        raise AuthError(400, 'A feedback period cannot span more than a year.')
    module_id, period_id = secrets.token_hex(8), secrets.token_hex(8)
    db.execute('INSERT INTO modules (id,code,name,archived) VALUES (?,?,?,0)', (module_id, code, name))
    db.execute('INSERT INTO feedback_periods VALUES (?,?,?,?,?)', (period_id, module_id, term['id'], opens_at, deadline))
    audit(db, user, 'module.create', module_id, f'{code} in {term["id"]}', now)
    return 201, {'module': {'module_id': module_id, 'code': code, 'name': name, 'archived': False,
                            'period_id': period_id, 'opens_at': opens_at, 'deadline': deadline},
                 'message': f'{code} created with a feedback period in {term["name"]}. Assign people to build its roster.'}


def set_archived(db, user, module_id, body, now):
    module = module_in(db, module_id)
    archived = flag(body, 'archived', 'Archived')
    db.execute('UPDATE modules SET archived=? WHERE id=?', (1 if archived else 0, module_id))
    audit(db, user, 'module.archive' if archived else 'module.restore', module_id, module['code'], now)
    verb = 'archived' if archived else 'restored'
    return 200, {'module_id': module_id, 'archived': archived,
                 'message': f'{module["code"]} {verb}. Archived modules stay in the record '
                            f'but leave student and staff dashboards.'}


def set_deadline(db, user, module_id, body, term, now):
    module = module_in(db, module_id)
    period = period_in(db, module_id, term['id'])
    if 'deadline' in (body or {}):
        deadline = whole(body, 'deadline', period['opens_at'] + 1, period['opens_at'] + 365 * 86400, 'Deadline')
    else:
        days = whole(body, 'extend_days', 1, MAX_EXTENSION_DAYS, 'Extension in days')
        # Extend from whichever is later, so extending a lapsed deadline gives a
        # period that is open from now rather than one that is still in the past.
        deadline = max(period['deadline'], now) + days * 86400
        if deadline - period['opens_at'] > 365 * 86400:
            raise AuthError(400, 'A feedback period cannot span more than a year.')
    db.execute('UPDATE feedback_periods SET deadline=? WHERE id=?', (deadline, period['id']))
    audit(db, user, 'period.deadline', module_id, f'{period["deadline"]} -> {deadline}', now)
    state = state_of({'opens_at': period['opens_at'], 'deadline': deadline}, now)
    return 200, {'module_id': module_id, 'code': module['code'], 'period_id': period['id'],
                 'previous_deadline': period['deadline'], 'deadline': deadline, 'period_state': state,
                 'message': f'{module["code"]} deadline moved. Feedback is now {state.lower()}.'}


def roster(db, module_id, term_id):
    module_in(db, module_id)
    people = []
    for table, role in (('student_modules', 'student'), ('staff_modules', 'staff')):
        # Names and roles only. Submission status is never joined in here: the
        # roster is the one admin view where it would be directly attributable.
        people += [{'user_id': r['id'], 'name': r['name'], 'email': r['email'], 'role': role}
                   for r in db.execute(f'''SELECT u.id,u.name,u.email FROM {table} a
                       JOIN users u ON u.id=a.user_id WHERE a.module_id=? AND a.trimester_id=?
                       ORDER BY u.name''', (module_id, term_id))]
    return 200, {'module_id': module_id, 'roster': people}


def change_roster(db, user, module_id, body, term, now):
    module = module_in(db, module_id)
    action = (body or {}).get('action')
    if action not in ('add', 'remove'):
        raise AuthError(400, 'Action must be add or remove.')
    email = text(body, 'email', 3, 254, 'Email').lower()
    person = db.execute('SELECT id,name,role FROM users WHERE email=?', (email,)).fetchone()
    if person is None:
        raise AuthError(404, 'No registered account uses this email.')
    if person['role'] == 'admin':
        raise AuthError(400, 'Administrator accounts are not enrolled in modules.')
    table = 'student_modules' if person['role'] == 'student' else 'staff_modules'
    if action == 'add':
        period_in(db, module_id, term['id'])
        db.execute(f'INSERT OR IGNORE INTO {table} VALUES (?,?,?)', (person['id'], module_id, term['id']))
    else:
        # Submitted feedback is deliberately left untouched and removal always
        # reports success. Refusing to remove a student who had already
        # responded would disclose that they responded.
        db.execute(f'DELETE FROM {table} WHERE user_id=? AND module_id=? AND trimester_id=?',
                   (person['id'], module_id, term['id']))
    audit(db, user, f'roster.{action}', module_id, f'{person["role"]} in {module["code"]}', now)
    moved = 'assigned to' if action == 'add' else 'removed from'
    return 200, {'module_id': module_id, 'action': action,
                 'message': f'{person["name"]} {moved} {module["code"]}.'}


def send_reminders(db, user, module_id, term, now):
    module = module_in(db, module_id)
    period = period_in(db, module_id, term['id'])
    state = state_of(period, now)
    if state != 'Open':
        raise AuthError(409, f'Feedback for {module["code"]} is {state.lower()}. '
                             f'Extend the deadline before sending reminders.')
    # COUNT, never the rows. The addressed students are resolved inside SQLite
    # and their identities never enter this process, so no later serialisation
    # mistake can expose who has yet to submit.
    recipients = db.execute('''SELECT COUNT(*) FROM student_modules sm
        WHERE sm.module_id=? AND sm.trimester_id=? AND NOT EXISTS
          (SELECT 1 FROM feedback f WHERE f.period_id=? AND f.student_id=sm.user_id)''',
        (module_id, term['id'], period['id'])).fetchone()[0]
    db.execute('INSERT INTO reminder_log VALUES (?,?,?,?,?)',
               (secrets.token_hex(16), period['id'], user['userId'], now, recipients))
    audit(db, user, 'reminder.send', module_id, f'{recipients} recipients', now)
    return 200, {'module_id': module_id, 'code': module['code'], 'recipients': recipients, 'sent_at': now,
                 'delivery': 'mock',
                 'message': f'Reminder queued for {recipients} student(s) who have not yet submitted. '
                            f'Recipients are not disclosed.'}


def directory(db):
    rows = db.execute('''SELECT u.id,u.name,u.email,u.role,u.created_at,
        (SELECT COUNT(*) FROM student_modules s WHERE s.user_id=u.id) +
        (SELECT COUNT(*) FROM staff_modules t WHERE t.user_id=u.id) AS assignments
        FROM users u ORDER BY u.role, u.name''').fetchall()
    people = [{'user_id': r['id'], 'name': r['name'], 'email': r['email'], 'role': r['role'],
               'created_at': r['created_at'], 'assignments': r['assignments']} for r in rows]
    counts = {role: sum(1 for p in people if p['role'] == role) for role in ('student', 'staff', 'admin')}
    return 200, {'users': people, 'counts': counts, 'total': len(people)}


def set_trimester(db, user, body, now):
    trimester_id = text(body, 'trimester_id', 1, 64, 'Trimester')
    if not db.execute('SELECT 1 FROM trimesters WHERE id=?', (trimester_id,)).fetchone():
        raise AuthError(404, 'Trimester not found.')
    db.execute('INSERT INTO app_settings VALUES (1,?) ON CONFLICT(id) DO UPDATE SET current_trimester=?',
               (trimester_id, trimester_id))
    audit(db, user, 'trimester.activate', trimester_id, 'active trimester changed', now)
    return 200, {'current_trimester': trimester_id, 'message': 'Active trimester updated for every dashboard.'}


def create_trimester(db, user, body, now):
    name = text(body, 'name', 2, 80, 'Trimester name')
    trimester_id = secrets.token_hex(8)
    db.execute('INSERT INTO trimesters VALUES (?,?)', (trimester_id, name))
    audit(db, user, 'trimester.create', trimester_id, name, now)
    return 201, {'trimester': {'id': trimester_id, 'name': name},
                 'message': f'{name} created. Set it as active to switch every dashboard to it.'}


def admin_request(path, user, method, url, body=None, clock=time.time):
    """Return HTTP status and payload. None means this is not an admin route.

    The caller owns the role gate; the repeat check below keeps this module
    safe to reuse elsewhere and safe to unit test on its own.
    """
    route = urlsplit(url).path
    if route != '/api/admin' and not route.startswith('/api/admin/'):
        return None
    if user['role'] != 'admin':
        raise AuthError(403, 'Administrator access is required.')
    if method not in ('GET', 'POST'):
        raise AuthError(405, 'Method not allowed.')
    now = int(clock())
    if route == '/api/admin/health' and method == 'GET':
        return health(path, now)
    with closing(connect(path)) as db, db:
        # Serialise writes before reading the state they depend on, matching core.
        if method != 'GET':
            db.execute('BEGIN IMMEDIATE')
        if route == '/api/admin/users' and method == 'GET':
            return directory(db)
        if route == '/api/admin/trimesters':
            if method == 'GET':
                current = db.execute('SELECT current_trimester FROM app_settings WHERE id=1').fetchone()
                return 200, {'trimesters': [dict(r) for r in db.execute('SELECT id,name FROM trimesters ORDER BY name')],
                             'current_trimester': current['current_trimester'] if current else None}
            return create_trimester(db, user, body, now)
        if route == '/api/admin/trimester' and method == 'POST':
            return set_trimester(db, user, body, now)
        match = MODULE_ACTION.fullmatch(route)
        # Resolve the route before the trimester, so an unknown path reports 404
        # rather than the "no active trimester" conflict of a route that exists.
        if not match and route not in ('/api/admin/overview', '/api/admin/modules'):
            return None
        term = active_trimester(db)
        if route == '/api/admin/overview' and method == 'GET':
            modules = module_metrics(db, term['id'], now)
            live = [m for m in modules if not m['archived']]
            expected = sum(m['roster_size'] for m in live)
            received = sum(m['responses'] for m in live)
            return 200, {'trimester': dict(term), 'modules': modules, 'summary': {
                'active_modules': len(live), 'archived_modules': len(modules) - len(live),
                'expected_responses': expected, 'responses': received,
                'response_rate': round(100 * received / expected, 1) if expected else None,
                'modules_requiring_attention': sum(1 for m in live if m['alert']['requires_attention'])}}
        if route == '/api/admin/modules':
            if method == 'GET':
                return 200, {'trimester': dict(term), 'modules': module_metrics(db, term['id'], now)}
            return create_module(db, user, body, term, now)
        if match:
            module_id, action = match[1], match[2]
            if action == 'roster' and method == 'GET':
                return roster(db, module_id, term['id'])
            if method != 'POST':
                raise AuthError(405, 'Method not allowed.')
            if action == 'archive':
                return set_archived(db, user, module_id, body, now)
            if action == 'deadline':
                return set_deadline(db, user, module_id, body, term, now)
            if action == 'roster':
                return change_roster(db, user, module_id, body, term, now)
            return send_reminders(db, user, module_id, term, now)
    return None
