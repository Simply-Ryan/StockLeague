# 🚀 StockLeague - Next Features & Improvements Roadmap

**Generated:** December 24, 2025  
**Status:** Comprehensive implementation plan created  
**Total Prioritized Items:** 20 major features/improvements

---

## 📋 Executive Summary

The StockLeague platform is a mature, feature-rich paper trading application with 5,800+ lines of core code. The project has implemented:
- ✅ Core trading engine with buy/sell/options
- ✅ League system with leaderboards and activity feeds  
- ✅ Social features (friends, profiles, followers)
- ✅ Real-time WebSocket updates
- ✅ Advanced features (achievements, tournaments, challenges)
- ✅ H2H matchups and market status modal
- ✅ Copy trading and sentiment analysis

**Next Phase Focus:** Stability, Performance, Production-Readiness, and Advanced Analytics

---

## 🎯 Prioritized Implementation Plan

### PHASE 1: CRITICAL BUG FIXES & STABILITY (Weeks 1-2)

#### 1. Fix Undefined Variables in Sell/Copy Trades  
**Priority:** CRITICAL | **Effort:** 2 hours | **Risk:** HIGH  
**Status:** Issue identified but not fixed

**Problem:**
- `sell()` route has undefined `stock` variable in personal portfolio branch (line 3950)
- `copy_trade()` has undefined `league_id` and `user_id` (line 4600)
- Silent failures cause trading errors

**Solution:**
```python
# sell() - ensure stock is defined from context before use
stock = get_portfolio_stock(user_id, context, symbol)
if not stock:
    return apology("Stock not found in portfolio", 400)

# copy_trades() - define variables at function start
user_id = session["user_id"]
league_id = context.get("league_id")
```

**Files to Edit:**
- `app.py` (lines 3950, 4600)

**Testing:**
- Test selling stocks from personal portfolio
- Test copy trading in leagues

---

#### 2. Comprehensive Error Handling for All Routes  
**Priority:** CRITICAL | **Effort:** 6-8 hours | **Risk:** MEDIUM  
**Current State:** Only `buy()` has full error handling; other routes are fragile

**Scope:**
- Apply buy() error handling pattern to: `sell()`, `trade()`, all league routes
- Add try-catch to ALL database operations
- Add specific error logging for each failure type
- Improve user-facing error messages

**Implementation Pattern:**
```python
@app.route("/sell", methods=["POST"])
@login_required
def sell():
    try:
        # Input validation
        # Context validation
        # Stock lookup
        # Portfolio operations
        
    except ValueError as e:
        app_logger.error(f"Validation error: {e}")
        return apology("Invalid input", 400)
    except sqlite3.OperationalError as e:
        app_logger.error(f"Database error: {e}")
        return apology("Database error", 500)
    except Exception as e:
        app_logger.error(f"Unexpected error: {e}")
        return apology("Unexpected error", 500)
```

**Files to Edit:**
- `app.py` (sell, trade, league_trade, join_league routes)
- `database/db_manager.py` (all public methods)

**Testing:**
- Unit tests for error conditions
- Integration tests for each route

---

#### 3. Add Rate Limiting & Trade Throttling  
**Priority:** HIGH | **Effort:** 3-4 hours | **Risk:** LOW  
**Current State:** Partial implementation exists

**Features:**
- Max 10 trades per minute per user (already implemented)
- Max 100 trades per hour per league (already implemented)
- Cooldown between rapid trades (2 seconds)
- Circuit breaker for max daily losses (-$5000)
- Position size limits (max 25% of cash per stock)

**Implementation:**
```python
def check_trade_throttle(user_id, symbol):
    """Enforce per-user and per-stock rate limits"""
    # Check 2-second cooldown between trades
    # Check max 10 trades per minute
    # Check daily loss limit
    # Check position size limits
    
def calculate_max_position_size(user_id, context):
    """Calculate max shares allowed based on portfolio"""
    # Return (max_shares, reason)
```

**Files to Edit:**
- `utils.py` (add throttle functions)
- `app.py` (integrate into buy/sell/league_trade)
- `database/db_manager.py` (track rate limit state)

**Testing:**
- Rate limit exceeded scenarios
- Throttle bypass attempts
- Loss limit triggers

---

### PHASE 2: DATA INTEGRITY & SAFETY (Weeks 3-4)

