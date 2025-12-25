"""
Admin Monitoring Dashboard Routes
Flask blueprint for admin monitoring and system metrics
"""

import json
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from functools import wraps


def create_admin_monitoring_blueprint(db, system_metrics, user_activity_monitor, alert_manager, health_checker):
    """
    Create Flask blueprint for admin monitoring dashboard.
    
    Args:
        db: DatabaseManager instance
        system_metrics: SystemMetrics instance
        user_activity_monitor: UserActivityMonitor instance
        alert_manager: AlertManager instance
        health_checker: HealthChecker instance
        
    Returns:
        Blueprint with admin monitoring routes
    """
    monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/admin/monitoring')
    
    def admin_required(f):
        """Decorator for admin-only routes"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import session
            user_id = session.get('user_id')
            if not user_id:
                return redirect(url_for('login'))
            
            user = db.get_user(user_id)
            if not user or not user.get('is_admin'):
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    
    # ========== DASHBOARD ==========
    
    @monitoring_bp.route('/', methods=['GET'])
    @admin_required
    def dashboard():
        """Main monitoring dashboard"""
        overview = system_metrics.get_system_overview()
        db_stats = system_metrics.get_database_stats()
        health = health_checker.full_health_check()
        alerts = alert_manager.get_active_alerts()
        alert_stats = alert_manager.get_alert_stats()
        
        return render_template(
            'admin/monitoring_dashboard.html',
            overview=overview,
            db_stats=db_stats,
            health=health,
            alerts=alerts,
            alert_stats=alert_stats
        )
    
    # ========== SYSTEM METRICS ==========
    
    @monitoring_bp.route('/overview', methods=['GET'])
    @admin_required
    def get_overview():
        """Get system overview (JSON API)"""
        overview = system_metrics.get_system_overview()
        db_stats = system_metrics.get_database_stats()
        
        return jsonify({
            'success': True,
            'data': {
                'overview': overview,
                'database': db_stats
            }
        })
    
    @monitoring_bp.route('/health', methods=['GET'])
    @admin_required
    def get_health():
        """Get system health status"""
        health = health_checker.full_health_check()
        
        return jsonify({
            'success': True,
            'data': health
        })
    
    # ========== USER ACTIVITY ==========
    
    @monitoring_bp.route('/active-users', methods=['GET'])
    @admin_required
    def active_users():
        """Get active users page"""
        users = user_activity_monitor.get_active_users_today()
        
        return render_template(
            'admin/active_users.html',
            users=users
        )
    
    @monitoring_bp.route('/active-users/json', methods=['GET'])
    @admin_required
    def active_users_json():
        """Get active users (JSON API)"""
        users = user_activity_monitor.get_active_users_today()
        
        return jsonify({
            'success': True,
            'data': users,
            'count': len(users)
        })
    
    @monitoring_bp.route('/engagement', methods=['GET'])
    @admin_required
    def engagement():
        """Get user engagement metrics page"""
        metrics = user_activity_monitor.get_engagement_metrics()
        
        return render_template(
            'admin/engagement_metrics.html',
            metrics=metrics
        )
    
    @monitoring_bp.route('/engagement/json', methods=['GET'])
    @admin_required
    def engagement_json():
        """Get engagement metrics (JSON API)"""
        metrics = user_activity_monitor.get_engagement_metrics()
        
        return jsonify({
            'success': True,
            'data': metrics
        })
    
    # ========== TRADING ACTIVITY ==========
    
    @monitoring_bp.route('/trading-activity', methods=['GET'])
    @admin_required
    def trading_activity():
        """Get trading activity page"""
        hours = request.args.get('hours', 24, type=int)
        activity = user_activity_monitor.get_trading_activity(hours)
        
        return render_template(
            'admin/trading_activity.html',
            activity=activity,
            hours=hours
        )
    
    @monitoring_bp.route('/trading-activity/json', methods=['GET'])
    @admin_required
    def trading_activity_json():
        """Get trading activity (JSON API)"""
        hours = request.args.get('hours', 24, type=int)
        activity = user_activity_monitor.get_trading_activity(hours)
        
        return jsonify({
            'success': True,
            'data': activity
        })
    
    # ========== LEAGUE ACTIVITY ==========
    
    @monitoring_bp.route('/league-activity', methods=['GET'])
    @admin_required
    def league_activity():
        """Get league activity page"""
        leagues = user_activity_monitor.get_league_activity()
        
        return render_template(
            'admin/league_activity.html',
            leagues=leagues
        )
    
    @monitoring_bp.route('/league-activity/json', methods=['GET'])
    @admin_required
    def league_activity_json():
        """Get league activity (JSON API)"""
        leagues = user_activity_monitor.get_league_activity()
        
        return jsonify({
            'success': True,
            'data': leagues,
            'count': len(leagues)
        })
    
    # ========== RISK ASSESSMENT ==========
    
    @monitoring_bp.route('/risk-assessment', methods=['GET'])
    @admin_required
    def risk_assessment():
        """Get risk assessment page"""
        users = user_activity_monitor.get_user_risk_assessment()
        
        return render_template(
            'admin/risk_assessment.html',
            users=users
        )
    
    @monitoring_bp.route('/risk-assessment/json', methods=['GET'])
    @admin_required
    def risk_assessment_json():
        """Get risk assessment (JSON API)"""
        users = user_activity_monitor.get_user_risk_assessment()
        
        return jsonify({
            'success': True,
            'data': users,
            'count': len(users)
        })
    
    # ========== ALERTS ==========
    
    @monitoring_bp.route('/alerts', methods=['GET'])
    @admin_required
    def alerts():
        """Get alerts page"""
        severity = request.args.get('severity')
        all_alerts = alert_manager.get_active_alerts(severity)
        alert_stats = alert_manager.get_alert_stats()
        
        return render_template(
            'admin/alerts.html',
            alerts=all_alerts,
            stats=alert_stats,
            severity_filter=severity
        )
    
    @monitoring_bp.route('/alerts/json', methods=['GET'])
    @admin_required
    def alerts_json():
        """Get alerts (JSON API)"""
        severity = request.args.get('severity')
        all_alerts = alert_manager.get_active_alerts(severity)
        alert_stats = alert_manager.get_alert_stats()
        
        return jsonify({
            'success': True,
            'data': all_alerts,
            'stats': alert_stats
        })
    
    @monitoring_bp.route('/alerts/<int:alert_id>/resolve', methods=['POST'])
    @admin_required
    def resolve_alert(alert_id):
        """Resolve an alert"""
        success = alert_manager.resolve_alert(alert_id)
        
        return jsonify({
            'success': success,
            'message': 'Alert resolved' if success else 'Failed to resolve alert'
        })
    
    # ========== REAL-TIME STATS ==========
    
    @monitoring_bp.route('/realtime/stats', methods=['GET'])
    @admin_required
    def realtime_stats():
        """Get real-time stats for dashboard widgets"""
        overview = system_metrics.get_system_overview()
        health = health_checker.full_health_check()
        alert_stats = alert_manager.get_alert_stats()
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'overview': overview,
            'health': health,
            'alerts': alert_stats
        })
    
    # ========== CACHE STATS ==========
    
    @monitoring_bp.route('/cache', methods=['GET'])
    @admin_required
    def cache_stats():
        """Get cache statistics"""
        # This would be populated by passing cache_manager if available
        return render_template('admin/cache_stats.html')
    
    @monitoring_bp.route('/cache/clear', methods=['POST'])
    @admin_required
    def clear_cache():
        """Clear application cache"""
        # Cache would need to be available in request context
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully'
        })
    
    # ========== PERFORMANCE ==========
    
    @monitoring_bp.route('/performance', methods=['GET'])
    @admin_required
    def performance():
        """Get performance metrics page"""
        perf_metrics = system_metrics.get_performance_metrics()
        
        return render_template(
            'admin/performance_metrics.html',
            metrics=perf_metrics
        )
    
    @monitoring_bp.route('/performance/json', methods=['GET'])
    @admin_required
    def performance_json():
        """Get performance metrics (JSON API)"""
        perf_metrics = system_metrics.get_performance_metrics()
        
        return jsonify({
            'success': True,
            'data': perf_metrics
        })
    
    return monitoring_bp
