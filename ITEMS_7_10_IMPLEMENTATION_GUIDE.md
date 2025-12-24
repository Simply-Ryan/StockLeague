# Items #7-10 Implementation Guide

## Quick Reference for Next Batch

### Item #7: Soft Deletes for League Archives (Estimated: 40 minutes)

**What It Does:**
- Archive inactive leagues instead of hard-deleting them
- Allow restoration of archived leagues
- Keep historical data intact

**Technical Approach:**
1. Add `archived_at` column to leagues table
2. Soft delete by setting timestamp: `UPDATE leagues SET archived_at = NOW() WHERE id = ?`
3. Filter queries to exclude archived: `WHERE archived_at IS NULL`
4. Create `restore_league()` function: Clear archived_at timestamp
5. Create archive management utility functions

**Database Migration:**
```sql
ALTER TABLE leagues ADD COLUMN archived_at TIMESTAMP NULL;
CREATE INDEX idx_leagues_archived ON leagues(archived_at);
```

**Key Files to Create/Modify:**
- `database/db_manager.py` - Add archive_league(), restore_league() methods
- `app.py` - Modify league queries to filter archived
- Create `archive_utils.py` helper module
- Tests: `test_soft_deletes.py`

**Verification Points:**
- Archived leagues not visible in /leagues
- Archived leagues can be restored by admin
- Historical data preserved
- Ratings/standings unchanged for restored leagues

---

### Item #8: Comprehensive Audit Logging (Estimated: 60 minutes)

**What It Does:**
- Log all significant user actions (trades, joins, leaves, admin actions)
- Store audit trail for compliance/debugging
- Enable action replay and reversal for admins

**Technical Approach:**
1. Create `AuditLog` table:
   - user_id, action_type, entity_type, entity_id, details, timestamp, ip_address
2. Create audit decorators: `@audit_action()`
3. Intercept major operations:
   - Trades (buy/sell)
   - League joins/leaves
   - Profile updates
   - Admin actions (kicks, score resets)
   - Settings changes
4. Add query functions for audit retrieval

**Key Functions:**
- `log_audit_event(user_id, action_type, entity_type, entity_id, details)`
- `get_user_audit_trail(user_id, limit=100)`
- `get_entity_audit_trail(entity_type, entity_id)`
- `@audit_action('trade_buy')` decorator

**Database Migration:**
```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    action_type TEXT,
    entity_type TEXT,
    entity_id INTEGER,
    details TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(created_at);
```

**Key Files to Create/Modify:**
- Create `audit_logging.py` - Core audit functionality
- `database/db_manager.py` - Add audit methods
- `app.py` - Add @audit_action decorators
- Create admin view: `/audit-logs` route
- Tests: `test_audit_logging.py`

**Verification Points:**
- Trades logged with buy/sell details
- League joins/leaves captured
- Admin actions tracked
- Audit trail queryable by user/entity
- Details JSON stored correctly

---

### Item #9: Invite Code Expiration (Estimated: 30 minutes)

**What It Does:**
- Add expiration dates to league invite codes
- Prevent old invites from working
- Notify users when invites expire

**Technical Approach:**
1. Add `expires_at` column to invite codes
2. Generate code with default expiration (7, 14, 30 days configurable)
3. Validate expiration in `/leagues/join` route
4. Clean up expired invites periodically
5. Allow admins to regenerate codes

**Database Migration:**
```sql
ALTER TABLE league_invites ADD COLUMN expires_at TIMESTAMP;
ALTER TABLE league_invites ADD COLUMN generated_by INTEGER;
CREATE INDEX idx_invites_expires ON league_invites(expires_at);
```

**Key Functions:**
- `generate_invite_code(league_id, expires_in_days=14)` - Create new code
- `is_invite_code_valid(code)` - Check if not expired
- `regenerate_invite_code(league_id)` - New code for league
- Cleanup task to delete expired codes

**Key Files to Modify:**
- `database/db_manager.py` - Add expires_at handling
- `app.py` - Validate expiration in /leagues/join
- `helpers.py` - Add expiration utilities
- Tests: `test_invite_expiration.py`

**API Changes:**
- POST `/leagues/<id>/join` - Now checks expiration
- POST `/leagues/<id>/regenerate-invite` - Generate new code
- GET `/leagues/<id>/settings` - Show expiration time

**Verification Points:**
- New codes generated with expiration
- Expired codes rejected on join
- Regenerate code works
- Admin can see expiration time
- User gets friendly error message

---

### Item #10: Max Members Limit Enforcement (Estimated: 25 minutes)

**What It Does:**
- Enforce maximum member limit per league
- Prevent joins when limit reached
- Show capacity in UI

**Technical Approach:**
1. Add `max_members` column to leagues table
2. Add validation in `join_league()` route
3. Check current members vs limit
4. Return friendly error if at capacity
5. Show capacity in leaderboard UI

**Database Migration:**
```sql
ALTER TABLE leagues ADD COLUMN max_members INTEGER DEFAULT 100;
```

**Key Changes:**
1. `join_league()` route - Add capacity check
2. `league_detail()` - Return member count vs limit
3. `create_league()` - Allow max_members parameter
4. Leaderboard display - Show capacity (e.g., "8/10 members")

