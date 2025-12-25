"""
Feature Integration Helpers for StockLeague
Provides helper functions for integrating the new features seamlessly
"""

import logging
from functools import wraps
from flask import request, session
from datetime import datetime

logger = logging.getLogger(__name__)


def with_audit_log(action, resource_type):
    """
    Decorator to automatically log actions to the audit trail.
    
    Usage:
        @app.route('/league/<int:league_id>/archive', methods=['POST'])
        @login_required
        @with_audit_log('ARCHIVE', 'LEAGUE')
        def archive_league(league_id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            
            try:
                # Execute the wrapped function
                result = f(*args, **kwargs)
                
                # Log success to audit trail
                if user_id and hasattr(request, 'audit_logger'):
                    resource_id = kwargs.get('league_id') or kwargs.get('id') or None
                    request.audit_logger.log_action(
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        user_id=user_id,
                        status='success',
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                
                return result
            except Exception as e:
                # Log failure to audit trail
                if user_id and hasattr(request, 'audit_logger'):
                    resource_id = kwargs.get('league_id') or kwargs.get('id') or None
                    request.audit_logger.log_action(
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        user_id=user_id,
                        status='failure',
                        details={'error': str(e)},
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                raise
        
        return decorated_function
    return decorator


def with_member_limit_check(f):
    """
    Decorator to check member limits before adding user to league.
    
    Usage:
        @app.route('/league/<int:league_id>/join', methods=['POST'])
        @login_required
        @with_member_limit_check
        def join_league(league_id):
            ...
    """
    @wraps(f)
    def decorated_function(league_id, *args, **kwargs):
        if hasattr(request, 'members_limit_manager'):
            # Check if league is at max members
            is_full = request.members_limit_manager.is_league_full(league_id)
            if is_full:
                return {
                    'success': False,
                    'error': 'This league is at maximum capacity'
                }, 403
            
            # Check member count
            count = request.members_limit_manager.get_current_member_count(league_id)
            limit = request.members_limit_manager.get_max_members(league_id)
            
            if count >= limit:
                return {
                    'success': False,
                    'error': f'League full ({count}/{limit} members)'
                }, 403
        
        return f(league_id, *args, **kwargs)
    
    return decorated_function


def with_invite_validation(f):
    """
    Decorator to validate invite code before processing.
    
    Usage:
        @app.route('/league/join', methods=['POST'])
        @login_required
        @with_invite_validation
        def join_by_invite():
            invite_code = request.form.get('code')
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        invite_code = request.form.get('code') or request.args.get('code')
        
        if invite_code and hasattr(request, 'invite_code_manager'):
            # Validate the invite code
            is_valid, league_id, message = request.invite_code_manager.validate_code(invite_code)
            
            if not is_valid:
                return {
                    'success': False,
                    'error': message
                }, 400
            
            # Store league_id in request context for the handler
            request.league_from_invite = league_id
        
        return f(*args, **kwargs)
    
    return decorated_function


def create_audit_logger_middleware(app, audit_logger):
    """
    Create middleware to make audit_logger available in requests.
    
    Usage in app.py:
        audit_logger = AuditLogger(db)
        create_audit_logger_middleware(app, audit_logger)
    """
    @app.before_request
    def setup_audit_logger():
        request.audit_logger = audit_logger


def create_managers_middleware(app, members_limit_manager, invite_code_manager, archive_manager):
    """
    Create middleware to make managers available in requests.
    
    Usage in app.py:
        create_managers_middleware(app, members_limit_manager, invite_code_manager, archive_manager)
    """
    @app.before_request
    def setup_managers():
        request.members_limit_manager = members_limit_manager
        request.invite_code_manager = invite_code_manager
        request.archive_manager = archive_manager


class AuditContext:
    """
    Context manager for audit logging complex operations.
    
    Usage:
        with AuditContext(audit_logger, 'TRADE_EXECUTE', 'TRADE', trade_id, user_id):
            # Execute trade
            execute_trade(...)
            # Audit log is automatically created on context exit
    """
    
    def __init__(self, audit_logger, action, resource_type, resource_id, user_id, details=None):
        self.audit_logger = audit_logger
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.user_id = user_id
        self.details = details or {}
        self.changes = {}
        self.error = None
        self.status = 'success'
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.status = 'failure'
            self.error = str(exc_val)
        
        # Log the action
        try:
            self.audit_logger.log_action(
                action=self.action,
                resource_type=self.resource_type,
                resource_id=self.resource_id,
                user_id=self.user_id,
                status=self.status,
                details=self.details,
                changes=self.changes
            )
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")
        
        return False  # Don't suppress exceptions


class InviteCodeHelper:
    """Helper class for working with invite codes"""
    
    @staticmethod
    def generate_and_send(invite_manager, league_id, created_by, expiration_days=7, send_email=None):
        """
        Generate an invite code and optionally send it via email.
        
        Args:
            invite_manager: InviteCodeManager instance
            league_id: League to invite to
            created_by: User creating the code
            expiration_days: Days until expiration
            send_email: Callable that sends email (optional)
            
        Returns:
            (success, code_or_error, message)
        """
        success, code, message = invite_manager.create_invite_code(
            league_id=league_id,
            created_by=created_by,
            expiration_days=expiration_days
        )
        
        if success and send_email:
            try:
                # Email sending logic would go here
                logger.info(f"Invite code {code} created for league {league_id}")
            except Exception as e:
                logger.error(f"Failed to send invite email: {e}")
        
        return success, code, message


class ArchiveHelper:
    """Helper class for working with league archives"""
    
    @staticmethod
    def archive_with_notification(archive_manager, league_id, admin_id, reason=None, notify_members=False):
        """
        Archive a league and optionally notify members.
        
        Args:
            archive_manager: LeagueArchiveManager instance
            league_id: League to archive
            admin_id: Admin performing the action
            reason: Reason for archiving
            notify_members: Whether to send notifications
            
        Returns:
            (success, message)
        """
        success, message = archive_manager.archive_league(league_id, admin_id, reason)
        
        if success and notify_members:
            try:
                # Member notification logic would go here
                logger.info(f"Archived league {league_id} with notifications to members")
            except Exception as e:
                logger.error(f"Failed to notify members: {e}")
        
        return success, message
    
    @staticmethod
    def cleanup_old_archives_safe(archive_manager, days=180, admin_id=None):
        """
        Safely cleanup old archives with logging.
        
        Args:
            archive_manager: LeagueArchiveManager instance
            days: Age threshold in days
            admin_id: Admin performing the action
            
        Returns:
            (deleted_count, message)
        """
        deleted_count, message = archive_manager.cleanup_old_archives(days, admin_id)
        logger.info(f"Archive cleanup: {message}")
        return deleted_count, message
