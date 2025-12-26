## StockLeague — AI Next Steps & Prioritized Todo

Purpose
- This file is an AI-friendly roadmap and handoff for continuing work on StockLeague.
- Each item is prioritized, has a short implementation plan, files to edit, DB/migration notes, test guidance, and evidence pointers.

How to use
- Read the prioritized list below. For any item marked `In Progress`, follow the implementation steps and update this file and `FEATURE_PLAN.md` when complete.
- When creating code changes: branch from `main` using the recommended branch name, commit, and open a PR with the suggested PR title and checklist.

Developer commands (Windows PowerShell)
- Change to project directory:
```
cd "C:\Users\elfan\OneDrive\Documents\Programming\Visual_Studio_Code\StockLeague"
```
- Start dev server (common options):
```
# Option A: helper script if present
python setup_and_run.py

# Option B: run app directly (if app.py is executable)
python app.py
```
- Run tests (if test suite exists):
```
# Pytest (if configured)
pytest -q
```

Worker & production notes
- The app now uses `APScheduler` to schedule leaderboard snapshot jobs when running `python app.py`.
- To run the app with the scheduler locally (development):
```
python app.py
```
- To run the scheduler in production with a WSGI server, run a separate process that imports the app and starts the scheduler, or enable the scheduler in your deployment process. Example using `gunicorn` + a tiny runner script `run_with_scheduler.py` is recommended.

Run tests and the worker in CI
- In CI you should run tests without starting the scheduler to avoid background jobs interfering. Example GitHub Actions job step:
```
- name: Run tests
  run: pytest -q
```

Notes on caching
- Leaderboard snapshots are stored in `leaderboard_snapshots` (compact rows) and there is also a `leaderboards` JSON cache for quick read. Prefer reading snapshots for analytical queries and the JSON cache for quick UI listing.

Priority list (top first)

1) Leaderboards & Ranking Pages — In Progress
- Why: Leaderboards are central to game mechanics and used by leagues and users.
- Goal: Add global, time-based (daily/weekly/monthly), and per-league leaderboards with API endpoints and frontend pages.
- Files to edit:
  - `app.py` (new routes: `/leaderboards`, `/leaderboards/<type>`, `/leagues/<id>/leaderboard`)
  - `database/db_manager.py` (add queries to compute rankings and snapshots)
  - `templates/leaderboards.html`, `templates/league_leaderboard.html`
  - `static/js/leaderboards.js` (optional client-side fetching + polling)
- DB/migration notes: add `leaderboard_snapshots` table (or cache computed values) to avoid heavy queries on large datasets.
- Tests: unit tests for ranking calculation and API integration test for leaderboard endpoints.
- Evidence / starting points: portfolio and transaction tables in `database/db_manager.py`; existing `league_portfolios` and `portfolio_snapshots` tables.
- Branch: `feature/leaderboards`
- Est. effort: Medium

2) Notifications System (in-app + email)
- Why: Keep users informed of friend requests, reactions, league invites, and leaderboard movements.
- Files to edit:
  - `database/db_manager.py` (add `notifications` table + helpers)
  - `app.py` (endpoints to fetch/mark notifications)
  - `templates/_notifications_dropdown.html` and `templates/notifications.html`
  - `static/js/notifications.js`
- DB: `notifications(id, user_id, type, payload_json, read, created_at)`
- Tests: API tests for creating/fetching notifications and UI smoke tests.
- Branch: `feature/notifications`
- Est. effort: Medium

3) Social Feed: Comments & Follow System
- Why: Improves discovery and engagement (comments, following users to personalize feed).
- Files to edit:
  - `database/db_manager.py` (ensure `posts`, `comments`, `post_likes` exist — they do)
  - `app.py` (POST endpoints to create posts, comments, follow/unfollow)
  - `templates/feed.html` (post composer + comment threads)
  - `static/js/feed.js`
- Notes: `posts`, `comments`, and `post_likes` already exist — add endpoints and templates if missing.
- Branch: `feature/social-feed-comments`
- Est. effort: Medium

4) Friends: Blocks, Search, View Friend Portfolios
- Why: Privacy and better social features.
- Files:
  - `database/db_manager.py` (extend `friends` table or status values for 'blocked')
  - `app.py` (endpoints for block/unblock, search users)
  - `templates/profile.html` (respect privacy), `templates/friends.html`
- Branch: `feature/friends-improvements`
- Est. effort: Small

5) League Admin Tools (kick/mute/settings UI)
- Why: Needed for safe league management and moderation.
- Files:
  - `database/db_manager.py` (flags in `league_members` such as `is_admin` already exist)
  - `app.py` (endpoints for admin actions: `/leagues/<id>/kick`, `/leagues/<id>/mute`)
  - `templates/league_detail.html` (admin controls)
- Notes: Add server-side checks to ensure only league admins can act; use socketio to broadcast admin actions to the league room.
- Branch: `feature/league-admin-tools`
- Est. effort: Small–Medium

6) Portfolio Analytics & Charts
- Why: Improve retention by showing performance insights.
- Files: `static/js/charts/*`, integrate with Chart.js or lightweight plotting library, templates for analytics pages.
- DB: rely on `portfolio_snapshots` and `transactions` tables.
- Branch: `feature/analytics`
- Est. effort: Medium

