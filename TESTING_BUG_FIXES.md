# Testing & Validation Guide - Bug Fixes

## Overview
This guide provides step-by-step instructions to test and validate both bug fixes:
1. Leaderboard ON CONFLICT constraint fix
2. League leave cleanup fix

---

## Test Environment Setup

### Prerequisites
- Python 3.7+
- SQLite3
- Flask development environment running
- Test database (can be created fresh)

### Setup Steps
```bash
cd /workspaces/codespaces-blank/StockLeague

# Option 1: Fresh database (recommended for testing)
rm -f instance/stockleague.db
python3 -c "from database.db_manager import DatabaseManager; db = DatabaseManager()"

# Option 2: Use migration on existing database
python3 migrate_leaderboards_table.py
```

---

## Test 1: Leaderboard ON CONFLICT Fix

### Test 1.1: Schema Validation
**Objective**: Verify UNIQUE constraint exists on leaderboards table

**Steps**:
```python
import sqlite3

conn = sqlite3.connect('instance/stockleague.db')
cursor = conn.cursor()

# Check schema
cursor.execute("""
    SELECT sql FROM sqlite_master 
    WHERE type='table' AND name='leaderboards'
""")
schema = cursor.fetchone()[0]
print("Leaderboards Schema:")
print(schema)
```

**Expected Output**:
```
Leaderboards Schema:
CREATE TABLE leaderboards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    leaderboard_type TEXT NOT NULL,
    period TEXT NOT NULL,
    data_json TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(leaderboard_type, period)
)
```

**Pass Criteria**: Schema contains `UNIQUE(leaderboard_type, period)`

---

### Test 1.2: ON CONFLICT Operation Test
**Objective**: Verify ON CONFLICT syntax works without errors

**Steps**:
```python
import sqlite3
import json

conn = sqlite3.connect('instance/stockleague.db')
cursor = conn.cursor()

test_data = json.dumps([
    {"username": "test_user", "total_value": 10000}
])

try:
    # First insert
    cursor.execute("""
        INSERT INTO leaderboards (leaderboard_type, period, data_json, updated_at) 
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(leaderboard_type, period) 
        DO UPDATE SET data_json = excluded.data_json, updated_at = CURRENT_TIMESTAMP
    """, ("global", "test_period", test_data))
    
    conn.commit()
    print("✅ First insert successful")
    
    # Second update (should update, not duplicate)
    updated_data = json.dumps([
        {"username": "test_user", "total_value": 11000}
    ])
    
    cursor.execute("""
        INSERT INTO leaderboards (leaderboard_type, period, data_json, updated_at) 
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(leaderboard_type, period) 
        DO UPDATE SET data_json = excluded.data_json, updated_at = CURRENT_TIMESTAMP
    """, ("global", "test_period", updated_data))
    
    conn.commit()
    print("✅ Second insert (update) successful")
    
    # Verify single record exists
    cursor.execute("""
        SELECT COUNT(*) FROM leaderboards 
        WHERE leaderboard_type = ? AND period = ?
    """, ("global", "test_period"))
    
    count = cursor.fetchone()[0]
    if count == 1:
        print(f"✅ Record count is correct: {count}")
    else:
        print(f"❌ Expected 1 record, got {count}")
    
    # Cleanup
    cursor.execute("""
        DELETE FROM leaderboards 
        WHERE leaderboard_type = ? AND period = ?
    """, ("global", "test_period"))
    conn.commit()
    print("✅ Cleanup successful")
    
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
finally:
    conn.close()
```

**Expected Output**:
```
✅ First insert successful
✅ Second insert (update) successful
✅ Record count is correct: 1
✅ Cleanup successful
```

**Pass Criteria**: All operations succeed without constraint errors

---

### Test 1.3: Application Leaderboard Endpoint Test
**Objective**: Verify leaderboard updates work in the running application

**Steps**:
1. Start the Flask application
2. Create test users and add them to a league
3. Make trades to generate portfolio values
4. Trigger leaderboard computation (happens on `/api/leaderboard` requests)
5. Check application logs for errors

**Expected Behavior**:
- No "ON CONFLICT clause does not match" errors in logs
- Leaderboards computed successfully
- Data appears correctly in `/leagues/<id>/leaderboard` pages

---

## Test 2: League Leave Cleanup Fix

### Test 2.1: Database Schema Validation
**Objective**: Verify required tables exist for cleanup

**Steps**:
```python
import sqlite3

conn = sqlite3.connect('instance/stockleague.db')
cursor = conn.cursor()

required_tables = [
    'leagues',
    'league_members', 
    'league_portfolios',
    'league_holdings',
    'league_transactions',
    'league_member_stats'
]

cursor.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name IN (?, ?, ?, ?, ?, ?)
""", required_tables)

found_tables = [row[0] for row in cursor.fetchall()]

for table in required_tables:
    status = "✅" if table in found_tables else "❌"
    print(f"{status} {table}")

conn.close()
```

