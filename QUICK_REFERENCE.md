# StockLeague Feature Quick Reference Card

## Phase 1: Completed Features (Dec 25, 2025)

### 1️⃣ League Soft Deletes & Archives
```python
from app import archive_manager

# Archive a league
archive_manager.archive_league(league_id, admin_id, reason="Inactive")

# Restore league
archive_manager.restore_league(league_id, admin_id)

# Get user's archived leagues
leagues = archive_manager.get_user_archived_leagues(user_id)

# Cleanup old archives
deleted_count = archive_manager.cleanup_old_archives(days=180)

# Get statistics
stats = archive_manager.get_archive_statistics()
```

### 2️⃣ Audit Logging System
```python
from app import audit_logger

# Log an action
audit_logger.log_action(
    action='LEAGUE_CREATE',
    resource_type='LEAGUE',
    resource_id=5,
    user_id=1,
    status='success',
    details={'name': 'New League'},
    changes={'field': 'value'},
    ip_address='192.168.1.1',
    user_agent='Mozilla/5.0...'
)

# Get audit trail
logs = audit_logger.get_audit_trail(
    user_id=1,
    resource_type='LEAGUE',
    start_date=datetime.now() - timedelta(days=30)
)

# Generate compliance report
report = audit_logger.generate_compliance_report(days=30)

# Verify trail integrity
is_valid = audit_logger.verify_trail_integrity(log_id=42)
```

**Decorator Usage:**
```python
from feature_integration_helpers import with_audit_log

@app.route('/league/<id>/archive', methods=['POST'])
@with_audit_log('ARCHIVE', 'LEAGUE')
def archive_route(league_id):
    # Automatically logged
    ...
```

**Context Manager:**
```python
from feature_integration_helpers import AuditContext

with AuditContext(audit_logger, 'TRADE_EXECUTE', 'TRADE', trade_id, user_id):
    execute_complex_trade()
    # Auto-logged on context exit
```

### 3️⃣ Invite Code Expiration
```python
from app import invite_code_manager

# Create code (8 chars, expires in 7 days by default)
success, code, msg = invite_code_manager.create_invite_code(
    league_id=5,
    created_by=1,
    expiration_days=7,
    is_single_use=False,
    max_uses=None
)

# Validate code
is_valid, league_id, msg = invite_code_manager.validate_code(
    code=code,
    user_id=2
)

# Use code to join
success, msg = invite_code_manager.use_invite_code(
    code=code,
    user_id=2,
    ip_address='192.168.1.1'
)

# Revoke code
invite_code_manager.revoke_code(code, admin_id=1)

# Cleanup expired codes
count = invite_code_manager.cleanup_expired_codes()

# Get analytics
analytics = invite_code_manager.get_analytics_for_league(league_id=5)
```

### 4️⃣ Max Members Enforcement
```python
from app import members_limit_manager

# Set member limit
members_limit_manager.set_max_members(league_id=5, max_members=20)

# Check if full
is_full = members_limit_manager.is_league_full(league_id=5)

# Get counts
max_count = members_limit_manager.get_max_members(league_id=5)
current_count = members_limit_manager.get_current_member_count(league_id=5)

# Add member (with limit check)
success, msg = members_limit_manager.add_member(league_id=5, user_id=2)

# Handle waitlist
if is_full:
    members_limit_manager.add_to_waitlist(league_id=5, user_id=2)

# Promote from waitlist
promoted_id = members_limit_manager.promote_from_waitlist(league_id=5)

# Get waitlist
waitlist = members_limit_manager.get_waitlist(league_id=5)
```

**Decorator Usage:**
```python
from feature_integration_helpers import with_member_limit_check

@app.route('/league/<id>/join', methods=['POST'])
@with_member_limit_check
def join_league(league_id):
    # Automatically enforces limit
    ...
```

### 5️⃣ Complete Options Trading
```python
from app import options_manager
from helpers import lookup

# Get current price
quote = lookup('AAPL')
current_price = quote['price']  # 175.50

# BUY option
success, msg, position_id = options_manager.buy_option(
    user_id=1,
    league_id=5,
    symbol='AAPL',
    strike_price=175.0,
    expiration_date='2026-01-17',  # YYYY-MM-DD
    option_type='call',  # or 'put'
    quantity=1,
    current_price=current_price
)

# SELL option
success, msg, profit_loss = options_manager.sell_option(
    user_id=1,
    league_id=5,
    position_id=position_id,
    current_price=178.0
)

# Get user positions
positions = options_manager.get_user_positions(
    user_id=1,
    league_id=5,
    status='open'  # or 'closed', 'expired'
)

# Get portfolio stats
stats = options_manager.get_portfolio_stats(user_id=1, league_id=5)

# Check for expired positions
expired_count, messages = options_manager.expire_positions()
```

