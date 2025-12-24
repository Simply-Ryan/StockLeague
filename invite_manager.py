"""
Item #9: Invite Code Expiration System
Time-limited invite codes with single/multi-use support
"""

import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class InviteCodeManager:
    """Manages time-limited invite codes for leagues"""
    
    # Default expiration times (in days)
    DEFAULT_EXPIRATION_DAYS = 7
    MIN_EXPIRATION_DAYS = 1
    MAX_EXPIRATION_DAYS = 365
    
    # Code generation
    CODE_LENGTH = 8
    CODE_CHARSET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    
    def __init__(self, db):
        """Initialize invite code manager"""
        self.db = db
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Create invite code tables if they don't exist"""
        cursor = self.db.get_connection().cursor()
        
        # Main invite codes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invite_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                league_id INTEGER NOT NULL,
                created_by INTEGER NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_single_use INTEGER DEFAULT 0,
                max_uses INTEGER,
                current_uses INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                metadata TEXT,
                FOREIGN KEY (league_id) REFERENCES leagues (id),
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # Track who used each invite
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invite_code_uses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                FOREIGN KEY (code_id) REFERENCES invite_codes (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Invite code analytics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invite_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                total_codes INTEGER DEFAULT 0,
                active_codes INTEGER DEFAULT 0,
                expired_codes INTEGER DEFAULT 0,
                total_uses INTEGER DEFAULT 0,
                last_used_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(league_id),
                FOREIGN KEY (league_id) REFERENCES leagues (id)
            )
        ''')
        
        # Create indices for performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_invite_code 
            ON invite_codes (code)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_invite_league 
            ON invite_codes (league_id, is_active)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_invite_expires 
            ON invite_codes (expires_at)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_invite_uses_code 
            ON invite_code_uses (code_id)
        ''')
        
        self.db.get_connection().commit()
        logger.debug("Invite code tables verified/created")
    
    def generate_code(self) -> str:
        """
        Generate a unique invite code
        
        Returns:
            Generated code (e.g., "INVITE123")
        """
        while True:
            code = ''.join(secrets.choice(self.CODE_CHARSET) for _ in range(self.CODE_LENGTH))
            
            # Check uniqueness
            cursor = self.db.get_connection().cursor()
            cursor.execute('SELECT id FROM invite_codes WHERE code = ?', (code,))
            
            if not cursor.fetchone():
                return code
    
    def create_invite_code(self,
                          league_id: int,
                          created_by: int,
                          expiration_days: int = DEFAULT_EXPIRATION_DAYS,
                          is_single_use: bool = False,
                          max_uses: Optional[int] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, str]:
        """
        Create a new invite code
        
        Args:
            league_id: League to invite to
            created_by: User creating the code
            expiration_days: Days until code expires (1-365, default 7)
            is_single_use: Single-use code (overrides max_uses)
            max_uses: Max number of times code can be used
            metadata: Additional metadata (tags, notes, etc.)
            
        Returns:
            (success, code_or_error, message)
        """
        try:
            # Validate expiration
            if not (self.MIN_EXPIRATION_DAYS <= expiration_days <= self.MAX_EXPIRATION_DAYS):
                return False, '', f'Expiration must be between {self.MIN_EXPIRATION_DAYS} and {self.MAX_EXPIRATION_DAYS} days'
            
            # Validate league exists
            league = self.db.get_league(league_id)
            if not league:
                return False, '', 'League not found'
            
            # Validate user is admin
            cursor = self.db.get_connection().cursor()
            cursor.execute('''
                SELECT is_admin FROM league_members 
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, created_by))
            
            member = cursor.fetchone()
            if not member or not member['is_admin']:
                return False, '', 'Only league admins can create invite codes'
            
            # Generate code
            code = self.generate_code()
            
            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(days=expiration_days)
            
            # Single-use overrides max_uses
            if is_single_use:
                max_uses = 1
            
            # Store metadata
            metadata_json = json.dumps(metadata) if metadata else None
            
            # Insert code
            cursor.execute('''
                INSERT INTO invite_codes
                (code, league_id, created_by, expires_at, is_single_use, max_uses, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (code, league_id, created_by, expires_at, 1 if is_single_use else 0, max_uses, metadata_json))
            
            self.db.get_connection().commit()
            
            # Update analytics
            self._update_analytics(league_id)
            
            logger.info(f"Created invite code {code} for league {league_id}")
            return True, code, f'Invite code created: {code}'
            
        except Exception as e:
            logger.error(f"Failed to create invite code: {str(e)}")
            return False, '', f'Error creating code: {str(e)}'
    
    def validate_code(self, code: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Validate an invite code
        
        Args:
            code: Code to validate
            
        Returns:
            (is_valid, code_info, error_message)
        """
        try:
            cursor = self.db.get_connection().cursor()
            cursor.execute('''
                SELECT * FROM invite_codes WHERE code = ?
            ''', (code,))
            
            code_info = cursor.fetchone()
            
            # Code exists?
            if not code_info:
                return False, None, 'Invalid invite code'
            
            # Code active?
            if not code_info['is_active']:
                return False, None, 'This invite code has been deactivated'
            
            # Code expired?
            if datetime.fromisoformat(code_info['expires_at']) < datetime.utcnow():
                return False, None, 'This invite code has expired'
            
            # Max uses reached?
            if code_info['max_uses'] and code_info['current_uses'] >= code_info['max_uses']:
                return False, None, 'This invite code has reached its usage limit'
            
            # All checks passed
            return True, dict(code_info), 'Code is valid'
            
        except Exception as e:
            logger.error(f"Failed to validate code {code}: {str(e)}")
            return False, None, f'Error validating code: {str(e)}'
    
    def use_code(self, code: str, user_id: int, ip_address: Optional[str] = None) -> Tuple[bool, int, str]:
        """
        Use an invite code to join a league
        
        Args:
            code: Invite code
            user_id: User using the code
            ip_address: IP address for tracking
            
        Returns:
            (success, league_id, message)
        """
        try:
            # Validate code
            is_valid, code_info, error_msg = self.validate_code(code)
            if not is_valid:
                return False, 0, error_msg
            
            league_id = code_info['league_id']
            code_id = code_info['id']
            
            cursor = self.db.get_connection().cursor()
            
            # Check if user already in league
            cursor.execute('''
                SELECT id FROM league_members
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, user_id))
            
            if cursor.fetchone():
                return False, league_id, 'You are already a member of this league'
            
            # Add user to league
            cursor.execute('''
                INSERT INTO league_members (league_id, user_id, joined_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (league_id, user_id))
            
            # Record code usage
            cursor.execute('''
                INSERT INTO invite_code_uses (code_id, user_id, ip_address)
                VALUES (?, ?, ?)
            ''', (code_id, user_id, ip_address))
            
            # Update use count
            current_uses = code_info['current_uses'] + 1
            cursor.execute('''
                UPDATE invite_codes
                SET current_uses = ?
                WHERE id = ?
            ''', (current_uses, code_id))
            
            # Deactivate if single-use
            if code_info['is_single_use']:
                cursor.execute('''
                    UPDATE invite_codes
                    SET is_active = 0
                    WHERE id = ?
                ''', (code_id,))
            
            self.db.get_connection().commit()
            
            # Update analytics
            self._update_analytics(league_id)
            
            logger.info(f"User {user_id} used code {code} to join league {league_id}")
            return True, league_id, 'Successfully joined the league'
            
        except Exception as e:
            logger.error(f"Failed to use code: {str(e)}")
            return False, 0, f'Error: {str(e)}'
    
    def get_league_codes(self, league_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all invite codes for a league
        
        Args:
            league_id: League ID
            active_only: Only return active codes
            
        Returns:
            List of code info dicts
        """
        cursor = self.db.get_connection().cursor()
        
        query = 'SELECT * FROM invite_codes WHERE league_id = ?'
        params = [league_id]
        
        if active_only:
            query += ' AND is_active = 1 AND expires_at > CURRENT_TIMESTAMP'
        
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, params)
        
        codes = cursor.fetchall()
        result = []
        
        for code in codes:
            code_dict = dict(code)
            
            # Parse metadata
            if code_dict.get('metadata'):
                try:
                    code_dict['metadata'] = json.loads(code_dict['metadata'])
                except:
                    pass
            
            # Calculate days remaining
            expires_at = datetime.fromisoformat(code_dict['expires_at'])
            days_left = (expires_at - datetime.utcnow()).days
            code_dict['days_remaining'] = max(0, days_left)
            code_dict['is_expired'] = days_left < 0
            
            # Calculate usage percentage
            if code_dict['max_uses']:
                code_dict['usage_percentage'] = int((code_dict['current_uses'] / code_dict['max_uses']) * 100)
            else:
                code_dict['usage_percentage'] = 0
            
            result.append(code_dict)
        
        return result
    
    def deactivate_code(self, code: str, league_id: int, admin_id: int) -> Tuple[bool, str]:
        """
        Deactivate an invite code
        
        Args:
            code: Code to deactivate
            league_id: League that owns the code
            admin_id: Admin performing action
            
        Returns:
            (success, message)
        """
        try:
            # Verify admin
            cursor = self.db.get_connection().cursor()
            cursor.execute('''
                SELECT is_admin FROM league_members
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, admin_id))
            
            member = cursor.fetchone()
            if not member or not member['is_admin']:
                return False, 'Only league admins can deactivate codes'
            
            # Find and deactivate code
            cursor.execute('''
                UPDATE invite_codes
                SET is_active = 0
                WHERE code = ? AND league_id = ?
            ''', (code, league_id))
            
            if cursor.rowcount == 0:
                return False, 'Code not found'
            
            self.db.get_connection().commit()
            self._update_analytics(league_id)
            
            logger.info(f"Code {code} deactivated by admin {admin_id}")
            return True, f'Code {code} has been deactivated'
            
        except Exception as e:
            logger.error(f"Failed to deactivate code: {str(e)}")
            return False, f'Error: {str(e)}'
    
    def get_code_users(self, code: str) -> List[Dict[str, Any]]:
        """
        Get list of users who used a code
        
        Args:
            code: Invite code
            
        Returns:
            List of users who used the code
        """
        cursor = self.db.get_connection().cursor()
        
        cursor.execute('''
            SELECT u.id, u.username, u.email, icu.used_at, icu.ip_address
            FROM invite_code_uses icu
            JOIN users u ON icu.user_id = u.id
            JOIN invite_codes ic ON icu.code_id = ic.id
            WHERE ic.code = ?
            ORDER BY icu.used_at DESC
        ''', (code,))
        
        users = cursor.fetchall()
        return [dict(user) for user in users]
    
    def cleanup_expired_codes(self, dry_run: bool = True) -> int:
        """
        Deactivate expired invite codes
        
        Args:
            dry_run: If True, only count, don't delete
            
        Returns:
            Number of codes cleaned up
        """
        cursor = self.db.get_connection().cursor()
        
        # Find expired codes
        cursor.execute('''
            SELECT COUNT(*) as count FROM invite_codes
            WHERE is_active = 1 AND expires_at < CURRENT_TIMESTAMP
        ''')
        
        count = cursor.fetchone()['count']
        
        if not dry_run and count > 0:
            cursor.execute('''
                UPDATE invite_codes
                SET is_active = 0
                WHERE expires_at < CURRENT_TIMESTAMP
            ''')
            self.db.get_connection().commit()
            logger.info(f"Cleaned up {count} expired invite codes")
        
        return count
    
    def _update_analytics(self, league_id: int):
        """Update league invite analytics"""
        cursor = self.db.get_connection().cursor()
        
        # Get current stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_active = 1 AND expires_at > CURRENT_TIMESTAMP THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN is_active = 0 OR expires_at <= CURRENT_TIMESTAMP THEN 1 ELSE 0 END) as expired,
                SUM(current_uses) as total_uses,
                MAX(CASE WHEN is_active = 1 THEN (SELECT MAX(used_at) FROM invite_code_uses WHERE code_id = invite_codes.id) END) as last_used
            FROM invite_codes
            WHERE league_id = ?
        ''', (league_id,))
        
        stats = cursor.fetchone()
        
        # Update or insert analytics
        cursor.execute('''
            INSERT INTO invite_analytics 
            (league_id, total_codes, active_codes, expired_codes, total_uses, last_used_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(league_id) 
            DO UPDATE SET 
                total_codes = excluded.total_codes,
                active_codes = excluded.active_codes,
                expired_codes = excluded.expired_codes,
                total_uses = excluded.total_uses,
                last_used_at = excluded.last_used_at,
                updated_at = CURRENT_TIMESTAMP
        ''', (
            league_id,
            stats['total'] or 0,
            stats['active'] or 0,
            stats['expired'] or 0,
            stats['total_uses'] or 0,
            stats['last_used'] if stats['last_used'] else None
        ))
        
        self.db.get_connection().commit()
    
    def get_analytics(self, league_id: int) -> Optional[Dict[str, Any]]:
        """Get invite analytics for a league"""
        cursor = self.db.get_connection().cursor()
        cursor.execute('SELECT * FROM invite_analytics WHERE league_id = ?', (league_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def resend_code_email(self, code: str, user_email: str) -> Tuple[bool, str]:
        """
        Prepare email data for resending an invite code
        
        Args:
            code: Code to resend
            user_email: Email to send to
            
        Returns:
            (success, message)
        """
        # Validate code exists and is active
        is_valid, code_info, msg = self.validate_code(code)
        if not is_valid:
            return False, 'Cannot resend expired or invalid code'
        
        # In real app, would send email here
        logger.info(f"Resend requested for code {code} to {user_email}")
        
        return True, f'Invite code {code} would be sent to {user_email}'