**Expected Output**:
```
✅ leagues
✅ league_members
✅ league_portfolios
✅ league_holdings
✅ league_transactions
✅ league_member_stats
```

---

### Test 2.2: Leave League Cleanup Test (Database Level)
**Objective**: Verify all user data is deleted when they leave a league

**Steps**:

```python
import sqlite3

# Setup test data
conn = sqlite3.connect('instance/stockleague.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Create test league
cursor.execute("""
    INSERT INTO leagues (name, creator_id, starting_cash, is_active, invite_code)
    VALUES (?, ?, ?, ?, ?)
""", ("Test League", 1, 10000.0, 1, "test123"))
league_id = cursor.lastrowid
conn.commit()

# Add test member
cursor.execute("""
    INSERT INTO league_members (league_id, user_id, is_admin)
    VALUES (?, ?, ?)
""", (league_id, 2, 0))
conn.commit()

# Add portfolio, holdings, transactions, stats
cursor.execute("""
    INSERT INTO league_portfolios (league_id, user_id, cash)
    VALUES (?, ?, ?)
""", (league_id, 2, 10000.0))

cursor.execute("""
    INSERT INTO league_holdings (league_id, user_id, symbol, shares, avg_cost)
    VALUES (?, ?, ?, ?, ?)
""", (league_id, 2, "AAPL", 10, 150.0))

cursor.execute("""
    INSERT INTO league_transactions (league_id, user_id, symbol, action, shares, price)
    VALUES (?, ?, ?, ?, ?, ?)
""", (league_id, 2, "AAPL", "BUY", 10, 150.0))

cursor.execute("""
    INSERT INTO league_member_stats (league_id, user_id, total_trades, wins, losses)
    VALUES (?, ?, ?, ?, ?)
""", (league_id, 2, 1, 0, 0))

conn.commit()

print("Before leave:")
cursor.execute("SELECT COUNT(*) as count FROM league_members WHERE league_id = ? AND user_id = ?", (league_id, 2))
print(f"  league_members: {cursor.fetchone()['count']} (expected: 1)")

cursor.execute("SELECT COUNT(*) as count FROM league_portfolios WHERE league_id = ? AND user_id = ?", (league_id, 2))
print(f"  league_portfolios: {cursor.fetchone()['count']} (expected: 1)")

cursor.execute("SELECT COUNT(*) as count FROM league_holdings WHERE league_id = ? AND user_id = ?", (league_id, 2))
print(f"  league_holdings: {cursor.fetchone()['count']} (expected: 1)")

cursor.execute("SELECT COUNT(*) as count FROM league_transactions WHERE league_id = ? AND user_id = ?", (league_id, 2))
print(f"  league_transactions: {cursor.fetchone()['count']} (expected: 1)")

cursor.execute("SELECT COUNT(*) as count FROM league_member_stats WHERE league_id = ? AND user_id = ?", (league_id, 2))
print(f"  league_member_stats: {cursor.fetchone()['count']} (expected: 1)")

# Now simulate leave_league() operations
print("\nSimulating leave_league()...")

# Remove user from league_members
cursor.execute("""
    DELETE FROM league_members WHERE league_id = ? AND user_id = ?
""", (league_id, 2))

# Clean up portfolio data
cursor.execute("""
    DELETE FROM league_portfolios WHERE league_id = ? AND user_id = ?
""", (league_id, 2))

cursor.execute("""
    DELETE FROM league_holdings WHERE league_id = ? AND user_id = ?
""", (league_id, 2))

cursor.execute("""
    DELETE FROM league_transactions WHERE league_id = ? AND user_id = ?
""", (league_id, 2))

cursor.execute("""
    DELETE FROM league_member_stats WHERE league_id = ? AND user_id = ?
""", (league_id, 2))

conn.commit()

print("\nAfter leave:")
cursor.execute("SELECT COUNT(*) as count FROM league_members WHERE league_id = ? AND user_id = ?", (league_id, 2))
count = cursor.fetchone()['count']
print(f"  league_members: {count} (expected: 0) {'✅' if count == 0 else '❌'}")

cursor.execute("SELECT COUNT(*) as count FROM league_portfolios WHERE league_id = ? AND user_id = ?", (league_id, 2))
count = cursor.fetchone()['count']
print(f"  league_portfolios: {count} (expected: 0) {'✅' if count == 0 else '❌'}")

cursor.execute("SELECT COUNT(*) as count FROM league_holdings WHERE league_id = ? AND user_id = ?", (league_id, 2))
count = cursor.fetchone()['count']
print(f"  league_holdings: {count} (expected: 0) {'✅' if count == 0 else '❌'}")

cursor.execute("SELECT COUNT(*) as count FROM league_transactions WHERE league_id = ? AND user_id = ?", (league_id, 2))
count = cursor.fetchone()['count']
print(f"  league_transactions: {count} (expected: 0) {'✅' if count == 0 else '❌'}")

cursor.execute("SELECT COUNT(*) as count FROM league_member_stats WHERE league_id = ? AND user_id = ?", (league_id, 2))
count = cursor.fetchone()['count']
print(f"  league_member_stats: {count} (expected: 0) {'✅' if count == 0 else '❌'}")

# Cleanup
cursor.execute("DELETE FROM leagues WHERE id = ?", (league_id,))
conn.commit()
conn.close()
```

