"""
Advanced League System - Backend Services

Implements:
- AdvancedLeagueManager: High-level league operations
- RatingSystem: Elo-based skill ratings
- AchievementEngine: Badge and achievement system
- QuestSystem: Daily/weekly challenges
- FairPlayEngine: Suspicious activity detection
- AnalyticsCalculator: Performance metrics
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any


class RatingSystem:
    """Elo-like rating system for skill-based matching and rankings."""
    
    K_FACTOR = 32  # Rating change per match
    BASE_RATING = 1600
    
    def __init__(self, db):
        self.db = db
    
    def get_user_rating(self, user_id: int, league_id: int) -> float:
        """Get current rating for a user in a league."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(AVG(score), ?) FROM league_member_stats
            WHERE user_id = ? AND league_id = ?
        """, (self.BASE_RATING, user_id, league_id))
        rating = cursor.fetchone()[0]
        conn.close()
        return rating
    
    def calculate_new_rating(self, current_rating: float, opponent_rating: float,
                            result: str) -> float:
        """Calculate new rating after a trade result."""
        expected_score = 1 / (1 + 10 ** ((opponent_rating - current_rating) / 400))
        
        if result == 'win':
            actual_score = 1
        elif result == 'draw':
            actual_score = 0.5
        else:
            actual_score = 0
        
        new_rating = current_rating + self.K_FACTOR * (actual_score - expected_score)
        return new_rating
    
    def find_matched_opponent(self, user_id: int, league_id: int,
                             rating_tolerance: float = 200) -> Optional[Dict]:
        """Find similarly-rated opponent for head-to-head competition."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        user_rating = self.get_user_rating(user_id, league_id)
        min_rating = user_rating - rating_tolerance
        max_rating = user_rating + rating_tolerance
        
        cursor.execute("""
            SELECT u.id, u.username, AVG(stats.score) as rating
            FROM league_member_stats stats
            JOIN users u ON stats.user_id = u.id
            WHERE stats.league_id = ? AND stats.user_id != ?
            AND AVG(stats.score) BETWEEN ? AND ?
            GROUP BY stats.user_id
            ORDER BY ABS(AVG(stats.score) - ?) ASC
            LIMIT 1
        """, (league_id, user_id, min_rating, max_rating, user_rating))
        
        result = cursor.fetchone()
        conn.close()
        
        return dict(result) if result else None


class AchievementEngine:
    """Manages achievement unlocking and badge progression."""
    
    ACHIEVEMENT_TEMPLATES = {
        'first_trade': {
            'name': 'First Steps',
            'description': 'Complete your first trade',
            'rarity': 'common',
            'points': 10
        },
        'win_streak_5': {
            'name': 'On a Roll',
            'description': 'Achieve 5 consecutive winning trades',
            'rarity': 'rare',
            'points': 50
        },
        'trader_100k': {
            'name': 'Century Club',
            'description': 'Accumulate $100,000 in trading volume',
            'rarity': 'epic',
            'points': 100
        },
        'perfect_week': {
            'name': 'Flawless',
            'description': 'Win all trades in a single week',
            'rarity': 'epic',
            'points': 75
        },
        'diversification': {
            'name': 'Portfolio Master',
            'description': 'Hold positions in 10+ different stocks',
            'rarity': 'rare',
            'points': 40
        },
        'recovery': {
            'name': 'Comeback Kid',
            'description': 'Recover from -50% drawdown back to breakeven',
            'rarity': 'legendary',
            'points': 200
        }
    }
    
    def __init__(self, db):
        self.db = db
    
    def initialize_achievements(self, league_id: int):
        """Create default achievements for a league."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        for key, achievement in self.ACHIEVEMENT_TEMPLATES.items():
            try:
                cursor.execute("""
                    INSERT INTO league_achievements
                    (league_id, name, description, rarity, points_reward, badge_icon)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    league_id,
                    achievement['name'],
                    achievement['description'],
                    achievement['rarity'],
                    achievement['points'],
                    f"fa-{key.lower()}"
                ))
            except:
                pass
        
        conn.commit()
        conn.close()
    
    def check_achievements(self, user_id: int, league_id: int, stats: Dict) -> List[int]:
        """Check and unlock earned achievements based on current stats."""
        unlocked = []
        
        # Check win streak achievements
        if stats.get('win_streak', 0) >= 5:
            if self._unlock_achievement(user_id, league_id, 'win_streak_5'):
                unlocked.append('win_streak_5')
        
        # Check trading volume
        if stats.get('total_trading_volume', 0) >= 100000:
            if self._unlock_achievement(user_id, league_id, 'trader_100k'):
                unlocked.append('trader_100k')
        
        # Check diversification
        if stats.get('position_count', 0) >= 10:
            if self._unlock_achievement(user_id, league_id, 'diversification'):
                unlocked.append('diversification')
        
        return unlocked
    
    def _unlock_achievement(self, user_id: int, league_id: int, achievement_key: str) -> bool:
        """Unlock an achievement for a user."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id FROM league_achievements
                WHERE league_id = ? AND name = ?
            """, (league_id, self.ACHIEVEMENT_TEMPLATES[achievement_key]['name']))
            
            achievement = cursor.fetchone()
            if not achievement:
                return False
            
            cursor.execute("""
                INSERT OR IGNORE INTO league_badges
                (league_id, user_id, achievement_id, unlocked_at)
                VALUES (?, ?, ?, ?)
            """, (league_id, user_id, achievement[0], datetime.now()))
            
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get_user_badges(self, user_id: int, league_id: int) -> List[Dict]:
        """Get all badges earned by a user in a league."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                a.name, a.description, a.badge_icon, a.rarity,
                b.unlocked_at, b.is_displayed
            FROM league_badges b
            JOIN league_achievements a ON b.achievement_id = a.id
            WHERE b.user_id = ? AND b.league_id = ?
            ORDER BY b.unlocked_at DESC
        """, (user_id, league_id))
        
        badges = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return badges


