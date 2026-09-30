"""Loopback-only local API. Run: python server/server.py"""
import json
import os
import time
from collections import defaultdict, deque
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit
from auth import AuthError, authenticate_account, new_session, session_user, revoke_session
from database import initialise
from core import execute
from analytics import analytics_request


def make_server(path, port=8001, origin='http://127.0.0.1:5173'):
    initialise(path)
    attempts = defaultdict(deque)
    lock = Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not log credentials, payloads or session cookies.

        def respond(self, status, value, cookie=None):
            payload = json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if cookie is not None:
                self.send_header('Set-Cookie', f'mfi_session={cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age={28800 if cookie else 0}')
            self.end_headers()
            self.wfile.write(payload)

        def token(self):
            try:
                cookies = SimpleCookie(self.headers.get('Cookie', ''))
                return cookies['mfi_session'].value if 'mfi_session' in cookies else ''
            except Exception:
                return ''

        def handle_api(self):
            try:
                host = urlsplit('http://' + self.headers.get('Host', '')).hostname
                if host not in ('localhost', '127.0.0.1'):
                    raise AuthError(403, 'Invalid host.')
                request_origin = self.headers.get('Origin')
                if request_origin and request_origin != origin:
                    raise AuthError(403, 'Cross-origin requests are not allowed.')
                route = urlsplit(self.path).path
                if self.command == 'POST':
                    if self.headers.get('X-Requested-With') != 'ModuleFeedbackInsight':
                        raise AuthError(403, 'Invalid request. Refresh and try again.')
                    if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                        raise AuthError(415, 'JSON required.')
                    try:
                        size = int(self.headers.get('Content-Length', '0'))
                        if not 0 < size <= 8192:
                            raise AuthError(413, 'Request too large or empty.')
                        body = json.loads(self.rfile.read(size))
                    except (ValueError, UnicodeError):
                        raise AuthError(400, 'Invalid JSON request.')
                    if not isinstance(body, dict):
                        raise AuthError(400, 'JSON object required.')
                    if route in ('/api/auth/register', '/api/auth/login'):
                        with lock:
                            bucket = attempts[self.client_address[0]]
                            now = time.monotonic()
                            while bucket and bucket[0] < now-300:
                                bucket.popleft()
                            if len(bucket) >= 20:
                                raise AuthError(429, 'Too many attempts. Try again in five minutes.')
                            bucket.append(now)
                        user = authenticate_account(path, route.rsplit('/', 1)[1], body)
                        token = new_session(path, user['userId'], self.token())
                        return self.respond(201 if route.endswith('register') else 200, {'user': user}, token)
                    if route == '/api/auth/logout':
                        revoke_session(path, self.token())
                        return self.respond(200, {'user': None}, '')
                user = session_user(path, self.token())
                if not user:
                    raise AuthError(401, 'Please sign in to continue.')
                if self.command == 'GET' and route == '/api/auth/me':
                    return self.respond(200, {'user': user})
                analysis = analytics_request(path, user, self.command, self.path)
                if analysis is not None:
                    return self.respond(*analysis)
                if route.startswith('/api/staff/') and user['role'] != 'staff':
                    raise AuthError(403, 'Staff access is required.')
                if (route.startswith('/api/student/') or route == '/api/feedback') and user['role'] != 'student':
                    raise AuthError(403, 'Student access is required.')
                result = execute(path, user, self.command, route, body if self.command == 'POST' else None)
                if result is not None:
                    return self.respond(*result)
                raise AuthError(404, 'Page or module not found.')
            except AuthError as error:
                self.respond(error.status, {'message': error.message})
            except Exception:
                self.respond(500, {'message': 'The local service encountered an error.'})

        do_GET = handle_api
        do_POST = handle_api

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    db_path = os.environ.get('MFI_DB_PATH', str(Path(__file__).parent / 'local-data' / 'auth.sqlite3'))
    port = int(os.environ.get('MFI_API_PORT', '8001'))
    origin = os.environ.get('MFI_WEB_ORIGIN', 'http://127.0.0.1:5173')
    print(f'Local authentication API: http://127.0.0.1:{port}', flush=True)
    make_server(db_path, port, origin).serve_forever()
