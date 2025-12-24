"""
Item #8: Flask Integration for Audit Logging
Provides audit routes and middleware for Flask app
"""

import json
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, g, render_template, redirect, url_for
from audit_logger import AuditLogger


def create_audit_blueprint(db, audit_logger: AuditLogger):
    """
    Create Flask blueprint for audit routes
    
    Args:
        db: Database connection
        audit_logger: AuditLogger instance
        
    Returns:
        Blueprint with audit routes
    """
    audit_bp = Blueprint('audit', __name__, url_prefix='/admin/audit')
    
    @audit_bp.route('/logs', methods=['GET'])
    def view_audit_logs():
        """Display audit logs with filters"""
        # Get filter parameters
        user_id = request.args.get('user_id', type=int)
        resource_type = request.args.get('resource_type')
        action = request.args.get('action')
        days = request.args.get('days', 30, type=int)
        
        start_date = None
        if days:
            start_date = datetime.utcnow() - timedelta(days=days)
        
        # Fetch logs
        logs = audit_logger.get_audit_trail(
            user_id=user_id,
            resource_type=resource_type,
            action=action,
            start_date=start_date,
            limit=500
        )
        
        # Parse JSON fields
        for log in logs:
            if log.get('details'):
                try:
                    log['details'] = json.loads(log['details'])
                except:
                    pass
            if log.get('changes'):
                try:
                    log['changes'] = json.loads(log['changes'])
                except:
                    pass
        
        return render_template(
            'audit_logs.html',
            logs=logs,
            filters={
                'user_id': user_id,
                'resource_type': resource_type,
                'action': action,
                'days': days
            }
        )
    
    @audit_bp.route('/logs/json', methods=['GET'])
    def get_audit_logs_json():
        """Get audit logs as JSON (API endpoint)"""
        # Get filter parameters
        user_id = request.args.get('user_id', type=int)
        resource_type = request.args.get('resource_type')
        action = request.args.get('action')
        days = request.args.get('days', 30, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        start_date = None
        if days:
            start_date = datetime.utcnow() - timedelta(days=days)
        
        # Fetch logs
        logs = audit_logger.get_audit_trail(
            user_id=user_id,
            resource_type=resource_type,
            action=action,
            start_date=start_date,
            limit=min(limit, 1000)  # Cap at 1000
        )
        
        # Parse JSON fields
        for log in logs:
            if log.get('details'):
                try:
                    log['details'] = json.loads(log['details'])
                except:
                    pass
            if log.get('changes'):
                try:
                    log['changes'] = json.loads(log['changes'])
                except:
                    pass
        
        return jsonify({
            'success': True,
            'count': len(logs),
            'logs': logs
        })
    
    @audit_bp.route('/user/<int:user_id>', methods=['GET'])
    def user_activity(user_id):
        """Get user activity summary"""
        days = request.args.get('days', 30, type=int)
        
        activity = audit_logger.get_user_activity(user_id, days)
        
        return render_template(
            'user_activity.html',
            activity=activity,
            user_id=user_id
        )
    
    @audit_bp.route('/user/<int:user_id>/json', methods=['GET'])
    def user_activity_json(user_id):
        """Get user activity as JSON"""
        days = request.args.get('days', 30, type=int)
        
        activity = audit_logger.get_user_activity(user_id, days)
        
        # Convert datetime objects to strings
        activity['start_date'] = activity['start_date'].isoformat()
        activity['end_date'] = activity['end_date'].isoformat()
        
        return jsonify({
            'success': True,
            'activity': activity
        })
    
    @audit_bp.route('/reports/activity', methods=['GET'])
    def activity_report():
        """Generate activity report"""
        days = request.args.get('days', 30, type=int)
        format_type = request.args.get('format', 'html')
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = audit_logger.get_audit_trail(
            start_date=start_date,
            limit=10000
        )
        
        # Aggregate statistics
        action_stats = {}
        user_stats = {}
        resource_stats = {}
        
        for log in logs:
            # Action statistics
            action = log['action']
            action_stats[action] = action_stats.get(action, 0) + 1
            
            # User statistics
            user_id = log['user_id']
            if user_id not in user_stats:
                user_stats[user_id] = {
                    'actions': 0,
                    'success': 0,
                    'failures': 0
                }
            user_stats[user_id]['actions'] += 1
            if log['status'] == 'success':
                user_stats[user_id]['success'] += 1
            else:
                user_stats[user_id]['failures'] += 1
            
            # Resource statistics
            resource_type = log['resource_type']
            resource_stats[resource_type] = resource_stats.get(resource_type, 0) + 1
        
        report = {
            'generated_at': datetime.utcnow(),
            'period_days': days,
            'total_actions': len(logs),
            'action_statistics': action_stats,
            'user_statistics': user_stats,
            'resource_statistics': resource_stats
        }
        
        if format_type == 'json':
            # Convert datetime to string for JSON
            report['generated_at'] = report['generated_at'].isoformat()
            return jsonify({
                'success': True,
                'report': report
            })
        else:
            return render_template(
                'activity_report.html',
                report=report,
                days=days
            )
    
    @audit_bp.route('/reports/risk', methods=['GET'])
    def risk_report():
        """Generate risk report"""
        days = request.args.get('days', 7, type=int)
        
        risky_activities = audit_logger.get_high_risk_activities(days)
        
        return render_template(
            'risk_report.html',
            risky_activities=risky_activities,
            days=days,
            risk_count=len(risky_activities)
        )
    
    @audit_bp.route('/export', methods=['GET'])
    def export_logs():
        """Export audit logs"""
        format_type = request.args.get('format', 'json')
        user_id = request.args.get('user_id', type=int)
        days = request.args.get('days', 90, type=int)
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        data = audit_logger.export_audit_report(
            user_id=user_id,
            start_date=start_date,
            format=format_type
        )
        
        if format_type == 'csv':
            return {
                'data': data,
                'headers': {
                    'Content-Type': 'text/csv',
                    'Content-Disposition': f'attachment; filename="audit_logs_{datetime.utcnow().strftime("%Y%m%d")}.csv"'
                }
            }, 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename="audit_logs_{datetime.utcnow().strftime("%Y%m%d")}.csv"'
            }
        else:
            return {
                'data': json.loads(data),
                'headers': {
                    'Content-Type': 'application/json',
                    'Content-Disposition': f'attachment; filename="audit_logs_{datetime.utcnow().strftime("%Y%m%d")}.json"'
                }
            }, 200, {
                'Content-Type': 'application/json',
                'Content-Disposition': f'attachment; filename="audit_logs_{datetime.utcnow().strftime("%Y%m%d")}.json"'
            }
    
    @audit_bp.route('/verify/<int:log_id>', methods=['GET'])
    def verify_integrity(log_id):
        """Verify audit log integrity"""
        verified = audit_logger.verify_audit_integrity(log_id)
        
        return jsonify({
            'success': True,
            'log_id': log_id,
            'verified': verified,
            'message': 'Audit entry is verified intact' if verified else 'Audit entry integrity check failed'
        })
    
    @audit_bp.route('/cleanup', methods=['POST'])
    def cleanup_old_logs():
        """Clean up old audit logs (admin-only)"""
        days = request.json.get('days', 365)
        dry_run = request.json.get('dry_run', True)
        
        count = audit_logger.cleanup_old_logs(days=days, dry_run=dry_run)
        
        action = "Would delete" if dry_run else "Deleted"
        
        return jsonify({
            'success': True,
            'message': f'{action} {count} audit logs older than {days} days',
            'count': count,
            'dry_run': dry_run
        })
    
    return audit_bp


