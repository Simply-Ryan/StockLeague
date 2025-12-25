-- Phase 3 Database Schema Migrations
-- For StockLeague Application
-- This file contains all SQL needed to set up Phase 3 engagement features

-- 1. League Activity Feed table
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
);

-- 2. Index for fast activity queries
CREATE INDEX IF NOT EXISTS idx_league_activity_log_league_time 
ON league_activity_log(league_id, created_at DESC);

-- 3. League Announcements table
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
);

-- 4. Index for announcements
CREATE INDEX IF NOT EXISTS idx_league_announcements_league 
ON league_announcements(league_id, pinned DESC, created_at DESC);

-- 5. League System Events table
CREATE TABLE IF NOT EXISTS league_system_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    description TEXT,
    data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(league_id) REFERENCES leagues(id)
);

-- 6. Index for system events
CREATE INDEX IF NOT EXISTS idx_league_system_events_league_time 
ON league_system_events(league_id, created_at DESC);

-- 7. League Performance Snapshots (for metrics history)
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
);

-- 8. Index for performance snapshots
CREATE INDEX IF NOT EXISTS idx_league_performance_snapshots_league_user 
ON league_performance_snapshots(league_id, user_id, snapshot_date DESC);

-- 9. League Analytics table
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
);

-- 10. Index for league analytics
CREATE INDEX IF NOT EXISTS idx_league_analytics_league_date 
ON league_analytics(league_id, analytics_date DESC);

-- 11. Unique constraint to league_analytics
CREATE UNIQUE INDEX IF NOT EXISTS idx_league_analytics_unique_date
ON league_analytics(league_id, analytics_date);

-- 12. Unique constraint to league_performance_snapshots
CREATE UNIQUE INDEX IF NOT EXISTS idx_league_performance_snapshots_unique_date
ON league_performance_snapshots(league_id, user_id, snapshot_date);

-- 13. Add columns to leagues table
ALTER TABLE leagues ADD COLUMN IF NOT EXISTS 
last_activity_update TIMESTAMP;

-- 14. Add columns to league_members table
ALTER TABLE league_members ADD COLUMN IF NOT EXISTS 
total_trades INTEGER DEFAULT 0;

-- 15. Add columns to league_members table
ALTER TABLE league_members ADD COLUMN IF NOT EXISTS 
win_rate REAL DEFAULT 0;

-- Migration complete!
-- All Phase 3 tables and indexes created.