**Validation Logic:**
```python
members = db.get_league_members(league_id)
if len(members) >= league['max_members']:
    return apology(f"League is full ({league['max_members']}/{league['max_members']} members)")
```

**Key Files to Modify:**
- `database/db_manager.py` - Add max_members handling
- `app.py` - Validate in join_league()
- `templates/league_detail.html` - Show capacity
- Tests: `test_max_members.py`

**UI Changes:**
- League card: Show "8/10 members"
- Join button: Disabled if full
- Error message: "League is full"
- Settings: Allow admin to change limit

**Verification Points:**
- Leagues created with default/custom limit
- Join blocked at limit
- Capacity shown in UI
- Admin can change limit
- Error messages clear

---

## Implementation Order & Dependencies

```
Item #7: Soft Deletes
    ├─ No dependencies
    └─ Enables: Better league management
    
Item #8: Audit Logging
    ├─ Depends on: League operations (already exist)
    └─ Benefits: All subsequent changes audited
    
Item #9: Invite Expiration
    ├─ Depends on: Invite code system (already exists)
    └─ Independent: Can be done in parallel
    
Item #10: Max Members
    ├─ Depends on: League creation, join logic (exist)
    └─ Parallel: Can be done with Item #9
```

**Recommended Order:**
1. Item #7 (enables archive management)
2. Item #8 (audit everything after)
3. Items #9 & #10 (can be parallel, no dependencies)

---

## Database Migrations Summary

**Total Schema Changes**: 5
```sql
-- Item #7: Soft Deletes
ALTER TABLE leagues ADD COLUMN archived_at TIMESTAMP NULL;

-- Item #8: Audit Logging (new table)
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    action_type TEXT,
    entity_type TEXT,
    entity_id INTEGER,
    details TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Item #9: Invite Expiration
ALTER TABLE league_invites ADD COLUMN expires_at TIMESTAMP;
ALTER TABLE league_invites ADD COLUMN generated_by INTEGER;

-- Item #10: Max Members
ALTER TABLE leagues ADD COLUMN max_members INTEGER DEFAULT 100;
```

**Migration File**: Create `migrations/add_items_7_10.py`

---

## Testing Strategy for Items #7-10

**Test Files to Create:**
1. `test_soft_deletes.py` (20-30 tests)
2. `test_audit_logging.py` (25-35 tests)
3. `test_invite_expiration.py` (15-20 tests)
4. `test_max_members.py` (15-20 tests)

**Test Coverage Areas:**
- Basic functionality
- Edge cases
- Error handling
- Integration tests
- Performance tests

---

## Common Patterns to Follow

All implementations should follow patterns established in Items #1-6:

✅ **Error Handling**
```python
try:
    # operation
except Exception as e:
    logger.error(f"Error: {e}")
    return apology("User-friendly message", 400)
```

✅ **Database Operations**
```python
def operation(self, params):
    """Clear docstring"""
    try:
        # operation
        self.db.commit()
        return True
    except Exception as e:
        logger.error(f"Error: {e}")
        self.db.rollback()
        return False
```

✅ **WebSocket Broadcasting**
```python
try:
    socketio.emit('event_name', data, room=f'room_name')
except Exception as e:
    logger.error(f"Error broadcasting: {e}")
```

✅ **Validation**
```python
if not params:
    return apology("Parameter required", 400)

if len(records) == 0:
    return apology("Not found", 404)
```

---

## Quick Start Commands

**Run tests for Items #7-10 (when ready):**
```bash
python -m pytest test_soft_deletes.py -v
python -m pytest test_audit_logging.py -v
python -m pytest test_invite_expiration.py -v
python -m pytest test_max_members.py -v
```

**Check syntax:**
```bash
python -m py_compile archive_utils.py audit_logging.py
```

**Run database migrations:**
```bash
python migrations/add_items_7_10.py
```

---

## Documentation to Create

For each item, create:
1. `ITEM_#_FEATURE_COMPLETE.md` - Comprehensive reference
2. `ITEM_#_SESSION_SUMMARY.md` - What was done in session
3. Update `NEXT_FEATURES_IMPLEMENTATION_PLAN.md` - Progress tracking

---

## Success Criteria

Each item should have:
- ✅ All functions implemented and tested
- ✅ No syntax errors (verified via Pylance)
- ✅ 40+ test cases per item
- ✅ Error handling 100% coverage
- ✅ Documentation complete
- ✅ Backwards compatible
- ✅ Production-ready code

---

## Estimated Timeline

| Item | Time | Status |
|------|------|--------|
| #7 Soft Deletes | 40 min | Ready to start |
| #8 Audit Logging | 60 min | Depends on #7 |
| #9 Invite Expiration | 30 min | Can parallel with #10 |
| #10 Max Members | 25 min | Can parallel with #9 |
| **Total** | **155 min** | **≈ 2.5 hours** |

**Phase 2 (Items #6-10)**: ~3.5 hours total (Item #6 done in 45 min)

---

## Next Action

Ready to proceed with Item #7: Soft Deletes for League Archives?

Let me know when you want to start, and I'll follow this implementation guide!