**Options Contract Details:**
```
Position = {
    'position_id': 1,
    'symbol': 'AAPL',
    'option_type': 'call',
    'strike_price': 175.0,
    'expiration_date': '2026-01-17',
    'quantity': 1,
    'premium_paid': 2.50,      # Price per share at purchase
    'total_cost': 250.00,      # quantity * premium * 100
    'status': 'open',
    'days_to_expiration': 15,
    'is_expired': False
}
```

**Greeks (from pricing):**
```
Greeks = {
    'delta': 0.65,      # -1.0 to +1.0
    'gamma': 0.02,      # Convexity
    'theta': -0.05,     # Daily decay
    'vega': 0.30,       # Volatility sensitivity
    'rho': 0.10         # Interest rate sensitivity
}
```

---

## Database Tables Quick Reference

### Soft Deletes
- `leagues.soft_deleted_at` (TIMESTAMP or NULL)

### Audit Logging
- `audit_logs` (id, action, resource_type, resource_id, user_id, timestamp, checksum)
- `audit_trail_integrity` (log_id, current_checksum, previous_checksum)
- `user_activity_summary` (user_id, date, actions_count)

### Invite Codes
- `invite_codes` (id, code, league_id, expires_at, is_active)
- `invite_code_uses` (code_id, user_id, used_at, ip_address)
- `invite_analytics` (league_id, total_codes, active_codes, total_uses)

### Member Limits
- `league_member_limits` (league_id, max_members, current_members)
- `league_member_waitlist` (id, league_id, user_id, added_at)
- `member_limit_audit` (league_id, old_limit, new_limit, changed_at)

### Options Trading
- `options_contracts` (id, symbol, strike_price, expiration_date, option_type)
- `user_options_positions` (id, user_id, league_id, contract_id, quantity, status)
- `options_price_history` (contract_id, price, timestamp)
- `options_portfolio_stats` (user_id, league_id, total_positions, open_positions)

---

## HTTP Routes

### Archives
- `POST /league/<id>/archive` - Archive league
- `POST /league/<id>/restore` - Restore league
- `GET /admin/archives` - View archives

### Audit
- `GET /admin/audit/logs` - View audit logs
- `GET /admin/audit/logs/json` - Audit API
- `GET /admin/audit/report` - Compliance report

### Invites
- `POST /invite/create` - Create code
- `GET /invite/<code>` - Validate code
- `POST /invite/use` - Use code
- `GET /invite/list` - User's codes

### Members
- `POST /league/<id>/members/limit` - Set limit
- `GET /league/<id>/waitlist` - View waitlist

### Options
- `GET /options` - Dashboard
- `GET /options/chain/<symbol>` - Options chain
- `POST /options/buy` - Buy option
- `POST /options/sell` - Sell option
- `GET /options/positions` - User positions

---

## Common Patterns

### Checking Before Action
```python
# Check if league is full before joining
if members_limit_manager.is_league_full(league_id):
    members_limit_manager.add_to_waitlist(league_id, user_id)
    return "Added to waitlist"
else:
    members_limit_manager.add_member(league_id, user_id)
    return "Joined league"
```

### Log Then Act
```python
# Always log important actions
audit_logger.log_action(action='ACTION', resource_type='TYPE', ...)
# Then execute the action
result = perform_action()
```

### Expire Check
```python
# Check for expired options daily
if options_manager.expire_positions():
    print("Some options expired today")
```

---

## Configuration

### Archive Settings
- Default: 180-day retention before auto-delete
- Can be customized in `cleanup_old_archives(days=X)`

### Invite Code Settings
- Default expiration: 7 days
- Min: 1 day, Max: 365 days
- Code length: 8 characters
- Format: Alphanumeric (A-Z, 0-9)

### Member Limits
- Public leagues: default 50, range 2-500
- Private leagues: default 20, range 2-100
- Exclusive leagues: default 10, range 2-50

### Options Pricing
- Risk-free rate: 4.5% annual
- Default volatility: 30% annual
- Contract size: 100 shares per contract

---

## Error Handling

All features return tuples or dicts with:
- `success` (bool) - Operation succeeded
- `message` (str) - User-friendly message
- `data` (optional) - Return value

```python
success, message, data = feature_manager.method(...)
if not success:
    return error(message), 400
return success_response(data)
```

---

## Performance Notes

- All features use database indices for fast lookups
- Audit logs rotate with integrity verification
- Invite codes use cryptographic generation
- Options pricing uses scipy.stats for accuracy

---

**Full Documentation:** See `FEATURE_INTEGRATION_GUIDE.md`
**Completion Report:** See `PHASE_1_COMPLETION_REPORT.md`
