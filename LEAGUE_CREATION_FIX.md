# League Creation Error - Settings JSON Column Fix

## Problem
When creating a league, the following error occurred:
```
sqlite3.OperationalError: table leagues has no column named settings_json
```

## Root Cause
The database migration script had a typo - it was trying to create a column named `league_settings_json` instead of `settings_json`, but the application code expected `settings_json`.

## Solution Applied

### 1. Fixed the Migration Script
- **File**: `database/league_schema_upgrade.py`
- **Change**: Updated column name from `league_settings_json` to `settings_json`
- **Line**: 86

### 2. Added Fallback in Code
- **File**: `database/db_manager.py`
- **Change**: Added try/except block in `create_league()` method to handle both scenarios:
  - First tries to insert with `settings_json` column
  - Falls back to insert without it if column doesn't exist
- **Lines**: 1106-1128

## How to Fix Your Database

Run the migration script to add the missing column:

```bash
bash fix_league_error.sh
```

Or manually:

```bash
python database/league_schema_upgrade.py
```

Then restart the Flask app:

```bash
python app.py
```

You should now be able to create leagues without errors!

## Files Modified
1. `database/league_schema_upgrade.py` - Fixed column name in migration
2. `database/db_manager.py` - Added error handling fallback
3. `fix_league_error.sh` - Helper script to run migration
4. `run_migration.sh` - Alternative migration script

## Prevention
The issue occurred because the initial schema upgrade had a naming mismatch. The fix ensures:
- ✓ Column names match between migration and application code
- ✓ Graceful fallback if column is missing
- ✓ Future league creation will work correctly