class QuestSystem:
    """Manages daily/weekly/seasonal quests and rewards."""
    
    DAILY_QUEST_TEMPLATES = [
        {
            'title': 'Daily Trader',
            'description': 'Execute 3 trades',
            'quest_type': 'daily',
            'reward_points': 10,
            'reward_cash': 10
        },
        {
            'title': 'Lucky Sevens',
            'description': 'Win 2 trades today',
            'quest_type': 'daily',
            'reward_points': 15,
            'reward_cash': 25
        },
        {
            'title': 'Volume Master',
            'description': 'Trade at least $10,000 in volume',
            'quest_type': 'daily',
            'reward_points': 20,
            'reward_cash': 50
        }
    ]
    
    def __init__(self, db):
        self.db = db
    
    def generate_daily_quests(self, league_id: int):
        """Create daily quests for a league."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        
        for template in self.DAILY_QUEST_TEMPLATES:
            cursor.execute("""
                INSERT OR IGNORE INTO league_quests
                (league_id, title, description, quest_type,
                 start_date, end_date, reward_points, reward_cash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                league_id, template['title'], template['description'],
                template['quest_type'], now, tomorrow,
                template['reward_points'], template['reward_cash']
            ))
        
        conn.commit()
        conn.close()
    
    def get_active_quests(self, league_id: int) -> List[Dict]:
        """Get all active quests for a league."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now()
        cursor.execute("""
            SELECT * FROM league_quests
            WHERE league_id = ? AND start_date <= ? AND end_date > ?
            ORDER BY quest_type DESC
        """, (league_id, now, now))
        
        quests = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return quests
    
    def claim_quest_reward(self, user_id: int, quest_id: int) -> Tuple[bool, str]:
        """Claim reward for completed quest."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if quest is completed
            cursor.execute("""
                SELECT progress FROM league_quest_progress
                WHERE quest_id = ? AND user_id = ? AND completed_at IS NOT NULL
            """, (quest_id, user_id))
            
            if not cursor.fetchone():
                return False, "Quest not completed"
            
            # Get reward
            cursor.execute("""
                SELECT reward_cash FROM league_quests WHERE id = ?
            """, (quest_id,))
            
            reward = cursor.fetchone()
            if not reward:
                return False, "Quest not found"
            
            # Mark as claimed and add cash
            cursor.execute("""
                UPDATE league_quest_progress
                SET claimed_at = ?
                WHERE quest_id = ? AND user_id = ?
            """, (datetime.now(), quest_id, user_id))
            
            # TODO: Add cash to user account
            conn.commit()
            return True, f"Earned ${reward[0]:.2f}!"
        finally:
            conn.close()


