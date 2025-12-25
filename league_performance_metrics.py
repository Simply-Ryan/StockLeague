"""
League Performance Metrics Service - Phase 3.2
Calculates and tracks performance metrics for league members
Includes portfolio analysis, trade statistics, and comparative metrics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from database.db_manager import DatabaseManager

# Configure logger
logger = logging.getLogger('league_metrics')
logger.setLevel(logging.INFO)


class LeaguePerformanceMetrics:
    """Service for calculating league member performance metrics"""
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        """Initialize metrics service"""
        self.db = db or DatabaseManager()
        self.logger = logger
    
    def get_user_league_metrics(self, league_id: int, user_id: int) -> Tuple[bool, Dict, Optional[str]]:
        """
        Get comprehensive metrics for a user in a league
        
        Returns:
            (success, metrics_dict, error_message)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get basic user info and portfolio value
            cursor.execute('''
                SELECT u.id, u.username, u.cash,
                       SUM(CASE WHEN p.league_id = ? THEN p.shares ELSE 0 END) as league_shares,
                       SUM(CASE WHEN p.league_id = ? THEN p.shares * 
                           (SELECT price FROM stocks WHERE symbol = p.symbol LIMIT 1) ELSE 0 END) as league_holdings
                FROM users u
                LEFT JOIN portfolios p ON u.id = p.user_id
                WHERE u.id = ?
                GROUP BY u.id
            ''', (league_id, league_id, user_id))
            
            user_result = cursor.fetchone()
            if not user_result:
                conn.close()
                return False, {}, 'User not found'
            
            user_id, username, cash, league_shares, league_holdings = user_result
            portfolio_value = cash + (league_holdings or 0)
            
            # Get trade statistics
            cursor.execute('''
                SELECT COUNT(*),
                       SUM(CASE WHEN type = 'buy' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN type = 'sell' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END),
                       SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END),
                       SUM(profit),
                       AVG(profit),
                       MAX(profit),
                       MIN(profit)
                FROM trades
                WHERE user_id = ? AND league_id = ?
            ''', (user_id, league_id))
            
            trade_result = cursor.fetchone()
            if trade_result and trade_result[0]:
                total_trades, buy_count, sell_count = trade_result[0], trade_result[1], trade_result[2]
                winning_trades = trade_result[3] or 0
                losing_trades = trade_result[4] or 0
                total_profit = trade_result[5] or 0
                avg_profit = trade_result[6] or 0
                best_trade = trade_result[7] or 0
                worst_trade = trade_result[8] or 0
                win_rate = winning_trades / total_trades if total_trades > 0 else 0
            else:
                total_trades = buy_count = sell_count = winning_trades = losing_trades = 0
                total_profit = avg_profit = best_trade = worst_trade = 0
                win_rate = 0
            
            # Get daily performance
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            cursor.execute('''
                SELECT SUM(profit) FROM trades
                WHERE user_id = ? AND league_id = ? AND created_at > ?
            ''', (user_id, league_id, today_start))
            
            daily_result = cursor.fetchone()
            daily_pl = daily_result[0] or 0 if daily_result else 0
            daily_pl_pct = (daily_pl / (portfolio_value - daily_pl)) * 100 if (portfolio_value - daily_pl) > 0 else 0
            
            # Get weekly and monthly performance
            week_start = (datetime.now() - timedelta(days=7)).isoformat()
            month_start = (datetime.now() - timedelta(days=30)).isoformat()
            
            cursor.execute('''
                SELECT SUM(profit) FROM trades
                WHERE user_id = ? AND league_id = ? AND created_at > ?
            ''', (user_id, league_id, week_start))
            weekly_pl = cursor.fetchone()[0] or 0
            
            cursor.execute('''
                SELECT SUM(profit) FROM trades
                WHERE user_id = ? AND league_id = ? AND created_at > ?
            ''', (user_id, league_id, month_start))
            monthly_pl = cursor.fetchone()[0] or 0
            
            # Get best performing stock
            cursor.execute('''
                SELECT symbol, SUM(profit) as total_profit
                FROM trades
                WHERE user_id = ? AND league_id = ?
                GROUP BY symbol
                ORDER BY total_profit DESC
                LIMIT 1
            ''', (user_id, league_id))
            
            best_stock_result = cursor.fetchone()
            best_stock = best_stock_result[0] if best_stock_result else 'N/A'
            
            # Get league rank and comparison stats
            cursor.execute('''
                SELECT COUNT(*) FROM league_members
                WHERE league_id = ?
            ''', (league_id,))
            
            member_count = cursor.fetchone()[0]
            
            # Calculate rank (based on portfolio value - would be more sophisticated in production)
            cursor.execute('''
                SELECT COUNT(*) + 1 FROM (
                    SELECT DISTINCT u.id, u.cash + COALESCE(SUM(p.shares * 
                        (SELECT price FROM stocks WHERE symbol = p.symbol LIMIT 1)), 0) as portfolio_value
                    FROM users u
                    LEFT JOIN portfolios p ON u.id = p.user_id
                    WHERE u.id IN (
                        SELECT user_id FROM league_members WHERE league_id = ?
                    )
                    GROUP BY u.id
                    HAVING portfolio_value > ?
                )
            ''', (league_id, portfolio_value))
            
            rank = cursor.fetchone()[0]
            
            # Get league averages for comparison
            cursor.execute('''
                SELECT AVG(u.cash + COALESCE(portfolio_holdings, 0)) as avg_portfolio,
                       AVG(win_rate) as avg_win_rate,
                       AVG(trade_count) as avg_trades
                FROM (
                    SELECT u.id,
                           u.cash,
                           COALESCE(SUM(p.shares * 
                               (SELECT price FROM stocks WHERE symbol = p.symbol LIMIT 1)), 0) as portfolio_holdings,
                           SUM(CASE WHEN t.profit > 0 THEN 1.0 ELSE 0 END) / 
                               NULLIF(COUNT(DISTINCT t.id), 0) as win_rate,
                           COUNT(DISTINCT t.id) as trade_count
                    FROM users u
                    LEFT JOIN portfolios p ON u.id = p.user_id
                    LEFT JOIN trades t ON u.id = t.user_id AND t.league_id = ?
                    WHERE u.id IN (
                        SELECT user_id FROM league_members WHERE league_id = ?
                    )
                    GROUP BY u.id
                )
            ''', (league_id, league_id))
            
            comparison_result = cursor.fetchone()
            if comparison_result:
                avg_portfolio = comparison_result[0] or 0
                avg_win_rate = comparison_result[1] or 0
                avg_trades = comparison_result[2] or 0
            else:
                avg_portfolio = avg_win_rate = avg_trades = 0
            
            conn.close()
            
            metrics = {
                'user_id': user_id,
                'username': username,
                'portfolio_value': round(portfolio_value, 2),
                'league_shares': league_shares or 0,
                'rank': rank,
                'rank_percentile': round((1 - rank / max(member_count, 1)) * 100, 1),
                'daily_pl': round(daily_pl, 2),
                'daily_pl_pct': round(daily_pl_pct, 2),
                'weekly_pl': round(weekly_pl, 2),
                'monthly_pl': round(monthly_pl, 2),
                'ytd_pl': round(total_profit, 2),  # Year-to-date
                'total_trades': total_trades,
                'buy_trades': buy_count or 0,
                'sell_trades': sell_count or 0,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 3),
                'avg_profit_per_trade': round(avg_profit, 2),
                'best_trade': round(best_trade, 2),
                'worst_trade': round(worst_trade, 2),
                'best_stock': best_stock,
                'league_comparison': {
                    'avg_portfolio': round(avg_portfolio, 2),
                    'portfolio_vs_average': round(portfolio_value - avg_portfolio, 2),
                    'avg_win_rate': round(avg_win_rate, 3),
                    'win_rate_vs_average': round(win_rate - avg_win_rate, 3),
                    'avg_trades': round(avg_trades, 1),
                    'trades_vs_average': round(total_trades - avg_trades, 1),
                },
                'member_count': member_count,
            }
            
            self.logger.info(f"Metrics retrieved for user {user_id} in league {league_id}")
            return True, metrics, None
            
        except Exception as e:
            self.logger.error(f"Error calculating metrics: {e}")
            return False, {}, str(e)
    
    def get_league_performance_breakdown(self, league_id: int) -> Tuple[bool, Dict, Optional[str]]:
        """
        Get comprehensive performance breakdown for entire league
        
        Returns:
            (success, breakdown_dict, error_message)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get member rankings with performance stats
            cursor.execute('''
                SELECT u.id, u.username, 
                       u.cash + COALESCE(SUM(p.shares * 
                           (SELECT price FROM stocks WHERE symbol = p.symbol LIMIT 1)), 0) as portfolio_value,
                       COUNT(DISTINCT t.id) as trade_count,
                       SUM(CASE WHEN t.profit > 0 THEN 1 ELSE 0 END) as winning_trades,
                       SUM(CASE WHEN t.profit > 0 THEN 1.0 ELSE 0 END) / 
                           NULLIF(COUNT(DISTINCT t.id), 0) as win_rate,
                       SUM(t.profit) as total_profit
                FROM users u
                LEFT JOIN portfolios p ON u.id = p.user_id AND p.league_id = ?
                LEFT JOIN trades t ON u.id = t.user_id AND t.league_id = ?
                WHERE u.id IN (
                    SELECT user_id FROM league_members WHERE league_id = ?
                )
                GROUP BY u.id
                ORDER BY portfolio_value DESC
            ''', (league_id, league_id, league_id))
            
            rankings = []
            for idx, row in enumerate(cursor.fetchall(), 1):
                rankings.append({
                    'rank': idx,
                    'user_id': row[0],
                    'username': row[1],
                    'portfolio_value': round(row[2] or 0, 2),
                    'trade_count': row[3] or 0,
                    'winning_trades': row[4] or 0,
                    'win_rate': round(row[5] or 0, 3),
                    'total_profit': round(row[6] or 0, 2),
                })
            
            # Get league-wide statistics
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id),
                       AVG(portfolio_value) as avg_portfolio,
                       SUM(total_trades) as total_league_trades,
                       SUM(total_profit) as total_league_profit
                FROM (
                    SELECT u.id as user_id,
                           u.cash + COALESCE(SUM(p.shares * 
                               (SELECT price FROM stocks WHERE symbol = p.symbol LIMIT 1)), 0) as portfolio_value,
                           COUNT(DISTINCT t.id) as total_trades,
                           SUM(t.profit) as total_profit
                    FROM users u
                    LEFT JOIN portfolios p ON u.id = p.user_id AND p.league_id = ?
                    LEFT JOIN trades t ON u.id = t.user_id AND t.league_id = ?
                    WHERE u.id IN (
                        SELECT user_id FROM league_members WHERE league_id = ?
                    )
                    GROUP BY u.id
                )
            ''', (league_id, league_id, league_id))
            
            stats_result = cursor.fetchone()
            if stats_result:
                active_members = stats_result[0]
                avg_portfolio = stats_result[1] or 0
                total_trades = stats_result[2] or 0
                total_profit = stats_result[3] or 0
            else:
                active_members = 0
                avg_portfolio = total_trades = total_profit = 0
            
            # Get most active stocks
            cursor.execute('''
                SELECT symbol, COUNT(*) as trade_count, SUM(profit) as total_profit
                FROM trades
                WHERE league_id = ?
                GROUP BY symbol
                ORDER BY trade_count DESC
                LIMIT 10
            ''', (league_id,))
            
            popular_stocks = []
            for row in cursor.fetchall():
                popular_stocks.append({
                    'symbol': row[0],
                    'trades': row[1],
                    'total_profit': round(row[2] or 0, 2),
                })
            
            conn.close()
            
            breakdown = {
                'league_id': league_id,
                'member_count': len(rankings),
                'active_members': active_members,
                'avg_portfolio_value': round(avg_portfolio, 2),
                'total_league_trades': total_trades,
                'total_league_profit': round(total_profit, 2),
                'rankings': rankings,
                'popular_stocks': popular_stocks,
            }
            
            self.logger.info(f"Performance breakdown retrieved for league {league_id}")
            return True, breakdown, None
            
        except Exception as e:
            self.logger.error(f"Error getting league breakdown: {e}")
            return False, {}, str(e)
    
    def get_performance_history(self, league_id: int, user_id: int, 
                                days: int = 30) -> Tuple[bool, List[Dict], Optional[str]]:
        """
        Get historical performance data for a user
        
        Returns:
            (success, daily_performance_list, error_message)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            start_date = (datetime.now() - timedelta(days=days)).date()
            
            # Get daily performance snapshots
            cursor.execute('''
                SELECT DATE(created_at) as date,
                       COUNT(*) as trades,
                       SUM(CASE WHEN type = 'buy' THEN 1 ELSE 0 END) as buys,
                       SUM(CASE WHEN type = 'sell' THEN 1 ELSE 0 END) as sells,
                       SUM(profit) as daily_profit,
                       SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades
                FROM trades
                WHERE user_id = ? AND league_id = ? AND DATE(created_at) >= ?
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            ''', (user_id, league_id, start_date))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'date': row[0],
                    'trade_count': row[1],
                    'buy_count': row[2] or 0,
                    'sell_count': row[3] or 0,
                    'daily_profit': round(row[4] or 0, 2),
                    'winning_trades': row[5] or 0,
                })
            
            conn.close()
            
            self.logger.info(f"Performance history retrieved for user {user_id} in league {league_id}")
            return True, history, None
            
        except Exception as e:
            self.logger.error(f"Error getting performance history: {e}")
            return False, [], str(e)
    
    def calculate_risk_metrics(self, league_id: int, user_id: int) -> Tuple[bool, Dict, Optional[str]]:
        """
        Calculate risk metrics for a user
        
        Returns:
            (success, risk_metrics_dict, error_message)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get portfolio concentration
            cursor.execute('''
                SELECT symbol, SUM(shares) as total_shares,
                       SUM(shares * (SELECT price FROM stocks WHERE symbol = portfolios.symbol LIMIT 1)) as value
                FROM portfolios
                WHERE user_id = ? AND league_id = ?
                GROUP BY symbol
                ORDER BY value DESC
            ''', (user_id, league_id))
            
            positions = cursor.fetchall()
            
            if positions:
                total_value = sum(p[2] or 0 for p in positions)
                concentration = []
                max_position_pct = 0
                
                for symbol, shares, value in positions:
                    pct = (value / total_value * 100) if total_value > 0 else 0
                    concentration.append({
                        'symbol': symbol,
                        'shares': shares,
                        'value': round(value or 0, 2),
                        'pct_of_portfolio': round(pct, 1),
                    })
                    max_position_pct = max(max_position_pct, pct)
                
                # Top 5 positions represent what % of portfolio
                top_5_pct = sum(c['pct_of_portfolio'] for c in concentration[:5])
            else:
                concentration = []
                max_position_pct = 0
                top_5_pct = 0
            
            # Get volatility of returns
            cursor.execute('''
                SELECT profit FROM trades
                WHERE user_id = ? AND league_id = ?
                ORDER BY created_at DESC
                LIMIT 100
            ''', (user_id, league_id))
            
            profits = [row[0] for row in cursor.fetchall() if row[0] is not None]
            
            if len(profits) > 1:
                avg_profit = sum(profits) / len(profits)
                variance = sum((p - avg_profit) ** 2 for p in profits) / len(profits)
                volatility = variance ** 0.5
            else:
                volatility = 0
            
            conn.close()
            
            risk_metrics = {
                'portfolio_concentration': {
                    'max_position_pct': round(max_position_pct, 1),
                    'top_5_positions_pct': round(top_5_pct, 1),
                    'diversification_level': 'High' if max_position_pct < 15 else 'Medium' if max_position_pct < 30 else 'Low',
                    'positions': concentration,
                },
                'profit_volatility': round(volatility, 2),
                'trading_consistency': 'High' if volatility < 100 else 'Medium' if volatility < 500 else 'Low',
            }
            
            self.logger.info(f"Risk metrics calculated for user {user_id} in league {league_id}")
            return True, risk_metrics, None
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            return False, {}, str(e)


if __name__ == '__main__':
    metrics_service = LeaguePerformanceMetrics()
    print("League Performance Metrics service loaded")
