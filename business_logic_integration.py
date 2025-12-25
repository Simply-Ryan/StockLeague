"""
Business Logic Integration - Activity Logging Hooks
Integrates engagement features into core trading and league operations
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from league_activity_feed import LeagueActivityFeed
from league_performance_metrics import LeaguePerformanceMetrics
from league_announcements import LeagueAnnouncements
from database.db_manager import DatabaseManager

logger = logging.getLogger('business_logic_integration')

class EngagementHooks:
    """Provides hooks for logging engagement activities in business logic"""
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        """Initialize engagement hooks"""
        self.db = db or DatabaseManager()
        self.activity_feed = LeagueActivityFeed(db=self.db)
        self.metrics = LeaguePerformanceMetrics(db=self.db)
        self.announcements = LeagueAnnouncements(db=self.db)
    
    def log_trade_execution(self, league_id: int, user_id: int, username: str, 
                          trade_type: str, symbol: str, shares: int, 
                          price: float, **kwargs) -> bool:
        """
        Log a trade execution event
        Call this when a trade is executed
        """
        try:
            success, activity_id, error = self.activity_feed.log_trade_activity(
                league_id=league_id,
                user_id=user_id,
                username=username,
                trade_type=trade_type,
                symbol=symbol,
                shares=shares,
                price=price
            )
            
            if success:
                logger.info(f"Trade logged: {username} {trade_type} {shares} {symbol} at ${price}")
            else:
                logger.warning(f"Failed to log trade: {error}")
            
            return success
        except Exception as e:
            logger.error(f"Trade logging error: {e}")
            return False
    
    def log_achievement_unlock(self, league_id: int, user_id: int, username: str,
                              achievement_name: str, achievement_description: str,
                              **kwargs) -> bool:
        """
        Log an achievement unlock event
        Call this when a user unlocks an achievement
        """
        try:
            success, activity_id, error = self.activity_feed.log_achievement_unlocked(
                league_id=league_id,
                user_id=user_id,
                username=username,
                achievement_name=achievement_name,
                achievement_description=achievement_description
            )
            
            if success:
                logger.info(f"Achievement logged: {username} unlocked {achievement_name}")
            else:
                logger.warning(f"Failed to log achievement: {error}")
            
            return success
        except Exception as e:
            logger.error(f"Achievement logging error: {e}")
            return False
    
    def log_ranking_update(self, league_id: int, user_id: int, username: str,
                          old_rank: int, new_rank: int, **kwargs) -> bool:
        """
        Log a ranking change event
        Call this when a user's ranking changes
        """
        try:
            if old_rank == new_rank:
                return True  # No change
            
            success, activity_id, error = self.activity_feed.log_ranking_change(
                league_id=league_id,
                user_id=user_id,
                username=username,
                old_rank=old_rank,
                new_rank=new_rank
            )
            
            if success:
                direction = "improved" if new_rank < old_rank else "decreased"
                logger.info(f"Ranking logged: {username} {direction} from #{old_rank} to #{new_rank}")
            else:
                logger.warning(f"Failed to log ranking change: {error}")
            
            return success
        except Exception as e:
            logger.error(f"Ranking logging error: {e}")
            return False
    
    def log_member_joined_league(self, league_id: int, user_id: int, username: str,
                                league_name: str, **kwargs) -> bool:
        """
        Log a member joining a league
        Call this when a user joins a league
        """
        try:
            success, activity_id, error = self.activity_feed.log_member_joined(
                league_id=league_id,
                user_id=user_id,
                username=username,
                league_name=league_name
            )
            
            if success:
                logger.info(f"Member logged: {username} joined {league_name}")
            else:
                logger.warning(f"Failed to log member join: {error}")
            
            return success
        except Exception as e:
            logger.error(f"Member join logging error: {e}")
            return False
    
    def log_milestone_reached(self, league_id: int, user_id: int, username: str,
                             milestone_name: str, milestone_value: Any, **kwargs) -> bool:
        """
        Log a milestone event
        Call this when a user reaches a milestone (e.g., $10k portfolio)
        """
        try:
            success, activity_id, error = self.activity_feed.log_activity(
                league_id=league_id,
                user_id=user_id,
                username=username,
                activity_type='milestone_reached',
                description=f"{username} reached {milestone_name}: {milestone_value}",
                metadata={'milestone': milestone_name, 'value': str(milestone_value)}
            )
            
            if success:
                logger.info(f"Milestone logged: {username} - {milestone_name}: {milestone_value}")
            else:
                logger.warning(f"Failed to log milestone: {error}")
            
            return success
        except Exception as e:
            logger.error(f"Milestone logging error: {e}")
            return False
    
    def post_league_announcement(self, league_id: int, author_id: int, author_username: str,
                                title: str, content: str, pinned: bool = False, **kwargs) -> bool:
        """
        Post an announcement to a league
        Call this when admin/owner posts league announcement
        """
        try:
            success, announcement_id, error = self.announcements.create_announcement(
                league_id=league_id,
                author_id=author_id,
                author_username=author_username,
                title=title,
                content=content,
                pinned=pinned
            )
            
            if success:
                logger.info(f"Announcement posted: {title} (ID: {announcement_id})")
            else:
                logger.warning(f"Failed to post announcement: {error}")
            
            return success
        except Exception as e:
            logger.error(f"Announcement error: {e}")
            return False
    
    def calculate_and_store_metrics(self, league_id: int, user_id: int, **kwargs) -> bool:
        """
        Calculate and store performance metrics for a user
        Call this periodically or after trades
        """
        try:
            success, metrics, error = self.metrics.get_user_league_metrics(
                league_id=league_id,
                user_id=user_id
            )
            
            if success:
                # Store metrics in performance_snapshots table
                cursor = self.db.get_connection().cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO league_performance_snapshots
                    (league_id, user_id, snapshot_date, portfolio_value, daily_pl, total_pl, win_rate, created_at)
                    VALUES (?, ?, date('now'), ?, ?, ?, ?, datetime('now'))
                """, (
                    league_id,
                    user_id,
                    metrics.get('portfolio_value', 0),
                    metrics.get('daily_pl', 0),
                    metrics.get('total_pl', 0),
                    metrics.get('win_rate', 0)
                ))
                self.db.get_connection().commit()
                
                logger.info(f"Metrics stored for user {user_id} in league {league_id}")
                return True
            else:
                logger.warning(f"Failed to calculate metrics: {error}")
                return False
        except Exception as e:
            logger.error(f"Metrics storage error: {e}")
            return False