class FairPlayEngine:
    """Detects and flags suspicious trading patterns."""
    
    THRESHOLDS = {
        'rapid_trading_minutes': 5,        # 5 trades in 5 minutes
        'rapid_trading_count': 5,
        'unusual_win_rate': 0.95,          # >95% win rate
        'timing_variance': 2.0,            # Standard deviations
        'volume_spike': 5.0,               # 5x normal volume
    }
    
    def __init__(self, db):
        self.db = db
    
    def analyze_trading_pattern(self, user_id: int, league_id: int) -> List[Dict]:
        """Analyze user's trading pattern for anomalies."""
        flags = []
        
        # Check for rapid trading
        if self._check_rapid_trading(user_id, league_id):
            flags.append({
                'type': 'rapid_trading',
                'severity': 'medium',
                'description': 'Unusual number of trades in short time'
            })
        
        # Check win rate
        win_rate = self._calculate_win_rate(user_id, league_id)
        if win_rate > self.THRESHOLDS['unusual_win_rate']:
            flags.append({
                'type': 'unusual_win_rate',
                'severity': 'high',
                'description': f'Exceptionally high win rate: {win_rate:.1%}'
            })
        
        # Check volume patterns
        if self._check_volume_spike(user_id, league_id):
            flags.append({
                'type': 'volume_spike',
                'severity': 'medium',
                'description': 'Unusual trading volume'
            })
        
        return flags
    
    def _check_rapid_trading(self, user_id: int, league_id: int) -> bool:
        """Check if user is trading suspiciously fast."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        five_min_ago = datetime.now() - timedelta(minutes=5)
        
        cursor.execute("""
            SELECT COUNT(*) FROM league_transactions
            WHERE user_id = ? AND league_id = ? AND timestamp > ?
        """, (user_id, league_id, five_min_ago))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count >= self.THRESHOLDS['rapid_trading_count']
    
    def _calculate_win_rate(self, user_id: int, league_id: int) -> float:
        """Calculate user's win rate in the league."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT win_rate FROM league_member_stats
            WHERE user_id = ? AND league_id = ?
            ORDER BY joined_at DESC LIMIT 1
        """, (user_id, league_id))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0
    
    def _check_volume_spike(self, user_id: int, league_id: int) -> bool:
        """Check for unusual trading volume."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get today's volume
        today = datetime.now().date()
        cursor.execute("""
            SELECT SUM(shares * price) FROM league_transactions
            WHERE user_id = ? AND league_id = ? 
            AND DATE(timestamp) = ?
        """, (user_id, league_id, today))
        
        today_volume = cursor.fetchone()[0] or 0
        
        # Get average volume for last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        cursor.execute("""
            SELECT AVG(daily_volume) FROM (
                SELECT SUM(shares * price) as daily_volume
                FROM league_transactions
                WHERE user_id = ? AND league_id = ? 
                AND timestamp > ?
                GROUP BY DATE(timestamp)
            )
        """, (user_id, league_id, thirty_days_ago))
        
        avg_volume = cursor.fetchone()[0] or 1
        conn.close()
        
        return today_volume > (avg_volume * self.THRESHOLDS['volume_spike'])


class AnalyticsCalculator:
    """Calculates real-time performance metrics."""
    
    def __init__(self, db):
        self.db = db
    
    def calculate_sharpe_ratio(self, user_id: int, league_id: int, days: int = 30) -> float:
        """Calculate Sharpe ratio (risk-adjusted returns)."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        start_date = datetime.now() - timedelta(days=days)
        
        cursor.execute("""
            SELECT daily_return FROM league_analytics
            WHERE user_id = ? AND league_id = ? AND date >= ?
            ORDER BY date ASC
        """, (user_id, league_id, start_date))
        
        returns = [row[0] or 0 for row in cursor.fetchall()]
        conn.close()
        
        if not returns or len(returns) < 2:
            return 0
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0
        
        # Annualize (252 trading days)
        risk_free_rate = 0.02 / 252
        return (mean_return - risk_free_rate) / std_dev * math.sqrt(252)
    
    def calculate_max_drawdown(self, user_id: int, league_id: int) -> float:
        """Calculate maximum drawdown percentage."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT portfolio_value FROM league_analytics
            WHERE user_id = ? AND league_id = ?
            ORDER BY date ASC
        """, (user_id, league_id))
        
        values = [row[0] for row in cursor.fetchall() if row[0]]
        conn.close()
        
        if not values:
            return 0
        
        max_val = values[0]
        max_drawdown = 0
        
        for val in values:
            if val > max_val:
                max_val = val
            drawdown = (max_val - val) / max_val
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def record_daily_metrics(self, user_id: int, league_id: int,
                            portfolio_value: float, trades_count: int,
                            wins: int, losses: int):
        """Record daily performance metrics."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        daily_return = 0  # Would be calculated from previous day
        win_loss_ratio = wins / losses if losses > 0 else wins
        
        cursor.execute("""
            INSERT OR REPLACE INTO league_analytics
            (league_id, user_id, date, trades_count, win_count, loss_count,
             daily_return, portfolio_value, win_loss_ratio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (league_id, user_id, datetime.now().date(),
              trades_count, wins, losses, daily_return,
              portfolio_value, win_loss_ratio))
        
        conn.commit()
        conn.close()


