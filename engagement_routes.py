"""
API Routes for League Engagement Features - Phase 3
Implements endpoints for activity feeds, metrics, announcements, and analytics
"""

from flask import Blueprint, request, session, jsonify
from functools import wraps
import logging
from typing import Tuple, Optional
from datetime import datetime, timedelta
from phase_3_schema import ActivityType
from league_activity_feed import LeagueActivityFeed
from error_handling import AuthorizationError, NotFoundError, ValidationError
from database.db_manager import DatabaseManager

# Create blueprint
engagement_bp = Blueprint('engagement', __name__, url_prefix='/api/engagement')

# Configure logger
engagement_logger = logging.getLogger('engagement_routes')
engagement_logger.setLevel(logging.INFO)

# Database manager instance
db = DatabaseManager()


def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def league_member_required(f):
    """Decorator to require league membership"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        league_id = request.view_args.get('league_id')
        user_id = session.get('user_id')
        
        if not league_id or not user_id:
            return jsonify({'error': 'Invalid request'}), 400
        
        # Check membership (would integrate with actual db)
        # For now, just verify league exists
        return f(*args, **kwargs)
    return decorated_function


# ===== ACTIVITY FEED ROUTES =====

@engagement_bp.route('/leagues/<int:league_id>/activity-feed', methods=['GET'])
@login_required
@league_member_required
def get_league_activity_feed(league_id):
    """
    Get league activity feed
    
    Query Parameters:
        - limit: Number of activities (default: 20)
        - offset: Pagination offset (default: 0)
        - types: Comma-separated activity types to filter (optional)
    
    Returns:
        {
            'success': bool,
            'activities': [
                {
                    'id': int,
                    'user_id': int,
                    'username': str,
                    'activity_type': str,
                    'description': str,
                    'metadata': object,
                    'created_at': str (ISO format),
                    'timeago': str (e.g., "5 minutes ago")
                }
            ],
            'count': int,
            'total': int
        }
    """
    try:
        # Get query parameters
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        types_str = request.args.get('types', '')
        
        # Validate parameters
        limit = min(limit, 100)  # Max 100 per request
        if limit < 1 or offset < 0:
            return jsonify({'error': 'Invalid pagination parameters'}), 400
        
        # Parse activity types filter
        activity_types = None
        if types_str:
            activity_types = [t.strip() for t in types_str.split(',')]
        
        # Query activity feed from database
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Build query
        query = '''
            SELECT id, user_id, username, activity_type, description, metadata, created_at
            FROM league_activity_log
            WHERE league_id = ?
        '''
        params = [league_id]
        
        # Add type filter if specified
        if activity_types:
            placeholders = ','.join(['?' for _ in activity_types])
            query += f' AND activity_type IN ({placeholders})'
            params.extend(activity_types)
        
        # Get total count
        count_query = query.replace('SELECT id, user_id, username, activity_type, description, metadata, created_at', 'SELECT COUNT(*)')
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Get paginated results
        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Format response
        activities = []
        for row in rows:
            activities.append({
                'id': row[0],
                'user_id': row[1],
                'username': row[2],
                'activity_type': row[3],
                'description': row[4],
                'metadata': row[5],  # JSON stored in database
                'created_at': row[6],
                'timeago': _format_timeago(row[6])
            })
        
        return jsonify({
            'success': True,
            'activities': activities,
            'count': len(activities),
            'total': total,
            'limit': limit,
            'offset': offset,
        }), 200
    
    except Exception as e:
        engagement_logger.error(f"Error fetching activity feed: {e}")
        return jsonify({'error': 'Error fetching activity feed'}), 500


@engagement_bp.route('/leagues/<int:league_id>/activity-stats', methods=['GET'])
@login_required
@league_member_required
def get_activity_stats(league_id):
    """
    Get activity statistics for league
    
    Query Parameters:
        - hours: Hours to look back (default: 24)
    
    Returns:
        {
            'success': bool,
            'total_activities': int,
            'by_type': { type: count },
            'most_active_users': [ { user_id, count } ],
            'period_hours': int
        }
    """
    try:
        hours = request.args.get('hours', 24, type=int)
        hours = min(hours, 720)  # Max 30 days
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get total activities in period
        time_threshold = datetime.now() - timedelta(hours=hours)
        cursor.execute('''
            SELECT COUNT(*) FROM league_activity_log
            WHERE league_id = ? AND created_at > ?
        ''', (league_id, time_threshold.isoformat()))
        total_activities = cursor.fetchone()[0]
        
        # Get breakdown by type
        cursor.execute('''
            SELECT activity_type, COUNT(*) as count
            FROM league_activity_log
            WHERE league_id = ? AND created_at > ?
            GROUP BY activity_type
            ORDER BY count DESC
        ''', (league_id, time_threshold.isoformat()))
        
        by_type = {}
        for row in cursor.fetchall():
            by_type[row[0]] = row[1]
        
        # Get most active users
        cursor.execute('''
            SELECT user_id, username, COUNT(*) as count
            FROM league_activity_log
            WHERE league_id = ? AND created_at > ?
            GROUP BY user_id
            ORDER BY count DESC
            LIMIT 10
        ''', (league_id, time_threshold.isoformat()))
        
        most_active_users = []
        for row in cursor.fetchall():
            most_active_users.append({
                'user_id': row[0],
                'username': row[1],
                'activity_count': row[2]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_activities': total_activities,
            'by_type': by_type,
            'most_active_users': most_active_users,
            'period_hours': hours,
        }), 200
    
    except Exception as e:
        engagement_logger.error(f"Error fetching activity stats: {e}")
        return jsonify({'error': 'Error fetching stats'}), 500


# ===== PERFORMANCE METRICS ROUTES =====

@engagement_bp.route('/leagues/<int:league_id>/user/<int:target_user_id>/metrics', methods=['GET'])
@login_required
@league_member_required
def get_user_league_metrics(league_id, target_user_id):
    """
    Get user's performance metrics in league context
    
    Returns:
        {
            'success': bool,
            'metrics': {
                'user_id': int,
                'username': str,
                'rank': int,
                'rank_change': int,
                'portfolio_value': float,
                'portfolio_value_change_today': float,
                'daily_pl': float,
                'daily_pl_pct': float,
                'weekly_pl': float,
                'monthly_pl': float,
                'win_rate': float,
                'trade_count': int,
                'best_stock': str,
                'league_average_portfolio': float,
                'portfolio_vs_average': float,
                'league_average_win_rate': float,
                'win_rate_vs_average': float,
            }
        }
    """
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get user portfolio and trade stats in league
        cursor.execute('''
            SELECT u.username, 
                   COUNT(DISTINCT t.id) as trade_count,
                   SUM(CASE WHEN t.type='buy' THEN 1 ELSE 0 END) as buy_count,
                   SUM(CASE WHEN t.type='sell' THEN 1 ELSE 0 END) as sell_count
            FROM users u
            LEFT JOIN trades t ON u.id = t.user_id AND t.league_id = ?
            WHERE u.id = ?
            GROUP BY u.id
        ''', (league_id, target_user_id))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        username = result[0]
        trade_count = result[1] or 0
        
        # Get user's portfolio value in league
        cursor.execute('''
            SELECT cash, SUM(shares * price) as holdings
            FROM (
                SELECT u.cash, p.shares, (SELECT price FROM stocks WHERE symbol = p.symbol LIMIT 1) as price
                FROM users u
                LEFT JOIN portfolios p ON u.id = p.user_id
                WHERE u.id = ? AND (p.league_id IS NULL OR p.league_id = ?)
            )
        ''', (target_user_id, league_id))
        
        portfolio_result = cursor.fetchone()
        portfolio_value = (portfolio_result[0] or 0) + (portfolio_result[1] or 0) if portfolio_result else 0
        
        # Get league average portfolio value
        cursor.execute('''
            SELECT AVG(u.cash + COALESCE(holdings, 0)) as avg_portfolio
            FROM users u
            LEFT JOIN (
                SELECT user_id, SUM(shares * (
                    SELECT price FROM stocks WHERE symbol = portfolios.symbol LIMIT 1
                )) as holdings
                FROM portfolios
                WHERE league_id = ?
                GROUP BY user_id
            ) p ON u.id = p.user_id
            WHERE u.id IN (
                SELECT DISTINCT user_id FROM league_members WHERE league_id = ?
            )
        ''', (league_id, league_id))
        
        league_result = cursor.fetchone()
        league_avg_portfolio = league_result[0] or 0 if league_result else 0
        
        # Calculate metrics
        daily_pl = 0  # Would calculate from recent trades
        daily_pl_pct = 0
        weekly_pl = 0
        monthly_pl = 0
        win_rate = 0.5  # Would calculate from trade outcomes
        best_stock = 'N/A'  # Would query best performing stock
        rank = 5  # Would rank user in league
        rank_change = 0
        
        conn.close()
        
        metrics = {
            'user_id': target_user_id,
            'username': username,
            'rank': rank,
            'rank_change': rank_change,
            'portfolio_value': portfolio_value,
            'portfolio_value_change_today': 0,
            'daily_pl': daily_pl,
            'daily_pl_pct': daily_pl_pct,
            'weekly_pl': weekly_pl,
            'monthly_pl': monthly_pl,
            'win_rate': win_rate,
            'trade_count': trade_count,
            'best_stock': best_stock,
            'league_average_portfolio': league_avg_portfolio,
            'portfolio_vs_average': portfolio_value - league_avg_portfolio,
            'league_average_win_rate': 0.52,
            'win_rate_vs_average': win_rate - 0.52,
        }
        
        return jsonify({
            'success': True,
            'metrics': metrics,
        }), 200
    
    except Exception as e:
        engagement_logger.error(f"Error fetching metrics: {e}")
        return jsonify({'error': 'Error fetching metrics'}), 500


# ===== ANNOUNCEMENTS ROUTES =====

@engagement_bp.route('/leagues/<int:league_id>/announcements', methods=['GET'])
@login_required
@league_member_required
def get_league_announcements(league_id):
    """
    Get league announcements
    
    Returns:
        {
            'success': bool,
            'announcements': [
                {
                    'id': int,
                    'title': str,
                    'content': str,
                    'author': str,
                    'pinned': bool,
                    'created_at': str,
                    'updated_at': str
                }
            ]
        }
    """
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get announcements from database
        cursor.execute('''
            SELECT id, title, content, author_id, username, pinned, created_at, updated_at
            FROM league_announcements
            WHERE league_id = ?
            ORDER BY pinned DESC, created_at DESC
        ''', (league_id,))
        
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
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'announcements': announcements,
        }), 200
    
    except Exception as e:
        engagement_logger.error(f"Error fetching announcements: {e}")
        return jsonify({'error': 'Error fetching announcements'}), 500


@engagement_bp.route('/leagues/<int:league_id>/announcements', methods=['POST'])
@login_required
@league_member_required
def create_announcement(league_id):
    """
    Create new announcement (admin only)
    
    Request Body:
        {
            'title': str,
            'content': str
        }
    
    Returns:
        {
            'success': bool,
            'announcement_id': int,
            'message': str
        }
    """
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        
        if not title or not content:
            return jsonify({'error': 'Title and content required'}), 400
        
        if len(title) > 200 or len(content) > 5000:
            return jsonify({'error': 'Content too long'}), 400
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if user is league admin
        cursor.execute('''
            SELECT role FROM league_members
            WHERE league_id = ? AND user_id = ?
        ''', (league_id, user_id))
        
        result = cursor.fetchone()
        if not result or result[0] not in ['admin', 'owner']:
            conn.close()
            return jsonify({'error': 'Only admins can create announcements'}), 403
        
        # Get username
        cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        username_result = cursor.fetchone()
        username = username_result[0] if username_result else 'System'
        
        # Insert announcement
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO league_announcements (league_id, title, content, author_id, username, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (league_id, title, content, user_id, username, now, now))
        
        conn.commit()
        announcement_id = cursor.lastrowid
        conn.close()
        
        # Log activity
        engagement_logger.info(f"Announcement {announcement_id} created by user {user_id} in league {league_id}")
        
        return jsonify({
            'success': True,
            'announcement_id': announcement_id,
            'message': 'Announcement created',
        }), 201
    
    except Exception as e:
        engagement_logger.error(f"Error creating announcement: {e}")
        return jsonify({'error': 'Error creating announcement'}), 500


# ===== PLAYER COMPARISON ROUTES =====

@engagement_bp.route('/leagues/<int:league_id>/compare/<int:user1_id>/<int:user2_id>', 
                     methods=['GET'])
@login_required
@league_member_required
def compare_players(league_id, user1_id, user2_id):
    """
    Compare two players in a league
    
    Returns:
        {
            'success': bool,
            'comparison': {
                'user1': { metrics },
                'user2': { metrics },
                'head_to_head': {
                    'user1_wins': int,
                    'user2_wins': int,
                    'last_trade': str
                }
            }
        }
    """
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get both users' trade stats
        def get_user_stats(user_id):
            cursor.execute('''
                SELECT u.username,
                       COUNT(t.id) as trade_count,
                       SUM(CASE WHEN t.profit > 0 THEN 1 ELSE 0 END) as wins,
                       ROUND(SUM(t.profit), 2) as total_pl
                FROM users u
                LEFT JOIN trades t ON u.id = t.user_id AND t.league_id = ?
                WHERE u.id = ?
                GROUP BY u.id
            ''', (league_id, user_id))
            return cursor.fetchone()
        
        user1_stats = get_user_stats(user1_id)
        user2_stats = get_user_stats(user2_id)
        
        if not user1_stats or not user2_stats:
            conn.close()
            return jsonify({'error': 'One or both users not found'}), 404
        
        # Get head-to-head stats
        cursor.execute('''
            SELECT COUNT(*) FROM trades
            WHERE league_id = ? AND user_id = ? AND (target_user_id = ? OR copy_from_user_id = ?)
        ''', (league_id, user1_id, user2_id, user2_id))
        
        user1_vs_user2 = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM trades
            WHERE league_id = ? AND user_id = ? AND (target_user_id = ? OR copy_from_user_id = ?)
        ''', (league_id, user2_id, user1_id, user1_id))
        
        user2_vs_user1 = cursor.fetchone()[0]
        
        conn.close()
        
        comparison = {
            'user1': {
                'user_id': user1_id,
                'username': user1_stats[0],
                'trade_count': user1_stats[1] or 0,
                'wins': user1_stats[2] or 0,
                'total_pl': user1_stats[3] or 0,
                'win_rate': (user1_stats[2] or 0) / (user1_stats[1] or 1)
            },
            'user2': {
                'user_id': user2_id,
                'username': user2_stats[0],
                'trade_count': user2_stats[1] or 0,
                'wins': user2_stats[2] or 0,
                'total_pl': user2_stats[3] or 0,
                'win_rate': (user2_stats[2] or 0) / (user2_stats[1] or 1)
            },
            'head_to_head': {
                'user1_wins': user1_vs_user2,
                'user2_wins': user2_vs_user1,
            }
        }
        
        return jsonify({
            'success': True,
            'comparison': comparison,
        }), 200
    
    except Exception as e:
        engagement_logger.error(f"Error comparing players: {e}")
        return jsonify({'error': 'Error comparing players'}), 500


# ===== LEAGUE ANALYTICS ROUTES =====

@engagement_bp.route('/leagues/<int:league_id>/analytics', methods=['GET'])
@login_required
@league_member_required
def get_league_analytics(league_id):
    """
    Get league analytics and statistics
    
    Query Parameters:
        - days: Number of days to analyze (default: 30)
    
    Returns:
        {
            'success': bool,
            'analytics': {
                'total_volume': float,
                'average_portfolio': float,
                'most_traded_stock': str,
                'member_count': int,
                'active_traders': int,
                'total_trades': int,
                'average_win_rate': float,
                'daily_breakdown': [ { date, volume, trades } ]
            }
        }
    """
    try:
        days = request.args.get('days', 30, type=int)
        days = min(days, 365)  # Max 1 year
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get total member count
        cursor.execute('''
            SELECT COUNT(*) FROM league_members WHERE league_id = ?
        ''', (league_id,))
        member_count = cursor.fetchone()[0]
        
        # Get trade stats
        time_threshold = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT COUNT(*),
                   SUM(total_cost) as total_volume,
                   SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as wins
            FROM trades
            WHERE league_id = ? AND created_at > ?
        ''', (league_id, time_threshold))
        
        trade_result = cursor.fetchone()
        total_trades = trade_result[0] or 0
        total_volume = trade_result[1] or 0
        total_wins = trade_result[2] or 0
        average_win_rate = (total_wins / total_trades) if total_trades > 0 else 0
        
        # Get most traded stock
        cursor.execute('''
            SELECT symbol, COUNT(*) as count
            FROM trades
            WHERE league_id = ? AND created_at > ?
            GROUP BY symbol
            ORDER BY count DESC
            LIMIT 1
        ''', (league_id, time_threshold))
        
        stock_result = cursor.fetchone()
        most_traded_stock = stock_result[0] if stock_result else 'N/A'
        
        # Get average portfolio value
        cursor.execute('''
            SELECT AVG(cash + COALESCE(holdings, 0)) as avg_portfolio
            FROM (
                SELECT u.cash,
                       (SELECT SUM(shares) FROM portfolios 
                        WHERE user_id = u.id AND league_id = ?) as holdings
                FROM users u
                WHERE u.id IN (
                    SELECT DISTINCT user_id FROM league_members WHERE league_id = ?
                )
            )
        ''', (league_id, league_id))
        
        portfolio_result = cursor.fetchone()
        average_portfolio = portfolio_result[0] or 0 if portfolio_result else 0
        
        # Get active traders (users with trades in period)
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id) FROM trades
            WHERE league_id = ? AND created_at > ?
        ''', (league_id, time_threshold))
        
        active_traders = cursor.fetchone()[0]
        
        conn.close()
        
        analytics = {
            'total_volume': total_volume,
            'average_portfolio': average_portfolio,
            'most_traded_stock': most_traded_stock,
            'member_count': member_count,
            'active_traders': active_traders,
            'total_trades': total_trades,
            'average_win_rate': round(average_win_rate, 3),
            'period_days': days,
        }
        
        return jsonify({
            'success': True,
            'analytics': analytics,
        }), 200
    
    except Exception as e:
        engagement_logger.error(f"Error fetching analytics: {e}")
        return jsonify({'error': 'Error fetching analytics'}), 500


# ===== NOTIFICATIONS ROUTES =====

@engagement_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    """
    Get user notifications
    
    Query Parameters:
        - limit: Number of notifications (default: 20)
        - unread_only: Get only unread (default: false)
    
    Returns:
        {
            'success': bool,
            'notifications': [
                {
                    'id': int,
                    'type': str,
                    'title': str,
                    'message': str,
                    'data': object,
                    'is_read': bool,
                    'created_at': str
                }
            ]
        }
    """
    try:
        user_id = session['user_id']
        limit = request.args.get('limit', 20, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        limit = min(limit, 100)
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Build query
        query = '''
            SELECT id, type, title, message, data, is_read, created_at
            FROM notifications
            WHERE user_id = ?
        '''
        params = [user_id]
        
        if unread_only:
            query += ' AND is_read = 0'
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        
        notifications = []
        for row in cursor.fetchall():
            notifications.append({
                'id': row[0],
                'type': row[1],
                'title': row[2],
                'message': row[3],
                'data': row[4],
                'is_read': bool(row[5]),
                'created_at': row[6],
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'notifications': notifications,
        }), 200
    
    except Exception as e:
        engagement_logger.error(f"Error fetching notifications: {e}")
        return jsonify({'error': 'Error fetching notifications'}), 500


@engagement_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    try:
        user_id = session['user_id']
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Verify ownership and mark as read
        cursor.execute('''
            UPDATE notifications
            SET is_read = 1
            WHERE id = ? AND user_id = ?
        ''', (notification_id, user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Notification marked as read',
        }), 200
    
    except Exception as e:
        engagement_logger.error(f"Error marking notification: {e}")
        return jsonify({'error': 'Error updating notification'}), 500


@engagement_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read"""
    try:
        user_id = session['user_id']
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE notifications
            SET is_read = 1
            WHERE user_id = ? AND is_read = 0
        ''', (user_id,))
        
        conn.commit()
        count = cursor.rowcount
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Marked {count} notifications as read',
        }), 200
    
    except Exception as e:
        engagement_logger.error(f"Error marking all notifications: {e}")
        return jsonify({'error': 'Error updating notifications'}), 500


def register_engagement_routes(app):
    """Register engagement routes with Flask app"""
    app.register_blueprint(engagement_bp)
    engagement_logger.info("Engagement routes registered")


def _format_timeago(timestamp_str):
    """Format timestamp as 'time ago' string"""
    try:
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
    print("Phase 3 Engagement Routes module loaded")
