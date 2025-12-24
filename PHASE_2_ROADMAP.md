# Phase 2 & Beyond - Items #6-20 Roadmap

## Phase 2 (Items #6-10) - Real-Time Features & Governance

### Item #6: WebSocket Real-Time Leaderboard Updates
**Estimated Effort**: 20 hours
**Priority**: HIGH
**Dependencies**: None

**Scope**:
- Real-time score updates as trades execute
- Activity feed broadcasting to league members
- Trade notifications
- Position change alerts
- Leaderboard rank updates

**Implementation**:
```python
@socketio.on('join_league')
def on_join_league(data):
    league_id = data['league_id']
    join_room(f'league_{league_id}')
    
@socketio.on('trade_executed')
def on_trade_executed(trade_data):
    league_id = trade_data['league_id']
    # Recalculate league scores
    scores = db.update_league_scores(league_id)
    # Broadcast to all members
    socketio.emit('leaderboard_update', {
        'league_id': league_id,
        'scores': scores,
        'updated_at': datetime.now().isoformat()
    }, room=f'league_{league_id}')
```

**Files to Modify**:
- app.py - Add WebSocket handlers
- templates/league_detail.html - Add real-time updates
- static/js/league.js - New WebSocket client

**Tests Needed**:
- WebSocket connection tests
- Real-time update delivery
- Disconnection handling
- Multiple browser tab sync

---

### Item #7: Soft Deletes for League Archives
**Estimated Effort**: 12 hours
**Priority**: MEDIUM
**Dependencies**: Item #8 (audit logging recommended)

**Scope**:
- Add `deleted_at` timestamp to leagues table
- Archive instead of delete completed leagues
- Allow league admins to recover deleted leagues
- Exclude deleted leagues from normal queries
- Audit trail for deletions

**Schema Changes**:
```sql
ALTER TABLE leagues ADD COLUMN deleted_at TIMESTAMP NULL;
CREATE INDEX idx_leagues_deleted ON leagues(deleted_at);
```

**Implementation**:
```python
def soft_delete_league(league_id):
    """Archive a league instead of deleting"""
    conn = self.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE leagues 
        SET deleted_at = ? 
        WHERE id = ?
    """, (datetime.now(), league_id))
    conn.commit()
    conn.close()

def get_league(league_id, include_deleted=False):
    """Get league, optionally including deleted ones"""
    conn = self.get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM leagues WHERE id = ?"
    params = [league_id]
    
    if not include_deleted:
        query += " AND deleted_at IS NULL"
    
    cursor.execute(query, params)
    league = cursor.fetchone()
    conn.close()
    return dict(league) if league else None
```

**Files to Modify**:
- database/db_manager.py - Add soft delete methods
- app.py - Update queries to exclude deleted
- admin routes - Add recovery functionality

---

### Item #8: Comprehensive Audit Logging System
**Estimated Effort**: 15 hours
**Priority**: MEDIUM
**Dependencies**: Error handling (complete)

**Scope**:
- Log all trade executions
- Log league membership changes
- Log user permission changes
- Log admin actions
- Searchable audit trail
- Compliance-ready format

**New Table**:
```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id INTEGER,
    details JSON,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Implementation**:
```python
def log_audit(user_id, action, entity_type, entity_id, details, request):
    """Log an audit event"""
    conn = self.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_logs 
        (user_id, action, entity_type, entity_id, details, 
         ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, action, entity_type, entity_id,
        json.dumps(details),
        request.remote_addr,
        request.user_agent
    ))
    conn.commit()
    conn.close()

# Usage in routes
log_audit(user_id, 'TRADE_BUY', 'stock', symbol, 
          {'shares': 100, 'price': 150.0}, request)
```

**Files to Create**:
- audit_logger.py - Audit logging utilities

**Files to Modify**:
- app.py - Add audit logging to key routes
- database/db_manager.py - Audit table management

---

### Item #9: Invite Code Expiration Validation
**Estimated Effort**: 8 hours
**Priority**: LOW
**Dependencies**: None

**Scope**:
- Add expiration timestamps to invite codes
- Validate expiration on league join
- Auto-generate new codes for admins
- Show remaining validity time

**Schema Changes**:
```sql
ALTER TABLE league_invites ADD COLUMN 
    expires_at TIMESTAMP DEFAULT (datetime('now', '+30 days'));
