# Phase 3 — staff analytics UI with sample analysis

Run the existing app with `npm run dev:api` and `npm run dev` in separate terminals. Open http://127.0.0.1:5173/ . Authentication and module assignments are unchanged.

## Demo

Sign in with `demo.staff@singaporetech.edu.sg`, password the password chosen during local sample setup. Open Cloud Computing → View analytics. The local seed adds 90 fictional responses across five themes and weeks 1–3. Existing feedback is retained and remains unanalysed without labels. Other modules demonstrate privacy suppression.

To recreate sample data in a new local database: `python server/sample_analytics.py`. This is repeatable and does not reset existing accounts, dates or feedback. All labels and confidence values are fixed fixtures, not predictions. Teaching weeks are sample categories, not inferred from feedback timestamps. Fixture respondents cannot sign in: they have invalid institutional domains and unusable password hashes.

## Manual tests

1. Open Cloud analytics. Verify total submitted responses, three sentiment percentages, the top five themes, weekly stacked bars and anonymous excerpts.
2. Filter Theme = Workload, Sentiment = Neutral, Teaching week = 1: six sample responses match. Change sentiment to Positive: no matching group is large enough, so details and comments are hidden. Clear filters to restore the full view.
3. Open Database or Security: fewer than five responses means detailed results and comments are hidden, including through the API.
4. Visit `/staff/periods/software-current`: access remains denied for this staff account. Students cannot access staff analytics URLs or APIs.
5. Expand Accessible weekly data to inspect the chart's exact data. Hidden weeks are labelled hidden, never zero.

## Calculation and privacy policy

`server/analytics.py` calculates all results independently of React. Endpoint: GET `/api/staff/periods/{periodId}/analytics`, with optional theme, sentiment and teaching_week query parameters. Stored staff role and teaching assignment are checked first. API output uses an allowlist and never contains student names, IDs, emails, submission IDs or timestamps. The previous raw staff-feedback response returns no comments, so it cannot bypass the privacy threshold.

An additive `feedback_analysis` table stores sentiment, sentiment_score, theme, theme_confidence, teaching_week and source for each feedback row. Existing user, assignment and feedback tables remain intact. Deletion cascades to analysis. Editing invalidates old labels; new and edited text is not automatically classified.

Total responses counts all module submissions (including unanalysed feedback), and is hidden below five. Filtered details require both five matching responses and five valid labelled responses. Sentiment percentages use labelled matching responses as denominator. Theme mention percentages use all matching submitted responses as denominator; one theme is populated per sample response. They describe responses, not all enrolled students. Percentages are rounded to one decimal and may not sum to exactly 100.

Theme rankings include up to five eligible themes with at least five matching responses. A weekly bar requires five matching labelled responses for that week. Representative comments additionally require five responses in the exact theme/sentiment/week intersection; up to six deterministic illustrative excerpts are returned. This selection is neither an AI summary nor a statistical sample. Filter choices use a static vocabulary, not small-group data. Unlabelled feedback never defaults to neutral.

This implements count-based suppression, not formal differential privacy. Free-text comments are displayed verbatim; the existing student form warns against self-identification. Sample comments contain no real student identities. No identity metadata is sent to staff.

## Validation

30 backend tests and 3 route tests passed; production build passed. Coverage includes exact threshold boundaries, combined filters, denominators, suppressed theme/week/comment groups, top-five ranking, identity exclusion, role/assignment checks, label invalidation and feedback deletion. Browser checks cover populated and suppressed analytics. Staff chart code is lazy-loaded so login does not download chart dependencies.

## Files changed

- server/database.py — additive analysis table.
- server/analytics.py — pure aggregation and protected endpoint.
- server/core.py — close raw feedback bypass; invalidate labels on edit.
- server/server.py — analytics route integration.
- server/sample_analytics.py — fixed synthetic feedback and analysis fixtures.
- server/tests/test_analytics.py — calculation/privacy/access tests.
- server/tests/test_auth.py, server/tests/test_core.py — update expectations for protected staff feedback.
- src/pages/StaffAnalytics.jsx — filters, KPIs, theme table, weekly chart and anonymous excerpts.
- src/pages/ModuleFeedbackPage.jsx — lazy-loaded staff analytics, existing student flow retained.
- src/pages/AuthDashboard.jsx — View analytics link label.
- src/index.css — filter/table styling.
- README.md, PHASE3.md — current instructions.

No real ML, AI summaries, AWS, Lambda, email reminders or subsequent phase is implemented.
