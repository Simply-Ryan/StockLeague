#!/usr/bin/env python3
"""
Phase 3 Migration Fixer
Diagnoses and fixes migration issues
"""

import sqlite3
import os
from phase_3_schema import get_schema_migrations

db_path = 'database/stocks.db'

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

print("=" * 70)
print("PHASE 3 MIGRATION DIAGNOSTIC AND FIXER")
print("=" * 70)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all migrations
migrations = get_schema_migrations()
print(f"\nTotal migrations: {len(migrations)}")

# Run each migration with detailed error reporting
successful = 0
failed = 0
skipped = 0

for idx, migration in enumerate(migrations, 1):
    if not migration.strip():
        continue
    
    print(f"\n[Migration {idx}]")
    print(f"  SQL: {migration.strip()[:80]}...")
    
    try:
        cursor.execute(migration)
        print(f"  ✓ SUCCESS")
        successful += 1
        
    except sqlite3.OperationalError as e:
        error_msg = str(e).lower()
        
        if 'already exists' in error_msg or 'duplicate column' in error_msg:
            print(f"  ⊘ SKIPPED (already exists)")
            skipped += 1
        else:
            print(f"  ✗ FAILED: {e}")
            failed += 1
            
            # Try to provide more context
            if "no such column" in error_msg:
                print(f"    Issue: Referenced column doesn't exist")
                print(f"    Action: This might be a schema dependency issue")
            elif "no such table" in error_msg:
                print(f"    Issue: Referenced table doesn't exist")
                print(f"    Action: Check if prerequisite migrations failed")
            elif "foreign key" in error_msg:
                print(f"    Issue: Foreign key constraint problem")
                print(f"    Action: Check if referenced table exists")
    
    except Exception as e:
        print(f"  ✗ UNEXPECTED ERROR: {e}")
        failed += 1

# Commit successful migrations
conn.commit()
conn.close()

print("\n" + "=" * 70)
print("MIGRATION SUMMARY")
print("=" * 70)
print(f"  Successful: {successful}")
print(f"  Skipped:    {skipped}")
print(f"  Failed:     {failed}")
print(f"  Total:      {len(migrations)}")

if failed == 0:
    print("\n✓ All migrations completed successfully!")
else:
    print(f"\n✗ {failed} migrations failed. Please check the errors above.")

print("=" * 70)