7) Achievements & Badges System
- Why: Gamification; attach badges to user profiles.
- Files: `database/db_manager.py` (tables `achievements`, `user_achievements`), `app.py`, templates and UI.
- Branch: `feature/achievements`
- Est. effort: Medium

8) Moderation & Reporting
- Why: Safety — allow users to report abusive content and have admin review workflows.
- Files: `database/db_manager.py` (reports table), `app.py`, admin UI templates.
- Branch: `feature/moderation`
- Est. effort: Medium

9) Accessibility Improvements
- Why: Improve inclusivity (ARIA attributes, keyboard navigation, color contrast checks).
- Files: templates & potential CSS updates (e.g., `static/css/styles.css`).
- Branch: `chore/accessibility`
- Est. effort: Small

10) Testing & CI Setup
- Why: Ensure regressions are caught and provide confidence for future PRs.
- Files: Add tests under `tests/`, create `github/workflows/ci.yml` to run `pytest` and `ruff`/`flake8`.
- Branch: `chore/ci-tests`
- Est. effort: Small–Medium

Developer workflow guidance (for each feature)
- 1) Create branch from `main` using the recommended branch name.
- 2) Implement changes and add a DB migration (or SQL in `database/db_manager.py`) with `CREATE TABLE IF NOT EXISTS ...` so upgrades are idempotent.
- 3) Add unit tests for core logic and an integration test for the new endpoint(s).
- 4) Run the dev server and verify UI changes locally.
- 5) Open a PR with description, a short testing checklist, and link to evidence in code.

PR template (suggested)
```
Title: [feature] Short description (e.g. Leaderboards: add global + per-league leaderboards)

Description:
- What: brief summary
- Why: brief motivation
- Files: key files changed

Testing:
- Steps to verify locally

Notes:
- Estimated risk/rollback plan
```

Evidence pointers (quick links)
- Chat & socket handlers: `app.py` (@socketio.on('chat_message'), `db.insert_chat_message`)
- Friends table: `database/db_manager.py` (CREATE TABLE friends ...)
- Posts/comments/likes: `database/db_manager.py` (posts, comments, post_likes) and `templates/feed.html`
- Leagues: `database/db_manager.py` (leagues, league_members, league_portfolios, league_messages) and `app.py` (`/leagues/create`, `join_league`)

Maintainers / Ownership
- If multiple maintainers exist, add an `OWNERS` file with GitHub usernames. For now, assign generic owner: `@repo-maintainer` in the PR body.

— End of file

Next Todos (tracked)s
- Leaderboards (In Progress): branch `feature/leaderboards` — Implement global, time-based, and per-league leaderboards.
  - Files: `app.py`, `database/db_manager.py`, `templates/leaderboards.html`, `templates/league_leaderboard.html`, `static/js/leaderboards.js`
  - Acceptance: API endpoints `/leaderboards` and `/leagues/<id>/leaderboard` return cached JSON; leaderboard pages render and update via polling or server-side render.
  - Tests: unit tests for ranking calculation; integration test for leaderboard endpoints.

- Notifications (Not Started): branch `feature/notifications` — Add `notifications` table + endpoints and UI.
  - Files: `database/db_manager.py`, `app.py`, `templates/_notifications_dropdown.html`, `templates/notifications.html`, `static/js/notifications.js`
  - Acceptance: create/fetch/mark-read endpoints exist; sample emails can be sent via configured `email_service.py`.
  - Tests: API tests for create/fetch flows.

- Social Feed (Not Started): branch `feature/social-feed-comments` — Post composer, comments, follow/unfollow.
  - Files: `database/db_manager.py`, `app.py`, `templates/feed.html`, `static/js/feed.js`
  - Acceptance: users can create posts, comment, and follow; feed returns personalized results.

- Friends (Not Started): branch `feature/friends-improvements` — Block/unblock, search, privacy-aware portfolio view.
  - Files: `database/db_manager.py`, `app.py`, `templates/profile.html`, `templates/friends.html`
  - Acceptance: block prevents viewing private data; search returns paginated results.

- League Admin Tools (Not Started): branch `feature/league-admin-tools` — Kick/mute/admin settings.
  - Files: `database/db_manager.py`, `app.py`, `templates/league_detail.html`
  - Acceptance: only admins can perform admin actions; actions broadcast via sockets.

- Testing & CI (Not Started): branch `chore/ci-tests` — Add tests and CI pipeline.
  - Files: `tests/`, `.github/workflows/ci.yml`, `requirements.txt` (dev deps)
  - Acceptance: `pytest -q` runs in CI; linting/format checks included.

How to mark a Todo done
- Create feature branch from `main` with the suggested branch name.
- Implement feature, add minimal DB migration (idempotent `CREATE TABLE IF NOT EXISTS ...`).
- Add tests and run `pytest -q` locally.
- Update this file `AI_NEXT_STEPS.md` to mark the item complete and include the PR link.

If you want, I can start the `feature/leaderboards` branch next and scaffold the API endpoints and DB helpers.
