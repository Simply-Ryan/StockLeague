"""
Advanced League System - Database Schema Extensions

This script adds advanced league tables to support:
- Seasons and divisions
- Detailed performance tracking
- Tournaments and teams
- Achievements and quests
- Fair play monitoring
- Real-time analytics

Run: python database/league_schema_upgrade.py
"""

import sqlite3
from datetime import datetime


def upgrade_leagues_table(cursor):
    """Enhance existing leagues table with new columns."""
    try:
        cursor.execute("""
            ALTER TABLE leagues ADD COLUMN league_tier TEXT DEFAULT 'bronze'
        """)
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("""
            ALTER TABLE leagues ADD COLUMN lifecycle_state TEXT DEFAULT 'active'
        """)
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("""
            ALTER TABLE leagues ADD COLUMN competition_mode TEXT DEFAULT 'percentage'
        """)
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("""
            ALTER TABLE leagues ADD COLUMN season_number INTEGER DEFAULT 1
        """)
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("""
            ALTER TABLE leagues ADD COLUMN max_members INTEGER DEFAULT NULL
        """)
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("""
            ALTER TABLE leagues ADD COLUMN prize_pool NUMERIC DEFAULT 0
        """)
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("""
            ALTER TABLE leagues ADD COLUMN cover_image_url TEXT
        """)
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("""
            ALTER TABLE leagues ADD COLUMN is_rated INTEGER DEFAULT 1
        """)
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("""
            ALTER TABLE leagues ADD COLUMN visibility TEXT DEFAULT 'public'
        """)
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("""
            ALTER TABLE leagues ADD COLUMN league_settings_json TEXT
        """)
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("""
            ALTER TABLE leagues ADD COLUMN performance_tracking_enabled INTEGER DEFAULT 1
        """)
    except sqlite3.OperationalError:
        pass


def create_league_seasons_table(cursor):
    """Create seasons table for multi-season support."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_seasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            season_number INTEGER NOT NULL,
            start_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP NOT NULL,
            theme TEXT,
            prize_pool NUMERIC DEFAULT 0,
            is_active INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            UNIQUE(league_id, season_number)
        )
    """)


def create_league_member_stats_table(cursor):
    """Create detailed member performance tracking."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_member_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            season_number INTEGER NOT NULL,
            
            current_rank INTEGER,
            score NUMERIC DEFAULT 0,
            portfolio_value NUMERIC,
            starting_value NUMERIC,
            peak_value NUMERIC,
            valley_value NUMERIC,
            
            trades_executed INTEGER DEFAULT 0,
            win_rate NUMERIC DEFAULT 0,
            avg_return NUMERIC DEFAULT 0,
            volatility NUMERIC DEFAULT 0,
            sharpe_ratio NUMERIC DEFAULT 0,
            max_drawdown NUMERIC DEFAULT 0,
            
            win_streak INTEGER DEFAULT 0,
            current_streak_value NUMERIC DEFAULT 0,
            highest_streak INTEGER DEFAULT 0,
            
            total_playtime_hours INTEGER DEFAULT 0,
            last_trade_at TIMESTAMP,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(league_id, user_id, season_number)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_league_member_stats_rank 
        ON league_member_stats(league_id, season_number, current_rank)
    """)


def create_league_divisions_table(cursor):
    """Create divisions table for tiered competition."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_divisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            season_number INTEGER NOT NULL,
            name TEXT NOT NULL,
            tier TEXT NOT NULL,
            min_score NUMERIC,
            max_score NUMERIC,
            promotion_threshold NUMERIC,
            demotion_threshold NUMERIC,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            UNIQUE(league_id, season_number, tier)
        )
    """)


def create_tournament_tables(cursor):
    """Create tournament and participant tables."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            tournament_type TEXT,
            max_participants INTEGER,
            registration_start TIMESTAMP,
            registration_end TIMESTAMP,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            prize_pool NUMERIC DEFAULT 0,
            status TEXT DEFAULT 'registration',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournament_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            team_id INTEGER,
            seed_position INTEGER,
            current_position INTEGER,
            final_rank INTEGER,
            total_score NUMERIC DEFAULT 0,
            status TEXT DEFAULT 'active',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tournament_participants_status 
        ON tournament_participants(tournament_id, status)
    """)