```

**Implementation**:
```python
def is_invite_valid(code):
    """Check if invite code is valid and not expired"""
    conn = self.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, league_id, expires_at 
        FROM league_invites 
        WHERE code = ? AND expires_at > ? AND used = 0
    """, (code, datetime.now()))
    
    result = cursor.fetchone()
    conn.close()
    return result is not None
```

---

### Item #10: Max Members Limit Enforcement
**Estimated Effort**: 8 hours
**Priority**: LOW
**Dependencies**: None

**Scope**:
- Add max_members field to leagues
- Validate on join
- Show capacity in league list
- Auto-close league when full

**Implementation**:
```python
def join_league(league_id, user_id):
    """Join league with member limit check"""
    league = self.get_league(league_id)
    if not league:
        return False, "League not found"
    
    members = self.get_league_members(league_id)
    if len(members) >= league['max_members']:
        return False, f"League is full ({league['max_members']} members)"
    
    # Proceed with join
    return self.add_league_member(league_id, user_id)
```

---

## Phase 3 (Items #11-15) - Advanced Features & Infrastructure

### Item #11: Options Trading Implementation
**Estimated Effort**: 40+ hours
**Priority**: MEDIUM
**Complexity**: HIGH

**Scope**:
- Call/put option trading
- Strike price selection
- Expiration date handling
- Greeks calculation (delta, gamma, theta, vega)
- Option valuation models

**Key Components**:
- New options table schema
- Options pricing calculator
- Greeks computation
- Route handlers for options trading
- Option portfolio display

**Challenge**: High mathematical complexity, external pricing data needed

---

### Item #12: Redis Caching Layer
**Estimated Effort**: 24 hours
**Priority**: MEDIUM
**Dependencies**: Item #15 (PostgreSQL migration recommended)

**Scope**:
- Cache user portfolios (5-minute TTL)
- Cache leaderboard scores (1-minute TTL)
- Cache stock quotes (1-minute TTL)
- Cache popular stocks list (hourly)
- Cache user session data

**Benefits**:
- 10x faster lookups for hot data
- Reduced database load
- Better scalability
- Real-time invalidation on changes

---

### Item #13: Admin Dashboard
**Estimated Effort**: 20 hours
**Priority**: LOW
**Dependencies**: Audit logging (Item #8)

**Scope**:
- System health monitoring
- User statistics
- Trade volume tracking
- Error rate monitoring
- Audit log search
- Manual actions (reset user, delete league, etc.)

---

### Item #14: Advanced Portfolio Analytics
**Estimated Effort**: 25 hours
**Priority**: MEDIUM

**Scope**:
- Performance attribution
- Risk metrics (Sharpe ratio, max drawdown)
- Sector allocation charts
- Correlation analysis
- Historical performance comparison

---

### Item #15: PostgreSQL Migration
**Estimated Effort**: 30+ hours
**Priority**: HIGH (for production)
**Dependencies**: All previous items

**Scope**:
- Database schema migration
- ORM/query abstraction
- Connection pooling
- Prepared statements
- Backup/recovery procedures

**Benefits**:
- Unlimited scalability
- Production-grade reliability
- Better query optimization
- Replication support

---

## Phase 4 (Items #16-20) - Growth & Intelligence

### Item #16: Email Notifications System
**Estimated Effort**: 15 hours
**Priority**: MEDIUM

**Scope**:
- Trade confirmation emails
- League invitation emails
- Achievement emails
- Weekly summary reports
- Notification preferences

---

### Item #17: Mobile-Optimized UI
**Estimated Effort**: 30+ hours
**Priority**: HIGH (for adoption)

**Scope**:
- Responsive design overhaul
- Touch-friendly controls
- Mobile app (PWA or native)
- Optimized performance
- Mobile trading experience

---

### Item #18: API Documentation & Swagger UI
**Estimated Effort**: 12 hours
**Priority**: MEDIUM

**Scope**:
- OpenAPI/Swagger specification
- Interactive API documentation
- Example requests/responses
- Authentication guide
- Rate limit documentation

---

### Item #19: ML Predictions for Trades
**Estimated Effort**: 40+ hours
**Priority**: LOW
**Complexity**: VERY HIGH

**Scope**:
- Price prediction models
- Technical indicator analysis
- Sentiment analysis
- Portfolio optimization suggestions
- Risk assessment

**Challenges**:
- Complex ML infrastructure
- Data quality requirements
- Model training/updates
- Feature engineering

---

### Item #20: Performance Monitoring & Metrics
**Estimated Effort**: 16 hours
**Priority**: MEDIUM

**Scope**:
- Transaction latency tracking
- Error rate monitoring
- User engagement metrics
- API performance metrics
- Database query optimization

---

## Prioritization Matrix

### High Priority (Complete in Phase 2-3)
1. ✅ Item #1-5 (DONE - Phase 1)
2. Item #6 - WebSocket real-time updates (HIGH impact, moderate effort)
3. Item #15 - PostgreSQL migration (Required for scale)
4. Item #12 - Redis caching (Improves performance 10x)

### Medium Priority (Phase 3-4)
- Item #7-9 - Governance features
- Item #14 - Portfolio analytics
- Item #16 - Email notifications
- Item #20 - Metrics & monitoring

### Low Priority (Nice-to-Have)
- Item #11 - Options trading (Very complex)
- Item #13 - Admin dashboard
- Item #17 - Mobile UI (if native app planned)
- Item #18 - API docs (good for partners)
- Item #19 - ML predictions (research phase)

## Recommended Implementation Order

**For MVP v1** (3-4 weeks):
```
✅ Items #1-5 (COMPLETE)
→ Item #6 (Real-time updates)
→ Item #7-8 (Governance)
→ Item #9-10 (Validation)
= Basic stable platform ready
```

**For MVP v2** (4-6 weeks):
```
→ Item #12 (Redis caching)
→ Item #15 (PostgreSQL)
→ Item #14 (Analytics)
→ Item #16 (Notifications)
= Production-ready, scalable
```

**For v2 Features** (6-12 weeks):
```
→ Item #11 (Options - optional)
→ Item #17 (Mobile UI)
→ Item #18 (API docs)
→ Item #20 (Monitoring)
= Enterprise features
```

---

## Effort & Timeline Estimate

| Phase | Items | Effort | Timeline |
|-------|-------|--------|----------|
| 1 | #1-5 | ✅ DONE | Complete |
| 2 | #6-10 | 60 hours | 2-3 weeks |
| 3 | #11-15 | 120 hours | 4-6 weeks |
| 4 | #16-20 | 100 hours | 3-5 weeks |
| **TOTAL** | **All 20** | **~280 hours** | **~12-14 weeks** |

---

## Current Roadmap Status

```
✅ Phase 1: Core Foundation (COMPLETE)
   - Error handling ✅
   - Transactions ✅
   - Testing ✅
   - Throttling ✅

▶️ Phase 2: Real-Time Features (NEXT)
   - WebSocket updates [START HERE]
   - Governance features
   - Validation rules

⏳ Phase 3: Infrastructure
   - PostgreSQL migration
   - Redis caching
   - Advanced analytics

⏳ Phase 4: Growth
   - Mobile UI
   - API docs
   - Email notifications
   - ML predictions
```

---

## Dependencies & Blocking Issues

### Item #6 (WebSocket) - Can start immediately
- No dependencies
- Uses existing error handlers
- Can be tested in isolation

### Item #11 (Options) - Blocked until:
- Decision on options complexity
- External pricing data source
- Greeks calculator library

### Item #15 (PostgreSQL) - Depends on:
- Item #1-5 (atomic transactions) ✅
- Item #8 (audit logging) recommended
- Schema migration plan needed

---

## Resource Requirements

### Development
- 1 Backend Developer (primary)
- Frontend Developer for Items #17
- DevOps for Item #15

### Infrastructure
- SQLite (current) → PostgreSQL (Item #15)
- Redis instance (Item #12)
- WebSocket server support (Item #6)
- Email service integration (Item #16)

### Testing
- 80+ unit tests (done) ✅
- Load testing (Item #12 onwards)
- Performance testing (Item #15)

---

**Next Action**: Begin Item #6 - WebSocket Real-Time Leaderboard Updates
