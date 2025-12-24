"""
Item #8: Comprehensive Audit Logging System
Tracks all user actions with immutable audit trail for compliance
"""

import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional, Callable
import hashlib

logger = logging.getLogger(__name__)


class AuditLog:
    """Represents a single audit log entry"""
    
    def __init__(self, 
                 action: str,
                 resource_type: str,
                 resource_id: int,
                 user_id: int,
                 status: str = "success",
                 details: Optional[Dict[str, Any]] = None,
                 changes: Optional[Dict[str, Any]] = None,
                 ip_address: Optional[str] = None,
                 user_agent: Optional[str] = None):
        """
        Initialize audit log entry
        
        Args:
            action: Action performed (CREATE, READ, UPDATE, DELETE, ARCHIVE, RESTORE)
            resource_type: Type of resource (LEAGUE, MEMBER, TRADE, PORTFOLIO, etc.)
            resource_id: ID of affected resource
            user_id: User who performed action
            status: Operation status (success, failure, partial)
            details: Additional context data
            changes: Before/after values for modifications
            ip_address: Client IP address
            user_agent: Client user agent
        """
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.user_id = user_id
        self.status = status
        self.details = details or {}
        self.changes = changes or {}
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.timestamp = datetime.utcnow()
        self.checksum = self._generate_checksum()
    
    def _generate_checksum(self) -> str:
        """Generate immutable checksum for audit trail integrity"""
        data = f"{self.action}{self.resource_type}{self.resource_id}{self.user_id}{self.timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'user_id': self.user_id,
            'status': self.status,
            'details': json.dumps(self.details),
            'changes': json.dumps(self.changes),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp,
            'checksum': self.checksum
        }