def create_team_tables(cursor):
    """Create team and team member tables."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            creator_id INTEGER NOT NULL,
            logo_url TEXT,
            max_members INTEGER DEFAULT 5,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            FOREIGN KEY (creator_id) REFERENCES users(id),
            UNIQUE(league_id, name)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT DEFAULT 'member',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES league_teams(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(team_id, user_id)
        )
    """)


def create_achievement_tables(cursor):
    """Create achievement and badge tracking tables."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            badge_icon TEXT,
            rarity TEXT DEFAULT 'common',
            points_reward INTEGER DEFAULT 0,
            criteria_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            UNIQUE(league_id, name)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            achievement_id INTEGER NOT NULL,
            progress NUMERIC DEFAULT 0,
            unlocked_at TIMESTAMP,
            is_displayed INTEGER DEFAULT 1,
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (achievement_id) REFERENCES league_achievements(id),
            UNIQUE(league_id, user_id, achievement_id)
        )
    """)


def create_quest_tables(cursor):
    """Create quest and progress tracking tables."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            quest_type TEXT,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            reward_points INTEGER DEFAULT 0,
            reward_cash NUMERIC DEFAULT 0,
            criteria_json TEXT,
            FOREIGN KEY (league_id) REFERENCES leagues(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_quest_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quest_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            progress NUMERIC DEFAULT 0,
            completed_at TIMESTAMP,
            claimed_at TIMESTAMP,
            FOREIGN KEY (quest_id) REFERENCES league_quests(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(quest_id, user_id)
        )
    """)


def create_analytics_tables(cursor):
    """Create performance analytics tables."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            
            trades_count INTEGER DEFAULT 0,
            total_trading_volume NUMERIC DEFAULT 0,
            win_count INTEGER DEFAULT 0,
            loss_count INTEGER DEFAULT 0,
            daily_return NUMERIC DEFAULT 0,
            portfolio_value NUMERIC,
            
            win_loss_ratio NUMERIC DEFAULT 0,
            daily_sharpe NUMERIC DEFAULT 0,
            trading_frequency TEXT,
            
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(league_id, user_id, date)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_league_analytics_date 
        ON league_analytics(league_id, date DESC)
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_leaderboards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            season_number INTEGER,
            leaderboard_type TEXT,
            user_id INTEGER NOT NULL,
            rank INTEGER,
            score NUMERIC,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(league_id, season_number, leaderboard_type, user_id)
        )
    """)


def create_fairplay_tables(cursor):
    """Create fair play monitoring tables."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            reporter_id INTEGER NOT NULL,
            reported_user_id INTEGER NOT NULL,
            report_type TEXT,
            description TEXT,
            evidence_json TEXT,
            status TEXT DEFAULT 'open',
            moderator_notes TEXT,
            reviewed_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            FOREIGN KEY (reporter_id) REFERENCES users(id),
            FOREIGN KEY (reported_user_id) REFERENCES users(id),
            FOREIGN KEY (reviewed_by) REFERENCES users(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fair_play_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            flag_type TEXT,
            severity TEXT DEFAULT 'low',
            description TEXT,
            automated_check INTEGER DEFAULT 1,
            auto_flagged_at TIMESTAMP,
            human_reviewed_at TIMESTAMP,
            action_taken TEXT,
            resolved_at TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)


def run_upgrade(db_path: str = "database/stockleague.db"):
    """Run all schema upgrades."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔧 Starting Advanced League System upgrade...")
        
        print("  → Upgrading leagues table...")
        upgrade_leagues_table(cursor)
        
        print("  → Creating league seasons...")
        create_league_seasons_table(cursor)
        
        print("  → Creating member stats...")
        create_league_member_stats_table(cursor)
        
        print("  → Creating divisions...")
        create_league_divisions_table(cursor)
        
        print("  → Creating tournaments...")
        create_tournament_tables(cursor)
        
        print("  → Creating teams...")
        create_team_tables(cursor)
        
        print("  → Creating achievements...")
        create_achievement_tables(cursor)
        
        print("  → Creating quests...")
        create_quest_tables(cursor)
        
        print("  → Creating analytics...")
        create_analytics_tables(cursor)
        
        print("  → Creating fair play...")
        create_fairplay_tables(cursor)
        
        conn.commit()
        print("\n✅ Advanced League System upgrade complete!")
        print("   New tables and columns ready for use.")
        
    except Exception as e:
        print(f"\n❌ Error during upgrade: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_upgrade()
