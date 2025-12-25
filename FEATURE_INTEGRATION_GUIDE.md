# Feature Integration & Implementation Guide

## Completed Features (In-Progress Phase 1)

### 1. League Soft Deletes & Archives ✓
**Status:** Core implemented, routes integrated
**Files:**
- `soft_deletes.py` - LeagueArchiveManager class
- `database/db_manager.py` - archive/restore database methods
- `app.py` - archive/restore/list routes

**Integration Points:**
- Added `archive_manager = LeagueArchiveManager(db)` initialization in app.py
- Routes available at `/league/<id>/archive` and `/league/<id>/restore`
- Database column: `leagues.soft_deleted_at`

**Key Methods:**
```python
archive_manager.archive_league(league_id, admin_id, reason)
archive_manager.restore_league(league_id, admin_id)
archive_manager.get_user_archived_leagues(user_id, admin_only=False)
archive_manager.cleanup_old_archives(days=180, admin_id)
archive_manager.get_archive_statistics()
archive_manager.permanently_delete_league(league_id, admin_id, confirm=True)
```

### 2. Audit Logging System ✓
**Status:** Core implemented, routes integrated
**Files:**
- `audit_logger.py` - AuditLogger and AuditLog classes
- `audit_routes.py` - Flask blueprint with audit UI routes
- `app.py` - audit logger initialization and blueprint registration

**Integration Points:**
- Added `audit_logger = AuditLogger(db)` initialization in app.py
- Blueprint registered at `/admin/audit/` with dashboard and JSON endpoints
- Database tables: `audit_logs`, `audit_trail_integrity`, `user_activity_summary`

**Key Methods:**
```python
audit_logger.log_action(action, resource_type, resource_id, user_id, 
                       status='success', details, changes, ip_address, user_agent)
audit_logger.get_audit_trail(user_id, resource_type, action, start_date, limit)
audit_logger.get_user_activity_summary(user_id, date)
audit_logger.generate_compliance_report(days=30)
audit_logger.verify_trail_integrity(log_id)
```

**Helper Decorators:**
```python
@with_audit_log('ARCHIVE', 'LEAGUE')
def archive_league(league_id):
    # Automatically logs action to audit trail
    ...

with AuditContext(audit_logger, 'TRADE_EXECUTE', 'TRADE', trade_id, user_id):
    # Logs complex operations
    execute_trade(...)
```

### 3. Invite Code Expiration ✓
**Status:** Core implemented, routes integrated
**Files:**
- `invite_manager.py` - InviteCodeManager class
- `invite_routes.py` - Flask routes for invite management
- `app.py` - invite manager initialization

**Integration Points:**
- Added `invite_code_manager = InviteCodeManager(db)` initialization in app.py
- Database tables: `invite_codes`, `invite_code_uses`, `invite_analytics`
- Routes available at `/invite/create`, `/invite/validate`, `/invite/list`

**Key Methods:**
```python
invite_code_manager.create_invite_code(league_id, created_by, 
                                       expiration_days=7, is_single_use=False, max_uses=None)
invite_code_manager.validate_code(code, user_id)
invite_code_manager.use_invite_code(code, user_id, ip_address)
invite_code_manager.revoke_code(code, admin_id)
invite_code_manager.cleanup_expired_codes()
invite_code_manager.get_analytics_for_league(league_id)
```

**Code Generation:**
- Format: 8 alphanumeric characters (e.g., "INVITE12")
- Automatically unique
- Expiration: configurable 1-365 days
- Supports single-use or multi-use with limits

### 4. Max Members Enforcement ✓
**Status:** Core implemented, routes integrated
**Files:**
- `members_limit_manager.py` - MembersLimitManager class
- `members_limit_routes.py` - Flask routes
- `app.py` - members limit manager initialization

**Integration Points:**
- Added `members_limit_manager = MembersLimitManager(db)` initialization in app.py
- Database tables: `league_member_limits`, `league_member_waitlist`, `member_limit_audit`
- Default limits: public=50, private=20, exclusive=10

**Key Methods:**
```python
members_limit_manager.set_max_members(league_id, max_members)
members_limit_manager.is_league_full(league_id)
members_limit_manager.get_current_member_count(league_id)
members_limit_manager.add_member(league_id, user_id)
members_limit_manager.add_to_waitlist(league_id, user_id)
members_limit_manager.get_waitlist(league_id)
members_limit_manager.promote_from_waitlist(league_id)
```

**Helper Decorator:**
```python
@with_member_limit_check
def join_league(league_id):
    # Automatically checks and enforces member limits
    ...
```

---

## Usage Guide - Using the Features

### Archiving a League
```python
from app import archive_manager

# Archive a league
success, message = archive_manager.archive_league(
    league_id=5,
    admin_id=1,
    reason="Inactive for 6 months"
)

# Later, restore it
success, message = archive_manager.restore_league(
    league_id=5,
    admin_id=1
)

# Cleanup old archives
deleted_count, message = archive_manager.cleanup_old_archives(
    days=180,
    admin_id=1
)
```

### Logging Audit Events
```python
from app import audit_logger
from feature_integration_helpers import AuditContext

# Simple logging
audit_logger.log_action(
    action='TRADE_EXECUTE',
    resource_type='TRADE',
    resource_id=42,
    user_id=1,
    details={'symbol': 'AAPL', 'quantity': 100},
    changes={'cash_before': 5000, 'cash_after': 4500}
)

# Or use context manager for complex operations
with AuditContext(audit_logger, 'TRADE_EXECUTE', 'TRADE', trade_id, user_id):
    execute_trade(...)  # Logs automatically on exit
```