def setup_audit_middleware(app, db, audit_logger: AuditLogger):
    """
    Setup audit logging middleware for Flask app
    
    Args:
        app: Flask application
        db: Database connection
        audit_logger: AuditLogger instance
    """
    
    @app.before_request
    def before_request():
        """Initialize audit logger in request context"""
        g.audit_logger = audit_logger
        g.user_id = None  # Set by auth middleware
        g.request_start_time = datetime.utcnow()
    
    @app.after_request
    def after_request(response):
        """Log response metrics"""
        if hasattr(g, 'audit_logger') and hasattr(g, 'request_start_time'):
            duration = (datetime.utcnow() - g.request_start_time).total_seconds()
            
            # Log slow requests (>1 second)
            if duration > 1.0:
                g.audit_logger.log_action(
                    action='SLOW_REQUEST',
                    resource_type='HTTP',
                    resource_id=0,
                    user_id=g.get('user_id', 0),
                    status='success',
                    details={
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'path': request.path,
                        'duration_seconds': duration,
                        'status_code': response.status_code
                    }
                )
        
        return response


def require_audit(f):
    """
    Decorator to require audit logging for a route
    Validates that audit logger is available
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'audit_logger'):
            return {'error': 'Audit logging not configured'}, 500
        return f(*args, **kwargs)
    return decorated_function


def log_action_decorator(resource_type: str):
    """
    Decorator to automatically log route actions
    
    Usage:
        @app.route('/leagues', methods=['POST'])
        @log_action_decorator('LEAGUE')
        def create_league():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            audit_logger = g.get('audit_logger')
            if not audit_logger:
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
                result = f(*args, **kwargs)
                
                # Log success
                audit_logger.log_action(
                    action=action,
                    resource_type=resource_type,
                    resource_id=kwargs.get('id', 0),
                    user_id=g.get('user_id', 0),
                    status='success',
                    details={
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'path': request.path
                    },
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
                    details={
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'path': request.path,
                        'error': str(e)
                    },
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string
                )
                raise
        
        return decorated_function
    return decorator