#### 4. Implement Database Transactions for Concurrent Trades  
**Priority:** HIGH | **Effort:** 5-6 hours | **Risk:** MEDIUM  
**Current State:** No transaction isolation

**Problem:**
- Two simultaneous trades could overdraw cash or double shares
- Leaderboard score updates during trades could be inconsistent
- Portfolio values calculated between read and write

**Solution:**
```python
def execute_league_trade_atomic(league_id, user_id, symbol, action, shares, price):
    """Execute trade as atomic database transaction"""
    conn = db.get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")  # Exclusive lock
        
        # All operations in transaction
        cursor = conn.cursor()
        cursor.execute("SELECT cash FROM league_portfolios WHERE ... FOR UPDATE")
        
        # ... trade logic ...
        
        conn.commit()
        return True, None, txn_id
    except Exception as e:
        conn.rollback()
        return False, str(e), None
    finally:
        conn.close()
```

**Files to Edit:**
- `database/db_manager.py` (add atomic operations)
- `app.py` (use atomic methods for trades)

**Testing:**
- Concurrent trading simulations
- Cash overdraft prevention
- Leaderboard consistency checks

---

#### 5. Create Automated Test Suite  
**Priority:** HIGH | **Effort:** 8-10 hours | **Risk:** LOW  
**Current State:** Few tests exist

**Coverage Areas:**
```
tests/
├── unit/
│   ├── test_validation.py (input validation)
│   ├── test_portfolio_calculations.py (returns, gains)
│   ├── test_rate_limiting.py (throttle logic)
│   └── test_league_scoring.py (leaderboard calculation)
├── integration/
│   ├── test_buy_sell_flow.py
│   ├── test_league_trading.py
│   ├── test_concurrent_trades.py
│   └── test_copy_trading.py
└── performance/
    ├── test_large_portfolio.py (1000+ stocks)
    ├── test_large_league.py (1000+ members)
    └── test_load_testing.py (100 concurrent users)
```

**Target Coverage:** 80%+ of critical paths

**Files to Create:**
- `tests/conftest.py` (fixtures, database setup)
- `tests/unit/*.py` (unit tests)
- `tests/integration/*.py` (integration tests)

---

### PHASE 3: ADVANCED FEATURES (Weeks 5-6)

#### 6. WebSocket Real-Time Leaderboard Updates  
**Priority:** MEDIUM | **Effort:** 4-5 hours | **Risk:** LOW  
**Current State:** Leaderboard updated on page load only

**Implementation:**
```python
@socketio.on('subscribe_league_leaderboard')
def handle_leaderboard_subscribe(data):
    league_id = data['league_id']
    join_room(f'leaderboard_{league_id}')
    
    # Send initial leaderboard
    leaderboard = db.get_league_leaderboard(league_id)
    emit('leaderboard_update', {'leaderboard': leaderboard})

# When trade executes:
socketio.emit('leaderboard_update', 
    {'leaderboard': updated_leaderboard}, 
    room=f'leaderboard_{league_id}')
```

**Features:**
- Real-time ranking updates after trades
- Score change animations
- Position change notifications
- Smooth transitions

**Files to Edit:**
- `app.py` (add SocketIO handlers)
- `static/js/leaderboard.js` (client-side updates)
- `templates/league_detail.html` (integrate updates)

---

#### 7. Implement Soft Deletes for League Archives  
**Priority:** MEDIUM | **Effort:** 3-4 hours | **Risk:** LOW  
**Current State:** Hard deletes, data lost permanently

**Implementation:**
```sql
ALTER TABLE leagues ADD COLUMN deleted_at TIMESTAMP;
ALTER TABLE league_members ADD COLUMN deleted_at TIMESTAMP;
ALTER TABLE league_transactions ADD COLUMN deleted_at TIMESTAMP;

-- Query pattern:
SELECT * FROM leagues WHERE deleted_at IS NULL;

-- Soft delete:
UPDATE leagues SET deleted_at = NOW() WHERE id = ?;
```

**Features:**
- Archive leagues instead of deleting
- Restore functionality for admins
- Historical data preservation
- Compliance audit trails

**Files to Edit:**
- `database/league_schema_upgrade.py` (migrations)
- `database/db_manager.py` (add soft delete methods)
- `app.py` (use soft delete methods)

---

#### 8. Add Comprehensive Audit Logging System  
**Priority:** MEDIUM | **Effort:** 5-6 hours | **Risk:** LOW  
**Current State:** Basic logging to file only