### Creating and Using Invite Codes
```python
from app import invite_code_manager

# Create invite code
success, code, message = invite_code_manager.create_invite_code(
    league_id=5,
    created_by=1,
    expiration_days=7,
    is_single_use=True
)

# Validate code
is_valid, league_id, message = invite_code_manager.validate_code(
    code=code,
    user_id=2
)

# Use code to join
success, message = invite_code_manager.use_invite_code(
    code=code,
    user_id=2,
    ip_address='192.168.1.1'
)

# Check analytics
analytics = invite_code_manager.get_analytics_for_league(league_id=5)
```

### Enforcing Member Limits
```python
from app import members_limit_manager

# Set member limit for league
members_limit_manager.set_max_members(league_id=5, max_members=20)

# Check if full
is_full = members_limit_manager.is_league_full(league_id=5)

# Get current count
count = members_limit_manager.get_current_member_count(league_id=5)

# Handle waitlist
if is_full:
    members_limit_manager.add_to_waitlist(league_id=5, user_id=2)
    
# Promote from waitlist when space opens
members_limit_manager.promote_from_waitlist(league_id=5)
```

---

## Testing

### Test Files Available
- `test_soft_deletes.py` - League archiving tests (20 tests)
- `test_audit_logger.py` - Audit logging tests (35+ tests)
- `test_invite_codes.py` - Invite code tests (25+ tests)

### Running Tests
```bash
# Run all tests for a feature
python -m pytest test_soft_deletes.py -v

# Run specific test class
python -m pytest test_audit_logger.py::TestAuditLogger -v

# Run with coverage
python -m pytest test_invite_codes.py --cov=invite_manager -v
```

---

## Database Schema

### Key Tables
- **audit_logs** - All audit trail entries with checksums
- **audit_trail_integrity** - Integrity verification records
- **user_activity_summary** - Daily activity summaries
- **invite_codes** - Time-limited invite codes
- **invite_code_uses** - Track who used each code
- **invite_analytics** - Code usage analytics
- **league_member_limits** - Per-league member limits
- **league_member_waitlist** - Users waiting to join full leagues
- **leagues.soft_deleted_at** - Timestamp when league was archived

---

## Best Practices

### 1. Always Use Audit Logging
```python
# Good - logs the action
audit_logger.log_action(
    action='LEAGUE_ARCHIVE',
    resource_type='LEAGUE',
    resource_id=league_id,
    user_id=user_id
)

# Better - use decorator
@with_audit_log('LEAGUE_ARCHIVE', 'LEAGUE')
def archive_route(league_id):
    ...
```

### 2. Check Member Limits Before Adding
```python
# Always check limits
if members_limit_manager.is_league_full(league_id):
    # Offer waitlist
    members_limit_manager.add_to_waitlist(league_id, user_id)
```

### 3. Validate Invite Codes Properly
```python
# Always validate expiration and usage
is_valid, league_id, message = invite_code_manager.validate_code(code)
if not is_valid:
    return error(message)
```

### 4. Archive Old Leagues Periodically
```python
# Schedule monthly cleanup
@scheduler.scheduled_job('cron', day_of_week='0', hour='2')
def cleanup_old_archives():
    archive_manager.cleanup_old_archives(days=180, admin_id=1)
```

---

## Next Features to Implement

1. **Complete Options Trading** - Options Greeks, pricing, execution
2. **Redis Caching Layer** - Cache leaderboards, user data, expensive queries
3. **Admin Monitoring Dashboard** - Real-time stats, user activity, system health
4. **Advanced Portfolio Analytics** - Performance attribution, risk analysis
5. **PostgreSQL Migration** - Move from SQLite to PostgreSQL
6. **Email Notifications** - League events, trades, achievements
7. **Mobile Optimizations** - Responsive design, touch UI
8. **API Documentation (Swagger)** - Interactive API docs
9. **ML Predictions** - Price predictions, portfolio recommendations
10. **Performance Monitoring** - Query optimization, bottleneck detection

---

## Middleware Integration

All managers are automatically available in Flask request context via middleware:

```python
from flask import request

@app.route('/league/join', methods=['POST'])
def join_league():
    # Automatically available
    request.audit_logger.log_action(...)
    request.members_limit_manager.get_current_member_count(...)
    request.invite_code_manager.validate_code(...)
    request.archive_manager.get_user_archived_leagues(...)
```

---

## Troubleshooting

### Audit logs not appearing
1. Check that `audit_logger` is initialized in app.py
2. Verify database tables exist: `SELECT * FROM audit_logs;`
3. Check logs for errors: `tail -f /tmp/flask.log`

### Invite codes expiring too quickly
1. Check `invite_codes.expires_at` column
2. Verify system clock is correct
3. Test with `invite_code_manager.validate_code(code)`

### Member limits not enforced
1. Verify table exists: `SELECT * FROM league_member_limits;`
2. Check max_members value is set correctly
3. Ensure decorator is applied to join route

### Archives not working
1. Verify `soft_deleted_at` column exists in leagues table
2. Test directly: `archive_manager.archive_league(league_id)`
3. Check database for errors

---

## Documentation URLs

- Audit Routes: `/admin/audit/logs` (view logs)
- Audit JSON API: `/admin/audit/logs/json` (API access)
- Archive Routes: `/league/<id>/archive` (archive action)
- Invite Routes: `/invite/create` (create code)
