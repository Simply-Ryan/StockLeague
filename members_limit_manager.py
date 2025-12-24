"""
Item #10: Max Members Limit Enforcement System
Enforces maximum member limits per league with configurable limits
"""

from typing import Tuple, Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class MembersLimitManager:
    """Manages member limits and enforcement"""
    
    # Default limits
    DEFAULT_MAX_MEMBERS = 100
    MIN_MAX_MEMBERS = 2
    MAX_MAX_MEMBERS = 1000
    
    # Limit tiers for different league types
    LIMIT_TIERS = {
        'public': {'default': 50, 'min': 2, 'max': 500},
        'private': {'default': 20, 'min': 2, 'max': 100},
        'exclusive': {'default': 10, 'min': 2, 'max': 50}
    }
    
    def __init__(self, db):
        """Initialize members limit manager"""
        self.db = db
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Create members limit tables if they don't exist"""
        cursor = self.db.get_connection().cursor()
        
        # League member limits table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS league_member_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER UNIQUE NOT NULL,
                max_members INTEGER NOT NULL,
                current_members INTEGER DEFAULT 0,
                is_enforced INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues (id)
            )
        ''')
        
        # Waitlist for when league is full
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS member_waitlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'waiting',
                position INTEGER,
                UNIQUE(league_id, user_id),
                FOREIGN KEY (league_id) REFERENCES leagues (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Member limits history (for audit)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS member_limits_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                changed_by INTEGER,
                old_limit INTEGER,
                new_limit INTEGER,
                reason TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues (id),
                FOREIGN KEY (changed_by) REFERENCES users (id)
            )
        ''')
        
        # Create indices
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_limit_league 
            ON league_member_limits (league_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_waitlist_league 
            ON member_waitlist (league_id, requested_at)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_waitlist_user 
            ON member_waitlist (user_id)
        ''')
        
        self.db.get_connection().commit()
        logger.debug("Member limits tables verified/created")
    
    def initialize_league_limit(self, league_id: int, league_type: str = 'public') -> Tuple[bool, str]:
        """
        Initialize member limit for a league
        
        Args:
            league_id: League ID
            league_type: League type (public, private, exclusive)
            
        Returns:
            (success, message)
        """
        try:
            # Get default limit for league type
            tier = self.LIMIT_TIERS.get(league_type, self.LIMIT_TIERS['public'])
            max_members = tier['default']
            
            cursor = self.db.get_connection().cursor()
            
            # Check if already initialized
            cursor.execute('''
                SELECT id FROM league_member_limits WHERE league_id = ?
            ''', (league_id,))
            
            if cursor.fetchone():
                return False, 'League limit already initialized'
            
            # Get current member count
            cursor.execute('''
                SELECT COUNT(*) as count FROM league_members WHERE league_id = ?
            ''', (league_id,))
            
            current_count = cursor.fetchone()['count']
            
            # Initialize limit
            cursor.execute('''
                INSERT INTO league_member_limits 
                (league_id, max_members, current_members)
                VALUES (?, ?, ?)
            ''', (league_id, max_members, current_count))
            
            self.db.get_connection().commit()
            logger.info(f"Initialized member limit for league {league_id}: {max_members}")
            return True, f'Member limit set to {max_members}'
            
        except Exception as e:
            logger.error(f"Failed to initialize limit: {str(e)}")
            return False, str(e)
    
    def get_league_limit(self, league_id: int) -> Optional[Dict[str, Any]]:
        """
        Get member limit info for a league
        
        Args:
            league_id: League ID
            
        Returns:
            Limit info dict or None
        """
        cursor = self.db.get_connection().cursor()
        cursor.execute('''
            SELECT * FROM league_member_limits WHERE league_id = ?
        ''', (league_id,))
        
        row = cursor.fetchone()
        if row:
            row_dict = dict(row)
            row_dict['members_remaining'] = row_dict['max_members'] - row_dict['current_members']
            row_dict['is_full'] = row_dict['members_remaining'] <= 0
            row_dict['capacity_percentage'] = int((row_dict['current_members'] / row_dict['max_members']) * 100)
            return row_dict
        
        return None
    
    def set_member_limit(self, 
                        league_id: int,
                        max_members: int,
                        admin_id: int,
                        reason: Optional[str] = None) -> Tuple[bool, str]:
        """
        Set/update member limit for a league
        
        Args:
            league_id: League ID
            max_members: New max members
            admin_id: Admin making change
            reason: Reason for change
            
        Returns:
            (success, message)
        """
        try:
            # Validate limit
            if not (self.MIN_MAX_MEMBERS <= max_members <= self.MAX_MAX_MEMBERS):
                return False, f'Limit must be between {self.MIN_MAX_MEMBERS} and {self.MAX_MAX_MEMBERS}'
            
            # Verify admin
            cursor = self.db.get_connection().cursor()
            cursor.execute('''
                SELECT is_admin FROM league_members
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, admin_id))
            
            member = cursor.fetchone()
            if not member or not member['is_admin']:
                return False, 'Only league admins can change member limits'
            
            # Get current limit
            current_limit = self.get_league_limit(league_id)
            if not current_limit:
                return False, 'League limit not initialized'
            
            old_limit = current_limit['max_members']
            
            # Check if new limit is below current member count
            if max_members < current_limit['current_members']:
                return False, f'Cannot set limit below current member count ({current_limit["current_members"]})'
            
            # Update limit
            cursor.execute('''
                UPDATE league_member_limits
                SET max_members = ?, updated_at = CURRENT_TIMESTAMP
                WHERE league_id = ?
            ''', (max_members, league_id))
            
            # Log change
            cursor.execute('''
                INSERT INTO member_limits_history
                (league_id, changed_by, old_limit, new_limit, reason)
                VALUES (?, ?, ?, ?, ?)
            ''', (league_id, admin_id, old_limit, max_members, reason))
            
            self.db.get_connection().commit()
            
            logger.info(f"Updated member limit for league {league_id}: {old_limit} -> {max_members}")
            return True, f'Member limit updated from {old_limit} to {max_members}'
            
        except Exception as e:
            logger.error(f"Failed to set limit: {str(e)}")
            return False, str(e)
    
    def can_add_member(self, league_id: int) -> Tuple[bool, str]:
        """
        Check if a member can be added to a league
        
        Args:
            league_id: League ID
            
        Returns:
            (can_add, message)
        """
        try:
            limit = self.get_league_limit(league_id)
            
            if not limit:
                return True, 'No limit set'
            
            if not limit['is_enforced']:
                return True, 'Limit not enforced'
            
            if limit['is_full']:
                return False, f'League is full ({limit["current_members"]}/{limit["max_members"]} members)'
            
            return True, 'Can add member'
            
        except Exception as e:
            logger.error(f"Error checking member limit: {str(e)}")
            return True, 'Error checking limit, allowing member addition'
    
    def add_member(self, league_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Add a member to league (with limit enforcement)
        
        Args:
            league_id: League ID
            user_id: User ID
            
        Returns:
            (success, message)
        """
        try:
            # Check if can add
            can_add, check_msg = self.can_add_member(league_id)
            
            if not can_add:
                # Add to waitlist instead
                return self._add_to_waitlist(league_id, user_id, check_msg)
            
            cursor = self.db.get_connection().cursor()
            
            # Add member
            cursor.execute('''
                INSERT INTO league_members (league_id, user_id, joined_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (league_id, user_id))
            
            # Update current count
            cursor.execute('''
                UPDATE league_member_limits
                SET current_members = current_members + 1
                WHERE league_id = ?
            ''', (league_id,))
            
            # Remove from waitlist if exists
            cursor.execute('''
                DELETE FROM member_waitlist
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, user_id))
            
            self.db.get_connection().commit()
            
            logger.info(f"Added user {user_id} to league {league_id}")
            return True, 'Successfully added to league'
            
        except Exception as e:
            logger.error(f"Failed to add member: {str(e)}")
            return False, str(e)
    
    def remove_member(self, league_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Remove a member from league
        
        Args:
            league_id: League ID
            user_id: User ID
            
        Returns:
            (success, message)
        """
        try:
            cursor = self.db.get_connection().cursor()
            
            # Remove member
            cursor.execute('''
                DELETE FROM league_members
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, user_id))
            
            if cursor.rowcount == 0:
                return False, 'Member not found'
            
            # Update current count
            cursor.execute('''
                UPDATE league_member_limits
                SET current_members = current_members - 1
                WHERE league_id = ?
            ''', (league_id,))
            
            self.db.get_connection().commit()
            
            # Check waitlist for pending members
            self._process_waitlist(league_id)
            
            logger.info(f"Removed user {user_id} from league {league_id}")
            return True, 'Member removed successfully'
            
        except Exception as e:
            logger.error(f"Failed to remove member: {str(e)}")
            return False, str(e)
    
    def _add_to_waitlist(self, league_id: int, user_id: int, reason: str) -> Tuple[bool, str]:
        """Add user to waitlist when league is full"""
        try:
            cursor = self.db.get_connection().cursor()
            
            # Get position in waitlist
            cursor.execute('''
                SELECT COUNT(*) + 1 as position FROM member_waitlist
                WHERE league_id = ?
            ''', (league_id,))
            
            position = cursor.fetchone()['position']
            
            # Add to waitlist
            cursor.execute('''
                INSERT INTO member_waitlist (league_id, user_id, position)
                VALUES (?, ?, ?)
            ''', (league_id, user_id, position))
            
            self.db.get_connection().commit()
            
            logger.info(f"Added user {user_id} to waitlist for league {league_id} (position {position})")
            return False, f'League is full. You have been added to the waitlist (position {position})'
            
        except Exception as e:
            logger.error(f"Failed to add to waitlist: {str(e)}")
            return False, 'League is full and could not add to waitlist'
    
    def _process_waitlist(self, league_id: int) -> int:
        """
        Process waitlist when space becomes available
        
        Args:
            league_id: League ID
            
        Returns:
            Number of members added from waitlist
        """
        try:
            cursor = self.db.get_connection().cursor()
            added = 0
            
            # Get current limit
            limit = self.get_league_limit(league_id)
            if not limit or limit['is_full']:
                return 0
            
            # Get waitlist members
            cursor.execute('''
                SELECT * FROM member_waitlist
                WHERE league_id = ? AND status = 'waiting'
                ORDER BY requested_at ASC
            ''', (league_id,))
            
            waitlist = cursor.fetchall()
            
            for entry in waitlist:
                # Check space
                limit = self.get_league_limit(league_id)
                if not limit or limit['is_full']:
                    break
                
                user_id = entry['user_id']
                
                # Add member
                cursor.execute('''
                    INSERT INTO league_members (league_id, user_id, joined_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (league_id, user_id))
                
                # Update limit
                cursor.execute('''
                    UPDATE league_member_limits
                    SET current_members = current_members + 1
                    WHERE league_id = ?
                ''', (league_id,))
                
                # Update waitlist status
                cursor.execute('''
                    UPDATE member_waitlist
                    SET status = 'accepted'
                    WHERE id = ?
                ''', (entry['id'],))
                
                added += 1
                logger.info(f"Promoted user {user_id} from waitlist for league {league_id}")
            
            self.db.get_connection().commit()
            return added
            
        except Exception as e:
            logger.error(f"Error processing waitlist: {str(e)}")
            return 0
    
    def get_waitlist(self, league_id: int) -> List[Dict[str, Any]]:
        """Get waitlist for a league"""
        cursor = self.db.get_connection().cursor()
        cursor.execute('''
            SELECT mw.*, u.username, u.email
            FROM member_waitlist mw
            JOIN users u ON mw.user_id = u.id
            WHERE mw.league_id = ? AND mw.status = 'waiting'
            ORDER BY mw.requested_at ASC
        ''', (league_id,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def remove_from_waitlist(self, league_id: int, user_id: int) -> Tuple[bool, str]:
        """Remove user from waitlist"""
        try:
            cursor = self.db.get_connection().cursor()
            
            cursor.execute('''
                DELETE FROM member_waitlist
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, user_id))
            
            if cursor.rowcount == 0:
                return False, 'User not on waitlist'
            
            self.db.get_connection().commit()
            return True, 'Removed from waitlist'
            
        except Exception as e:
            logger.error(f"Failed to remove from waitlist: {str(e)}")
            return False, str(e)
    
    def get_member_count(self, league_id: int) -> int:
        """Get current member count for a league"""
        cursor = self.db.get_connection().cursor()
        cursor.execute('''
            SELECT COUNT(*) as count FROM league_members WHERE league_id = ?
        ''', (league_id,))
        
        return cursor.fetchone()['count']
    
    def enforce_limit(self, league_id: int, enforce: bool) -> Tuple[bool, str]:
        """Enable or disable limit enforcement"""
        try:
            cursor = self.db.get_connection().cursor()
            
            cursor.execute('''
                UPDATE league_member_limits
                SET is_enforced = ?
                WHERE league_id = ?
            ''', (1 if enforce else 0, league_id))
            
            self.db.get_connection().commit()
            
            status = 'enabled' if enforce else 'disabled'
            logger.info(f"Member limit enforcement {status} for league {league_id}")
            return True, f'Limit enforcement {status}'
            
        except Exception as e:
            logger.error(f"Failed to toggle enforcement: {str(e)}")
            return False, str(e)
    
    def get_limit_history(self, league_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get history of limit changes for a league"""
        cursor = self.db.get_connection().cursor()
        cursor.execute('''
            SELECT * FROM member_limits_history
            WHERE league_id = ?
            ORDER BY changed_at DESC
            LIMIT ?
        ''', (league_id, limit))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
