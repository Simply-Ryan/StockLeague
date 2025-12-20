# League Leave Functionality - Bug Fixes

## Problem
The leave_league functionality had the following issues:
1. Ownership transfer wasn't working correctly when the owner left
2. League deletion wasn't working when the last member left
3. The query was using an incorrect column name (`created_at` instead of `joined_at`)
4. Error handling for non-existent tables was missing

## Root Causes
1. **Column name mismatch**: The code was querying `created_at` but the actual column is `joined_at` in the `league_members` table
2. **Missing error handling**: Code tried to delete from tables that don't exist in all schema versions
3. **Schema inconsistency**: The `join_league` method was querying a `max_members` column that doesn't exist

## Solutions Implemented

### 1. Fixed column name in ownership transfer query
**File**: `/workspaces/StockLeague/database/db_manager.py` - `leave_league()` method

Changed:
```python
ORDER BY created_at ASC, user_id ASC
```

To:
```python
ORDER BY joined_at ASC, user_id ASC
```

This ensures the query correctly identifies the first member who joined after the owner, so they inherit ownership.

### 2. Added robust error handling in `join_league()`
**File**: `/workspaces/StockLeague/database/db_manager.py` - `join_league()` method

- Changed the query to only check for league existence (not `max_members`)
- Wrapped the `max_members` check in a try-except to gracefully handle when the column doesn't exist
- This allows the method to work with both old and new schema versions

### 3. Added comprehensive error handling in `leave_league()` deletion block
**File**: `/workspaces/StockLeague/database/db_manager.py` - `leave_league()` method

Wrapped all optional table deletions in try-except blocks:
- `league_member_stats`
- `league_portfolio_snapshots`
- `league_activity_feed`
- `league_seasons`
- All advanced feature tables (achievements, badges, quests, moderation)

This ensures the league deletion succeeds even if some tables don't exist in the current schema.

## Behavior After Fix

### When Owner Leaves with Other Members Present
1. Owner is removed from the league
2. Owner's portfolio data is cleaned up
3. Ownership transfers to the first member who joined (based on `joined_at` timestamp)
4. New owner is marked as admin
5. League continues to exist with remaining members

### When Last Member Leaves
1. Member is removed from the league
2. All associated data is deleted in proper order
3. League is deleted from the database

### When Single-Member League Owner Leaves
1. Owner is removed
2. No ownership transfer needed (no other members)
3. League is automatically deleted

## Test Results
✓ Ownership transfer works correctly when owner leaves with other members present
✓ First member to join (after owner) inherits ownership
✓ League is deleted when the last member leaves
✓ Single-member league is deleted when owner leaves
✓ All database operations are atomic and handle missing tables gracefully

## Files Modified
1. `/workspaces/StockLeague/database/db_manager.py`
   - Fixed `leave_league()` method (column name and error handling)
   - Fixed `join_league()` method (schema compatibility)

2. `/workspaces/StockLeague/app.py`
   - No changes needed (route already handles the logic correctly)

## Verification
Created `/workspaces/StockLeague/test_leave_league.py` to verify:
- Ownership transfer
- League deletion
- Error handling for missing tables
- All scenarios pass successfully
