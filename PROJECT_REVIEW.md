<!-- PROJECT_REVIEW.md - Auto-generated comprehensive project review for StockLeague -->
# StockLeague — Project Review & Next Steps

Last updated: 2025-12-17

This document consolidates a full project review for the StockLeague application in this repository. It includes:

- Inventory of current implementations and how they are implemented.
- Prioritized list of future features (highest → lowest priority).
- Detailed database schema summary and table contents (as implemented or inferred).
- Potential issues and bugs to watch for.
- Suggestions for architecture, performance, security, testing, and UX improvements.
- A ready-to-use AI prompt / context block to hand this project to an assistant (complete with commands and constraints).
- Misc notes, commands and recommended next steps.

---

## 1) High-level project summary

- Language and framework: Python (Flask) web application.
- Frontend: Jinja2 templates, Bootstrap 5, Font Awesome, Chart.js (sparklines) and vanilla JS.
- Real-time: Flask-SocketIO.
- DB: SQLite used via a `DatabaseManager` (file: `database/db_manager.py`).
- Market data: `helpers.py` which wraps yfinance (or Yahoo) calls and implements short-lived in-process caching.
- Testing: pytest-based tests under `tests/` using Flask test client.

Main entry: `app.py` (large monolithic file with routes, helpers and core logic). Templates live in `templates/` and static assets in `static/`.

---

## 2) Implementations (detailed)

Below are the major subsystems and where to find/inspect them.

- App shell and routing
  - `app.py` — central file containing route definitions, Socket.IO integration, helpers imported from `helpers.py`, and the `DatabaseManager` instance usage.
  - Routes include auth, portfolio, league/social pages, `/explore`, `/api/chart/<symbol>`, admin endpoints and more.

- Templates & UI
  - `templates/layout.html` — main layout with navbar, theme system (dark/light/ocean/forest/sunset/auto) and JS for theme handling. Guest users default to light theme.
  - `templates/explore.html` — market discovery page; uses client-side async sparklines via `/api/chart/<symbol>` and Chart.js.
  - `templates/edit_portfolio.html` — personal portfolio edit route with destructive reset confirmation modal.

- Database layer
  - `database/db_manager.py` implements schema initialization (`init_db()`), CRUD helpers for users, holdings, leagues, transactions, notifications, and special methods like `reset_personal_portfolio(...)` and audit log insertion into `portfolio_resets`.

- Market helpers
  - `helpers.py` — includes `lookup()`, `get_chart_data(symbol, days)`, `get_popular_stocks()`, `get_market_movers()`, `get_volume_leaders()`, `get_market_indices()`, `usd()` formatting, and an in-memory `_market_cache` with TTL (~30–45s recommended). These functions fetch data from yfinance and apply short caches.

- Sparklines & charts
  - Client-side code in `templates/explore.html` fetches `/api/chart/<symbol>?days=30` and renders small Chart.js line charts inside canvases. Spinners show until data loads.

- Realtime
  - Socket.IO is initialized in `app.py` and used to push league events and stock updates. Client subscribes (in `layout.html`) to `stock_update` and other events.

- Tests
  - `tests/test_explore.py` (integration for explore page render), `tests/test_league_admin.py` (league admin behavior), other tests under `tests/`.

---

## 3) Database schema (summary & expected columns)

The authoritative schema is defined in `database/db_manager.py` within `init_db()`. The summary below is derived from code and audit logs. Run the command below to print exact CREATE statements if you want definitive, text-exact schema:

```powershell
python - <<'PY'
import sqlite3
db='database/stocks.db'
con=sqlite3.connect(db)
for row in con.execute("SELECT sql FROM sqlite_master WHERE type='table';"):
    print(row[0])
con.close()
PY
```

Typical tables and columns (common fields):

- `users`
  - id INTEGER PRIMARY KEY
  - username TEXT UNIQUE
  - email TEXT UNIQUE
  - password_hash TEXT
  - cash REAL (personal balance)
  - is_admin INTEGER (0/1)
  - avatar_url TEXT
  - settings JSON/TEXT (nullable)
  - created_at DATETIME

- `user_stocks` / `holdings`
  - id INTEGER PRIMARY KEY
  - user_id INTEGER REFERENCES users(id)
  - symbol TEXT
  - shares REAL
  - avg_price REAL
  - last_price REAL
  - updated_at DATETIME

