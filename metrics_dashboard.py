"""
Metrics Dashboard - League Performance Analytics
Provides comprehensive league and user performance visualization
"""

import json
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
from database.db_manager import DatabaseManager
from league_performance_metrics import LeaguePerformanceMetrics

class MetricsDashboard:
    """
    Generates performance metrics and analytics for dashboard display
    """
    
    def __init__(self, db: DatabaseManager = None):
        self.db = db or DatabaseManager()
        self.metrics = LeaguePerformanceMetrics(db=self.db)
    
    def get_user_dashboard(self, league_id: int, user_id: int) -> Tuple[bool, Dict[str, Any], str]:
        """
        Get personalized dashboard for a user
        Returns: (success, dashboard_data, error)
        """
        try:
            dashboard = {}
            
            # Get user metrics
            success, metrics, error = self.metrics.get_user_league_metrics(league_id, user_id)
            if success:
                dashboard['user_metrics'] = metrics
                dashboard['portfolio_value'] = metrics.get('portfolio_value', 0)
                dashboard['rank'] = metrics.get('rank', '--')
                dashboard['rank_percentile'] = metrics.get('rank_percentile', 0)
                dashboard['win_rate'] = metrics.get('win_rate', 0)
            else:
                return False, {}, error
            
            # Get risk metrics
            success, risk, error = self.metrics.calculate_risk_metrics(league_id, user_id)
            if success:
                dashboard['risk_metrics'] = risk
            
            # Get performance history
            success, history, error = self.metrics.get_performance_history(league_id, user_id, days=30)
            if success:
                dashboard['performance_history'] = history
            
            # Get performance charts data
            dashboard['charts'] = self._prepare_chart_data(dashboard)
            
            return True, dashboard, None
            
        except Exception as e:
            return False, {}, str(e)
    
    def get_league_dashboard(self, league_id: int) -> Tuple[bool, Dict[str, Any], str]:
        """
        Get league-wide analytics dashboard
        Returns: (success, dashboard_data, error)
        """
        try:
            dashboard = {}
            
            # Get league performance breakdown
            success, breakdown, error = self.metrics.get_league_performance_breakdown(league_id)
            if success:
                dashboard['rankings'] = breakdown.get('rankings', [])
                dashboard['total_members'] = breakdown.get('member_count', 0)
                dashboard['avg_portfolio'] = breakdown.get('average_portfolio_value', 0)
                dashboard['total_trades'] = breakdown.get('total_trades', 0)
                dashboard['popular_stocks'] = breakdown.get('popular_stocks', [])
            else:
                return False, {}, error
            
            # Get league analytics
            success, analytics, error = self._get_league_analytics(league_id)
            if success:
                dashboard['analytics'] = analytics
            
            # Get trending activities
            dashboard['trending_activities'] = self._get_trending_activities(league_id)
            
            # Get league stats summary
            dashboard['stats'] = self._get_league_stats_summary(league_id)
            
            # Prepare visualization data
            dashboard['charts'] = self._prepare_league_charts(league_id, dashboard)
            
            return True, dashboard, None
            
        except Exception as e:
            return False, {}, str(e)
    
    def _prepare_chart_data(self, user_dashboard: Dict) -> Dict[str, Any]:
        """Prepare data for user charts"""
        charts = {}
        
        # Portfolio value over time
        if 'performance_history' in user_dashboard:
            history = user_dashboard['performance_history']
            charts['portfolio_history'] = {
                'dates': [h.get('snapshot_date') for h in history],
                'values': [h.get('portfolio_value', 0) for h in history],
                'type': 'line'
            }
            
            # P&L over time
            charts['pl_history'] = {
                'dates': [h.get('snapshot_date') for h in history],
                'daily': [h.get('daily_pl', 0) for h in history],
                'cumulative': [h.get('total_pl', 0) for h in history],
                'type': 'combo'
            }
        
        # Win rate gauge
        if 'user_metrics' in user_dashboard:
            charts['win_rate_gauge'] = {
                'value': user_dashboard['user_metrics'].get('win_rate', 0),
                'max': 100,
                'type': 'gauge'
            }
        
        # Risk profile
        if 'risk_metrics' in user_dashboard:
            risk = user_dashboard['risk_metrics']
            charts['risk_profile'] = {
                'concentration': risk.get('portfolio_concentration', {}).get('diversification_level', 0),
                'volatility': risk.get('profit_volatility', 0),
                'consistency': risk.get('trading_consistency', 0),
                'type': 'radar'
            }
        
        return charts
    
    def _prepare_league_charts(self, league_id: int, dashboard: Dict) -> Dict[str, Any]:
        """Prepare data for league charts"""
        charts = {}
        
        # Rankings distribution
        if 'rankings' in dashboard:
            rankings = dashboard['rankings']
            charts['rankings'] = {
                'labels': [r.get('username', 'User') for r in rankings[:10]],
                'values': [r.get('portfolio_value', 0) for r in rankings[:10]],
                'type': 'bar'
            }
        
        # Top performers
        if 'rankings' in dashboard:
            top_5 = dashboard['rankings'][:5]
            charts['top_performers'] = {
                'performers': top_5,
                'type': 'table'
            }
        
        # Popular stocks
        if 'popular_stocks' in dashboard:
            stocks = dashboard['popular_stocks'][:10]
            charts['popular_stocks'] = {
                'symbols': [s.get('symbol') for s in stocks],
                'counts': [s.get('trade_count', 0) for s in stocks],
                'type': 'horizontal_bar'
            }
        
        # Trading activity heatmap
        charts['activity_heatmap'] = {
            'data': self._get_activity_heatmap(league_id),
            'type': 'heatmap'
        }
        
        return charts
    
    def _get_league_analytics(self, league_id: int) -> Tuple[bool, Dict, str]:
        """Get comprehensive league analytics"""
        try:
            cursor = self.db.get_connection().cursor()
            
            # Get latest analytics entry
            cursor.execute("""
                SELECT total_volume, average_portfolio_value, average_win_rate,
                       member_count, active_traders_count, total_trades_count
                FROM league_analytics
                WHERE league_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (league_id,))
            
            result = cursor.fetchone()
            if result:
                analytics = {
                    'total_volume': result[0] or 0,
                    'average_portfolio': result[1] or 0,
                    'average_win_rate': result[2] or 0,
                    'member_count': result[3] or 0,
                    'active_traders': result[4] or 0,
                    'total_trades': result[5] or 0
                }
                return True, analytics, None
            else:
                return True, {}, None
        except Exception as e:
            return False, {}, str(e)
    
    def _get_trending_activities(self, league_id: int, limit: int = 5) -> List[Dict]:
        """Get trending activities in the league"""
        try:
            cursor = self.db.get_connection().cursor()
            
            cursor.execute("""
                SELECT activity_type, COUNT(*) as count, MAX(created_at) as last_activity
                FROM league_activity_log
                WHERE league_id = ? AND created_at > datetime('now', '-7 days')
                GROUP BY activity_type
                ORDER BY count DESC
                LIMIT ?
            """, (league_id, limit))
            
            trending = []
            for row in cursor.fetchall():
                trending.append({
                    'activity_type': row[0],
                    'count': row[1],
                    'last_activity': row[2]
                })
            
            return trending
        except Exception as e:
            return []
    
    def _get_league_stats_summary(self, league_id: int) -> Dict[str, Any]:
        """Get summary statistics for the league"""
        try:
            cursor = self.db.get_connection().cursor()
            
            # Count members
            cursor.execute("SELECT COUNT(*) FROM league_members WHERE league_id = ?", (league_id,))
            member_count = cursor.fetchone()[0] or 0
            
            # Count trades
            cursor.execute(
                "SELECT COUNT(*) FROM league_activity_log WHERE league_id = ? AND activity_type LIKE 'trade_%'",
                (league_id,)
            )
            trade_count = cursor.fetchone()[0] or 0
            
            # Get avg portfolio value
            cursor.execute("""
                SELECT AVG(portfolio_value) FROM league_performance_snapshots 
                WHERE league_id = ? AND snapshot_date = date('now')
            """, (league_id,))
            avg_portfolio = cursor.fetchone()[0] or 0
            
            # Get total volume
            cursor.execute("""
                SELECT COALESCE(SUM(CAST(metadata ->> '$.shares' AS REAL) * 
                       CAST(metadata ->> '$.price' AS REAL)), 0)
                FROM league_activity_log
                WHERE league_id = ? AND activity_type = 'trade_buy'
            """, (league_id,))
            total_volume = cursor.fetchone()[0] or 0
            
            return {
                'members': member_count,
                'trades': trade_count,
                'avg_portfolio': avg_portfolio,
                'total_volume': total_volume
            }
        except Exception as e:
            return {}
    
    def _get_activity_heatmap(self, league_id: int) -> List[List]:
        """Get activity heatmap data (activity by day and hour)"""
        try:
            cursor = self.db.get_connection().cursor()
            
            # Get activities grouped by day of week and hour
            cursor.execute("""
                SELECT 
                    strftime('%w', created_at) as day_of_week,
                    strftime('%H', created_at) as hour,
                    COUNT(*) as count
                FROM league_activity_log
                WHERE league_id = ? AND created_at > datetime('now', '-30 days')
                GROUP BY day_of_week, hour
            """, (league_id,))
            
            # Build 7x24 matrix
            heatmap = [[0 for _ in range(24)] for _ in range(7)]
            
            for row in cursor.fetchall():
                day = int(row[0]) if row[0] else 0
                hour = int(row[1]) if row[1] else 0
                count = row[2]
                heatmap[day][hour] = count
            
            return heatmap
        except Exception as e:
            return []
    
    def export_dashboard_json(self, league_id: int, user_id: int = None) -> Tuple[bool, str, str]:
        """Export dashboard data as JSON"""
        try:
            if user_id:
                success, data, error = self.get_user_dashboard(league_id, user_id)
                if not success:
                    return False, "", error
                filename = f"dashboard_user_{user_id}_league_{league_id}.json"
            else:
                success, data, error = self.get_league_dashboard(league_id)
                if not success:
                    return False, "", error
                filename = f"dashboard_league_{league_id}.json"
            
            # Convert to JSON
            json_data = json.dumps(data, indent=2, default=str)
            
            # Save to file
            with open(filename, 'w') as f:
                f.write(json_data)
            
            return True, filename, None
        except Exception as e:
            return False, "", str(e)


if __name__ == '__main__':
    # Example usage
    print("Metrics Dashboard Module")
    print("=" * 70)
    
    dashboard = MetricsDashboard()
    
    print("\nAvailable methods:")
    print("  - get_user_dashboard(league_id, user_id)")
    print("  - get_league_dashboard(league_id)")
    print("  - export_dashboard_json(league_id, user_id=None)")
