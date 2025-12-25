"""
Phase 3 Database Migration Script
Applies Phase 3 schema to existing database
Run this to initialize engagement feature tables
"""

import sqlite3
import sys
import logging
from phase_3_schema import get_schema_migrations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('phase_3_migration')


def apply_migrations(db_path='database/stocks.db'):
    """
    Apply all Phase 3 migrations to the database
    
    Args:
        db_path: Path to SQLite database
    
    Returns:
        (success, count, error_message)
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all migrations
        migrations = get_schema_migrations()
        
        logger.info(f"Applying {len(migrations)} migrations to {db_path}")
        
        applied = 0
        for idx, migration in enumerate(migrations, 1):
            try:
                # Skip empty migrations
                if not migration.strip():
                    continue
                
                cursor.execute(migration)
                logger.debug(f"Migration {idx}: Applied successfully")
                applied += 1
                
            except sqlite3.OperationalError as e:
                error_msg = str(e).lower()
                # Table or index might already exist
                if any(x in error_msg for x in ['already exists', 'duplicate column']):
                    logger.info(f"Migration {idx}: Skipped ({error_msg})")
                    applied += 1
                else:
                    logger.error(f"Migration {idx}: Error - {e}")
                    # Don't raise here - some operations might fail but aren't critical
                    logger.debug(f"  Continuing with next migration...")
            except Exception as e:
                logger.warning(f"Migration {idx}: Warning - {e}")
                # Log but continue with other migrations
                logger.debug(f"  Continuing with next migration...")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully applied {applied} migrations")
        return True, applied, None
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False, 0, str(e)


def verify_schema(db_path='database/stocks.db'):
    """
    Verify that all required tables exist
    
    Returns:
        (success, tables_dict, error_message)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        required_tables = [
            'league_activity_log',
            'league_announcements',
            'league_system_events',
            'league_performance_snapshots',
            'league_analytics',
        ]
        
        tables = {}
        for table_name in required_tables:
            cursor.execute(f"SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            exists = cursor.fetchone()[0] > 0
            tables[table_name] = exists
            
            if exists:
                # Get column info
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in cursor.fetchall()]
                tables[f'{table_name}_columns'] = columns
                logger.info(f"✓ Table '{table_name}' exists with {len(columns)} columns")
            else:
                logger.warning(f"✗ Table '{table_name}' NOT FOUND")
        
        conn.close()
        
        all_exist = all(tables.get(t, False) for t in required_tables)
        
        if all_exist:
            logger.info("✓ All required tables exist!")
            return True, tables, None
        else:
            missing = [t for t in required_tables if not tables.get(t, False)]
            return False, tables, f"Missing tables: {', '.join(missing)}"
            
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False, {}, str(e)


def rollback_migrations(db_path='database/stocks.db'):
    """
    Drop all Phase 3 tables (use with caution!)
    
    Returns:
        (success, count, error_message)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        tables_to_drop = [
            'league_analytics',
            'league_performance_snapshots',
            'league_system_events',
            'league_announcements',
            'league_activity_log',
        ]
        
        dropped = 0
        for table_name in tables_to_drop:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                dropped += 1
                logger.info(f"Dropped table: {table_name}")
            except Exception as e:
                logger.error(f"Error dropping {table_name}: {e}")
        
        conn.commit()
        conn.close()
        
        logger.warning(f"Dropped {dropped} Phase 3 tables")
        return True, dropped, None
        
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return False, 0, str(e)


def print_schema_info(db_path='database/stocks.db'):
    """
    Print detailed schema information for Phase 3 tables
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        tables = [
            'league_activity_log',
            'league_announcements',
            'league_system_events',
            'league_performance_snapshots',
            'league_analytics',
        ]
        
        for table_name in tables:
            print(f"\n{'='*70}")
            print(f"Table: {table_name}")
            print('='*70)
            
            try:
                # Get column info
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                if columns:
                    print(f"{'Column':<25} {'Type':<15} {'Nullable':<10} {'Default':<15}")
                    print("-"*70)
                    for col in columns:
                        col_name, col_type, notnull, default, _ = col
                        nullable = "NO" if notnull else "YES"
                        print(f"{col_name:<25} {col_type:<15} {nullable:<10} {str(default):<15}")
                    
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    print(f"\nRows: {count}")
                    
                    # Get indexes
                    cursor.execute(f"PRAGMA index_list({table_name})")
                    indexes = cursor.fetchall()
                    if indexes:
                        print(f"\nIndexes:")
                        for idx in indexes:
                            print(f"  - {idx[1]}")
                else:
                    print(f"Table '{table_name}' not found or empty")
                    
            except sqlite3.OperationalError:
                print(f"Table '{table_name}' does not exist")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error printing schema info: {e}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Phase 3 Database Migration Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Apply migrations
  python migrate_phase_3.py --apply
  
  # Verify schema
  python migrate_phase_3.py --verify
  
  # Print schema info
  python migrate_phase_3.py --info
  
  # Rollback (careful!)
  python migrate_phase_3.py --rollback
        """
    )
    
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply Phase 3 migrations'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify Phase 3 schema'
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Print schema information'
    )
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Rollback Phase 3 (DROP tables)'
    )
    parser.add_argument(
        '--db',
        default='database/stocks.db',
        help='Path to database (default: database/stocks.db)'
    )
    
    args = parser.parse_args()
    
    # Default to apply if no action specified
    if not any([args.apply, args.verify, args.info, args.rollback]):
        args.apply = True
    
    if args.apply:
        logger.info("Starting Phase 3 migration...")
        success, count, error = apply_migrations(args.db)
        if success:
            logger.info(f"✓ Applied {count} migrations")
            # Verify after apply
            verify_success, _, _ = verify_schema(args.db)
            if verify_success:
                logger.info("✓ Schema verification passed!")
                return 0
            else:
                logger.error("✗ Schema verification failed!")
                return 1
        else:
            logger.error(f"✗ Migration failed: {error}")
            return 1
    
    if args.verify:
        logger.info("Verifying Phase 3 schema...")
        success, tables, error = verify_schema(args.db)
        if success:
            logger.info("✓ All Phase 3 tables exist!")
            return 0
        else:
            logger.error(f"✗ Verification failed: {error}")
            return 1
    
    if args.info:
        logger.info("Printing schema information...")
        print_schema_info(args.db)
        return 0
    
    if args.rollback:
        response = input("WARNING: This will DROP all Phase 3 tables. Are you sure? (yes/no): ")
        if response.lower() == 'yes':
            logger.warning("Rolling back Phase 3 schema...")
            success, count, error = rollback_migrations(args.db)
            if success:
                logger.warning(f"✓ Dropped {count} tables")
                return 0
            else:
                logger.error(f"✗ Rollback failed: {error}")
                return 1
        else:
            logger.info("Rollback cancelled")
            return 0
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