**Create Audit Log Table:**
```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    action TEXT,
    entity_type TEXT,
    entity_id INTEGER,
    old_values JSON,
    new_values JSON,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Audit Events to Log:**
- Trade execution (buy/sell details)
- League creation/modification
- Member kicks/mutes
- Admin actions
- Portfolio resets
- Account deletions

**Implementation:**
```python
def audit_log(user_id, action, entity_type, entity_id, old_values=None, new_values=None):
    """Log audit event"""
    # Store in audit_logs table
    # Also forward to centralized logging service (Splunk, etc.)
```

**Files to Edit:**
- `database/db_manager.py` (add audit_log method)
- `app.py` (call audit_log after critical operations)

---

### PHASE 4: LEAGUE SYSTEM IMPROVEMENTS (Weeks 7-8)

#### 9. Implement Invite Code Expiration Validation  
**Priority:** MEDIUM | **Effort:** 2-3 hours | **Risk:** LOW  
**Current State:** Invite codes don't expire

**Implementation:**
```python
# When creating invite code:
invite_code = secrets.token_urlsafe(16)
expires_at = datetime.now() + timedelta(days=7)  # 7 day expiration
db.create_invite_code(league_id, invite_code, expires_at)

# When joining:
invite = db.get_invite_by_code(invite_code)
if invite['expires_at'] < datetime.now():
    return apology("Invite code has expired", 400)
```

**Features:**
- Default 7-day expiration (configurable)
- Admin can refresh/extend codes
- Expired code cleanup job
- Audit trail of code usage

**Files to Edit:**
- `database/league_schema_upgrade.py` (add expires_at column)
- `database/db_manager.py` (expiration check)
- `app.py` (validate expiration in join_league)

---

#### 10. Add Max Members Limit Enforcement for Leagues  
**Priority:** MEDIUM | **Effort:** 2-3 hours | **Risk:** LOW  
**Current State:** No member limit

**Implementation:**
```python
# Leagues table: ADD COLUMN max_members INT DEFAULT 50

def can_join_league(league_id, user_id):
    """Check if user can join league"""
    league = db.get_league(league_id)
    
    if league['max_members'] is None:
        return True  # No limit
    
    member_count = db.get_league_member_count(league_id)
    return member_count < league['max_members']
```

**Features:**
- Configurable per league (10-1000 members)
- Admin can increase limit
- Waiting list functionality (optional)
- Notification when league is full

**Files to Edit:**
- `database/league_schema_upgrade.py` (add max_members)
- `database/db_manager.py` (add member count check)
- `app.py` (enforce in join_league)

---

### PHASE 5: TRADING FEATURES (Weeks 9-10)

#### 11. Complete Options Trading Implementation  
**Priority:** MEDIUM | **Effort:** 10-12 hours | **Risk:** MEDIUM  
**Current State:** Skeleton only, Greeks calculations done, UI not finished

**Completed:**
- ✅ Black-Scholes Greeks calculations
- ✅ Options chain generation
- ✅ ITM/OTM detection
- ✅ Options contracts table

**Missing:**
- ❌ Buy/Sell execution with margin requirements
- ❌ Expiration handling (auto-exercise ITM)
- ❌ Portfolio P&L calculations with options
- ❌ Options positions tracking
- ❌ UI for options dashboard
- ❌ Advanced strategies (spreads, straddles)

**Implementation Steps:**
1. Create `options_positions` table with margin tracking
2. Add option exercise/assignment logic on expiration
3. Update portfolio value calculation to include options
4. Create options dashboard UI
5. Add options P&L to performance metrics

**Files to Create/Edit:**
- `database/options_schema.py` (new - create schema)
- `app.py` (fix options routes)
- `templates/options.html` (new - positions dashboard)
- `static/js/options_calculator.js` (new - Greeks visualizer)

---

### PHASE 6: PERFORMANCE & SCALE (Weeks 11-12)

#### 12. Add Redis Caching Layer for Performance  
**Priority:** MEDIUM | **Effort:** 6-8 hours | **Risk:** MEDIUM  
**Current State:** In-memory caching only (price quotes)

**Caching Strategy:**
```python
# Cache hot data for 30-60 seconds
cache_keys = {
    'stock_quote:{symbol}': 60,           # Real-time quote
    'leaderboard:{league_id}': 30,        # Leaderboard data
    'user_portfolio:{user_id}': 30,       # Portfolio value
    'league_rankings:{league_id}': 60,    # League scores
    'market_status': 300,                 # Market open/close
}

