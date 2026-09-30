# Phase 1 completion

Independent local repository in `C:\Users\AuMyat\OneDrive\Documents\ChatGPT\Cloud`. The original `C:\SIT\module feedback\module_feedback_analysis` was not edited. Existing source and styling were copied as the starting point. No remote repository was created or published.

Login is the entry page. Register assigns and stores student/staff roles from exact institutional domains. Other domains are rejected. Passwords are salted and hashed; opaque sessions use HttpOnly cookies and server-side storage. Logout revokes the session. Both UI routes and API routes enforce roles. Student and Staff dashboards are authentication-only placeholders. Existing module/feedback source remains inactive; no AWS changes were made.

## Files added or changed relative to the copied website

- `.env.example`, `.gitignore`: local configuration and private-data exclusions.
- `package.json`, `package-lock.json`, `vite.config.js`: commands, dependencies and local API proxy.
- `README.md`, `PHASE1.md`, `PHASE1_REPORT.md`: current scope and run/test instructions.
- `server/database.py`: SQLite user and session schema.
- `server/auth.py`: domain validation, role assignment, password hashing and sessions.
- `server/server.py`: loopback HTTP API and authorization.
- `server/tests/test_auth.py`: seven backend integration tests.
- `tests/routes.test.mjs`: three route-policy tests.
- `src/App.jsx`: login entry, registration and protected dashboard routes.
- `src/config.js`: real local API mode.
- `src/auth/AuthContext.jsx`, `src/auth/RequireRole.jsx`: server-backed session state and navigation guards.
- `src/auth/navigation.js`, `src/auth/routePolicy.js`: student/staff navigation and destinations.
- `src/services/authService.js`: local API authentication requests.
- `src/pages/LoginPage.jsx`, `src/pages/AuthDashboard.jsx`: registration/login and role dashboards.
- `src/components/layout/AppLayout.jsx`, `src/components/layout/Sidebar.jsx`: Phase 1 scope text.
- `src/components/ui/StatusViews.jsx`: staff-aware dashboard return link.

Other files were copied unchanged as the independent baseline. Local SQLite data, build output and dependencies are ignored by Git.

## Validation

- Python HTTP/SQLite integration tests: 7 passed.
- Node route-policy tests: 3 passed.
- Vite production build: passed.
- Browser: anonymous `/staff` redirects to login; invalid email rejected; student and staff registrations reach their respective dashboards; both cross-role routes show 403; logout returns to login; register link works. Staff return link was corrected during browser review.

Two fabricated QA accounts remain in the ignored local database. Register your own test account to try the application. No email ownership verification or messages are implemented.

## Manual browser test

Open http://127.0.0.1:5173/ with both servers running. Register a new sample student address ending in `@sit.singaporetech.edu.sg`, with a 12–128 character test password. Confirm Student Dashboard; visit `/staff` to see 403. Sign out through the account menu, then register an address ending in `@singaporetech.edu.sg`. Confirm Staff Dashboard; `/student` must show 403. Sign out and attempt either protected URL: expect login. Try a Gmail address: expect domain validation. Log in again with a registered account to confirm its stored role.

To restart: run `npm run dev:api` and `npm run dev` in separate terminals from this repository. See PHASE1.md for full details.

## Module Insight design correction

The active UI now uses our original Module Insight wordmark, navy/teal palette, horizontal header, light background and rounded panels. It no longer uses the friend's split login screen, MF branding or sidebar. Authentication and role permissions are unchanged; module/feedback features remain deferred.

Files updated for this correction: src/pages/LoginPage.jsx, src/components/layout/Logo.jsx, src/components/layout/AppLayout.jsx, src/components/ui/Button.jsx, src/index.css, index.html, public/favicon.svg, PHASE1_REPORT.md. Production build and all three route tests passed; login styling checked in the browser.
