"""
Database Schema Extensions for Phase 3 - Engagement Features
Provides table definitions and migration helpers for activity feeds, announcements,
performance metrics, and league analytics
"""

import sqlite3
from datetime import datetime

def get_schema_migrations():
    """
    Get all database schema migrations for Phase 3
    
    Returns:
        List of SQL migration statements
    """
    migrations = [
        # League Activity Feed table
        """
        CREATE TABLE IF NOT EXISTS league_activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            description TEXT,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(league_id) REFERENCES leagues(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """,
        
        # Index for fast activity queries
        """
        CREATE INDEX IF NOT EXISTS idx_league_activity_log_league_time 
        ON league_activity_log(league_id, created_at DESC)
        """,
        
        # League Announcements table
        """
        CREATE TABLE IF NOT EXISTS league_announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            pinned BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(league_id) REFERENCES leagues(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """,
        
        # Index for announcements
        """
        CREATE INDEX IF NOT EXISTS idx_league_announcements_league 
        ON league_announcements(league_id, pinned DESC, created_at DESC)
        """,
        
        # League System Events table
        """
        CREATE TABLE IF NOT EXISTS league_system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            description TEXT,
            data JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(league_id) REFERENCES leagues(id)
        )
        """,
        
        # Index for system events
        """
        CREATE INDEX IF NOT EXISTS idx_league_system_events_league_time 
        ON league_system_events(league_id, created_at DESC)
        """,
        
        # League Performance Snapshots (for metrics history)
        """
        CREATE TABLE IF NOT EXISTS league_performance_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            snapshot_date DATE NOT NULL,
            portfolio_value REAL,
            daily_pl REAL,
            total_pl REAL,
            win_rate REAL,
            trade_count INTEGER,
            best_performing_stock TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(league_id) REFERENCES leagues(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """,
        
        # Index for performance snapshots
        """
        CREATE INDEX IF NOT EXISTS idx_league_performance_snapshots_league_user 
        ON league_performance_snapshots(league_id, user_id, snapshot_date DESC)
        """,
        
        # League Analytics table
        """
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
        """,
        
        # Index for league analytics
        """
        CREATE INDEX IF NOT EXISTS idx_league_analytics_league_date 
        ON league_analytics(league_id, analytics_date DESC)
        """,
        
        # Add unique constraint to league_analytics (alternative approach if needed)
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_league_analytics_unique_date
        ON league_analytics(league_id, analytics_date)
        """,
        
        # Add unique constraint to league_performance_snapshots
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_league_performance_snapshots_unique_date
        ON league_performance_snapshots(league_id, user_id, snapshot_date)
        """,
        
        # Add columns to leagues table
        """
        ALTER TABLE leagues ADD COLUMN IF NOT EXISTS 
        last_activity_update TIMESTAMP
        """,
        
        """
        ALTER TABLE league_members ADD COLUMN IF NOT EXISTS 
        total_trades INTEGER DEFAULT 0
        """,
        
        """
        ALTER TABLE league_members ADD COLUMN IF NOT EXISTS 
        win_rate REAL DEFAULT 0
        """,
    ]
    
    return migrations


def apply_migrations(db_connection):
    """
    Apply all Phase 3 migrations to database
    
    Args:
        db_connection: SQLite database connection
    
    Returns:
        (success, migrations_applied, errors)
    """
    cursor = db_connection.cursor()
    migrations = get_schema_migrations()
    applied = 0
    errors = []
    
    for migration in migrations:
        try:
            cursor.execute(migration)
            db_connection.commit()
            applied += 1
        except sqlite3.OperationalError as e:
            # Table/index might already exist, continue
            if "already exists" not in str(e):
                errors.append(str(e))
        except Exception as e:
            errors.append(str(e))
    
    cursor.close()
    return applied == len(migrations), applied, errors


# Activity type constants
class ActivityType:
    """Activity types for league activity log"""
    TRADE_BUY = "trade_buy"
    TRADE_SELL = "trade_sell"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    RANKING_CHANGE = "ranking_change"
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    LEAGUE_CREATED = "league_created"
    MILESTONE_REACHED = "milestone_reached"
    CHALLENGE_STARTED = "challenge_started"
    CHALLENGE_COMPLETED = "challenge_completed"


# System event type constants
class SystemEventType:
    """System event types"""
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    RANKING_CHANGED = "ranking_changed"
    MILESTONE_REACHED = "milestone_reached"
    SEASON_STARTED = "season_started"
    SEASON_ENDED = "season_ended"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"


if __name__ == '__main__':
    # Example usage
    print("Phase 3 Schema Migrations")
    print("=" * 50)
    migrations = get_schema_migrations()
    print(f"Total migrations: {len(migrations)}")
    for i, migration in enumerate(migrations, 1):
        print(f"\n{i}. {migration[:100]}...")