def get_cached_quote(symbol):
    """Get stock quote with Redis caching"""
    cached = redis.get(f'stock_quote:{symbol}')
    if cached:
        return json.loads(cached)
    
    quote = lookup(symbol, force_refresh=True)
    redis.setex(f'stock_quote:{symbol}', 60, json.dumps(quote))
    return quote
```

**Implementation:**
- Redis server setup (local dev, production deployment)
- Cache invalidation logic
- Cache warming strategies
- Performance monitoring

**Files to Edit:**
- `utils.py` (add caching decorators)
- `database/db_manager.py` (integrate Redis)
- `helpers.py` (cache_quote, cache_leaderboard)
- `app.py` (use cached lookups)

---

#### 13. Implement Admin Dashboard for System Monitoring  
**Priority:** MEDIUM | **Effort:** 8-10 hours | **Risk:** LOW  
**Current State:** No admin tools

**Dashboard Features:**
```
Admin Dashboard
├── System Health
│   ├── Database stats (size, row counts)
│   ├── API health (response times)
│   ├── Background job status
│   └── Error rate monitoring
├── Trading Metrics
│   ├── Daily volume (trades, cash moved)
│   ├── Popular stocks (most traded)
│   ├── Trade execution times
│   └── Failed trades (errors)
├── User Management
│   ├── New users (daily/weekly)
│   ├── Active traders (last 24h)
│   ├── User search/suspension
│   └── Account recovery
└── League Management
    ├── Active leagues (by size)
    ├── League activity heatmap
    ├── Moderation queue
    └── League settings override
```

**Implementation:**
- Create `/admin/dashboard` route
- Add admin-only database queries
- Create `templates/admin/dashboard.html`
- Add monitoring charts (Chart.js)

**Files to Create/Edit:**
- `app.py` (add admin routes)
- `database/db_manager.py` (add admin query methods)
- `templates/admin/dashboard.html` (new)
- `static/js/admin-charts.js` (new)

---

### PHASE 7: ANALYTICS & INSIGHTS (Weeks 13-14)

#### 14. Add Advanced Portfolio Analytics and Visualization  
**Priority:** MEDIUM | **Effort:** 8-10 hours | **Risk:** LOW  
**Current State:** Basic P&L only

**Analytics to Add:**
```
Portfolio Analytics
├── Risk Metrics
│   ├── Sharpe ratio (risk-adjusted returns)
│   ├── Sortino ratio (downside risk)
│   ├── Max drawdown (largest peak-to-trough decline)
│   ├── Beta (vs S&P 500)
│   └── Correlation analysis
├── Performance Charts
│   ├── Equity curve (balance over time)
│   ├── Drawdown chart
│   ├── Rolling returns (30/90/365 day)
│   └── Sector allocation pie chart
├── Trading Analysis
│   ├── Win rate (% profitable trades)
│   ├── Profit factor (gross profit / gross loss)
│   ├── Average trade size
│   ├── Holding period distribution
│   └── Trade P&L histogram
└── Comparisons
    ├── vs benchmark (S&P 500)
    ├── vs league average
    ├── vs friends
    └── Historical performance
```

**Implementation:**
- Add analytics calculation module
- Create performance charts (TradingView Lightweight Charts)
- Add daily/weekly/monthly rollups to database
- Create analytics comparison views

**Files to Create/Edit:**
- `helpers.py` (add analytics calculation functions)
- `database/analytics_schema.py` (new - create tables)
- `app.py` (add analytics routes)
- `templates/analytics_advanced.html` (new)
- `static/js/analytics-charts.js` (new)

---

### PHASE 8: INFRASTRUCTURE & SCALING (Weeks 15-16)

#### 15. Migrate from SQLite to PostgreSQL (Production)  
**Priority:** HIGH (for production) | **Effort:** 12-16 hours | **Risk:** HIGH  
**Current State:** SQLite only

**Migration Strategy:**
1. Run parallel databases (SQLite + PostgreSQL)
2. Dual-write for new transactions
3. Batch migrate historical data
4. Verification and testing
5. Cutover to PostgreSQL

**Benefits:**
- Better concurrency handling
- ACID transactions
- Full-text search
- JSON operations
- Scaling to millions of rows
- Connection pooling (pgbouncer)

**Implementation:**
- Create PostgreSQL schema (with pg-specific features)
- Update `DatabaseManager` to support both
- Create migration script
- Add connection pooling
- Update deployment docs

**Files to Edit:**
- `database/db_manager.py` (add PostgreSQL support)
- `database/schema.sql` (PostgreSQL variant)
- Create migration script
- `requirements.txt` (add psycopg2)

---

#### 16. Add Email Notifications System  
**Priority:** MEDIUM | **Effort:** 5-6 hours | **Risk:** LOW  
**Current State:** In-app notifications only

**Notification Types:**
- Friend requests approved
- League invitations and results
- Challenge completions
- Achievement unlocks
- Price alerts triggered
- Daily market summary

**Implementation:**
```python
def send_email_notification(user_id, subject, template, context):
    """Send email notification"""
    user = db.get_user(user_id)
    if not user['email'] or not user['notifications_email_enabled']:
        return
    
    html_body = render_template(f'emails/{template}.html', **context)
    
    send_email(
        to=user['email'],
        subject=subject,
        html_body=html_body
    )
