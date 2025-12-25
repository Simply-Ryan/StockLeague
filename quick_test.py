#!/usr/bin/env python3
"""Direct migration test - minimal dependencies"""

import sqlite3

def test_migration():
    db_path = 'database/stocks.db'
    
    print(f"Testing migrations on {db_path}...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Test migration 10 (the problematic one)
    migration_10 = """
    CREATE TABLE IF NOT EXISTS league_analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        league_id INTEGER NOT NULL,
        analytics_date DATE NOT NULL,
        total_volume REAL,
        average_portfolio_value REAL,
        average_win_rate REAL,
        most_traded_stock TEXT,
        member_count INTEGER,
        active_traders_count INTEGER,
        total_trades_count INTEGER,
        data JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(league_id) REFERENCES leagues(id)
    )
    """
    
    try:
        cursor.execute(migration_10)
        print("✓ Migration 10 (league_analytics) created successfully")
    except Exception as e:
        print(f"✗ Migration 10 failed: {e}")
        conn.close()
        return False
    
    # Test the unique index
    migration_unique = """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_league_analytics_unique_date
    ON league_analytics(league_id, analytics_date)
    """
    
    try:
        cursor.execute(migration_unique)
        print("✓ Unique index created successfully")
    except Exception as e:
        print(f"✗ Unique index failed: {e}")
        conn.close()
        return False
    
    conn.commit()
    conn.close()
    
    print("✓ All tests passed!")
    return True

if __name__ == '__main__':
    test_migration()
