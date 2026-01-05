# Copilot Instructions for StockLeague

This guide helps AI coding agents work productively in the StockLeague codebase. Focus on these core patterns and architectural decisions.

## 🏗️ Architecture Overview

**StockLeague** is a **gamified paper trading platform** with real-time stock quotes, social features, and competitive leagues. Built with **Flask + SQLite** backend and **Jinja2/Bootstrap** frontend.

### Major Components

1. **Core Flask App** (`app.py`, ~6700 lines)
   - Main entrypoint with mixed route groups (auth, portfolio, leagues, admin, explore, API)
   - Plan: Future refactoring into Blueprints (examples exist in `blueprints/` for modular routes)
   - WebSocket integration via Flask-SocketIO for real-time updates

2. **Database Layer** (`database/db_manager.py`, ~4700 lines)
   - Lightweight SQLite wrapper with ~30+ tables
   - Pattern: Each operation creates fresh connection with `conn.row_factory = sqlite3.Row`
   - Uses WAL mode + foreign key pragmas for concurrency
   - Migration pattern: Add new columns via `migrate_*` methods on DatabaseManager init

3. **Advanced Features** (modular system)
   - `advanced_league_system.py`: Divisions, seasons, tournaments, achievements, ratings
   - `advanced_orders.py`: Limit orders, stop orders, trailing stops
   - `options_trading.py`: Options contracts with Black-Scholes Greeks
   - `league_rules.py`: Per-league configuration and trade validation
   - `redis_cache_manager.py`: Optional Redis caching layer

4. **Real-time Updates** (`realtime_updates.py`, `leaderboard_updates.py`)
   - Socket.IO events for live leaderboard, portfolio changes, notifications
   - Broadcast pattern: `socketio.emit('event_name', data, room=f'room_or_user_id')`

5. **Monitoring & Optimization**
   - `performance_monitoring.py`: CPU, memory, API latency tracking
   - `database_optimization.py`: Query profiling, index verification
   - `audit_logger.py`: Comprehensive action logging for compliance

## 📁 File Organization

```
StockLeague/
├── app.py                           # Main Flask app + routes
├── database/
│   ├── db_manager.py               # SQLite wrapper with all schema
│   ├── league_schema_upgrade.py     # Migration helpers
│   ├── advanced_league_features.py  # Advanced table initialization
├── helpers.py                       # Stock lookup, caching, sentiment
├── utils.py                         # Validation, sanitization, rate limiting
├── error_handlers.py                # Standardized error patterns
├── advanced_league_system.py        # Divisions, ratings, achievements
├── advanced_orders.py               # Advanced order types
├── options_trading.py               # Options Greeks calculations
├── realtime_updates.py              # WebSocket event managers
├── performance_monitoring.py        # System metrics collection
├── audit_logger.py / audit_routes.py # Action logging + UI
├── blueprints/                      # Modular route groups (emerging pattern)
│   ├── auth_bp.py, portfolio_bp.py, etc.
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

1. Define in `app.py` or create new file in `blueprints/`
2. Use `@login_required` decorator if needs auth
3. Follow error handling pattern above
4. Add logging for important operations
5. If modifying database: add schema to `database/db_manager.py`, migrations to `init_db()`

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

- [database/db_manager.py](database/db_manager.py) - All DB methods (~4700 lines)
- [app.py](app.py) - All Flask routes (see imports for feature modules)
- [helpers.py](helpers.py) - Stock lookup, caching logic
- [error_handlers.py](error_handlers.py) - Error patterns
- [advanced_league_system.py](advanced_league_system.py) - League features
- [PHASE_2_PROGRESS_SUMMARY.md](PHASE_2_PROGRESS_SUMMARY.md) - Design pattern docs

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

**Last Updated:** January 2025  
**Contact:** See repository issues for questions on patterns or architecture
