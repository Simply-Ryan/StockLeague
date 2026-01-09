# Copilot Instructions for StockLeague

AI agents: Use this guide to understand architecture, patterns, and critical workflows. **Updated January 9, 2026.**

---

## 🏗️ Core Architecture

**StockLeague** is a gamified paper trading platform with real-time stock quotes, social features, and competitive leagues. Built with **Flask + SQLite** backend and **Jinja2/Bootstrap** frontend, featuring 187+ routes across 7 blueprints.

### Components at a Glance

| Component | File(s) | Purpose | Key Pattern |
|-----------|---------|---------|-------------|
| **App Factory** | `app_factory.py` (~536 lines) | Centralizes Flask config and extension initialization | `create_app(config_name)` returns fully configured app |
| **Blueprints** | `blueprints/*_bp.py` (7 files) | Modular route organization by domain | Each blueprint isolated; registered by factory |
| **Core App** | `app.py` (~6700 lines) | Main entrypoint; legacy routes | Routes can move to blueprints over time |
| **Database** | `database/db_manager.py` (~5082 lines) | SQLite wrapper with 30+ tables | Fresh connection per operation; `migrate_*()` methods for compatibility |
| **Stock Data** | `helpers.py` (~1587 lines) | yfinance wrapper with caching/sentiment | 30s local cache + optional Redis; 2-tier lookup strategy |
| **Real-time** | `realtime_updates.py`, `chat_bp.py` | WebSocket events for live updates | Room-based broadcasting: `room=f'league_{id}'` or `room=f'user_{id}'` |
| **Advanced** | `advanced_*.py`, `league_rules.py` | Options, orders, league logic | Pluggable modules; extend core functionality |
| **Monitoring** | `performance_monitoring.py`, `audit_logger.py` | Production observability | Query profiling, audit trails, system metrics |

---

## 🔄 Critical Patterns - Master These First

### Pattern #1: Database Operations (ALL DB calls follow this)

```python
def get_user_portfolio(self, user_id):
    """Pattern: Fresh connection, dict conversion, safe close."""
    try:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        cursor = conn.cursor()
        cursor.execute("""
            SELECT symbol, shares, avg_cost FROM user_stocks
            WHERE user_id = ? AND deleted_at IS NULL
        """, (user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]  # Always convert to dict
    except Exception as e:
        logger.error(f"DB error fetching portfolio: {e}")
        return []  # Return safe default on error
    finally:
        conn.close()  # CRITICAL: Never leak connections
```

**Remember:**
- Every operation gets fresh connection
- All connections auto-enable: `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL`
- Always close in finally block (even in exceptions)
- Return empty/default values on error; raise only for critical failures
- Check `deleted_at IS NULL` for soft-deleted records

### Pattern #2: Error Handling (All routes follow this)

```python
@trades_bp.route('/api/buy', methods=['POST'])
@login_required  # Validates session['user_id']
def buy_route():
    try:
        # 1. VALIDATE input
        symbol = request.form.get('symbol', '').strip().upper()
        qty = int(request.form.get('qty', 0))
        if not symbol or qty <= 0:
            return apology("Invalid symbol or quantity", 400)
        
        # 2. CHECK PERMISSIONS
        league_id = request.form.get('league_id')
        if not db.get_league_member(league_id, session['user_id']):
            return apology("Not a league member", 403)
        
        # 3. CHECK THROTTLE before executing
        if not validate_trade_throttle(session['user_id'], league_id, symbol):
            return apology("Trade limit reached", 429)
        
        # 4. EXECUTE operation
        trade_id = db.create_trade(session['user_id'], symbol, qty, price)
        
        # 5. EMIT real-time update
        socketio.emit('portfolio_updated', {'trade_id': trade_id}, 
                     room=f'user_{session["user_id"]}')
        
        # 6. RETURN result
        return jsonify({"status": "ok", "trade_id": trade_id})
        
    except DatabaseError as e:
        logger.error(f"DB transaction failed: {e}")
        return apology("Transaction failed", 500)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return apology("Invalid input format", 400)
    except Exception as e:
        logger.error(f"Unexpected error in /buy: {e}", exc_info=True)
        return apology("An error occurred", 500)
```