# Convenience functions to use as hooks
_hooks = None

def get_hooks():
    """Get or create engagement hooks instance"""
    global _hooks
    if _hooks is None:
        _hooks = EngagementHooks()
    return _hooks

def log_trade(league_id: int, user_id: int, username: str, 
              trade_type: str, symbol: str, shares: int, price: float, **kwargs):
    """Log a trade - use in trading routes"""
    return get_hooks().log_trade_execution(
        league_id, user_id, username, trade_type, symbol, shares, price, **kwargs
    )

def log_achievement(league_id: int, user_id: int, username: str,
                   achievement_name: str, achievement_description: str, **kwargs):
    """Log an achievement - use in achievement routes"""
    return get_hooks().log_achievement_unlock(
        league_id, user_id, username, achievement_name, achievement_description, **kwargs
    )

def log_ranking(league_id: int, user_id: int, username: str,
               old_rank: int, new_rank: int, **kwargs):
    """Log a ranking change - use after rank recalculation"""
    return get_hooks().log_ranking_update(
        league_id, user_id, username, old_rank, new_rank, **kwargs
    )

def log_member_join(league_id: int, user_id: int, username: str,
                   league_name: str, **kwargs):
    """Log member join - use in league join route"""
    return get_hooks().log_member_joined_league(
        league_id, user_id, username, league_name, **kwargs
    )

def log_milestone(league_id: int, user_id: int, username: str,
                 milestone_name: str, milestone_value: Any, **kwargs):
    """Log a milestone - use when milestones are reached"""
    return get_hooks().log_milestone_reached(
        league_id, user_id, username, milestone_name, milestone_value, **kwargs
    )

def post_announcement(league_id: int, author_id: int, author_username: str,
                     title: str, content: str, pinned: bool = False, **kwargs):
    """Post an announcement - use in admin announcement route"""
    return get_hooks().post_league_announcement(
        league_id, author_id, author_username, title, content, pinned, **kwargs
    )

def store_metrics(league_id: int, user_id: int, **kwargs):
    """Store performance metrics - call after trades or periodically"""
    return get_hooks().calculate_and_store_metrics(league_id, user_id, **kwargs)


if __name__ == '__main__':
    # Example usage
    print("Business Logic Integration Module")
    print("=" * 70)
    
    hooks = EngagementHooks()
    
    print("\nAvailable hooks:")
    print("  - log_trade_execution()")
    print("  - log_achievement_unlock()")
    print("  - log_ranking_update()")
    print("  - log_member_joined_league()")
    print("  - log_milestone_reached()")
    print("  - post_league_announcement()")
    print("  - calculate_and_store_metrics()")
    
    print("\nOr use convenience functions:")
    print("  - log_trade()")
    print("  - log_achievement()")
    print("  - log_ranking()")
    print("  - log_member_join()")
    print("  - log_milestone()")
    print("  - post_announcement()")
    print("  - store_metrics()")