class AuditLogger:
    """Main audit logging service"""
    
    # Action categories
    ACTIONS = {
        # League operations
        'LEAGUE_CREATE': 'CREATE',
        'LEAGUE_UPDATE': 'UPDATE',
        'LEAGUE_DELETE': 'DELETE',
        'LEAGUE_ARCHIVE': 'ARCHIVE',
        'LEAGUE_RESTORE': 'RESTORE',
        'LEAGUE_JOIN': 'JOIN',
        'LEAGUE_LEAVE': 'LEAVE',
        
        # Member operations
        'MEMBER_ADD': 'CREATE',
        'MEMBER_REMOVE': 'DELETE',
        'MEMBER_ROLE_CHANGE': 'UPDATE',
        'MEMBER_INVITE': 'CREATE',
        'MEMBER_KICK': 'DELETE',
        
        # Trade operations
        'TRADE_EXECUTE': 'CREATE',
        'TRADE_CANCEL': 'DELETE',
        'TRADE_REJECT': 'DELETE',
        
        # Portfolio operations
        'PORTFOLIO_UPDATE': 'UPDATE',
        'PORTFOLIO_RESET': 'UPDATE',
        
        # Settings operations
        'SETTINGS_UPDATE': 'UPDATE',
        'PASSWORD_CHANGE': 'UPDATE',
        'EMAIL_CHANGE': 'UPDATE',
        
        # Admin operations
        'ADMIN_ACTION': 'UPDATE',
        'ADMIN_REPORT_GENERATED': 'READ',
    }
    
    # Sensitive fields to redact
    SENSITIVE_FIELDS = {
        'password', 'email', 'phone', 'ssn', 'credit_card',
        'api_key', 'token', 'secret'
    }
    
    def __init__(self, db):
        """Initialize audit logger with database connection"""
        self.db = db
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Create audit tables if they don't exist"""
        cursor = self.db.get_connection().cursor()
        
        # Main audit log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                status TEXT DEFAULT 'success',
                details TEXT,
                changes TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                checksum TEXT UNIQUE NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Audit trail integrity table (for immutability verification)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_trail_integrity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_id INTEGER NOT NULL UNIQUE,
                previous_checksum TEXT,
                current_checksum TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified INTEGER DEFAULT 0,
                FOREIGN KEY (log_id) REFERENCES audit_logs (id)
            )
        ''')
        
        # User activity summary table (for quick reporting)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                actions_count INTEGER DEFAULT 0,
                resources_affected TEXT,
                risk_level TEXT DEFAULT 'low',
                UNIQUE(user_id, date),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Indices for performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_user_timestamp 
            ON audit_logs (user_id, timestamp DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_resource 
            ON audit_logs (resource_type, resource_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_action 
            ON audit_logs (action, timestamp DESC)
        ''')
        
        self.db.get_connection().commit()
        logger.debug("Audit tables verified/created")
    
    def log_action(self, 
                   action: str,
                   resource_type: str,
                   resource_id: int,
                   user_id: int,
                   status: str = "success",
                   details: Optional[Dict[str, Any]] = None,
                   changes: Optional[Dict[str, Any]] = None,
                   ip_address: Optional[str] = None,
                   user_agent: Optional[str] = None) -> int:
        """
        Log an action to the audit trail
        
        Args:
            action: Action performed
            resource_type: Type of resource
            resource_id: ID of resource
            user_id: User ID
            status: success/failure/partial
            details: Additional context
            changes: Before/after values
            ip_address: Client IP
            user_agent: Client info
            
        Returns:
            Log entry ID
        """
        try:
            # Redact sensitive information
            if details:
                details = self._redact_sensitive_data(details)
            if changes:
                changes = self._redact_sensitive_data(changes)
            
            # Create audit log entry
            log = AuditLog(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                status=status,
                details=details,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Store in database
            cursor = self.db.get_connection().cursor()
            log_data = log.to_dict()
            
            cursor.execute('''
                INSERT INTO audit_logs 
                (action, resource_type, resource_id, user_id, status, 
                 details, changes, ip_address, user_agent, timestamp, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                log_data['action'],
                log_data['resource_type'],
                log_data['resource_id'],
                log_data['user_id'],
                log_data['status'],
                log_data['details'],
                log_data['changes'],
                log_data['ip_address'],
                log_data['user_agent'],
                log_data['timestamp'],
                log_data['checksum']
            ))
            
            self.db.get_connection().commit()
            log_id = cursor.lastrowid
            
            # Update user activity summary
            self._update_user_summary(user_id, action)
            
            logger.debug(f"Logged action: {action} on {resource_type}:{resource_id}")
            return log_id
            
        except Exception as e:
            logger.error(f"Failed to log action: {str(e)}")
            raise
    
    def _redact_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive information from logged data"""
        redacted = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                redacted[key] = '[REDACTED]'
            elif isinstance(value, dict):
                redacted[key] = self._redact_sensitive_data(value)
            else:
                redacted[key] = value
        return redacted
    
    def _update_user_summary(self, user_id: int, action: str):
        """Update daily activity summary for user"""
        today = datetime.utcnow().date()
        cursor = self.db.get_connection().cursor()
        
        cursor.execute('''
            INSERT INTO user_activity_summary (user_id, date, actions_count, risk_level)
            VALUES (?, ?, 1, 'low')
            ON CONFLICT(user_id, date) 
            DO UPDATE SET actions_count = actions_count + 1
        ''', (user_id, today))
        
        self.db.get_connection().commit()
    
    def get_audit_trail(self,
                       user_id: Optional[int] = None,
                       resource_type: Optional[str] = None,
                       resource_id: Optional[int] = None,
                       action: Optional[str] = None,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail with optional filters
        
        Args:
            user_id: Filter by user
            resource_type: Filter by resource type
            resource_id: Filter by specific resource
            action: Filter by action
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum results
            
        Returns:
            List of audit log entries
        """
        query = 'SELECT * FROM audit_logs WHERE 1=1'
        params = []
        
        if user_id is not None:
            query += ' AND user_id = ?'
            params.append(user_id)
        
        if resource_type:
            query += ' AND resource_type = ?'
            params.append(resource_type)
        
        if resource_id is not None:
            query += ' AND resource_id = ?'
            params.append(resource_id)
        
        if action:
            query += ' AND action = ?'
            params.append(action)
        
        if start_date:
            query += ' AND timestamp >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND timestamp <= ?'
            params.append(end_date)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor = self.db.get_connection().cursor()
        cursor.execute(query, params)
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_user_activity(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get user activity summary for compliance reporting
        
        Args:
            user_id: User to report on
            days: Days to include (default 30)
            
        Returns:
            Activity summary dict
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        cursor = self.db.get_connection().cursor()
        
        # Get all actions for user
        cursor.execute('''
            SELECT action, COUNT(*) as count
            FROM audit_logs
            WHERE user_id = ? AND timestamp >= ?
            GROUP BY action
            ORDER BY count DESC
        ''', (user_id, start_date))
        
        actions = {row['action']: row['count'] for row in cursor.fetchall()}
        
        # Get affected resources
        cursor.execute('''
            SELECT resource_type, COUNT(DISTINCT resource_id) as count
            FROM audit_logs
            WHERE user_id = ? AND timestamp >= ?
            GROUP BY resource_type
            ORDER BY count DESC
        ''', (user_id, start_date))
        
        resources = {row['resource_type']: row['count'] for row in cursor.fetchall()}
        
        # Get success rate
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM audit_logs
            WHERE user_id = ? AND timestamp >= ?
            GROUP BY status
        ''', (user_id, start_date))
        
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        total = sum(status_counts.values())
        success_rate = (status_counts.get('success', 0) / total * 100) if total > 0 else 0
        
        return {
            'user_id': user_id,
            'days': days,
            'total_actions': total,
            'actions': actions,
            'resources_affected': resources,
            'success_rate': success_rate,
            'start_date': start_date,
            'end_date': datetime.utcnow()
        }
    
    def verify_audit_integrity(self, log_id: int) -> bool:
        """
        Verify audit log integrity using checksums
        
        Args:
            log_id: Log entry to verify
            
        Returns:
            True if integrity verified, False otherwise
        """
        cursor = self.db.get_connection().cursor()
        
        cursor.execute('SELECT checksum FROM audit_logs WHERE id = ?', (log_id,))
        row = cursor.fetchone()
        
        if not row:
            logger.warning(f"Log entry {log_id} not found")
            return False
        
        stored_checksum = row['checksum']
        
        # Check against integrity table
        cursor.execute('''
            SELECT verified FROM audit_trail_integrity 
            WHERE log_id = ? AND current_checksum = ?
        ''', (log_id, stored_checksum))
        
        verified = cursor.fetchone()
        return bool(verified)
    
    def export_audit_report(self,
                           user_id: Optional[int] = None,
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           format: str = 'json') -> str:
        """
        Export audit logs for compliance reporting
        
        Args:
            user_id: Filter by user
            start_date: Filter by start date
            end_date: Filter by end date
            format: Export format (json or csv)
            
        Returns:
            Exported data as string
        """
        logs = self.get_audit_trail(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        if format == 'json':
            return json.dumps(logs, indent=2, default=str)
        
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            if logs:
                writer = csv.DictWriter(output, fieldnames=logs[0].keys())
                writer.writeheader()
                writer.writerows(logs)
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_high_risk_activities(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Identify potentially risky activities
        
        Args:
            days: Days to analyze
            
        Returns:
            List of high-risk activities
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        cursor = self.db.get_connection().cursor()
        
        # Find failed operations
        cursor.execute('''
            SELECT * FROM audit_logs
            WHERE timestamp >= ? AND status != 'success'
            ORDER BY timestamp DESC
            LIMIT 100
        ''', (start_date,))
        
        risky = cursor.fetchall()
        return [dict(row) for row in risky]
    
    def cleanup_old_logs(self, days: int = 365, dry_run: bool = True) -> int:
        """
        Clean up old audit logs (keep 1+ years)
        
        Args:
            days: Delete logs older than this many days
            dry_run: If True, only count, don't delete
            
        Returns:
            Number of logs deleted/to be deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        cursor = self.db.get_connection().cursor()
        
        cursor.execute('''
            SELECT COUNT(*) as count FROM audit_logs 
            WHERE timestamp < ?
        ''', (cutoff_date,))
        
        count = cursor.fetchone()['count']
        
        if not dry_run and count > 0:
            cursor.execute('''
                DELETE FROM audit_logs WHERE timestamp < ?
            ''', (cutoff_date,))
            self.db.get_connection().commit()
            logger.info(f"Deleted {count} old audit logs")
        
        return count


def audit_action(resource_type: str, 
                 capture_changes: bool = False) -> Callable:
    """
    Decorator to automatically log Flask route actions
    
    Usage:
        @app.route('/leagues', methods=['POST'])
        @audit_action('LEAGUE', capture_changes=True)
        def create_league():
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get audit logger and request context
            from flask import request, g
            
            audit_logger = g.get('audit_logger')
            if not audit_logger:
                # Logger not available, just execute function
                return f(*args, **kwargs)
            
            # Determine action from HTTP method
            action_map = {
                'POST': 'CREATE',
                'PUT': 'UPDATE',
                'PATCH': 'UPDATE',
                'DELETE': 'DELETE',
                'GET': 'READ'
            }
            action = action_map.get(request.method, 'UPDATE')
            
            try:
                # Execute function
                result = f(*args, **kwargs)
                
                # Log success
                details = {
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'path': request.path
                }
                
                audit_logger.log_action(
                    action=action,
                    resource_type=resource_type,
                    resource_id=kwargs.get('id', 0),
                    user_id=g.get('user_id', 0),
                    status='success',
                    details=details,
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string
                )
                
                return result
                
            except Exception as e:
                # Log failure
                audit_logger.log_action(
                    action=action,
                    resource_type=resource_type,
                    resource_id=kwargs.get('id', 0),
                    user_id=g.get('user_id', 0),
                    status='failure',
                    details={'error': str(e)},
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string
                )
                raise
        
        return decorated_function
    return decorator