**Key Points:**
- Validate BEFORE checking permissions BEFORE executing
- Use `apology()` for HTML errors; `jsonify()` for API responses
- Catch specific exceptions first, general Exception last
- Always log with context (`exc_info=True` for full traceback)
- Emit WebSocket updates AFTER DB operation succeeds

### Pattern #3: WebSocket Broadcasting (Room-based only)

```python
# Broadcasting to all users in a league
socketio.emit('leaderboard_updated', {
    'league_id': league_id,
    'top_5': rankings[:5]  # Keep payload small
}, room=f'league_{league_id}')

# Broadcasting to specific user
socketio.emit('portfolio_changed', {
    'cash': new_cash,
    'total_value': new_value
}, room=f'user_{user_id}')

# Connection handler
@socketio.on('connect')
def on_connect(auth):
    user_id = session.get('user_id')
    join_room(f'user_{user_id}')  # Personal room
    for league in db.get_user_leagues(user_id):
        join_room(f'league_{league["id"]}')  # League room
```

**Never:** `socketio.emit(..., broadcast=True)` — this spams all users  
**Always:** Use `room=` parameter to target specific groups

### Pattern #4: Trade Validation (Throttle check required)

```python
from trade_throttle import validate_trade_throttle, record_trade

# MUST check before execution
if not validate_trade_throttle(user_id, league_id, symbol):
    return apology("Trade throttle limit reached", 429)

# Execute
trade_id = db.create_trade(user_id, symbol, qty, price)

# Record for throttle state
record_trade(user_id, league_id, symbol, trade_id)
```

---

## 📋 Blueprint Organization (Where to add code)

