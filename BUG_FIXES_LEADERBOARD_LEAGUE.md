# Bug Fixes - Leaderboard & League System

## Summary
Fixed two critical bugs in the StockLeague application:
1. **Global Leaderboard Error**: Fixed "ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE constraint" error
2. **League Leave Bug**: Improved cleanup when users leave leagues

---

## Fix 1: Leaderboard ON CONFLICT Error

### Problem
The global leaderboard caching function was failing with:
```
ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE constraint
```

**Root Cause**: The `leaderboards` table in the database schema was created without a UNIQUE constraint on the `(leaderboard_type, period)` columns, but the code attempted to use `ON CONFLICT(leaderboard_type, period)` which requires either a PRIMARY KEY or UNIQUE constraint.

**Location**: `/database/db_manager.py` lines 323-340 (schema definition)

### Solution
Added a `UNIQUE` constraint to the `leaderboards` table definition:

```sql
CREATE TABLE IF NOT EXISTS leaderboards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    leaderboard_type TEXT NOT NULL,
    period TEXT NOT NULL,
    data_json TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(leaderboard_type, period)  -- Added UNIQUE constraint
)
```

### Affected Code
- **File**: `/database/db_manager.py` line 323-332
- **Change**: Added `UNIQUE(leaderboard_type, period)` constraint to schema
- **Impact**: Allows `ON CONFLICT` clauses in `/app.py` lines 1744 and 1798 to work correctly

### Migration
Created `migrate_leaderboards_table.py` to handle existing databases:
- Backs up existing leaderboard data
- Drops and recreates table with UNIQUE constraint
- Restores deduplicated data (keeping most recent entries)

---

## Fix 2: League Leave Cleanup

### Problem
When a user left a league, their data wasn't being properly cleaned up:
- User could still see the league in "My Leagues" after leaving as owner
- Orphaned portfolio records remained in the database
- User's holdings and transactions weren't deleted

**Root Cause**: The `leave_league()` method only deleted the user from `league_members` table, but left related portfolio data (portfolios, holdings, transactions, member_stats) in place.

**Location**: `/database/db_manager.py` lines 1158-1230 (leave_league method)

### Solution
Added comprehensive cleanup when a user leaves a league:

```python
# Clean up user's portfolio data when they leave
cursor.execute(
    "DELETE FROM league_portfolios WHERE league_id = ? AND user_id = ?",
    (league_id, user_id)
)
cursor.execute(
    "DELETE FROM league_holdings WHERE league_id = ? AND user_id = ?",
    (league_id, user_id)
)
cursor.execute(
    "DELETE FROM league_transactions WHERE league_id = ? AND user_id = ?",
    (league_id, user_id)
)
cursor.execute(
    "DELETE FROM league_member_stats WHERE league_id = ? AND user_id = ?",
    (league_id, user_id)
)
```

### Affected Code
- **File**: `/database/db_manager.py` lines 1183-1200
- **Change**: Added 4 DELETE statements after removing user from league_members
- **Impact**: 
  - Prevents orphaned portfolio records
  - `get_user_leagues()` query correctly excludes left leagues (via INNER JOIN on league_members)
  - User's data completely cleaned up when they leave

### Data Cleanup Sequence
1. Remove from `league_members` (membership)
2. Transfer ownership if user is creator
3. Delete from `league_portfolios` (portfolio data)
4. Delete from `league_holdings` (stock holdings)
5. Delete from `league_transactions` (transaction history)
6. Delete from `league_member_stats` (member statistics)
7. Auto-delete entire league if no members remain

---

## Testing

### Test Files Created
1. **`migrate_leaderboards_table.py`**: Migration utility for existing databases
2. **`test_bug_fixes.py`**: Test suite to verify both fixes

### How to Test

#### Test 1: Leaderboard Fix
```python
# Verify UNIQUE constraint exists
SELECT sql FROM sqlite_master WHERE type='table' AND name='leaderboards'
# Should contain: UNIQUE(leaderboard_type, period)

# Test ON CONFLICT operation
INSERT INTO leaderboards (leaderboard_type, period, data_json) 
VALUES ('test', 'period1', '{}')
ON CONFLICT(leaderboard_type, period) 
DO UPDATE SET data_json = excluded.data_json
# Should succeed without error
```

#### Test 2: League Leave Fix
1. Create a test league as User A
2. Add User B to the league
3. User A leaves the league as owner
4. Verify:
   - League no longer appears in User A's "My Leagues"
   - Ownership transferred to User B
   - User A's portfolio data deleted from database
   - `SELECT * FROM league_portfolios WHERE user_id = A AND league_id = L` returns 0 rows

---

## Files Modified
1. `/database/db_manager.py`
   - Line 323-332: Added UNIQUE constraint to leaderboards table schema
   - Lines 1183-1200: Added portfolio cleanup in leave_league() method

## Files Created
1. `/migrate_leaderboards_table.py` - Migration utility for existing databases
2. `/test_bug_fixes.py` - Test suite for verifying fixes

---

## Expected Behavior After Fixes

### Leaderboard System
- Global leaderboard updates without ON CONFLICT errors
- League-specific leaderboard updates work correctly
- Leaderboard snapshots can be recorded without constraint violations

### League System
- User leaving a league removes them from "My Leagues"
- Ownership transfers correctly to remaining members
- All user data cleaned up when they leave
- No orphaned portfolio records in database
- League auto-deletes when last member leaves

---

## Rollback Instructions

If needed to revert:

### Revert Leaderboard Fix
```bash
# Use git to revert changes
git checkout database/db_manager.py
# Then run migration backwards (would need custom script)
```

### Revert League Fix
```bash
# Use git to revert changes
git checkout database/db_manager.py
```

Note: After reverting, existing databases should be cleaned up manually or re-initialized.

