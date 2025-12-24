"""
Soft Deletes Management for StockLeague
Handles league archiving, restoration, and archive management
"""

import logging
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class LeagueArchiveManager:
    """Manages league archiving and restoration with soft deletes."""
    
    def __init__(self, db):
        """
        Initialize archive manager.
        
        Args:
            db: DatabaseManager instance
        """
        self.db = db
    
    def archive_league(self, league_id, admin_id=None, reason=None):
        """Archive a league (soft delete).
        
        Args:
            league_id: ID of league to archive
            admin_id: ID of admin performing the action
            reason: Optional reason for archiving
            
        Returns:
            (success: bool, message: str)
        """
        try:
            # Verify league exists
            league = self.db.get_league(league_id, include_archived=True)
            if not league:
                return False, f"League {league_id} not found"
            
            # Check if already archived
            if league.get('soft_deleted_at'):
                return False, f"League {league_id} is already archived"
            
            # Archive the league
            if self.db.archive_league(league_id, admin_id):
                msg = f"League '{league['name']}' archived successfully"
                logger.info(f"{msg} by admin {admin_id}")
                
                # Log the action
                try:
                    self.db.log_audit_action(
                        admin_id,
                        'archive_league',
                        league_id,
                        f"League archived: {reason}" if reason else "League archived"
                    )
                except:
                    pass  # Audit logging is optional
                
                return True, msg
            else:
                return False, f"Failed to archive league {league_id}"
        
        except Exception as e:
            logger.error(f"Error archiving league {league_id}: {e}")
            return False, f"Error archiving league: {str(e)}"
    
    def restore_league(self, league_id, admin_id=None):
        """Restore an archived league.
        
        Args:
            league_id: ID of league to restore
            admin_id: ID of admin performing the action
            
        Returns:
            (success: bool, message: str)
        """
        try:
            # Verify league exists and is archived
            league = self.db.get_league(league_id, include_archived=True)
            if not league:
                return False, f"League {league_id} not found"
            
            if not league.get('soft_deleted_at'):
                return False, f"League {league_id} is not archived"
            
            # Restore the league
            if self.db.restore_league(league_id, admin_id):
                msg = f"League '{league['name']}' restored successfully"
                logger.info(f"{msg} by admin {admin_id}")
                
                # Log the action
                try:
                    self.db.log_audit_action(
                        admin_id,
                        'restore_league',
                        league_id,
                        "League restored"
                    )
                except:
                    pass
                
                return True, msg
            else:
                return False, f"Failed to restore league {league_id}"
        
        except Exception as e:
            logger.error(f"Error restoring league {league_id}: {e}")
            return False, f"Error restoring league: {str(e)}"
    
    def get_user_archived_leagues(self, user_id, admin_only=False):
        """Get archived leagues for a user.
        
        Args:
            user_id: User ID
            admin_only: Only return leagues where user is admin
            
        Returns:
            List of archived league dictionaries
        """
        try:
            leagues = self.db.get_archived_leagues(user_id, admin_only)
            return sorted(leagues, key=lambda x: x.get('soft_deleted_at', ''), reverse=True)
        except Exception as e:
            logger.error(f"Error getting archived leagues for user {user_id}: {e}")
            return []
    
    def get_archive_info(self, league_id):
        """Get information about an archived league.
        
        Args:
            league_id: ID of league
            
        Returns:
            Dictionary with archive information or None
        """
        try:
            league = self.db.get_league(league_id, include_archived=True)
            if not league:
                return None
            
            if not league.get('soft_deleted_at'):
                return None
            
            archived_at = league.get('soft_deleted_at')
            if isinstance(archived_at, str):
                archived_at = datetime.fromisoformat(archived_at)
            
            days_archived = (datetime.now() - archived_at).days
            
            return {
                'league_id': league_id,
                'league_name': league.get('name'),
                'archived_at': archived_at,
                'days_archived': days_archived,
                'member_count': len(self.db.get_league_members(league_id)) if league_id else 0,
                'is_creator': False  # Set by caller
            }
        
        except Exception as e:
            logger.error(f"Error getting archive info for league {league_id}: {e}")
            return None
    
    def permanently_delete_league(self, league_id, admin_id=None, confirm=False):
        """Permanently delete an archived league (irreversible).
        
        Args:
            league_id: ID of league to delete
            admin_id: ID of admin performing the action
            confirm: Must be True to actually delete
            
        Returns:
            (success: bool, message: str)
        """
        if not confirm:
            return False, "Confirmation required for permanent deletion"
        
        try:
            league = self.db.get_league(league_id, include_archived=True)
            if not league:
                return False, f"League {league_id} not found"
            
            if not league.get('soft_deleted_at'):
                return False, f"League {league_id} must be archived before permanent deletion"
            
            # Actually delete from database
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Delete related data
            cursor.execute("DELETE FROM league_members WHERE league_id = ?", (league_id,))
            cursor.execute("DELETE FROM league_portfolios WHERE league_id = ?", (league_id,))
            cursor.execute("DELETE FROM league_trades WHERE league_id = ?", (league_id,))
            cursor.execute("DELETE FROM league_activity WHERE league_id = ?", (league_id,))
            
            # Delete league
            cursor.execute("DELETE FROM leagues WHERE id = ?", (league_id,))
            
            conn.commit()
            conn.close()
            
            msg = f"League '{league['name']}' permanently deleted"
            logger.warning(f"{msg} by admin {admin_id}")
            
            # Log the action
            try:
                self.db.log_audit_action(
                    admin_id,
                    'permanently_delete_league',
                    league_id,
                    "League permanently deleted"
                )
            except:
                pass
            
            return True, msg
        
        except Exception as e:
            logger.error(f"Error permanently deleting league {league_id}: {e}")
            return False, f"Error deleting league: {str(e)}"
    
    def cleanup_old_archives(self, days=180, admin_id=None):
        """Permanently delete leagues archived over N days ago.
        
        Args:
            days: Number of days to keep archives (default: 180 days/6 months)
            admin_id: ID of admin performing the action
            
        Returns:
            (deleted_count: int, message: str)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Find leagues archived over N days ago
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute("""
                SELECT id, name FROM leagues
                WHERE soft_deleted_at IS NOT NULL
                AND soft_deleted_at < ?
            """, (cutoff_date,))
            
            old_leagues = cursor.fetchall()
            
            if not old_leagues:
                return 0, f"No archived leagues older than {days} days"
            
            # Delete each one
            deleted_count = 0
            for league_id, league_name in old_leagues:
                try:
                    # Delete related data
                    cursor.execute("DELETE FROM league_members WHERE league_id = ?", (league_id,))
                    cursor.execute("DELETE FROM league_portfolios WHERE league_id = ?", (league_id,))
                    cursor.execute("DELETE FROM league_trades WHERE league_id = ?", (league_id,))
                    cursor.execute("DELETE FROM league_activity WHERE league_id = ?", (league_id,))
                    
                    # Delete league
                    cursor.execute("DELETE FROM leagues WHERE id = ?", (league_id,))
                    
                    deleted_count += 1
                    logger.info(f"Permanently deleted archived league: {league_name}")
                except Exception as e:
                    logger.error(f"Error deleting league {league_id}: {e}")
            
            conn.commit()
            conn.close()
            
            msg = f"Cleaned up {deleted_count} archived leagues older than {days} days"
            logger.info(f"{msg} by admin {admin_id}")
            
            return deleted_count, msg
        
        except Exception as e:
            logger.error(f"Error cleaning up old archives: {e}")
            return 0, f"Error cleaning up archives: {str(e)}"
    
    def get_archive_statistics(self):
        """Get statistics about archived leagues.
        
        Returns:
            Dictionary with archive statistics
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Total archived leagues
            cursor.execute("SELECT COUNT(*) FROM leagues WHERE soft_deleted_at IS NOT NULL")
            total_archived = cursor.fetchone()[0]
            
            # Archives by age
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN soft_deleted_at >= date('now', '-7 days') THEN 1 ELSE 0 END) as week,
                    SUM(CASE WHEN soft_deleted_at >= date('now', '-30 days') THEN 1 ELSE 0 END) as month,
                    SUM(CASE WHEN soft_deleted_at >= date('now', '-90 days') THEN 1 ELSE 0 END) as quarter,
                    SUM(CASE WHEN soft_deleted_at >= date('now', '-180 days') THEN 1 ELSE 0 END) as half_year
                FROM leagues
                WHERE soft_deleted_at IS NOT NULL
            """)
            
            age_stats = cursor.fetchone()
            conn.close()
            
            return {
                'total_archived': total_archived,
                'archived_this_week': age_stats[0] or 0,
                'archived_this_month': age_stats[1] or 0,
                'archived_this_quarter': age_stats[2] or 0,
                'archived_this_half_year': age_stats[3] or 0
            }
        
        except Exception as e:
            logger.error(f"Error getting archive statistics: {e}")
            return {}