```

**Files to Create/Edit:**
- `notifications.py` (new - email system)
- `templates/emails/*.html` (new - email templates)
- `app.py` (integrate email sending)
- `utils.py` (email utility functions)

---

### PHASE 9: FRONTEND IMPROVEMENTS (Weeks 17-18)

#### 17. Implement Mobile-Optimized UI Improvements  
**Priority:** MEDIUM | **Effort:** 6-8 hours | **Risk:** LOW  
**Current State:** Responsive but not optimized

**Improvements:**
- Touch-friendly buttons and inputs
- Mobile-specific navigation
- Bottom sheet modals (instead of center)
- Swipe gestures for navigation
- Mobile charts (smaller, simplified)
- Progressive Web App (PWA) features
- Offline mode for cached data

**Files to Edit:**
- `static/css/mobile.css` (enhance)
- `templates/*.html` (add mobile classes)
- `static/js/offline.js` (new - offline support)
- `manifest.json` (new - PWA config)

---

#### 18. Add API Documentation and Swagger UI  
**Priority:** MEDIUM | **Effort:** 4-5 hours | **Risk:** LOW  
**Current State:** No API documentation

**Documentation:**
- OpenAPI 3.0 spec for all endpoints
- Interactive Swagger UI
- Example requests/responses
- Authentication details
- Rate limit documentation
- Error code reference

**Implementation:**
```python
# Using flask-restx or connexion for Swagger generation

@api.doc('get_market_status', responses={200: 'Market status'})
@app.route('/api/market/status')
def api_market_status():
    """Get current market status (open/closed)"""
    ...
```

**Files to Create/Edit:**
- `api_docs.py` (new - OpenAPI spec)
- `app.py` (register Swagger UI)
- `/docs` (new route - Swagger UI)

---

### PHASE 10: ADVANCED FEATURES (Weeks 19-20)

#### 19. Implement Machine Learning Predictions for Trades  
**Priority:** LOW | **Effort:** 15-20 hours | **Risk:** MEDIUM  
**Current State:** No ML features

**Models to Build:**
1. **Price Prediction** - LSTM for short-term trends
2. **Sentiment Analysis** - Already using VADER; could use BERT
3. **Anomaly Detection** - Unusual trading patterns
4. **Win Rate Predictor** - Estimate trade success probability

**Implementation:**
```python
def predict_stock_direction(symbol, lookback_days=30):
    """ML model to predict 1-day price direction"""
    # Get historical data
    # Extract features (technical indicators)
    # Run trained model
    # Return probability (0.0 to 1.0)

model = load_trained_model('direction_predictor.pkl')
confidence = model.predict(features)
```

**Files to Create/Edit:**
- `ml/models.py` (new - ML models)
- `ml/data_pipeline.py` (new - data preparation)
- `ml/training.py` (new - model training)
- `app.py` (integrate predictions)

---

#### 20. Add Performance Monitoring and Metrics Collection  
**Priority:** MEDIUM | **Effort:** 5-6 hours | **Risk:** LOW  
**Current State:** Basic logging only

**Metrics to Track:**
```
Performance Metrics
├── Response Times
│   ├── Route latency (p50, p95, p99)
│   ├── Database query times
│   ├── API call times
│   └── WebSocket message latency
├── Business Metrics
│   ├── Trades per minute
│   ├── Active traders (daily/weekly)
│   ├── League creations (daily)
│   └── Average portfolio value
└── System Metrics
    ├── CPU/Memory usage
    ├── Database connections
    ├── Error rates (by endpoint)
    └── Cache hit rates
```

**Implementation:**
```python
# Using Prometheus for metrics

from prometheus_client import Counter, Histogram

trade_counter = Counter('trades_total', 'Total trades', ['type'])
request_duration = Histogram('request_duration_seconds', 'Request duration')

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - request.start_time
    request_duration.observe(duration)
    return response
```

**Files to Create/Edit:**
- `metrics.py` (new - Prometheus setup)
- `app.py` (integrate metrics collection)
- Docker compose with Prometheus/Grafana

---

## 📊 Implementation Timeline

### Quick Wins (Low-Effort, High-Impact)
1. **Fix undefined variables** (2h)
2. **Invite code expiration** (3h)
3. **Max members limit** (3h)
4. **Soft deletes** (4h)

**Total:** ~12 hours for significant stability improvements

### Short-Term (Weeks 1-4)
- All Phase 1-2 items
- **Effort:** ~30-35 hours
- **Impact:** Critical bug fixes + data safety

### Medium-Term (Weeks 5-8)
- Phase 3-4 features
- **Effort:** ~25-30 hours
- **Impact:** Better league system + real-time features

### Long-Term (Weeks 9+)
- Phases 5-10 items
- **Effort:** Variable, can be done incrementally
- **Impact:** Scalability, analytics, ML

---

## 🔄 Continuous Maintenance Items

These should be done regularly throughout development:

1. **Code Quality**
   - Add type hints (gradual migration)
   - Increase test coverage (target: 80%+)
   - Refactor large functions (>200 lines)
   - Update documentation

2. **Security**
   - Run OWASP scan monthly
   - Update dependencies
   - Penetration testing (quarterly)
   - Audit admin actions

3. **Performance**
   - Monitor slow queries
   - Optimize database indexes
   - Update cache strategies
   - Load test regularly

4. **User Feedback**
   - Collect user feedback surveys
   - Track feature requests
   - Monitor error reports
   - Analyze user behavior

---

## 🎯 Success Metrics

Track these as you implement:

| Metric | Current | Target |
|--------|---------|--------|
| Test Coverage | <10% | 80%+ |
| Critical Bugs | 3+ identified | 0 |
| API Response Time (p95) | Unknown | <500ms |
| Trade Execution Success | ~98% | 99.9%+ |
| Uptime | Unknown | 99.9%+ |
| Support Tickets | N/A | <1 per 100 users/month |

---

## 🛠️ Development Setup for Contributors

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock faker

# Run tests
pytest tests/ -v --cov=. --cov-report=html

# Check code quality
flake8 app.py database/ --max-line-length=120
pylint app.py --disable=C0111,R0913

# Load test
locust -f load_test.py --host=http://localhost:5000
```

---

## 📚 Related Documentation

- [BUG_REPORT_AND_FIXES.md](BUG_REPORT_AND_FIXES.md) - Known issues
- [LEAGUE_SYSTEM_IMPROVEMENTS.md](LEAGUE_SYSTEM_IMPROVEMENTS.md) - League details
- [AI_NEXT_STEPS.md](AI_NEXT_STEPS.md) - Original roadmap
- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Current state
- [IMPROVEMENTS_LOG.md](IMPROVEMENTS_LOG.md) - What was done

---

## 💡 Quick Reference: Which Item to Work On?

**If you have 2 hours:** Fix undefined variables (Item #1)  
**If you have 4 hours:** Add rate limiting (Item #3)  
**If you have 1 week:** Do Phase 1 completely (Items #1-2)  
**If you have 1 month:** Do Phases 1-2 (Items #1-5)  
**If you have ongoing:** Cycle through all phases incrementally  

**Recommended Starting Order:**
1. Item #1 (undefined variables) - 2h
2. Item #2 (error handling) - 8h
3. Item #4 (transactions) - 6h
4. Item #5 (tests) - 10h
5. Then any Item in Phases 3-10

---

**Total Estimated Work:** 150-200 hours for all items  
**Critical Path (must do):** Items #1, #2, #4, #5 (~30 hours)  
**Quick Wins:** Items #1, #3, #9, #10 (~10 hours)

Generated by: GitHub Copilot AI  
Last Updated: December 24, 2025
