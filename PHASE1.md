# Phase 1 — local authentication

Only authentication, stored roles and dashboard access are active. Existing module, feedback and analytics source files are preserved, but their workflows are not enabled in this phase. No AWS changes, Cognito, ML or email services.

## Start locally

Requirements: Node 22.22+ and Python 3.11+. The Python API uses only the standard library.

From the repository folder, in terminal 1:

```powershell
npm run dev:api
```

In terminal 2:

```powershell
npm run dev
```

Open **http://127.0.0.1:5173/** (use this exact host). Vite proxies `/api` to the loopback Python API on port 8001. Both servers must stay running. An unrelated service already using either port must be stopped or reconfigured first.

SQLite user/session data lives in `server/local-data/auth.sqlite3`, excluded from Git. It survives restarts. Never commit this directory. No password or session token is stored in localStorage; old demo sessions are ignored.

Optional Python environment settings: `MFI_DB_PATH`, `MFI_API_PORT`, `MFI_WEB_ORIGIN`. The defaults match Vite. Changing the API port requires updating the Vite proxy. Do not expose either server publicly. Cookies use HttpOnly and SameSite=Strict; this localhost HTTP setup is not a public HTTPS deployment.

## Manual checks

1. In a fresh/private browser window open `/` or `/staff`: you should reach `/login`.
2. Create an account with a sample `@sit.singaporetech.edu.sg` address and a new test password of 12–128 characters: Student Dashboard opens.
3. As student, visit `/staff` or `/lecturer`: expect 403. Reload `/student`: the session remains.
4. Sign out via the account menu. Visiting `/student` now returns to login.
5. Create a sample `@singaporetech.edu.sg` account: Staff Dashboard opens. `/student` and `/student/modules/INF2001/feedback` must be denied.
6. Try `@gmail.com`, `@singaporetech.edu.sg.evil.com`, or a fabricated subdomain: registration must reject them. Role fields supplied manually are ignored.
7. Try an incorrect password; login fails. Sign in with the correct one; the stored role determines the dashboard.

Use fabricated local test addresses, not someone else's real identity. No emails are sent, and mailbox ownership is not verified. This is project-specific registration, not SIT single sign-on; never use a university password. Domain assignment is implemented as requested and is not proof that a person owns that domain's mailbox.

## Tests

```powershell
npm test
npm run test:api
npm run build
```

Node tests verify route decisions and dashboard mapping. Python tests run a real temporary HTTP API and SQLite database: domain restrictions, role persistence, role escalation rejection, access checks, password verification, session revocation, duplicate registration and cross-origin rejection. Browser walkthrough verifies the actual redirects and layout.

## Boundaries

UI guards are for navigation. Protected API routes independently resolve the stored session and database role. Role values are `student` and `staff`. The old lecturer route redirects authorized staff to `/staff`; no public admin account exists.

Feedback/module actions remain unavailable, including to authorized students. Later phases must add their own ownership, assignment and deadline checks. The previous mock code is retained as reference, not as authentication authority.

API endpoints: POST `/api/auth/register`, POST `/api/auth/login`, POST `/api/auth/logout`, GET `/api/auth/me`, GET `/api/student/dashboard`, GET `/api/staff/dashboard`. Mutation requests require JSON and the `X-Requested-With: ModuleFeedbackInsight` header; unexpected browser origins are rejected.
