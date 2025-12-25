"""
Admin Monitoring Dashboard for StockLeague
Real-time system health, user activity, and performance metrics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class SystemMetrics:
    """System-wide performance metrics"""
    
    def __init__(self, db):
        """
        Initialize system metrics tracker.
        
        Args:
            db: DatabaseManager instance
        """
        self.db = db
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get system overview metrics"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # User counts
            cursor.execute("SELECT COUNT(*) as total FROM users")
            total_users = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as active FROM users WHERE last_login >= datetime('now', '-7 days')")
            active_users = cursor.fetchone()['active']
            
            # League counts
            cursor.execute("SELECT COUNT(*) as total FROM leagues WHERE soft_deleted_at IS NULL")
            active_leagues = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM leagues WHERE soft_deleted_at IS NOT NULL")
            archived_leagues = cursor.fetchone()['total']
            
            # Trade volume
            cursor.execute("""
                SELECT COUNT(*) as total, SUM(quantity) as shares, SUM(price) as volume
                FROM trades WHERE executed_at >= datetime('now', '-24 hours')
            """)
            today_trades = cursor.fetchone()
            
            # Cache stats (if available)
            cache_stats = {
                'status': 'not_configured',
                'hits': 0,
                'misses': 0,
                'hit_rate': 0
            }
            
            conn.close()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'users': {
                    'total': total_users,
                    'active_7days': active_users,
                    'active_percentage': round(active_users / total_users * 100, 1) if total_users > 0 else 0
                },
                'leagues': {
                    'active': active_leagues,
                    'archived': archived_leagues,
                    'total': active_leagues + archived_leagues
                },
                'trading': {
                    'trades_24h': today_trades['total'] or 0,
                    'shares_traded_24h': today_trades['shares'] or 0,
                    'volume_24h': round(today_trades['volume'] or 0, 2)
                },
                'cache': cache_stats
            }
        except Exception as e:
            logger.error(f"Error getting system overview: {e}")
            return {}
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Table sizes (row counts)
            tables = ['users', 'leagues', 'league_members', 'trades', 'portfolios', 
                     'audit_logs', 'invite_codes', 'user_options_positions']
            
            table_stats = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                table_stats[table] = cursor.fetchone()['count']
            
            conn.close()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'tables': table_stats,
                'total_records': sum(table_stats.values())
            }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get application performance metrics"""
        return {
            'timestamp': datetime.now().isoformat(),
            'api_response_time_avg_ms': 250,  # Should be tracked by middleware
            'slow_queries': [],  # Should log queries > 1s
            'memory_usage_mb': 256,  # Should be tracked
            'uptime_hours': 72  # Should be tracked at startup
        }


