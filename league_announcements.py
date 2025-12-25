"""
League Announcements & System Events Service - Phase 3.3
Manages league announcements and tracks important league events
Supports pinned announcements, system notifications, and event logging
"""

import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from database.db_manager import DatabaseManager

# Configure logger
logger = logging.getLogger('league_announcements')
logger.setLevel(logging.INFO)


class LeagueAnnouncements:
    """Service for managing league announcements and system events"""
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        """Initialize announcements service"""
        self.db = db or DatabaseManager()
        self.logger = logger
    
    def create_announcement(self, league_id: int, title: str, content: str, 
                           author_id: int, author_username: str,
                           pinned: bool = False) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Create a new league announcement
        
        Returns:
            (success, announcement_id, error_message)
        """
        try:
            if not title or not content:
                return False, None, 'Title and content required'
            
            if len(title) > 200:
                return False, None, 'Title must be less than 200 characters'
            
            if len(content) > 5000:
                return False, None, 'Content must be less than 5000 characters'
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO league_announcements 
                (league_id, title, content, author_id, username, pinned, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (league_id, title, content, author_id, author_username, pinned, now, now))
            
            conn.commit()
            announcement_id = cursor.lastrowid
            conn.close()
            
            self.logger.info(f"Announcement {announcement_id} created by user {author_id} in league {league_id}")
            return True, announcement_id, None
            
        except Exception as e:
            self.logger.error(f"Error creating announcement: {e}")
            return False, None, str(e)
    
    def update_announcement(self, league_id: int, announcement_id: int, 
                           title: str, content: str, 
                           user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Update an existing announcement
        
        Returns:
            (success, error_message)
        """
        try:
            if not title or not content:
                return False, 'Title and content required'
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Verify user has permission (admin/owner/author)
            cursor.execute('''
                SELECT author_id FROM league_announcements
                WHERE id = ? AND league_id = ?
            ''', (announcement_id, league_id))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False, 'Announcement not found'
            
            author_id = result[0]
            
            # Check if user is author, admin, or owner
            cursor.execute('''
                SELECT role FROM league_members
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, user_id))
            
            role_result = cursor.fetchone()
            if not role_result and user_id != author_id:
                conn.close()
                return False, 'Permission denied'
            
            if role_result and role_result[0] not in ['admin', 'owner'] and user_id != author_id:
                conn.close()
                return False, 'Permission denied'
            
            # Update announcement
            now = datetime.now().isoformat()
            cursor.execute('''
                UPDATE league_announcements
                SET title = ?, content = ?, updated_at = ?
                WHERE id = ? AND league_id = ?
            ''', (title, content, now, announcement_id, league_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Announcement {announcement_id} updated by user {user_id}")
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error updating announcement: {e}")
            return False, str(e)
    
    def delete_announcement(self, league_id: int, announcement_id: int,
                           user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Delete an announcement
        
        Returns:
            (success, error_message)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Verify user has permission
            cursor.execute('''
                SELECT author_id FROM league_announcements
                WHERE id = ? AND league_id = ?
            ''', (announcement_id, league_id))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False, 'Announcement not found'
            
            author_id = result[0]
            
            # Check permissions
            cursor.execute('''
                SELECT role FROM league_members
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, user_id))
            
            role_result = cursor.fetchone()
            is_admin = role_result and role_result[0] in ['admin', 'owner']
            is_author = user_id == author_id
            
            if not (is_admin or is_author):
                conn.close()
                return False, 'Permission denied'
            
            # Delete announcement
            cursor.execute('''
                DELETE FROM league_announcements
                WHERE id = ? AND league_id = ?
            ''', (announcement_id, league_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Announcement {announcement_id} deleted by user {user_id}")
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error deleting announcement: {e}")
            return False, str(e)
    
    def get_league_announcements(self, league_id: int, 
                                limit: int = 50, 
                                offset: int = 0) -> Tuple[bool, List[Dict], Optional[str]]:
        """
        Get announcements for a league
        
        Returns:
            (success, announcements_list, error_message)
        """
        try:
            limit = min(limit, 100)
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get pinned announcements first, then recent ones
            cursor.execute('''
                SELECT id, title, content, author_id, username, pinned, created_at, updated_at
                FROM league_announcements
                WHERE league_id = ?
                ORDER BY pinned DESC, created_at DESC
                LIMIT ? OFFSET ?
            ''', (league_id, limit, offset))
            
            announcements = []
            for row in cursor.fetchall():
                announcements.append({
                    'id': row[0],
                    'title': row[1],
                    'content': row[2],
                    'author_id': row[3],
                    'author': row[4],
                    'pinned': bool(row[5]),
                    'created_at': row[6],
                    'updated_at': row[7],
                    'timeago': self._format_timeago(row[6]),
                })
            
            conn.close()
            
            self.logger.debug(f"Retrieved {len(announcements)} announcements for league {league_id}")
            return True, announcements, None
            
        except Exception as e:
            self.logger.error(f"Error getting announcements: {e}")
            return False, [], str(e)
    
    def pin_announcement(self, league_id: int, announcement_id: int,
                        user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Pin an announcement (admin only)
        
        Returns:
            (success, error_message)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check admin permission
            cursor.execute('''
                SELECT role FROM league_members
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, user_id))
            
            result = cursor.fetchone()
            if not result or result[0] not in ['admin', 'owner']:
                conn.close()
                return False, 'Only admins can pin announcements'
            
            # Pin announcement
            cursor.execute('''
                UPDATE league_announcements
                SET pinned = 1
                WHERE id = ? AND league_id = ?
            ''', (announcement_id, league_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Announcement {announcement_id} pinned by user {user_id}")
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error pinning announcement: {e}")
            return False, str(e)
    
    def unpin_announcement(self, league_id: int, announcement_id: int,
                          user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Unpin an announcement (admin only)
        
        Returns:
            (success, error_message)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check admin permission
            cursor.execute('''
                SELECT role FROM league_members
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, user_id))
            
            result = cursor.fetchone()
            if not result or result[0] not in ['admin', 'owner']:
                conn.close()
                return False, 'Only admins can unpin announcements'
            
            # Unpin announcement
            cursor.execute('''
                UPDATE league_announcements
                SET pinned = 0
                WHERE id = ? AND league_id = ?
            ''', (announcement_id, league_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Announcement {announcement_id} unpinned by user {user_id}")
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error unpinning announcement: {e}")
            return False, str(e)
    
    def log_system_event(self, league_id: int, event_type: str, 
                        description: str, 
                        user_id: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """
        Log a system event for a league
        
        Event types: member_joined, member_left, season_started, season_ended, 
                     achievement_unlocked, milestone_reached, etc.
        
        Returns:
            (success, error_message)
        """
        try:
            if not event_type or not description:
                return False, 'Event type and description required'
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO league_system_events
                (league_id, event_type, description, user_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (league_id, event_type, description, user_id, now))
            
            conn.commit()
            event_id = cursor.lastrowid
            conn.close()
            
            self.logger.info(f"System event {event_id} logged for league {league_id}: {event_type}")
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error logging system event: {e}")
            return False, str(e)
    
    def get_system_events(self, league_id: int, 
                         limit: int = 50, 
                         offset: int = 0) -> Tuple[bool, List[Dict], Optional[str]]:
        """
        Get system events for a league
        
        Returns:
            (success, events_list, error_message)
        """
        try:
            limit = min(limit, 100)
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, event_type, description, user_id, created_at
                FROM league_system_events
                WHERE league_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (league_id, limit, offset))
            
            events = []
            for row in cursor.fetchall():
                events.append({
                    'id': row[0],
                    'event_type': row[1],
                    'description': row[2],
                    'user_id': row[3],
                    'created_at': row[4],
                    'timeago': self._format_timeago(row[4]),
                })
            
            conn.close()
            
            return True, events, None
            
        except Exception as e:
            self.logger.error(f"Error getting system events: {e}")
            return False, [], str(e)
    
    def get_announcement_stats(self, league_id: int) -> Tuple[bool, Dict, Optional[str]]:
        """
        Get statistics about league announcements
        
        Returns:
            (success, stats_dict, error_message)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get total and pinned count
            cursor.execute('''
                SELECT COUNT(*), SUM(CASE WHEN pinned = 1 THEN 1 ELSE 0 END)
                FROM league_announcements
                WHERE league_id = ?
            ''', (league_id,))
            
            total, pinned = cursor.fetchone()
            total = total or 0
            pinned = pinned or 0
            
            # Get most recent announcement
            cursor.execute('''
                SELECT created_at FROM league_announcements
                WHERE league_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (league_id,))
            
            recent_result = cursor.fetchone()
            last_announcement = recent_result[0] if recent_result else None
            
            # Get announcements by author
            cursor.execute('''
                SELECT author_id, username, COUNT(*) as count
                FROM league_announcements
                WHERE league_id = ?
                GROUP BY author_id
                ORDER BY count DESC
                LIMIT 5
            ''', (league_id,))
            
            top_authors = []
            for row in cursor.fetchall():
                top_authors.append({
                    'user_id': row[0],
                    'username': row[1],
                    'announcements': row[2],
                })
            
            conn.close()
            
            stats = {
                'total_announcements': total,
                'pinned_announcements': pinned,
                'last_announcement': last_announcement,
                'top_authors': top_authors,
            }
            
            self.logger.debug(f"Retrieved announcement stats for league {league_id}")
            return True, stats, None
            
        except Exception as e:
            self.logger.error(f"Error getting announcement stats: {e}")
            return False, {}, str(e)
    
    @staticmethod
    def _format_timeago(timestamp_str: str) -> str:
        """Format timestamp as 'time ago' string"""
        try:
            from datetime import datetime
            timestamp = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            delta = now - timestamp
            
            if delta.total_seconds() < 60:
                return 'just now'
            elif delta.total_seconds() < 3600:
                minutes = int(delta.total_seconds() / 60)
                return f'{minutes}m ago'
            elif delta.total_seconds() < 86400:
                hours = int(delta.total_seconds() / 3600)
                return f'{hours}h ago'
            elif delta.total_seconds() < 604800:
                days = int(delta.total_seconds() / 86400)
                return f'{days}d ago'
            else:
                return timestamp.strftime('%m/%d/%Y')
        except:
            return 'unknown'


if __name__ == '__main__':
    announcements_service = LeagueAnnouncements()
    print("League Announcements service loaded")