class AdvancedLeagueManager:
    """High-level league management with all advanced features."""
    
    def __init__(self, db):
        self.db = db
        self.rating_system = RatingSystem(db)
        self.achievements = AchievementEngine(db)
        self.quests = QuestSystem(db)
        self.fair_play = FairPlayEngine(db)
        self.analytics = AnalyticsCalculator(db)
    
    def create_league_with_config(self, name: str, description: str,
                                 creator_id: int, config: Dict) -> int:
        """Create a league with advanced configuration."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        league_id, invite_code = self.db.create_league(
            name, description, creator_id,
            league_type=config.get('league_type', 'public'),
            starting_cash=config.get('starting_cash', 10000)
        )
        
        # Set advanced settings
        cursor.execute("""
            UPDATE leagues SET
                league_tier = ?, competition_mode = ?, max_members = ?,
                prize_pool = ?, league_settings_json = ?,
                visibility = ?
            WHERE id = ?
        """, (
            config.get('tier', 'bronze'),
            config.get('mode', 'percentage'),
            config.get('max_members'),
            config.get('prize_pool', 0),
            json.dumps(config.get('settings', {})),
            config.get('visibility', 'public'),
            league_id
        ))
        
        # Create first season
        cursor.execute("""
            INSERT INTO league_seasons
            (league_id, season_number, start_date, end_date, is_active)
            VALUES (?, 1, ?, ?, 1)
        """, (league_id, datetime.now(), datetime.now() + timedelta(days=30)))
        
        conn.commit()
        conn.close()
        
        # Initialize achievements and quests
        self.achievements.initialize_achievements(league_id)
        self.quests.generate_daily_quests(league_id)
        
        return league_id
    
    def auto_update_rankings(self, league_id: int, season_number: int = 1):
        """Auto-update all member rankings and scores."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get all members with current stats
        cursor.execute("""
            SELECT user_id, score FROM league_member_stats
            WHERE league_id = ? AND season_number = ?
            ORDER BY score DESC
        """, (league_id, season_number))
        
        members = cursor.fetchall()
        
        # Assign ranks
        for rank, (user_id, score) in enumerate(members, 1):
            cursor.execute("""
                UPDATE league_member_stats
                SET current_rank = ?
                WHERE league_id = ? AND user_id = ? AND season_number = ?
            """, (rank, league_id, user_id, season_number))
        
        conn.commit()
        conn.close()
    
    def process_end_of_season(self, league_id: int, season_number: int):
        """Handle season ending: archive data, start new season, announce winners."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Mark season as inactive
        cursor.execute("""
            UPDATE league_seasons
            SET is_active = 0
            WHERE league_id = ? AND season_number = ?
        """, (league_id, season_number))
        
        # Create next season
        cursor.execute("""
            INSERT INTO league_seasons
            (league_id, season_number, start_date, end_date, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (league_id, season_number + 1,
              datetime.now(), datetime.now() + timedelta(days=30)))
        
        # Reset all member scores for new season
        cursor.execute("""
            INSERT INTO league_member_stats
            (league_id, user_id, season_number, score)
            SELECT league_id, user_id, ?, 0
            FROM league_members
            WHERE league_id = ?
        """, (season_number + 1, league_id))
        
        conn.commit()
        conn.close()
