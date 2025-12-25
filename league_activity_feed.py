"""
League Activity Feed Service
Manages league-specific activity tracking, querying, and real-time updates
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
from phase_3_schema import ActivityType, SystemEventType

# Configure logger
activity_logger = logging.getLogger('activity_feed')
activity_logger.setLevel(logging.INFO)


class LeagueActivityFeed:
    """Service for managing league activity feeds"""
    
    def __init__(self, db):
        """
        Initialize activity feed service
        
        Args:
            db: Database manager instance
        """
        self.db = db
    
    # ===== ACTIVITY LOGGING =====
    
    def log_activity(
        self,
        league_id: int,
        user_id: int,
        activity_type: str,
        description: str,
        metadata: Dict = None
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Log an activity in league activity feed
        
        Args:
            league_id: League ID
            user_id: User ID
            activity_type: Type of activity (see ActivityType)
            description: Human-readable description
            metadata: Additional JSON data
        
        Returns:
            (success, activity_id, error_message)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute("""
                INSERT INTO league_activity_log 
                (league_id, user_id, activity_type, description, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (league_id, user_id, activity_type, description, metadata_json, datetime.now()))
            
            conn.commit()
            activity_id = cursor.lastrowid
            conn.close()
            
            activity_logger.info(
                f"Activity logged: league={league_id}, user={user_id}, "
                f"type={activity_type}, id={activity_id}"
            )
            
            return True, activity_id, None
        
        except Exception as e:
            activity_logger.error(f"Error logging activity: {e}")
            return False, None, str(e)
    
    # ===== ACTIVITY QUERYING =====
    
    def get_league_activity_feed(
        self,
        league_id: int,
        limit: int = 20,
        offset: int = 0,
        activity_types: List[str] = None
    ) -> Tuple[bool, List[Dict], Optional[str]]:
        """
        Get activity feed for a league
        
        Args:
            league_id: League ID
            limit: Number of activities to return
            offset: Pagination offset
            activity_types: Filter by activity types (None = all)
        
        Returns:
            (success, activities, error_message)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    la.id, la.league_id, la.user_id, 
                    la.activity_type, la.description, 
                    la.metadata, la.created_at,
                    u.username, u.avatar_url
                FROM league_activity_log la
                JOIN users u ON la.user_id = u.id
                WHERE la.league_id = ?
            """
            
            params = [league_id]
            
            # Filter by activity types if provided
            if activity_types:
                placeholders = ','.join('?' * len(activity_types))
                query += f" AND la.activity_type IN ({placeholders})"
                params.extend(activity_types)
            
            query += " ORDER BY la.created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to dictionaries
            activities = []
            for row in rows:
                activity = {
                    'id': row[0],
                    'league_id': row[1],
                    'user_id': row[2],
                    'activity_type': row[3],
                    'description': row[4],
                    'metadata': json.loads(row[5]) if row[5] else {},
                    'created_at': row[6],
                    'username': row[7],
                    'avatar_url': row[8],
                }
                activities.append(activity)
            
            activity_logger.debug(f"Retrieved {len(activities)} activities for league {league_id}")
            
            return True, activities, None
        
        except Exception as e:
            activity_logger.error(f"Error fetching activity feed: {e}")
            return False, [], str(e)
    
    # ===== ACTIVITY STATISTICS =====
    
    def get_recent_activity_stats(
        self,
        league_id: int,
        hours: int = 24
    ) -> Tuple[bool, Dict, Optional[str]]:
        """
        Get activity statistics for recent period
        
        Args:
            league_id: League ID
            hours: Number of hours to look back
        
        Returns:
            (success, stats, error_message)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Get activity summary
            cursor.execute("""
                SELECT 
                    activity_type,
                    COUNT(*) as count
                FROM league_activity_log
                WHERE league_id = ? AND created_at >= ?
                GROUP BY activity_type
            """, (league_id, cutoff_time))
            
            type_counts = {}
            for row in cursor.fetchall():
                type_counts[row[0]] = row[1]
            
            # Get total activities
            cursor.execute("""
                SELECT COUNT(*) FROM league_activity_log
                WHERE league_id = ? AND created_at >= ?
            """, (league_id, cutoff_time))
            
            total_count = cursor.fetchone()[0]
            
            # Get most active users
            cursor.execute("""
                SELECT user_id, COUNT(*) as count
                FROM league_activity_log
                WHERE league_id = ? AND created_at >= ?
                GROUP BY user_id
                ORDER BY count DESC
                LIMIT 5
            """, (league_id, cutoff_time))
            
            most_active = []
            for row in cursor.fetchall():
                most_active.append({'user_id': row[0], 'count': row[1]})
            
            conn.close()
            
            stats = {
                'total_activities': total_count,
                'by_type': type_counts,
                'most_active_users': most_active,
                'period_hours': hours,
            }
            
            return True, stats, None
        
        except Exception as e:
            activity_logger.error(f"Error getting activity stats: {e}")
            return False, {}, str(e)
    
    # ===== ACTIVITY HELPERS =====
    
    def log_trade_activity(
        self,
        league_id: int,
        user_id: int,
        action: str,
        symbol: str,
        shares: int,
        price: float
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Log a trade activity
        
        Args:
            league_id: League ID
            user_id: User ID
            action: 'BUY' or 'SELL'
            symbol: Stock symbol
            shares: Number of shares
            price: Stock price
        
        Returns:
            (success, activity_id, error_message)
        """
        activity_type = ActivityType.TRADE_BUY if action.upper() == 'BUY' else ActivityType.TRADE_SELL
        description = f"{action.upper()}: {shares} shares of {symbol} @ ${price:.2f}"
        metadata = {
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'total_value': shares * price,
        }
        
        return self.log_activity(league_id, user_id, activity_type, description, metadata)
    
    def log_ranking_change(
        self,
        league_id: int,
        user_id: int,
        old_rank: int,
        new_rank: int
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """Log ranking change activity"""
        if old_rank == new_rank:
            return True, None, None
        
        change = old_rank - new_rank  # Positive = improvement
        direction = "↑" if change > 0 else "↓"
        
        description = f"Ranking changed from #{old_rank} to #{new_rank} {direction}"
        metadata = {
            'old_rank': old_rank,
            'new_rank': new_rank,
            'change': change,
        }
        
        return self.log_activity(league_id, user_id, ActivityType.RANKING_CHANGE, 
                                description, metadata)
    
    def log_achievement_unlocked(
        self,
        league_id: int,
        user_id: int,
        achievement_name: str,
        achievement_description: str
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """Log achievement unlock activity"""
        description = f"Unlocked achievement: {achievement_name}"
        metadata = {
            'achievement': achievement_name,
            'description': achievement_description,
        }
        
        return self.log_activity(league_id, user_id, ActivityType.ACHIEVEMENT_UNLOCKED,
                                description, metadata)
    
    def log_member_joined(
        self,
        league_id: int,
        user_id: int,
        username: str
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """Log member joined activity"""
        description = f"{username} joined the league"
        metadata = {'username': username}
        
        return self.log_activity(league_id, user_id, ActivityType.MEMBER_JOINED,
                                description, metadata)
    
    def log_system_event(
        self,
        league_id: int,
        event_type: str,
        description: str,
        data: Dict = None
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Log a system event
        
        Args:
            league_id: League ID
            event_type: Type of system event
            description: Human-readable description
            data: Additional JSON data
        
        Returns:
            (success, event_id, error_message)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            data_json = json.dumps(data) if data else None
            
            cursor.execute("""
                INSERT INTO league_system_events 
                (league_id, event_type, description, data, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (league_id, event_type, description, data_json, datetime.now()))
            
            conn.commit()
            event_id = cursor.lastrowid
            conn.close()
            
            activity_logger.info(
                f"System event logged: league={league_id}, "
                f"type={event_type}, id={event_id}"
            )
            
            return True, event_id, None
        
        except Exception as e:
            activity_logger.error(f"Error logging system event: {e}")
            return False, None, str(e)
    
    # ===== ACTIVITY CLEANUP =====
    
    def cleanup_old_activities(
        self,
        league_id: int,
        days_to_keep: int = 90
    ) -> Tuple[bool, int, Optional[str]]:
        """
        Delete old activities older than specified days
        
        Args:
            league_id: League ID
            days_to_keep: Keep activities from last N days
        
        Returns:
            (success, rows_deleted, error_message)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            cursor.execute("""
                DELETE FROM league_activity_log
                WHERE league_id = ? AND created_at < ?
            """, (league_id, cutoff_date))
            
            rows_deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            activity_logger.info(f"Cleaned up {rows_deleted} activities for league {league_id}")
            
            return True, rows_deleted, None
        
        except Exception as e:
            activity_logger.error(f"Error cleaning up activities: {e}")
            return False, 0, str(e)


if __name__ == '__main__':
    print("League Activity Feed Service loaded")
