#!/usr/bin/env python3
"""Check current database structure"""

import sqlite3
import os

db_path = 'database/stocks.db'

if not os.path.exists(db_path):
    print(f"Database not found: {db_path}")
    exit(1)

print(f"Database: {db_path}")
print("=" * 70)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all user tables (not system tables)
print("\nAll Tables in Database:")
print("-" * 70)

cursor.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' 
    AND name NOT LIKE 'sqlite_%'
    ORDER BY name
""")

tables = cursor.fetchall()
if tables:
    for (table_name,) in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  {table_name:40} ({count:,} rows)")
else:
    print("  No tables found")

# Check for Phase 3 specific tables
print("\nPhase 3 Tables Status:")
print("-" * 70)

phase3_tables = [
    'league_activity_log',
    'league_announcements',
    'league_system_events',
    'league_performance_snapshots',
    'league_analytics'
]

for table in phase3_tables:
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
    exists = cursor.fetchone() is not None
    status = "✓ EXISTS" if exists else "✗ MISSING"
    print(f"  {table:40} {status}")

# Check for Phase 3 indexes
print("\nPhase 3 Indexes:")
print("-" * 70)

cursor.execute("""
    SELECT name FROM sqlite_master
    WHERE type='index'
    AND name LIKE 'idx_league%'
    ORDER BY name
""")

indexes = cursor.fetchall()
if indexes:
    for (idx_name,) in indexes:
        print(f"  ✓ {idx_name}")
else:
    print("  No Phase 3 indexes found")

conn.close()

print("\n" + "=" * 70)
print("Database structure check complete.")
print("=" * 70)
