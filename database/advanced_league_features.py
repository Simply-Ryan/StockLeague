"""
database/advanced_league_features.py

Advanced League Features - Database Schema and Methods
Adds support for:
- Head-to-Head (H2H) Matchups
- League Seasons with resets
- Division/Tier System
- Enhanced Activity Feed with filtering
- League Statistics
"""

import sqlite3
from datetime import datetime, timedelta
import json


class AdvancedLeagueDB:
    """Database operations for advanced league features."""
    
    def __init__(self, db_manager):
        """Initialize with reference to main DatabaseManager."""
        self.db = db_manager
    
    def init_h2h_tables(self):
        """Create tables for Head-to-Head matchups."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # H2H Matchups table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS h2h_matchups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                challenger_id INTEGER NOT NULL,
                opponent_id INTEGER NOT NULL,
                duration_days INTEGER DEFAULT 7,
                starting_capital NUMERIC NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                status TEXT DEFAULT 'active',
                challenger_final_value NUMERIC,
                opponent_final_value NUMERIC,
                winner_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues(id),
                FOREIGN KEY (challenger_id) REFERENCES users(id),
                FOREIGN KEY (opponent_id) REFERENCES users(id),
                FOREIGN KEY (winner_id) REFERENCES users(id)
            )
        """)
        
        # H2H Activity tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS h2h_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matchup_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                portfolio_value NUMERIC,
                description TEXT,
                metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (matchup_id) REFERENCES h2h_matchups(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # H2H Records (win/loss history)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS h2h_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                total_matchups INTEGER DEFAULT 0,
                win_rate NUMERIC DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(league_id, user_id)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_h2h_matchups_league 
            ON h2h_matchups(league_id, status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_h2h_matchups_players 
            ON h2h_matchups(challenger_id, opponent_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_h2h_records_league 
            ON h2h_records(league_id, win_rate DESC)
        """)
        
        conn.commit()
        conn.close()
    
    def init_season_tables(self):
        """Create tables for league seasons."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # League Seasons - table may already exist from schema_upgrade, so check first
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS league_seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                season_number INTEGER NOT NULL,
                name TEXT,
                started_at TIMESTAMP NOT NULL,
                ended_at TIMESTAMP,
                theme TEXT,
                prize_pool NUMERIC DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues(id),
                UNIQUE(league_id, season_number)
            )
        """)
        
        # Add status column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE league_seasons ADD COLUMN status TEXT DEFAULT 'active'")
        except:
            pass
        
        # Season standings (final rankings)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS season_standings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                final_rank INTEGER,
                final_value NUMERIC,
                performance_score NUMERIC,
                badges_earned TEXT,
                prize_won NUMERIC DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (season_id) REFERENCES league_seasons(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(season_id, user_id)
            )
        """)
        
        # Create indexes
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_league_seasons_league 
                ON league_seasons(league_id)
            """)
        except:
            pass
        
        conn.commit()
        conn.close()
    
    def init_division_tables(self):
        """Create tables for league divisions/tiers."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # League Divisions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS league_divisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                season_number INTEGER NOT NULL,
                name TEXT NOT NULL,
                tier_level INTEGER,
                min_score NUMERIC,
                max_score NUMERIC,
                icon TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues(id),
                UNIQUE(league_id, season_number, tier_level)
            )
        """)
        
        # Division Membership
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS division_membership (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                division_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                division_rank INTEGER,
                score NUMERIC DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (division_id) REFERENCES league_divisions(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(division_id, user_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def init_enhanced_activity_feed(self):
        """Enhance activity feed with filtering and categories."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Add columns to existing league_activity_feed if not present
        try:
            cursor.execute("ALTER TABLE league_activity_feed ADD COLUMN category TEXT DEFAULT 'general'")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE league_activity_feed ADD COLUMN priority INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE league_activity_feed ADD COLUMN is_pinned INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE league_activity_feed ADD COLUMN mentions_json TEXT")
        except sqlite3.OperationalError:
            pass
        
        # Activity Categories index
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_feed_category 
            ON league_activity_feed(league_id, category, created_at DESC)
        """)
        
        conn.commit()
        conn.close()
    
    # ===== H2H MATCHUP METHODS =====
    
    def create_h2h_matchup(self, league_id, challenger_id, opponent_id, duration_days=7, starting_capital=10000):
        """Create a new H2H matchup."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO h2h_matchups 
            (league_id, challenger_id, opponent_id, duration_days, starting_capital, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        """, (league_id, challenger_id, opponent_id, duration_days, starting_capital))
        
        matchup_id = cursor.lastrowid
        
        # Initialize H2H records if not exist
        for user_id in [challenger_id, opponent_id]:
            cursor.execute("""
                INSERT OR IGNORE INTO h2h_records (league_id, user_id)
                VALUES (?, ?)
            """, (league_id, user_id))
        
        conn.commit()
        conn.close()
        
        return matchup_id
    
    def get_user_h2h_matchups(self, user_id, league_id=None, status='active', limit=10):
        """Get H2H matchups for a user."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT * FROM h2h_matchups 
            WHERE (challenger_id = ? OR opponent_id = ?)
        """
        params = [user_id, user_id]
        
        if league_id:
            query += " AND league_id = ?"
            params.append(league_id)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def end_h2h_matchup(self, matchup_id, challenger_final, opponent_final):
        """End an H2H matchup and determine winner."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get matchup details
        cursor.execute("SELECT * FROM h2h_matchups WHERE id = ?", (matchup_id,))
        matchup = dict(cursor.fetchone())
        
        # Determine winner
        if challenger_final > opponent_final:
            winner_id = matchup['challenger_id']
        elif opponent_final > challenger_final:
            winner_id = matchup['opponent_id']
        else:
            winner_id = None
        
        # Update matchup
        cursor.execute("""
            UPDATE h2h_matchups 
            SET status = 'completed', 
                challenger_final_value = ?,
                opponent_final_value = ?,
                winner_id = ?,
                ended_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (challenger_final, opponent_final, winner_id, matchup_id))
        
        # Update H2H records
        if winner_id == matchup['challenger_id']:
            cursor.execute("""
                UPDATE h2h_records 
                SET wins = wins + 1, total_matchups = total_matchups + 1
                WHERE league_id = ? AND user_id = ?
            """, (matchup['league_id'], matchup['challenger_id']))
            cursor.execute("""
                UPDATE h2h_records 
                SET losses = losses + 1, total_matchups = total_matchups + 1
                WHERE league_id = ? AND user_id = ?
            """, (matchup['league_id'], matchup['opponent_id']))
        elif winner_id == matchup['opponent_id']:
            cursor.execute("""
                UPDATE h2h_records 
                SET losses = losses + 1, total_matchups = total_matchups + 1
                WHERE league_id = ? AND user_id = ?
            """, (matchup['league_id'], matchup['challenger_id']))
            cursor.execute("""
                UPDATE h2h_records 
                SET wins = wins + 1, total_matchups = total_matchups + 1
                WHERE league_id = ? AND user_id = ?
            """, (matchup['league_id'], matchup['opponent_id']))
        else:
            # Draw
            cursor.execute("""
                UPDATE h2h_records 
                SET draws = draws + 1, total_matchups = total_matchups + 1
                WHERE league_id = ? AND user_id = ?
            """, (matchup['league_id'], matchup['challenger_id']))
            cursor.execute("""
                UPDATE h2h_records 
                SET draws = draws + 1, total_matchups = total_matchups + 1
                WHERE league_id = ? AND user_id = ?
            """, (matchup['league_id'], matchup['opponent_id']))
        
        # Update win rate
        for user_id in [matchup['challenger_id'], matchup['opponent_id']]:
            cursor.execute("""
                UPDATE h2h_records 
                SET win_rate = CASE 
                    WHEN total_matchups = 0 THEN 0
                    ELSE ROUND(CAST(wins AS FLOAT) / total_matchups * 100, 2)
                END
                WHERE league_id = ? AND user_id = ?
            """, (matchup['league_id'], user_id))
        
        conn.commit()
        conn.close()
    
    def get_h2h_leaderboard(self, league_id, limit=20):
        """Get H2H leaderboard for a league."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                hr.*,
                u.username,
                u.avatar_url
            FROM h2h_records hr
            JOIN users u ON hr.user_id = u.id
            WHERE hr.league_id = ?
            ORDER BY hr.win_rate DESC, hr.wins DESC
            LIMIT ?
        """, (league_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ===== SEASON METHODS =====
    
    def create_league_season(self, league_id, season_number, name=None, duration_days=30):
        """Create a new league season."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        started_at = datetime.now()
        ended_at = started_at + timedelta(days=duration_days)
        
        cursor.execute("""
            INSERT INTO league_seasons 
            (league_id, season_number, name, started_at, ended_at, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        """, (league_id, season_number, name or f"Season {season_number}", started_at, ended_at))
        
        season_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return season_id
    
    def end_league_season(self, season_id):
        """End a league season and record final standings."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM league_seasons WHERE id = ?", (season_id,))
        season = dict(cursor.fetchone())
        
        # Update season status
        cursor.execute("""
            UPDATE league_seasons SET status = 'completed', ended_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (season_id,))
        
        # Get final leaderboard for season
        cursor.execute("""
            SELECT lm.user_id, lm.score, lm.current_rank
            FROM league_members lm
            WHERE lm.league_id = ?
            ORDER BY lm.current_rank ASC
        """, (season['league_id'],))
        
        standings = cursor.fetchall()
        
        # Record season standings
        for i, standing in enumerate(standings):
            cursor.execute("""
                INSERT INTO season_standings (season_id, user_id, final_rank, performance_score)
                VALUES (?, ?, ?, ?)
            """, (season_id, standing[0], i + 1, standing[1]))
        
        conn.commit()
        conn.close()
    
    def get_season_standings(self, season_id, limit=50):
        """Get final standings for a season."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                ss.*,
                u.username,
                u.avatar_url
            FROM season_standings ss
            JOIN users u ON ss.user_id = u.id
            WHERE ss.season_id = ?
            ORDER BY ss.final_rank ASC
            LIMIT ?
        """, (season_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ===== ENHANCED ACTIVITY FEED METHODS =====
    
    def add_categorized_activity(self, league_id, activity_type, title, description, user_id, 
                                category='general', priority=0, metadata=None):
        """Add activity with category and priority."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute("""
            INSERT INTO league_activity_feed 
            (league_id, activity_type, title, description, user_id, category, priority, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (league_id, activity_type, title, description, user_id, category, priority, metadata_json))
        
        activity_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return activity_id
    
    def get_activity_feed_by_category(self, league_id, category, limit=20, offset=0):
        """Get activity feed filtered by category."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM league_activity_feed
            WHERE league_id = ? AND category = ?
            ORDER BY priority DESC, created_at DESC
            LIMIT ? OFFSET ?
        """, (league_id, category, limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def pin_activity(self, activity_id, is_pinned=True):
        """Pin/unpin an activity to top of feed."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE league_activity_feed
            SET is_pinned = ?, priority = ?
            WHERE id = ?
        """, (1 if is_pinned else 0, 100 if is_pinned else 0, activity_id))
        
        conn.commit()
        conn.close()
    
    def get_league_statistics(self, league_id):
        """Get comprehensive league statistics."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Member count
        cursor.execute("SELECT COUNT(*) FROM league_members WHERE league_id = ?", (league_id,))
        member_count = cursor.fetchone()[0]
        
        # Total activity
        cursor.execute("SELECT COUNT(*) FROM league_activity_feed WHERE league_id = ?", (league_id,))
        activity_count = cursor.fetchone()[0]
        
        # Top trader
        cursor.execute("""
            SELECT lm.user_id, u.username, lm.score
            FROM league_members lm
            JOIN users u ON lm.user_id = u.id
            WHERE lm.league_id = ?
            ORDER BY lm.score DESC
            LIMIT 1
        """, (league_id,))
        top_trader = dict(cursor.fetchone()) if cursor.fetchone() else None
        
        # Average portfolio value
        cursor.execute("""
            SELECT AVG(lp.cash) FROM league_portfolios lp
            WHERE lp.league_id = ?
        """, (league_id,))
        avg_portfolio = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'member_count': member_count,
            'activity_count': activity_count,
            'top_trader': top_trader,
            'avg_portfolio_value': avg_portfolio
        }