| Blueprint | File | Routes | When to Use |
|-----------|------|--------|------------|
| **auth** | `blueprints/auth_bp.py` | login, register, logout, password reset | User authentication |
| **portfolio** | `blueprints/portfolio_bp.py` | /portfolio, context switching, holdings | User's personal stocks |
| **trades** | `blueprints/trades_bp.py` | /buy, /sell, orders (limit/stop), execution | Trading operations |
| **leagues** | `blueprints/leagues_bp.py` | create league, join, leave, settings, invite | League management |
| **chat** | `blueprints/chat_bp.py` | messaging, WebSocket connect/disconnect | Real-time chat |
| **explore** | `blueprints/explore_bp.py` | /explore page, stock search, discovery | Stock browsing |
| **api** | `blueprints/api_bp.py` | /api/* RESTful endpoints | JSON API responses |
| **audit** | `blueprints/audit_bp.py` | /audit logs, compliance reports | Admin/audit features |
| **monitoring** | `blueprints/monitoring_bp.py` | /metrics, /health, system status | Admin metrics |

**How blueprints load:**
1. `app_factory.py` calls `create_app()`
2. `create_app()` imports all blueprints from `blueprints/__init__.py`
3. Each blueprint auto-registers with Flask
4. Routes immediately available without manual registration

---

## 🗄️ Database Schema Quick Reference

### Core Tables

| Table | Purpose | Key Fields | Notes |
|-------|---------|-----------|-------|
| `users` | User accounts | `id`, `username`, `email`, `cash`, `created_at` | Primary user identity |
| `user_stocks` | Holdings per user | `user_id`, `symbol`, `shares`, `avg_cost` | NOT per-league (see league_portfolios) |
| `trades` | Trade history | `user_id`, `symbol`, `shares`, `price`, `type` (buy/sell), `timestamp` | Immutable ledger |
| `leagues` | League definitions | `id`, `creator_id`, `starting_cash`, `invite_code`, `deleted_at` | deleted_at for soft-deletes |
| `league_members` | League membership | `league_id`, `user_id`, `current_rank`, `score`, `is_admin` | Role/permission check |
| `league_portfolios` | Per-league cash/stocks | `league_id`, `user_id`, `cash`, `stocks_json` | Context: users can be in multiple leagues |
| `chat_messages` | Direct messages | `from_user_id`, `to_user_id`, `content`, `read`, `timestamp` | Personal messaging |
| `league_activity_feed` | Social activity log | `league_id`, `user_id`, `action_type`, `description`, `timestamp` | Broadcast via WebSocket |

### Advanced Tables (auto-created on init)

- `league_seasons`, `league_divisions` - Season and tier support
- `tournaments`, `matchups` - Head-to-head competitions
- `achievements`, `user_achievements` - Badge system
- `league_activity_reactions` - Likes/reactions on feed items
- `audit_logs` - Immutable compliance tracking

### Important: Pragmas applied to ALL connections

```python
conn.execute('PRAGMA foreign_keys = ON')    # Referential integrity
conn.execute('PRAGMA journal_mode = WAL')   # Write-Ahead Logging for concurrency
```

---

## 🚀 Essential Developer Workflows

### Start Development

```bash
source venv/bin/activate
pip install -r requirements.txt  # If needed
python app.py  # Starts Flask on http://localhost:5000
```

### Debug Database

```bash
python check_schema.py  # Validate schema
python validate_phase3_integration.py  # Full system check

# Direct querying
python -c "
from database.db_manager import DatabaseManager
db = DatabaseManager()
print(db.get_user(1))
"
```

### Run Tests

```bash
pytest tests/ -v  # All tests
pytest tests/test_engagement_features.py -v  # Specific file
pytest tests/test_engagement_features.py::TestClass::test_method -v  # Single test
```

### Pre-Deployment Checklist

```bash
# 1. Syntax check
python -m py_compile app.py && echo "✅ Syntax OK"

# 2. Full test suite
pytest tests/ -v

# 3. Validate setup
python validate_phase3_integration.py

# 4. App factory test
python -c "from app_factory import create_app; create_app('production')" && echo "✅ Factory OK"

# 5. Backup database
cp database/stocks.db database/stocks.db.backup

# 6. Deploy
git push origin main  # or equivalent
systemctl restart stockleague  # or python app.py
tail -f logs/app.log  # Monitor
```

---

## ⚠️ Common Pitfalls (Avoid These!)

| Pitfall | Consequence | Prevention |
|---------|------------|-----------|
| Forgetting `conn.close()` | Connection leaks; app hangs | Always use `finally: conn.close()` |
| Hardcoding `user_id` from URL | **SECURITY**: Users access others' data | Always use `session['user_id']` + `@login_required` |
| Broadcasting without `room=` | Global spam; all users see all events | Always use `room=f'league_{id}'` or `room=f'user_{id}'` |
| Skipping league membership check | Users access private leagues | Always check `db.get_league_member(league_id, user_id)` |
| Skipping throttle check before trade | Rate limit bypass; spam trades | Call `validate_trade_throttle()` BEFORE `create_trade()` |
| Using stale cache for critical data | Incorrect leaderboards, portfolio values | Use `force_refresh=True` for critical queries |
| Mixing user_stocks with league_portfolios | Data corruption across leagues | Remember: user_stocks is global; league_portfolios is per-league |

---

## 📊 High-Value APIs to Know

### Stock Quotes

```python
# In helpers.py
quote = lookup(symbol, force_refresh=False)
# Returns: {symbol, price, change_pct, market_status, historical_data}

# GET /api/quote/<symbol>
```

### Portfolio Management

```python
# GET /api/portfolio - User's holdings
# Returns: {symbol, shares, avg_cost, current_value} for each stock

# POST /api/trade - Execute buy/sell
# Body: {symbol, qty, type: "buy"/"sell", league_id?}
# Returns: {status: "ok", trade_id}
```

### Leaderboard

```python
# GET /api/league/<league_id>/leaderboard
# Returns: {rankings: [{user, score, rank, portfolio_value}, ...]}

# WebSocket broadcast on update: room=f'league_{league_id}'
```

### Activity Feed (Social)

```python
# GET /api/feed - User's social activities
# Returns: [{action_type, description, timestamp, user}, ...]

# Auto-broadcast via WebSocket when new activity: room=f'league_{league_id}'
```

---

## 📚 Key Files to Study (in order)

1. **Architecture**: `app_factory.py` → understand config loading and extension initialization
2. **Routes**: `blueprints/auth_bp.py` → see pattern of a complete blueprint
3. **Database**: `database/db_manager.py` → search for `def ` to find all operations; skim schema, focus on patterns
4. **Stock Data**: `helpers.py` → especially `lookup()` and caching logic
5. **Real-time**: `realtime_updates.py` → `blueprints/chat_bp.py` → WebSocket patterns
6. **Advanced**: `advanced_league_system.py` → `options_trading.py` (if working on those features)

---

## ✅ Development Status (January 9, 2026)

**Completed Phases:**
- ✅ Phase 3: Engagement Features (activity feed, achievements)
- ✅ Phase 4: WebSocket Real-time (leaderboard, portfolio, chat)
- ✅ Phase 5 (Tier 4): Feature Enhancements (chat polish, feed enrichment)
- 🔄 Tier 5: Testing, Documentation, Infrastructure

**Current Metrics:**
- 187+ routes implemented and tested
- 7 blueprints (auth, portfolio, trades, leagues, chat, explore, api, audit, monitoring)
- 30+ database tables (core + advanced)
- /explore page: <2 seconds load time
- WebSocket stable for 50+ concurrent users

**Known Limitations:**
- SQLite (single-writer); consider Postgres for 1000+ users
- Chat stored in DB (not media streaming)
- Options pricing requires real-time yfinance data

---

## 🤔 Still Confused?

1. **Architecture questions**: Review `app_factory.py` and blueprint `__init__.py`
2. **Pattern questions**: Search this file for the pattern name (Database, Error, WebSocket, Trade Validation)
3. **Database questions**: Use `python check_schema.py` to inspect live schema
4. **Known issues**: See `KNOWN_ISSUES_PERSONAL.md` in repo root
5. **Roadmap**: See `IMPLEMENTATION_PLAN_NEXT.md` for next development items

---

**Last Updated:** January 9, 2026 by GitHub Copilot  
**Scope**: All critical patterns, workflows, and gotchas for immediate productivity  
**Questions?** Check repo issues or KNOWN_ISSUES_PERSONAL.md

## 🏗️ Architecture Overview

**StockLeague** is a **gamified paper trading platform** with real-time stock quotes, social features, and competitive leagues. Built with **Flask + SQLite** backend and **Jinja2/Bootstrap** frontend.

### Major Components

1. **Application Factory** (`app_factory.py`, ~460 lines)
   - Flask factory pattern for environment-specific configuration
   - Supports dev, production, and testing environments
   - Centralizes extension initialization (DB, SocketIO, scheduler)
   - Blueprint registration and WebSocket setup

2. **Blueprint System** (`blueprints/` directory)
   - Modular route organization replacing monolithic app.py
   - Core blueprints: auth_bp.py, portfolio_bp.py, trades_bp.py, leagues_bp.py, chat_bp.py
   - Specialized blueprints: explore_bp.py, api_bp.py, audit_bp.py, monitoring_bp.py, engagement_bp.py
   - Each blueprint handles specific feature domain with isolated logic

3. **Core Flask App** (`app.py`, ~6700 lines)
   - Main entrypoint with remaining core routes
   - Blueprint registration and initialization
   - WebSocket integration via Flask-SocketIO for real-time updates
   - Global error handlers and decorators

2. **Database Layer** (`database/db_manager.py`, ~4700 lines)
   - Lightweight SQLite wrapper with ~30+ tables
   - Pattern: Each operation creates fresh connection with `conn.row_factory = sqlite3.Row`
   - Uses WAL mode + foreign key pragmas for concurrency
   - Migration pattern: Add new columns via `migrate_*` methods on DatabaseManager init

3. **Stock Data** (`helpers.py`)
   - Stock lookup via yfinance (primary source)
   - Sentiment analysis via VADER NLP
   - Real-time quote caching (30-second TTL)
   - Market data aggregation from multiple sources

4. **Advanced Features** (modular system)
   - `advanced_league_system.py`: Divisions, seasons, tournaments, achievements, ratings
   - `advanced_orders.py`: Limit orders, stop orders, trailing stops
   - `options_trading.py`: Options contracts with Black-Scholes Greeks
   - `league_rules.py`: Per-league configuration and trade validation
   - `redis_cache_manager.py`: Optional Redis caching layer

5. **Real-time Updates** (`realtime_updates.py`, `leaderboard_updates.py`)
   - Socket.IO events for live leaderboard, portfolio changes, notifications
   - Broadcast pattern: `socketio.emit('event_name', data, room=f'room_or_user_id')`

6. **Monitoring & Optimization**
   - `performance_monitoring.py`: CPU, memory, API latency tracking
   - `database_optimization.py`: Query profiling, index verification
   - `audit_logger.py`: Comprehensive action logging for compliance

## 📁 File Organization

```
StockLeague/
├── app.py                           # Main Flask app + routes
├── app_factory.py                   # Application factory with environment configs
├── database/
│   ├── db_manager.py               # SQLite wrapper with all schema
│   ├── league_schema_upgrade.py     # Migration helpers
│   ├── advanced_league_features.py  # Advanced table initialization
├── blueprints/                      # Modular route groups
│   ├── auth_bp.py                  # Authentication routes
│   ├── portfolio_bp.py              # Portfolio management
│   ├── trades_bp.py                # Buy/sell/trade routes
│   ├── leagues_bp.py                # League management
│   ├── chat_bp.py                  # Chat + WebSocket handlers
│   ├── explore_bp.py                # Stock discovery
│   ├── api_bp.py                   # Core API endpoints
│   ├── audit_bp.py                 # Audit logging routes
│   ├── monitoring_bp.py             # Admin monitoring
│   ├── engagement_bp.py             # Engagement features
│   └── __init__.py                 # Blueprint exports
├── helpers.py                       # Stock lookup (yfinance), caching, sentiment
├── utils.py                         # Validation, sanitization, rate limiting
├── error_handlers.py                # Standardized error patterns
├── advanced_league_system.py        # Divisions, ratings, achievements
├── advanced_orders.py               # Advanced order types
├── options_trading.py               # Options Greeks calculations
├── realtime_updates.py              # WebSocket event managers
├── performance_monitoring.py        # System metrics collection
├── audit_logger.py / audit_routes.py # Action logging + UI
├── static/                          # CSS, JS, images
├── templates/                       # Jinja2 templates
└── tests/                           # Test files
```

## 🔄 Key Patterns

### Database Operations Pattern

```python
def get_user_portfolio(self, user_id):
    """Fetch user's current holdings."""
    try:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT symbol, shares, avg_cost FROM user_stocks
            WHERE user_id = ?
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"DB error fetching portfolio: {e}")
        return []
```

**Key points:**
- Get fresh connection for each operation
- Use `dict(row)` conversion for sqlite3.Row objects
- Always close connection in finally block
- Return empty/default values on error; raise only for critical failures

### Error Handling Pattern

```python
try:
    # Validate input
    if not symbol or len(symbol) > 5:
        return apology("Invalid symbol", 400)
    
    # Execute operation
    result = db.create_trade(user_id, symbol, qty, price)
    
    # Return result
    return jsonify({"status": "ok", "trade_id": result})
except DatabaseError as e:
    logger.error(f"DB transaction failed: {e}")
    return apology("Transaction failed", 500)
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return apology("An error occurred", 500)
```

**Key points:**
- Catch specific exceptions first, general Exception last
- Use `apology()` helper for user-facing HTML errors
- Use `jsonify()` for API JSON responses
- Always log with context before returning error

### WebSocket Broadcast Pattern

```python
# Broadcasting to all users in a league
socketio.emit('leaderboard_updated', {
    'league_id': league_id,
    'leaderboard': new_rankings
}, room=f'league_{league_id}')

# Broadcasting to specific user
socketio.emit('portfolio_changed', {
    'total_value': new_total,
    'cash': new_cash
}, room=f'user_{user_id}')
```

**Key points:**
- Always use `room` parameter to target specific groups
- Room naming convention: `'league_{id}'`, `'user_{id}'`
- Keep payload small; avoid sending full objects
- Wrap in try/except to prevent broadcast failures from crashing handlers

### Trade Validation Pattern

```python
from trade_throttle import validate_trade_throttle, record_trade

# Check throttle limits
if not validate_trade_throttle(user_id, league_id, symbol):
    return apology("Trade throttle limit reached", 429)

# Execute trade
trade_id = db.create_trade(user_id, symbol, qty, price)

# Record for rate limiting
record_trade(user_id, league_id, symbol, trade_id)
```

**Key points:**
- Always check throttle before executing
- Throttle is per league, per user, per symbol
- Helps prevent spam and market manipulation

## 🗄️ Database Schema Essentials

### Core Tables

| Table | Purpose | Key Field |
|-------|---------|-----------|
| `users` | User accounts | `id`, `username`, `email`, `cash` |
| `user_stocks` | Current holdings | `user_id`, `symbol`, `shares`, `avg_cost` |
| `trades` | Trade history | `user_id`, `symbol`, `shares`, `price`, `timestamp` |
| `leagues` | League definitions | `id`, `creator_id`, `starting_cash`, `invite_code` |
| `league_members` | League membership | `league_id`, `user_id`, `current_rank`, `score` |
| `league_portfolios` | Per-league cash/stocks | `league_id`, `user_id`, `cash`, `stocks_json` |

### Advanced Tables (created on first run via upgrades)

- `league_seasons`, `league_divisions`: Season and tier support
- `tournaments`, `matchups`: Head-to-head competitions
- `achievements`, `user_achievements`: Badge system
- `quests`: Daily/weekly challenges
- `league_activity_feed`: Social activity log

### Important Pragmas

All connections auto-enable:
```python
conn.execute('PRAGMA foreign_keys = ON')    # Referential integrity
conn.execute('PRAGMA journal_mode = WAL')   # Better concurrency
```

## 🔐 Authentication & Authorization

### Login Decorator

```python
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('user_id')  # Already validated by decorator
    # ...
```

### Permission Checks in Routes

```python
# Verify league membership
league = db.get_league(league_id)
if not league:
    return apology("League not found", 404)

member = db.get_league_member(league_id, session['user_id'])
if not member:
    return apology("Not a league member", 403)

# Check admin status
if not member.get('is_admin'):
    return apology("Admin access required", 403)
```

## 📊 API Endpoints to Know

### Stock Quotes
- `GET /api/quote/<symbol>` - Current price + historical data
- Uses `helpers.lookup()` → Yahoo Finance via yfinance (cached 30s)

### Portfolio
- `GET /api/portfolio` - User's holdings (JSON)
- `POST /api/trade` - Execute buy/sell (validates throttle, permissions)

### Leagues
- `GET /api/league/<league_id>/leaderboard` - JSON rankings
- `POST /api/league/create` - Create new league with invite code

### Activity Feed
- `GET /api/feed` - User's social feed (from `league_activity_feed` table)
- WebSocket: `join_room(f'league_{league_id}')` for live updates

## 🛠️ Common Development Tasks

### Adding a New Route

1. **Option A - Blueprint Route (Recommended)**: Add to appropriate blueprint in `blueprints/`:
   - Trades: `blueprints/trades_bp.py` (buy, sell, order management)
   - Portfolios: `blueprints/portfolio_bp.py` (holdings, context switching)
   - Leagues: `blueprints/leagues_bp.py` (league management)
   - Chat: `blueprints/chat_bp.py` (messaging, WebSocket)
   - API: `blueprints/api_bp.py` (RESTful endpoints)
   - Authentication: `blueprints/auth_bp.py` (login, register, logout)

2. **Option B - App.py Routes**: If adding to main `app.py`:
   - Routes added here automatically integrate with blueprints via fallback pattern
   - Useful for core features or temporary endpoints

3. **Implementation Steps** (either location):
   - Use `@login_required` decorator if needs auth
   - Follow error handling pattern (try/except with proper logging)
   - Add rate limiting for API endpoints
   - If modifying database: add schema to `database/db_manager.py`, migrations to `init_db()`

4. **Testing**: All blueprints automatically load and integrate via `app_factory.py`

### Modifying Database Schema

```python
# In database/db_manager.py init_db() method
cursor.execute("""
    CREATE TABLE IF NOT EXISTS my_new_table (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")

# For backward compatibility, add migration method
def migrate_add_new_column(self):
    try:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE existing_table ADD COLUMN new_col TEXT")
        conn.commit()
    except:
        pass  # Column likely already exists
    finally:
        conn.close()

# Call in __init__
self.migrate_add_new_column()
```

### Implementing Real-time Updates

```python
from realtime_updates import RealtimeUpdatesManager

# In your route after DB operation
socketio.emit('portfolio_updated', {
    'user_id': user_id,
    'new_balance': updated_balance,
    'timestamp': datetime.now().isoformat()
}, room=f'user_{user_id}')

# On client: Listen in template
<script>
socket.on('portfolio_updated', function(data) {
    console.log('Portfolio updated:', data);
    // Update UI
});
</script>
```

## ⚠️ Common Pitfalls

1. **Forgetting to close DB connections** → Connection leaks, app hang
   - Always use try/finally or context manager pattern
   
2. **Hardcoding user IDs instead of using session** → Security vulnerability
   - Always verify: `session.get('user_id')` matches request context

3. **Broadcasting without room targeting** → Global message spam
   - Use `room=f'league_{id}'` or `room=f'user_{id}'`

4. **Not validating league membership** → Users access others' private data
   - Always check: `db.get_league_member(league_id, user_id)`

5. **Skipping throttle checks on trades** → Rate limit bypass
   - Always call: `validate_trade_throttle()` before `create_trade()`

6. **Assuming cached data is fresh** → Stale leaderboards, incorrect portfolios
   - Use `force_refresh=True` for critical queries (e.g., `lookup(symbol, force_refresh=True)`)

## 📚 Key Files to Review

- [app_factory.py](app_factory.py) - Application factory with environment configuration
- [blueprints/](blueprints/) - Modular route system (auth, portfolio, trades, leagues, chat, api, audit, monitoring, engagement)
- [database/db_manager.py](database/db_manager.py) - All DB methods (~4700 lines)
- [app.py](app.py) - Core Flask app with remaining routes (see imports for feature modules)
- [helpers.py](helpers.py) - Stock lookup via yfinance, caching logic, sentiment analysis
- [error_handlers.py](error_handlers.py) - Error patterns and standardized responses
- [advanced_league_system.py](advanced_league_system.py) - Divisions, seasons, tournaments, achievements
- [advanced_orders.py](advanced_orders.py) - Limit/stop/trailing stop order implementation
- [options_trading.py](options_trading.py) - Black-Scholes Greeks and options contracts

## 🚀 Testing & Deployment

### Quick Test
```bash
cd /workspaces/StockLeague
python -m pytest tests/ -v
# Or run Flask directly
python app.py
```

### Database Reset (dev only)
```bash
rm database/stocks.db*
python -c "from database.db_manager import DatabaseManager; DatabaseManager()"
```

### Check for Issues
- Review [KNOWN_ISSUES.md](KNOWN_ISSUES.md) before starting work
- Performance: `pytest performance_monitoring.py`
- Schema validation: `python check_schema.py`

---

## ✅ Recent Completions (January 9, 2026)

**TIER 3 - Critical Bug Fixes**: ✅ COMPLETE
- ✅ Portfolio chart fix - Charts now render correctly with proper colors
- ✅ Challenges system removal - All references deleted, achievements is primary system
- ✅ Verify previous fixes - All previous work verified and stable

**TIER 3B - Performance Optimization**: ✅ COMPLETE
- ✅ /explore page speed - Optimized with pagination, now loads < 2 seconds
- ✅ /news feed integration - Real news displays correctly from yfinance

**TIER 4 - Feature Enhancements**: ✅ COMPLETE
- ✅ Chat system polish - WebSocket stable, typing indicators, read receipts working
- ✅ Activity feed enrichment - Own and friends' activities displaying with real-time updates

**Current Phase**: TIER 5 (renamed from TIER 5)
- Focus: Testing, Documentation, and Infrastructure
- Next Major: Integration Testing, Performance Profiling, Code Quality Enhancements

---

**Last Updated:** January 9, 2026 (Post Tier 4 - Ready for Tier 5)  
**Status**: First 4 tiers complete, all 187 routes tested, performance optimized, features polished, ready for advanced development  
**Contact:** See repository issues for questions on patterns or architecture