class UserActivityMonitor:
    """Monitor user activity and engagement"""
    
    def __init__(self, db, audit_logger=None):
        """
        Initialize user activity monitor.
        
        Args:
            db: DatabaseManager instance
            audit_logger: AuditLogger instance for detailed logging
        """
        self.db = db
        self.audit_logger = audit_logger
    
    def get_active_users_today(self) -> List[Dict[str, Any]]:
        """Get users active in last 24 hours"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT u.id, u.username, u.last_login, 
                       COUNT(DISTINCT l.id) as league_count,
                       COUNT(DISTINCT t.id) as trades_today
                FROM users u
                LEFT JOIN league_members lm ON u.id = lm.user_id
                LEFT JOIN leagues l ON lm.league_id = l.id
                LEFT JOIN trades t ON u.id = t.user_id AND t.executed_at >= datetime('now', '-24 hours')
                WHERE u.last_login >= datetime('now', '-24 hours')
                GROUP BY u.id
                ORDER BY u.last_login DESC
                LIMIT 50
            """)
            
            users = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return users
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    def get_trading_activity(self, hours: int = 24) -> Dict[str, Any]:
        """Get trading activity metrics"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cutoff = datetime.now() - timedelta(hours=hours)
            
            # Total trades
            cursor.execute("""
                SELECT COUNT(*) as total FROM trades WHERE executed_at >= ?
            """, (cutoff,))
            total_trades = cursor.fetchone()['total']
            
            # By type
            cursor.execute("""
                SELECT trade_type, COUNT(*) as count 
                FROM trades WHERE executed_at >= ?
                GROUP BY trade_type
            """, (cutoff,))
            by_type = {row['trade_type']: row['count'] for row in cursor.fetchall()}
            
            # By symbol (top 10)
            cursor.execute("""
                SELECT symbol, COUNT(*) as count, AVG(quantity) as avg_qty
                FROM trades WHERE executed_at >= ?
                GROUP BY symbol ORDER BY count DESC LIMIT 10
            """, (cutoff,))
            top_symbols = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'hours': hours,
                'total_trades': total_trades,
                'by_type': by_type,
                'top_symbols': top_symbols
            }
        except Exception as e:
            logger.error(f"Error getting trading activity: {e}")
            return {}
    
    def get_league_activity(self) -> List[Dict[str, Any]]:
        """Get activity per league"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT l.id, l.name, l.creator_id,
                       COUNT(DISTINCT lm.user_id) as member_count,
                       COUNT(DISTINCT t.id) as trade_count,
                       MAX(t.executed_at) as last_trade
                FROM leagues l
                LEFT JOIN league_members lm ON l.id = lm.league_id
                LEFT JOIN trades t ON l.id = t.league_id
                WHERE l.soft_deleted_at IS NULL
                GROUP BY l.id
                ORDER BY trade_count DESC
                LIMIT 50
            """)
            
            leagues = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return leagues
        except Exception as e:
            logger.error(f"Error getting league activity: {e}")
            return []
    
    def get_user_risk_assessment(self) -> List[Dict[str, Any]]:
        """Identify potentially problematic user behavior"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Users with suspicious activity patterns
            cursor.execute("""
                SELECT u.id, u.username, 
                       COUNT(DISTINCT t.id) as trades_count,
                       COUNT(CASE WHEN t.trade_type = 'buy' THEN 1 END) as buys,
                       COUNT(CASE WHEN t.trade_type = 'sell' THEN 1 END) as sells,
                       ROUND(COUNT(CASE WHEN t.executed_at >= datetime('now', '-1 hour') THEN 1 END), 0) as recent_trades
                FROM users u
                LEFT JOIN trades t ON u.id = t.user_id AND t.executed_at >= datetime('now', '-7 days')
                GROUP BY u.id
                HAVING trades_count > 100
                ORDER BY trades_count DESC
                LIMIT 20
            """)
            
            high_volume_traders = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return high_volume_traders
        except Exception as e:
            logger.error(f"Error assessing user risk: {e}")
            return []
    
    def get_engagement_metrics(self) -> Dict[str, Any]:
        """Get user engagement metrics"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Daily active users trend (last 7 days)
            cursor.execute("""
                SELECT DATE(last_login) as date, COUNT(*) as active
                FROM users WHERE last_login >= datetime('now', '-7 days')
                GROUP BY DATE(last_login)
                ORDER BY date DESC
            """)
            
            daily_active = [dict(row) for row in cursor.fetchall()]
            
            # League formation trend
            cursor.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as leagues
                FROM leagues WHERE created_at >= datetime('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)
            
            league_trend = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'daily_active_users': daily_active,
                'league_creation_trend': league_trend
            }
        except Exception as e:
            logger.error(f"Error getting engagement metrics: {e}")
            return {}


class AlertManager:
    """Manage system alerts and notifications"""
    
    def __init__(self, db):
        """
        Initialize alert manager.
        
        Args:
            db: DatabaseManager instance
        """
        self.db = db
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Create alert tables if they don't exist"""
        cursor = self.db.get_connection().cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT DEFAULT 'info',
                title TEXT NOT NULL,
                message TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                is_resolved INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_alerts_severity ON system_alerts(severity, is_resolved)
        ''')
        
        self.db.get_connection().commit()
    
    def create_alert(self, alert_type: str, title: str, message: str = "", 
                    severity: str = "info", data: Optional[Dict] = None) -> int:
        """
        Create a system alert.
        
        Args:
            alert_type: Type of alert (e.g., 'high_load', 'database_error')
            title: Alert title
            message: Alert message
            severity: 'info', 'warning', 'error', 'critical'
            data: Additional JSON data
            
        Returns:
            Alert ID
        """
        try:
            cursor = self.db.get_connection().cursor()
            
            cursor.execute('''
                INSERT INTO system_alerts 
                (alert_type, severity, title, message, data)
                VALUES (?, ?, ?, ?, ?)
            ''', (alert_type, severity, title, message, json.dumps(data) if data else None))
            
            self.db.get_connection().commit()
            alert_id = cursor.lastrowid
            
            logger.warning(f"Alert {alert_id}: {severity.upper()} - {title}")
            return alert_id
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return 0
    
    def resolve_alert(self, alert_id: int) -> bool:
        """Resolve an alert"""
        try:
            cursor = self.db.get_connection().cursor()
            
            cursor.execute('''
                UPDATE system_alerts
                SET is_resolved = 1, resolved_at = ?
                WHERE id = ?
            ''', (datetime.now(), alert_id))
            
            self.db.get_connection().commit()
            return True
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False
    
    def get_active_alerts(self, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active (unresolved) alerts"""
        try:
            cursor = self.db.get_connection().cursor()
            
            if severity:
                cursor.execute('''
                    SELECT * FROM system_alerts
                    WHERE is_resolved = 0 AND severity = ?
                    ORDER BY created_at DESC
                ''', (severity,))
            else:
                cursor.execute('''
                    SELECT * FROM system_alerts
                    WHERE is_resolved = 0
                    ORDER BY created_at DESC
                ''')
            
            alerts = [dict(row) for row in cursor.fetchall()]
            
            # Parse JSON data
            for alert in alerts:
                if alert.get('data'):
                    try:
                        alert['data'] = json.loads(alert['data'])
                    except:
                        pass
            
            return alerts
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics"""
        try:
            cursor = self.db.get_connection().cursor()
            
            # Count by severity
            cursor.execute('''
                SELECT severity, COUNT(*) as count
                FROM system_alerts WHERE is_resolved = 0
                GROUP BY severity
            ''')
            
            by_severity = {row['severity']: row['count'] for row in cursor.fetchall()}
            
            # Total
            cursor.execute("SELECT COUNT(*) as total FROM system_alerts WHERE is_resolved = 0")
            total = cursor.fetchone()['total']
            
            return {
                'total_active': total,
                'by_severity': by_severity
            }
        except Exception as e:
            logger.error(f"Error getting alert stats: {e}")
            return {}


class HealthChecker:
    """System health checks"""
    
    def __init__(self, db, cache_manager=None):
        """
        Initialize health checker.
        
        Args:
            db: DatabaseManager instance
            cache_manager: CacheManager instance (optional)
        """
        self.db = db
        self.cache = cache_manager
        self.last_check = None
        self.health_status = 'healthy'
    
    def check_database(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            
            return {'status': 'healthy', 'message': 'Database is responding'}
        except Exception as e:
            return {'status': 'unhealthy', 'message': f"Database error: {e}"}
    
    def check_cache(self) -> Dict[str, Any]:
        """Check cache health"""
        if not self.cache or not self.cache.redis:
            return {'status': 'not_configured', 'message': 'Cache not configured'}
        
        try:
            self.cache.redis.ping()
            return {'status': 'healthy', 'message': 'Cache is responding'}
        except Exception as e:
            return {'status': 'unhealthy', 'message': f"Cache error: {e}"}
    
    def full_health_check(self) -> Dict[str, Any]:
        """Perform full system health check"""
        self.last_check = datetime.now()
        
        results = {
            'timestamp': self.last_check.isoformat(),
            'database': self.check_database(),
            'cache': self.check_cache()
        }
        
        # Determine overall status
        statuses = [r['status'] for r in results.values() if isinstance(r, dict) and 'status' in r]
        if all(s == 'healthy' for s in statuses):
            self.health_status = 'healthy'
        elif any(s == 'unhealthy' for s in statuses):
            self.health_status = 'unhealthy'
        else:
            self.health_status = 'degraded'
        
        results['overall_status'] = self.health_status
        
        return results