- `transactions` / `trades`
  - id INTEGER PRIMARY KEY
  - user_id INTEGER
  - symbol TEXT
  - quantity REAL
  - price REAL
  - type TEXT ('buy'|'sell')
  - commission REAL
  - timestamp DATETIME
  - context TEXT ('personal'|'league')
  - league_id INTEGER (nullable)

- `leagues`
  - id INTEGER PRIMARY KEY
  - name TEXT
  - creator_id INTEGER
  - status TEXT
  - settings JSON/TEXT
  - created_at DATETIME

- `league_members`
  - id INTEGER PRIMARY KEY
  - league_id INTEGER
  - user_id INTEGER
  - is_admin INTEGER
  - joined_at DATETIME
  - balance REAL (league-specific)

- `league_holdings`
  - id INTEGER PRIMARY KEY
  - league_id INTEGER
  - user_id INTEGER
  - symbol TEXT
  - shares REAL
  - avg_price REAL
  - updated_at DATETIME

- `notifications`
  - id INTEGER PRIMARY KEY
  - user_id INTEGER
  - type TEXT
  - title TEXT
  - message TEXT
  - url TEXT
  - is_read INTEGER
  - created_at DATETIME

- `portfolio_resets` (audit)
  - id INTEGER PRIMARY KEY
  - user_id INTEGER (whose portfolio was reset)
  - performed_by INTEGER (user id or NULL for system)
  - old_cash REAL
  - new_cash REAL
  - reason TEXT
  - ip_address TEXT
  - user_agent TEXT
  - timestamp DATETIME

- `moderation` or `league_moderation`
  - id INTEGER PRIMARY KEY
  - league_id INTEGER
  - user_id INTEGER
  - is_muted INTEGER
  - muted_until DATETIME (nullable)
  - is_banned INTEGER
  - ban_reason TEXT

Other supporting tables may exist for watchlists, alerts, cached analytics, and app settings.

---

## 4) Future features — prioritized

Priority rationale: consider risk, value, effort, and user safety.

1) Move caching & session store to Redis (high priority)
   - Why: in-process cache and filesystem sessions do not scale across multiple processes; Redis centralizes caches and supports Socket.IO message queue.
   - Rough effort: small code changes + `requirements.txt` update + local test with Docker.

2) Cache `/api/chart/<symbol>` server-side for 5–30 minutes (high priority)
   - Why: Chart data is expensive/popular (yfinance). Caching removes duplicated calls and improves Explore performance.

3) Admin `portfolio_resets` UI and export (high)
   - Why: Audit transparency and admin tooling.

4) Add Playwright-based E2E tests for sparklines and modals (medium)

5) Background market-data fetcher (worker) to pre-warm caches (medium)

6) Migrate `app.py` to blueprints (tech debt / maintainability)

7) Add server-side theme preference persistence for logged-in users (low)

8) Replace filesystem sessions with Redis-backed sessions (paired with #1)

9) Hardening of destructive ops: soft-delete + rollback window + email confirmation (low/medium)

10) Migrate to a small timeseries DB for historical data (optional / long-term)

---

## 5) Potential issues / bugs

- In-memory caches are process-local -> inconsistent data and duplicated API calls under multi-worker servers.
- yfinance or Yahoo endpoints are subject to rate-limiting; no robust retry/backoff or circuit-breaker is currently implemented.
- Destructive `reset_personal_portfolio` must be guarded carefully — server-side checks and stricter confirmations are recommended.
- Session store is filesystem-based — not suitable for horizontally scaled deployments.
- Socket.IO currently configured with `async_mode='threading'` — for multi-worker deployments message queue (Redis) is needed.
- Potential SQL inefficiencies / N+1 queries in `DatabaseManager` — review queries where loops fetch dependent objects.
- Client-side sparklines depend on Chart.js CDN — a local fallback or pinned version is implemented but confirm integrity.
- Tests cover server rendering primarily; client-side behavior and visual regressions are not covered by unit tests.

---

## 6) Suggestions & improvements (concrete)

