#!/usr/bin/env python3
"""
Migration script to add UNIQUE constraint to leaderboards table
for databases that already exist.
"""

import sqlite3
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_leaderboards_table(db_path="instance/stockleague.db"):
    """Migrate existing leaderboards table to add UNIQUE constraint."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if leaderboards table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='leaderboards'
        """)
        
        if not cursor.fetchone():
            logger.info("Leaderboards table does not exist yet. No migration needed.")
            conn.close()
            return True
        
        logger.info("Leaderboards table found. Checking for UNIQUE constraint...")
        
        # Check if the UNIQUE constraint already exists
        cursor.execute("PRAGMA table_info(leaderboards)")
        columns = cursor.fetchall()
        
        # Check schema for UNIQUE constraint in CREATE TABLE definition
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='leaderboards'
        """)
        
        schema = cursor.fetchone()[0]
        if "UNIQUE" in schema:
            logger.info("UNIQUE constraint already exists on leaderboards table.")
            conn.close()
            return True
        
        logger.info("UNIQUE constraint not found. Performing migration...")
        
        # Backup old data
        cursor.execute("SELECT * FROM leaderboards")
        old_data = cursor.fetchall()
        
        # Drop old table
        cursor.execute("DROP TABLE IF EXISTS leaderboards")
        
        # Drop old index
        cursor.execute("DROP INDEX IF EXISTS idx_leaderboards_type")
        
        # Create new table with UNIQUE constraint
        cursor.execute("""
            CREATE TABLE leaderboards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                leaderboard_type TEXT NOT NULL,
                period TEXT NOT NULL,
                data_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(leaderboard_type, period)
            )
        """)
        
        # Recreate index
        cursor.execute("""
            CREATE INDEX idx_leaderboards_type ON leaderboards(leaderboard_type, period)
        """)
        
        # Restore data (handling duplicates - keep the most recent)
        if old_data:
            # Group by (leaderboard_type, period) and keep the most recent
            data_dict = {}
            for row in old_data:
                key = (row[1], row[2])  # (leaderboard_type, period)
                if key not in data_dict or row[4] > data_dict[key][4]:  # Compare updated_at
                    data_dict[key] = row
            
            for row in data_dict.values():
                cursor.execute("""
                    INSERT INTO leaderboards 
                    (leaderboard_type, period, data_json, updated_at) 
                    VALUES (?, ?, ?, ?)
                """, (row[1], row[2], row[3], row[4]))
            
            logger.info(f"Restored {len(data_dict)} leaderboard records")
        
        conn.commit()
        logger.info("Migration completed successfully!")
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = migrate_leaderboards_table()
    sys.exit(0 if success else 1)