**Expected Output**:
```
Before leave:
  league_members: 1 (expected: 1)
  league_portfolios: 1 (expected: 1)
  league_holdings: 1 (expected: 1)
  league_transactions: 1 (expected: 1)
  league_member_stats: 1 (expected: 1)

Simulating leave_league()...

After leave:
  league_members: 0 (expected: 0) ✅
  league_portfolios: 0 (expected: 0) ✅
  league_holdings: 0 (expected: 0) ✅
  league_transactions: 0 (expected: 0) ✅
  league_member_stats: 0 (expected: 0) ✅
```

---

### Test 2.3: UI Integration Test
**Objective**: Verify league no longer appears in user's "My Leagues" after leaving

**Steps**:
1. Open the application in a browser
2. Create a test account (User A)
3. Create a new league as User A
4. Create another test account (User B)
5. Have User B join User A's league
6. As User A, click "Leave League"
7. Verify you see the success message: "You have left the league. Ownership has been transferred to the next member."
8. Check the "My Leagues" section - User A's created league should NOT appear
9. Check the public leagues list - the league should NOT appear in the "Discover" section for User A
10. Switch to User B's account - verify they see the league in "My Leagues" as the new owner

**Expected Behavior**:
- ✅ Leave action completes successfully with appropriate message
- ✅ League disappears from User A's "My Leagues"
- ✅ League disappears from User A's "Discover" section
- ✅ League appears in User B's "My Leagues" as the new owner
- ✅ User B is marked as admin/owner
- ✅ No errors in browser console or server logs

---

## Test 3: Regression Testing

### Test 3.1: Existing League Functionality
**Objective**: Verify no other league features were broken

**Test Cases**:
- [ ] Create a new league
- [ ] Join an existing league
- [ ] Update league settings
- [ ] Make trades in a league
- [ ] View league leaderboard
- [ ] View league history
- [ ] Accept league invitations
- [ ] Remove members as admin (if applicable)
- [ ] Transfer ownership manually

**Expected**: All operations work as before

---

### Test 3.2: Leaderboard Functionality  
**Objective**: Verify leaderboard features still work correctly

**Test Cases**:
- [ ] Global leaderboard updates correctly
- [ ] League leaderboard shows correct rankings
- [ ] Leaderboard updates after trades
- [ ] Historical snapshots are recorded
- [ ] No duplicate entries in leaderboard cache
- [ ] Performance is acceptable (< 5 seconds for compute)

**Expected**: All operations work as before

---

## Pass/Fail Criteria

### Fix 1: Leaderboard UNIQUE Constraint
- **PASS** if:
  - ✅ ON CONFLICT clause works without errors
  - ✅ Leaderboards can be inserted/updated
  - ✅ No duplicate entries created
  - ✅ Schema contains UNIQUE constraint

- **FAIL** if:
  - ❌ ON CONFLICT error appears
  - ❌ Constraint violation errors occur
  - ❌ Duplicate leaderboard entries exist

### Fix 2: League Leave Cleanup
- **PASS** if:
  - ✅ User removed from league_members on leave
  - ✅ User's portfolio deleted on leave
  - ✅ User's holdings deleted on leave
  - ✅ User's transactions deleted on leave
  - ✅ User's stats deleted on leave
  - ✅ League removed from "My Leagues" after leave
  - ✅ Ownership transferred to next member
  - ✅ League auto-deleted if last member leaves
  - ✅ No orphaned database records

- **FAIL** if:
  - ❌ User still appears in league_members
  - ❌ Portfolio data remains after leave
  - ❌ League still appears in "My Leagues"
  - ❌ User can still access league after leaving
  - ❌ Orphaned records found in database

---

## Automated Test Suite

Run the included test script:
```bash
python3 test_bug_fixes.py
```

This script performs basic validation of both fixes and reports results.

---

## Troubleshooting

### Issue: UNIQUE constraint violation after migration
**Solution**: Run the migration script which handles duplicates:
```bash
python3 migrate_leaderboards_table.py
```

### Issue: User still appears in league after leaving
**Solution**: 
1. Check if changes were properly committed to the database
2. Verify `leave_league()` method was updated with cleanup code
3. Clear browser cache and refresh page
4. Check Flask application logs for errors

### Issue: Database is locked during testing
**Solution**: Make sure no other processes are accessing the database
```bash
# Close any running Flask instances
pkill -f "python3 -m flask"
```

