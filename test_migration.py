#!/usr/bin/env python3
"""Test the Phase 3 migrations"""

import sqlite3
import sys
import logging
from phase_3_schema import get_schema_migrations

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('migration_test')

def test_migrations():
    """Test and apply migrations"""
    db_path = 'database/stocks.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        migrations = get_schema_migrations()
        logger.info(f"Total migrations to apply: {len(migrations)}")
        
        applied = 0
        for idx, migration in enumerate(migrations, 1):
            if not migration.strip():
                continue
            
            try:
                logger.info(f"Migration {idx}: Executing...")
                logger.debug(f"SQL: {migration[:100]}...")
                cursor.execute(migration)
                logger.info(f"Migration {idx}: ✓ Success")
                applied += 1
                
            except sqlite3.OperationalError as e:
                if 'already exists' in str(e):
                    logger.info(f"Migration {idx}: Skipped (already exists)")
                    applied += 1
                else:
                    logger.error(f"Migration {idx}: ✗ Error - {e}")
                    logger.error(f"  SQL: {migration[:200]}...")
                    raise
            except Exception as e:
                logger.error(f"Migration {idx}: ✗ Unexpected error - {e}")
                logger.error(f"  SQL: {migration[:200]}...")
                raise
        
        conn.commit()
        conn.close()
        
        logger.info(f"✓ Successfully applied {applied}/{len(migrations)} migrations")
        return True
        
    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        return False

if __name__ == '__main__':
    success = test_migrations()
    sys.exit(0 if success else 1)
