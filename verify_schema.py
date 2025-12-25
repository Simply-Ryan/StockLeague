#!/usr/bin/env python3
"""Verify Phase 3 migration - check existing tables"""

import sqlite3
import os

db_path = 'database/stocks.db'

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

print(f"Checking database: {db_path}")
print("=" * 60)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if Phase 3 tables already exist
tables_to_check = [
    'league_activity_log',
    'league_announcements',
    'league_system_events',
    'league_performance_snapshots',
    'league_analytics'
]

print("\nExisting Phase 3 tables:")
print("-" * 60)

for table in tables_to_check:
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
    exists = cursor.fetchone() is not None
    status = "✓ EXISTS" if exists else "✗ MISSING"
    print(f"  {table:40} {status}")
    
    if exists:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        for col in columns[:3]:  # Show first 3 columns
            print(f"    - {col[1]:30} {col[2]}")
        if len(columns) > 3:
            print(f"    ... and {len(columns) - 3} more columns")

print("\nExisting Phase 3 indexes:")
print("-" * 60)

cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_league%' ORDER BY name")
indexes = cursor.fetchall()
if indexes:
    for idx in indexes:
        print(f"  ✓ {idx[0]}")
else:
    print("  No indexes found")

conn.close()
print("\nDone!")
