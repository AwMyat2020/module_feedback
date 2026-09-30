# Phase 2 — core local application

The active app is Module Insight, using the original teal styling and the Phase 1 authentication. SQLite is the local source of truth. No AWS, ML, analytics, exports or email services are added.

## Run

From this repository, keep two terminals open:

```powershell
npm run dev:api
```

```powershell
npm run dev
```

Open http://127.0.0.1:5173/ . Existing users and sessions are preserved. Run `python server/sample_data.py` once for the sample setup (already run here). Re-running it does not reset passwords, feedback or period dates.

## Sample accounts

These are fictional local test accounts. The initial password for each is the password chosen during local sample setup.

| Email | Role | Modules |
| --- | --- | --- |
| demo.student@sit.singaporetech.edu.sg | Student | Cloud, Database, Security |
| demo.other@sit.singaporetech.edu.sg | Student | Software Engineering only |
| demo.staff@singaporetech.edu.sg | Staff | Cloud, Database, Security |
| demo.other@singaporetech.edu.sg | Staff | Software Engineering only |

New registrations have no assignments. Add assignments to an existing registered account explicitly:

```powershell
python server/sample_data.py --assign-email your.name@sit.singaporetech.edu.sg --modules cloud database security
```

The same command works for staff emails and uses the stored role. Available sample module IDs are `cloud`, `database`, `security`, `software`. This is a local administrative command, not a student-facing self-enrolment endpoint.

## Data and rules

Tables: existing users/sessions plus trimesters, app_settings, modules, student_modules, staff_modules, feedback_periods, feedback. Current trimester is referenced by the singleton app_settings row. Assignments are trimester-specific. One feedback period per module/trimester keeps the model simple; changing the trimester supports another period. Dashboard lists only current assignments; a directly accessed historical period still requires assignment in that period's trimester.

All dates are stored as UTC epoch seconds and displayed in Singapore time. The sample period dates are fixed when first seeded: Cloud/Software open until 14 days later, Database expired one day earlier, Security opens seven days later. They do not slide forward on restart. Samples are illustrative, not an official SIT curriculum or calendar.

The server accepts writes only at `opens_at <= now < deadline`. Exactly at the deadline, changes stop. Submission, edit and delete all run in database transactions with assignment/ownership checks and a write lock. A database uniqueness constraint allows only one active submission per student/period. Delete allows resubmission while open; old IDs cannot affect a replacement submission. A missing/deleted/foreign feedback ID returns 404. Duplicate/closed conflicts return 409; validation 400; unassigned or wrong-role access 403; unauthenticated API requests 401 and browser routes redirect to login.

Statuses: Submitted if feedback exists (even after the deadline); Feedback Open if open without a submission; Not Submitted if expired without feedback; Closed for a period not yet open. The separate period label clarifies Open, Upcoming or Closed. The UI may remain on an open form as a deadline passes, but backend checks reject any late write; Refresh updates the display.

Staff feedback is projected from an explicit allowlist: comment and optional rating only. It contains no student ID/name/email, feedback ID or submission timestamps. Written comments are not automatically redacted, so the form asks students not to self-identify. No sentiment labels, themes, identity inference or analytics are generated.

## Manual browser walkthrough

1. Open `/` signed out: login appears. Sign in as demo.student.
2. Verify exactly Cloud Computing, Database Systems and Information Security appear with lecturer, trimester, dates and status.
3. Open Cloud, enter written feedback and an optional rating; submit. See Submitted. Edit and save, then delete via the confirmation. Submit again if desired.
4. Open Database: late submission is unavailable. Open Security: submission has not opened.
5. Visit `/student/periods/software-current`: access denied. Visit `/staff`: wrong role denied.
6. Sign out, then sign in as demo.staff. View Cloud feedback; only comment/rating are shown. Visit `/staff/periods/software-current`: denied. `/student` is also denied.
7. Sign in as either demo.other account to see Software Engineering only.
8. For an empty state, register a new institutional address; no modules are automatically assigned.

Expired submitted feedback is verified in automated tests with an injected clock; no system-clock changes are needed. The tests also verify edit/delete exactly at and after the deadline, invalid input, duplicate requests, another student's ownership and staff response privacy.

## Verification

`npm test`: 3 route tests passed. `python -m unittest discover -s server/tests -v`: 22 tests passed, including existing auth, HTTP core routes and concurrent duplicate submission. `npm run build`: passed. Browser walkthrough checks student submission/edit/delete, assigned dashboards, and staff access.

## Files changed in Phase 2

- server/database.py — additive schema; existing auth tables preserved.
- server/core.py — assignment, validation, feedback lifecycle, response projection.
- server/server.py — authenticated routing into core business logic.
- server/sample_data.py — repeatable fictional data and local assignment command.
- server/tests/test_core.py — business-rule tests, including deadlines and concurrency.
- server/tests/test_auth.py — real HTTP core integration coverage; existing auth tests retained.
- src/App.jsx — protected per-period routes.
- src/pages/AuthDashboard.jsx — assigned module cards.
- src/pages/ModuleFeedbackPage.jsx — student lifecycle forms and staff feedback list.
- src/services/coreService.js — fetching, expiry handling and Singapore date display.
- src/index.css — additional Module Insight card/form styling.
- README.md, PHASE2.md — current setup and documentation.

## Scope and remaining items

No requested core functionality is intentionally left incomplete. Assignment management is a local command rather than an admin UI. Sample dates/trimester are explicitly local fixtures. Email ownership verification and public production deployment remain outside this local phase. Analytics and every listed cloud/ML/export integration remain deferred.
