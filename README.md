# Module Insight

A local university module-feedback application. Students see enrolled modules and submit feedback during an open period. Staff see only their teaching modules and privacy-protected analytics based on explicitly pre-populated sample labels. The original Module Insight teal UI is retained.

This repository covers local phases 1–3. No cloud account, API key or paid service is needed.

## Stack and requirements

- React 19, React Router, Vite 8, Tailwind CSS 4, Recharts and Lucide.
- Python standard-library HTTP API, SQLite, PBKDF2 password hashing and server-side cookie sessions.
- Node.js **22.22+** (tested with 24.21), npm, Python **3.11+** (tested with 3.13).
- Commands below run from the repository root. On systems where Python is named `python3`, substitute that for `python`.

## First setup

```powershell
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_REPOSITORY_FOLDER>
npm ci
python server/sample_analytics.py
```

The seed command creates the local database, fictional test accounts, assignments, feedback periods and 90 sample-labelled Cloud Computing responses. It asks for a **local test password of 12–128 characters** using a hidden prompt. Choose a new test password; do not use a university password. The same chosen password applies to the newly created sample accounts. It is not written to source or printed.

For accounts and modules without analytics fixtures, use `python server/sample_data.py` instead. Both seed commands are repeatable: they preserve existing accounts/passwords, period dates and feedback. They are local development commands, not production data migrations.

No Python package installation is required. No `.env` file is required. `.env.example` is a placeholder reference; the app **does not automatically load dotenv files**. Optional settings are process environment variables:

| Variable | Default / purpose |
| --- | --- |
| `MFI_DB_PATH` | `server/local-data/auth.sqlite3` |
| `MFI_API_PORT` | `8001`; update the Vite proxy if changed |
| `MFI_WEB_ORIGIN` | `http://127.0.0.1:5173`; must match the browser origin |
| `MFI_DEMO_PASSWORD` | Optional non-interactive seed password; prefer the hidden prompt |

Do not commit environment values containing credentials. No `VITE_*` secret variables are used.

## Run locally

Terminal 1:

```powershell
python server/server.py
```

Terminal 2:

```powershell
npm run dev
```

Open **http://127.0.0.1:5173/**. Use this exact host, not `localhost`, because the API checks the browser origin. Vite proxies `/api` to the Python API at `127.0.0.1:8001`. Keep both terminals running. Ctrl+C stops each server.

`npm run build` validates a production frontend build. `npm run preview` alone is not a full application server: it does not provide the configured development API proxy. Use the two commands above for the supported local workflow.

## Sample accounts

Use the password you chose during setup; no fixed sample password is stored in this repository.

| Email | Role | Assigned modules |
| --- | --- | --- |
| `demo.student@sit.singaporetech.edu.sg` | Student | Cloud, Database, Security |
| `demo.other@sit.singaporetech.edu.sg` | Student | Software Engineering |
| `demo.staff@singaporetech.edu.sg` | Staff | Cloud, Database, Security |
| `demo.other@singaporetech.edu.sg` | Staff | Software Engineering |

Module codes, curriculum, names and trimester dates are illustrative fixtures, not official SIT records. Analytics respondent fixtures cannot log in.

Registration assigns roles by exact domain: `sit.singaporetech.edu.sg` → student; `singaporetech.edu.sg` → staff. Other domains are rejected. New accounts have no module assignments. Add assignments locally after registration:

```powershell
python server/sample_data.py --assign-email your.name@sit.singaporetech.edu.sg --modules cloud database security
```

The command also works for registered staff. Valid sample module IDs: `cloud`, `database`, `security`, `software`. It adds assignments to the configured current trimester and never lets browser users self-enrol.

## Current workflows

**Student:** login → assigned modules → module feedback. Each card shows the lecturer, trimester, opening date, deadline and status. Submit a required comment and optional integer rating from 1–5. View/edit/delete only your own feedback while open; after the deadline it is read-only. Delete permits resubmission before the deadline. Backend checks enforce assignment, ownership, duplicate protection and `opens_at <= now < deadline`.

**Staff:** login → teaching modules → analytics. View totals, sentiment percentages, top-five themes, weekly counts and illustrative comments. Filter by theme, sentiment and teaching week. Only assigned module endpoints are accessible. Staff responses exclude student identity metadata and submission IDs/timestamps; no raw-comment endpoint bypasses suppression.

Analytics is **sample analysis, not ML**. New submissions remain unanalysed; editing invalidates old analysis. Sentiment percentages use labelled matching responses. Theme mention percentages use all submitted matching responses, not all enrolled students. Fewer than five responses suppresses detailed module/filter/theme/week results. Comments additionally require five in the combined theme/sentiment/week cohort.

## Local data

SQLite is created automatically and retained across restarts in `server/local-data/`. It includes user hashes, sessions and feedback; do not share it. Every teammate should seed their own database. Tables are additive: users, sessions, trimesters, app_settings, modules, student_modules, staff_modules, feedback_periods, feedback, feedback_analysis.

Sample dates are fixed when first seeded: Cloud/Software open for 14 days, Database already expired, Security opens after seven days. Re-seeding does not reset deadlines. For a fresh isolated demo, stop the API, choose a new ignored database path in the same terminal, seed and restart:

```powershell
$env:MFI_DB_PATH = 'server/local-data/fresh-demo.sqlite3'
python server/sample_analytics.py
python server/server.py
```

This preserves the previous database. Set the same path for all seed/assignment/API commands. Do not change the system clock to test deadlines.

## Tests and checks

```powershell
npm test
python -m unittest discover -s server/tests -v
npm run build
```

Tests use temporary SQLite databases and generated authentication passwords. They do not modify your local application database. Coverage includes authentication, role/assignment isolation, the feedback lifecycle, deadline boundaries, concurrency, analytics denominators and privacy suppression.

Quick browser check: sign in as the sample student, submit/edit/delete Cloud feedback, check closed Database feedback, then sign in as staff and inspect analytics. Workload + Positive + Week 1 should suppress detailed results; clear filters to restore them. An unassigned Software module URL must deny access for the main sample accounts.

## Known limitations

- Local-only Python development server and HTTP cookies; not a production hosting configuration.
- Email-domain roles do not verify mailbox ownership. No password reset, institutional SSO or account-management UI.
- Assignment/current-trimester management uses local setup commands/data, not an admin screen.
- Deadlines do not automatically refresh an already open form; the backend still rejects late changes. Use Refresh for current UI state.
- Analytics uses fixed labels, one theme per response, with arbitrary sample confidence/score values. Unlabelled responses are explicitly excluded from sentiment denominators.
- Count suppression is not differential privacy. Free text is shown verbatim for eligible groups; students must not self-identify. There is no automatic identity redaction.
- Browser automation is a manual smoke check, not a committed end-to-end test runner.
- Sample dates eventually expire; use a fresh isolated database for a new demo.

## Intentionally deferred

AWS deployment, RDS migration, Cognito, Lambda, CloudWatch, Auto Scaling, email notifications/reminders, CSV/PDF exports, real sentiment training/inference, theme clustering and AI-generated summaries. No cloud credentials are required or included.

## Sharing safely

`.gitignore` excludes local databases (including WAL/journal files), environment files, keys, caches, node_modules, builds, work files and screenshots. `.env.example` contains placeholders only. Never use `git add -f` for ignored data. Review `git diff --cached` before committing. Historical `PHASE*.md` files record earlier milestones; this README is the current setup authority.

Create an empty private remote repository, then use the Git commands supplied in the handoff. No remote is configured or published automatically.