- Short-term (low friction)
  - Pin Chart.js to a stable version (done: `chart.umd.min.js@4.4.0`).
  - Add Redis dependency and a feature flag so devs can run without Redis; change default to in-process cache when Redis missing.
  - Add a small file-backed cache for chart arrays as a fallback for CI.

- Medium-term
  - Add Playwright smoke tests to ensure sparklines render and modals behave in a headless environment.
  - Implement an admin-only page for `portfolio_resets` (with filters + CSV export).
  - Move bulky `app.py` into modular Blueprints for `api`, `explore`, `portfolio`, `auth`, and `admin`.

- Long-term
  - Dedicated market-data microservice that ingests from yfinance and publishes to Redis; supports offline warm cache and better rate-limiting.
  - Replace SQLite with Postgres for production if concurrency and scale increases.

---

## 7) Operational & developer guidance

Local dev: recommended dockerized Redis for testing:

```powershell
docker run -d --name stockleague-redis -p 6379:6379 redis:7-alpine
```

Run tests with proper PYTHONPATH:

```powershell
$env:PYTHONPATH='.'; pytest -q
```

Run the app (dev):

```powershell
python app.py
# or use your existing run script
```

When adding Redis, update `requirements.txt` and the app init to use `redis` / `rq` / `flask-session` config for Redis-backed session.

---

## 8) Full AI prompt (expanded)

Use this prompt to hand the project to an AI or a new engineer. It contains repository-names, goals, constraints, and suggested first tasks.

```
Project: StockLeague (Flask social portfolio simulation)

Repo path (local dev): C:\Users\elfan\OneDrive\Documents\Programming\Visual_Studio_Code\StockLeague

Summary:
- Flask app (single large `app.py`) serving portfolio pages, leagues, and an Explore market discovery page. Uses `helpers.py` for yfinance/wrappers, Chart.js for sparklines, and `database/db_manager.py` for SQLite.

Primary objectives (pick 1–2 to start):
1. Implement Redis-based caching and session store. Migrate in-process caches for market data to Redis keys with TTL; ensure fallback to in-process cache if Redis unavailable.
2. Add server-side caching for `/api/chart/<symbol>` (cache price arrays for 5–30 minutes) and add tests to verify cache behavior (unit tests mocking Redis).
3. Build an admin UI to view `portfolio_resets` (with filters by user, performer, date range), and CSV export option.

Constraints:
- Do not drop or destroy user data without an explicit migration plan and admin confirmation. If DB schema changes are required, provide migration SQL and a script.
- Tests must continue to pass; add unit and E2E tests for any new behavior.
- Keep the guest theme behavior: guests see the light theme default and a guest-only light/dark toggle. Logged-in theme persistence remains.

Deliverables:
- A PR with commits for each logical change.
- `requirements.txt` updated for any new packages.
- New unit tests and Playwright E2E tests for client behaviors (sparklines, theme toggle, reset modal).
- README/DEV notes for running Redis and the tests.

Helpful commands:
```powershell
docker run -d --name stockleague-redis -p 6379:6379 redis:7-alpine
$env:PYTHONPATH='.'; pytest -q
```

Start with: cache `/api/chart/<symbol>` in Redis (key: `chart:{symbol}:{days}` with 10 min TTL) and add a fallback to `helpers.get_chart_data()` if cache miss. Add tests that simulate cache hit and miss.
```

---

## 9) Suggested immediate next actions (I can implement)

Choose one and I will implement it, test it locally and open/prepare a PR:

1. Add server-side caching for `/api/chart/<symbol>` using Redis with a 10-minute TTL and local fallback to current logic.
2. Add an admin page to view `portfolio_resets` with filters and CSV export (HTML + route + permission check).
3. Add Playwright smoke test to assert that `/explore` loads and at least one sparkline is visible after loading.

If you pick (1), I'll update `requirements.txt`, add minimal Redis client code, and include unit tests that mock Redis.

---

## 10) Notes & final thoughts

- The app is functionally rich: social features, leagues, and market discovery are all present. The top priorities should be operational (cache + session + scaling) and safety (destructive resets audit & admin tooling).
- I recommend treating this repo as actively evolving: move heavy features (market ingestion) to background workers and central caches to reduce load on the Flask app.

If you want I can implement one of the immediate next actions now — tell me which one to start with and I'll add it to the tracked todo list and begin.

---

End of document.
