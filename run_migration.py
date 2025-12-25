#!/usr/bin/env python3
"""
Complete Phase 3 Migration with detailed output
Applies all schemas and provides full diagnostics
"""

import sqlite3
import sys
import os

def migrate():
    """Apply Phase 3 migrations with full debugging"""
    
    db_path = 'database/stocks.db'
    
    if not os.path.exists(db_path):
        print(f"✗ Database not found: {db_path}")
        return False
    
    print("=" * 70)
    print("PHASE 3 DATABASE MIGRATION")
    print("=" * 70)
    print(f"Database: {db_path}")
    print()
    
    # Import migrations
    from phase_3_schema import get_schema_migrations
    
    migrations = get_schema_migrations()
    print(f"Loading {len(migrations)} migrations...\n")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Track results
    results = {
        'created': [],
        'skipped': [],
        'failed': []
    }
    
    # Run each migration
    for idx, migration in enumerate(migrations, 1):
        if not migration.strip():
            continue
        
        # Get a short description
        sql_lines = migration.strip().split('\n')
        first_line = sql_lines[0].upper()
        
        try:
            cursor.execute(migration)
            conn.commit()
            results['created'].append((idx, first_line))
            print(f"[{idx:2d}] ✓ {first_line[:65]}")
            
        except sqlite3.OperationalError as e:
            error_str = str(e).lower()
            
            # Classify the error
            if 'already exists' in error_str or 'duplicate column' in error_str:
                results['skipped'].append((idx, first_line, str(e)))
                print(f"[{idx:2d}] ⊘ {first_line[:55]} (already exists)")
            else:
                results['failed'].append((idx, first_line, str(e)))
                print(f"[{idx:2d}] ✗ {first_line[:55]}")
                print(f"      ERROR: {e}")
        
        except Exception as e:
            results['failed'].append((idx, first_line, str(e)))
            print(f"[{idx:2d}] ✗ {first_line[:55]}")
            print(f"      ERROR: {e}")
    
    conn.close()
    
    # Print summary
    print("\n" + "=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)
    print(f"Created:  {len(results['created'])}")
    print(f"Skipped:  {len(results['skipped'])}")
    print(f"Failed:   {len(results['failed'])}")
    print(f"Total:    {len(migrations)}")
    
    # Check if all required tables exist
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    required_tables = [
        'league_activity_log',
        'league_announcements',
        'league_system_events',
        'league_performance_snapshots',
        'league_analytics'
    ]
    
    all_exist = True
    for table in required_tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        exists = cursor.fetchone() is not None
        status = "✓" if exists else "✗"
        print(f"{status} {table}")
        if not exists:
            all_exist = False
    
    conn.close()
    
    print("\n" + "=" * 70)
    if all_exist and len(results['failed']) == 0:
        print("✓ MIGRATION COMPLETE - All Phase 3 tables created successfully!")
        print("=" * 70)
        return True
    elif all_exist:
        print("⚠ MIGRATION PARTIAL - Tables exist but some migrations failed")
        print("  (This is usually OK if failures are 'already exists' errors)")
        print("=" * 70)
        return len(results['failed']) == 0
    else:
        print("✗ MIGRATION FAILED - Some required tables are missing")
        print("=" * 70)
        return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
