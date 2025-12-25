"""
Advanced Portfolio Analytics for StockLeague
Performance attribution, risk metrics, and detailed analytics
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class PerformanceAnalytics:
    """Calculate portfolio performance metrics"""
    
    def __init__(self, db):
        """
        Initialize performance analytics.
        
        Args:
            db: DatabaseManager instance
        """
        self.db = db
    
    def calculate_returns(self, user_id: int, league_id: int, period_days: int = 30) -> Dict[str, float]:
        """
        Calculate portfolio returns for period.
        
        Args:
            user_id: User ID
            league_id: League ID
            period_days: Number of days to analyze
            
        Returns:
            Returns metrics dictionary
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get portfolio snapshots at start and end
            cutoff = datetime.now() - timedelta(days=period_days)
            
            cursor.execute("""
                SELECT cash, stock_value, option_value, total_value
                FROM portfolio_snapshots
                WHERE user_id = ? AND league_id = ? AND timestamp <= ?
                ORDER BY timestamp ASC
                LIMIT 1
            """, (user_id, league_id, cutoff))
            
            start_snapshot = cursor.fetchone()
            
            cursor.execute("""
                SELECT cash, stock_value, option_value, total_value
                FROM portfolio_snapshots
                WHERE user_id = ? AND league_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (user_id, league_id))
            
            end_snapshot = cursor.fetchone()
            conn.close()
            
            if not start_snapshot or not end_snapshot:
                return {
                    'total_return': 0,
                    'total_return_percent': 0,
                    'period_days': period_days
                }
            
            starting_value = start_snapshot['total_value']
            ending_value = end_snapshot['total_value']
            
            total_return = ending_value - starting_value
            total_return_percent = (total_return / starting_value * 100) if starting_value > 0 else 0
            
            # Calculate annualized return
            years = period_days / 365.0
            annualized_return = (((ending_value / starting_value) ** (1 / years)) - 1) * 100 if years > 0 else 0
            
            return {
                'starting_value': round(starting_value, 2),
                'ending_value': round(ending_value, 2),
                'total_return': round(total_return, 2),
                'total_return_percent': round(total_return_percent, 2),
                'annualized_return_percent': round(annualized_return, 2),
                'period_days': period_days
            }
        except Exception as e:
            logger.error(f"Error calculating returns: {e}")
            return {}
    
    def calculate_sharpe_ratio(self, user_id: int, league_id: int, period_days: int = 30,
                              risk_free_rate: float = 0.045) -> float:
        """
        Calculate Sharpe ratio (risk-adjusted return).
        
        Args:
            user_id: User ID
            league_id: League ID
            period_days: Period to analyze
            risk_free_rate: Annual risk-free rate (default 4.5%)
            
        Returns:
            Sharpe ratio
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cutoff = datetime.now() - timedelta(days=period_days)
            
            # Get daily returns
            cursor.execute("""
                SELECT DATE(timestamp) as date, total_value
                FROM portfolio_snapshots
                WHERE user_id = ? AND league_id = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            """, (user_id, league_id, cutoff))
            
            snapshots = cursor.fetchall()
            conn.close()
            
            if len(snapshots) < 2:
                return 0
            
            # Calculate daily returns
            returns = []
            for i in range(1, len(snapshots)):
                prev_value = snapshots[i-1]['total_value']
                curr_value = snapshots[i]['total_value']
                if prev_value > 0:
                    daily_return = (curr_value - prev_value) / prev_value
                    returns.append(daily_return)
            
            if not returns:
                return 0
            
            # Calculate mean return and std dev
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_dev = math.sqrt(variance)
            
            # Daily risk-free rate
            daily_rf = (risk_free_rate / 365.0)
            
            # Sharpe ratio
            if std_dev == 0:
                return 0
            
            sharpe = (mean_return - daily_rf) / std_dev
            return round(sharpe * math.sqrt(252), 4)  # Annualized
            
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0
    
    def calculate_volatility(self, user_id: int, league_id: int, period_days: int = 30) -> float:
        """
        Calculate portfolio volatility (standard deviation of returns).
        
        Args:
            user_id: User ID
            league_id: League ID
            period_days: Period to analyze
            
        Returns:
            Annualized volatility percentage
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cutoff = datetime.now() - timedelta(days=period_days)
            
            cursor.execute("""
                SELECT total_value FROM portfolio_snapshots
                WHERE user_id = ? AND league_id = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            """, (user_id, league_id, cutoff))
            
            values = [row['total_value'] for row in cursor.fetchall()]
            conn.close()
            
            if len(values) < 2:
                return 0
            
            # Calculate daily returns
            returns = []
            for i in range(1, len(values)):
                if values[i-1] > 0:
                    daily_return = (values[i] - values[i-1]) / values[i-1]
                    returns.append(daily_return)
            
            if not returns:
                return 0
            
            # Standard deviation
            mean = sum(returns) / len(returns)
            variance = sum((r - mean) ** 2 for r in returns) / len(returns)
            daily_vol = math.sqrt(variance)
            
            # Annualized
            annualized_vol = daily_vol * math.sqrt(252) * 100
            return round(annualized_vol, 2)
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return 0
    
    def calculate_max_drawdown(self, user_id: int, league_id: int, period_days: int = 30) -> Dict[str, Any]:
        """
        Calculate maximum drawdown from peak.
        
        Args:
            user_id: User ID
            league_id: League ID
            period_days: Period to analyze
            
        Returns:
            Max drawdown metrics
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cutoff = datetime.now() - timedelta(days=period_days)
            
            cursor.execute("""
                SELECT timestamp, total_value FROM portfolio_snapshots
                WHERE user_id = ? AND league_id = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            """, (user_id, league_id, cutoff))
            
            snapshots = cursor.fetchall()
            conn.close()
            
            if len(snapshots) < 2:
                return {'max_drawdown_percent': 0, 'drawdown_start': None, 'drawdown_end': None}
            
            max_value = snapshots[0]['total_value']
            max_drawdown = 0
            max_dd_start = snapshots[0]['timestamp']
            max_dd_end = snapshots[0]['timestamp']
            
            for snapshot in snapshots[1:]:
                curr_value = snapshot['total_value']
                
                if curr_value > max_value:
                    max_value = curr_value
                
                drawdown = (max_value - curr_value) / max_value if max_value > 0 else 0
                
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_dd_start = max_value
                    max_dd_end = snapshot['timestamp']
            
            return {
                'max_drawdown_percent': round(max_drawdown * 100, 2),
                'drawdown_start': max_dd_start,
                'drawdown_end': max_dd_end
            }
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return {}


class RiskAnalytics:
    """Calculate portfolio risk metrics"""
    
    def __init__(self, db):
        """Initialize risk analytics"""
        self.db = db
    
    def calculate_var(self, user_id: int, league_id: int, confidence: float = 0.95,
                     period_days: int = 30) -> Dict[str, Any]:
        """
        Calculate Value at Risk (VaR) at confidence level.
        
        Args:
            user_id: User ID
            league_id: League ID
            confidence: Confidence level (0.95 = 95%)
            period_days: Historical period
            
        Returns:
            VaR metrics
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cutoff = datetime.now() - timedelta(days=period_days)
            
            cursor.execute("""
                SELECT total_value FROM portfolio_snapshots
                WHERE user_id = ? AND league_id = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            """, (user_id, league_id, cutoff))
            
            values = [row['total_value'] for row in cursor.fetchall()]
            conn.close()
            
            if len(values) < 2:
                return {'var_percent': 0, 'confidence': confidence}
            
            # Calculate returns
            returns = []
            for i in range(1, len(values)):
                if values[i-1] > 0:
                    ret = (values[i] - values[i-1]) / values[i-1]
                    returns.append(ret)
            
            if not returns:
                return {'var_percent': 0, 'confidence': confidence}
            
            # Sort returns
            returns_sorted = sorted(returns)
            
            # Find percentile
            index = int(len(returns_sorted) * (1 - confidence))
            var_return = returns_sorted[index]
            var_percent = abs(var_return) * 100
            
            return {
                'var_percent': round(var_percent, 2),
                'var_amount': round(values[-1] * var_return, 2),
                'confidence': confidence,
                'interpretation': f"{confidence*100}% chance daily loss won't exceed {var_percent:.2f}%"
            }
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return {}
    
    def calculate_cvar(self, user_id: int, league_id: int, confidence: float = 0.95,
                      period_days: int = 30) -> Dict[str, Any]:
        """
        Calculate Conditional Value at Risk (CVaR/Expected Shortfall).
        
        Args:
            user_id: User ID
            league_id: League ID
            confidence: Confidence level
            period_days: Historical period
            
        Returns:
            CVaR metrics
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cutoff = datetime.now() - timedelta(days=period_days)
            
            cursor.execute("""
                SELECT total_value FROM portfolio_snapshots
                WHERE user_id = ? AND league_id = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            """, (user_id, league_id, cutoff))
            
            values = [row['total_value'] for row in cursor.fetchall()]
            conn.close()
            
            if len(values) < 2:
                return {'cvar_percent': 0, 'confidence': confidence}
            
            # Calculate returns
            returns = []
            for i in range(1, len(values)):
                if values[i-1] > 0:
                    ret = (values[i] - values[i-1]) / values[i-1]
                    returns.append(ret)
            
            if not returns:
                return {'cvar_percent': 0, 'confidence': confidence}
            
            # Sort returns
            returns_sorted = sorted(returns)
            
            # Find tail values beyond confidence level
            index = int(len(returns_sorted) * (1 - confidence))
            tail_returns = returns_sorted[:index + 1]
            
            # Average of tail
            cvar_return = sum(tail_returns) / len(tail_returns) if tail_returns else 0
            cvar_percent = abs(cvar_return) * 100
            
            return {
                'cvar_percent': round(cvar_percent, 2),
                'cvar_amount': round(values[-1] * cvar_return, 2),
                'confidence': confidence,
                'interpretation': f"Average loss in worst {100-confidence*100:.0f}% of days: {cvar_percent:.2f}%"
            }
        except Exception as e:
            logger.error(f"Error calculating CVaR: {e}")
            return {}
    
    def get_risk_profile(self, user_id: int, league_id: int) -> Dict[str, Any]:
        """
        Generate comprehensive risk profile.
        
        Args:
            user_id: User ID
            league_id: League ID
            
        Returns:
            Risk profile dictionary
        """
        perf = PerformanceAnalytics(self.db)
        
        return {
            'volatility': perf.calculate_volatility(user_id, league_id),
            'sharpe_ratio': perf.calculate_sharpe_ratio(user_id, league_id),
            'max_drawdown': perf.calculate_max_drawdown(user_id, league_id),
            'var_95': self.calculate_var(user_id, league_id, 0.95),
            'cvar_95': self.calculate_cvar(user_id, league_id, 0.95),
            'timestamp': datetime.now().isoformat()
        }


class AttributionAnalytics:
    """Performance attribution analysis"""
    
    def __init__(self, db):
        """Initialize attribution analytics"""
        self.db = db
    
    def get_position_contribution(self, user_id: int, league_id: int) -> Dict[str, float]:
        """
        Calculate each position's contribution to portfolio return.
        
        Args:
            user_id: User ID
            league_id: League ID
            
        Returns:
            Contribution by position
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get current positions with gains/losses
            cursor.execute("""
                SELECT symbol, 
                       SUM(quantity) as shares,
                       AVG(purchase_price) as avg_cost,
                       current_price,
                       (SUM(quantity) * current_price) as current_value,
                       (SUM(quantity) * (current_price - AVG(purchase_price))) as gain_loss,
                       (SUM(quantity) * (current_price - AVG(purchase_price))) / 
                        (SUM(quantity) * AVG(purchase_price)) * 100 as return_percent
                FROM user_holdings
                WHERE user_id = ? AND league_id = ? AND quantity > 0
                GROUP BY symbol
            """, (user_id, league_id))
            
            positions = cursor.fetchall()
            conn.close()
            
            # Get total portfolio value
            portfolio = self.db.get_portfolio(user_id, league_id)
            total_value = portfolio.get('total_value', 1)
            
            contribution = {}
            for pos in positions:
                weight = pos['current_value'] / total_value if total_value > 0 else 0
                contribution[pos['symbol']] = {
                    'weight_percent': round(weight * 100, 2),
                    'value': round(pos['current_value'], 2),
                    'gain_loss': round(pos['gain_loss'], 2),
                    'return_percent': round(pos['return_percent'], 2),
                    'shares': pos['shares']
                }
            
            return contribution
        except Exception as e:
            logger.error(f"Error calculating position contribution: {e}")
            return {}
    
    def get_sector_exposure(self, user_id: int, league_id: int) -> Dict[str, float]:
        """
        Calculate exposure by sector.
        
        Args:
            user_id: User ID
            league_id: League ID
            
        Returns:
            Sector allocation
        """
        # This would integrate with stock data to get sector info
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT uh.symbol, 
                       SUM(uh.quantity * uh.current_price) as position_value,
                       s.sector
                FROM user_holdings uh
                LEFT JOIN stock_data s ON uh.symbol = s.symbol
                WHERE uh.user_id = ? AND uh.league_id = ?
                GROUP BY uh.symbol
            """, (user_id, league_id))
            
            positions = cursor.fetchall()
            conn.close()
            
            # Group by sector
            sector_totals = defaultdict(float)
            total_value = 0
            
            for pos in positions:
                sector = pos.get('sector', 'Unknown')
                sector_totals[sector] += pos['position_value']
                total_value += pos['position_value']
            
            # Convert to percentages
            sector_allocation = {}
            for sector, value in sector_totals.items():
                sector_allocation[sector] = round(value / total_value * 100, 2) if total_value > 0 else 0
            
            return sector_allocation
        except Exception as e:
            logger.error(f"Error calculating sector exposure: {e}")
            return {}


class BenchmarkComparison:
    """Compare portfolio to benchmarks"""
    
    def __init__(self, db):
        """Initialize benchmark comparison"""
        self.db = db
    
    def get_peer_comparison(self, user_id: int, league_id: int, period_days: int = 30) -> Dict[str, Any]:
        """
        Compare user's performance to league peers.
        
        Args:
            user_id: User ID
            league_id: League ID
            period_days: Period to compare
            
        Returns:
            Peer comparison metrics
        """
        try:
            perf = PerformanceAnalytics(self.db)
            
            # Get user's returns
            user_returns = perf.calculate_returns(user_id, league_id, period_days)
            user_return_pct = user_returns.get('total_return_percent', 0)
            
            # Get all league members' returns
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT user_id FROM league_members WHERE league_id = ?
            """, (league_id,))
            
            members = [row['user_id'] for row in cursor.fetchall()]
            conn.close()
            
            member_returns = []
            for member_id in members:
                returns = perf.calculate_returns(member_id, league_id, period_days)
                if returns:
                    member_returns.append(returns.get('total_return_percent', 0))
            
            if not member_returns:
                return {'user_rank': 0, 'user_percentile': 0}
            
            # Calculate rank
            better_than = sum(1 for r in member_returns if r < user_return_pct)
            rank = better_than + 1
            percentile = (better_than / len(member_returns) * 100) if member_returns else 0
            
            return {
                'user_return_percent': round(user_return_pct, 2),
                'peer_avg_return': round(sum(member_returns) / len(member_returns), 2),
                'rank': rank,
                'out_of': len(member_returns),
                'percentile': round(percentile, 1)
            }
        except Exception as e:
            logger.error(f"Error comparing to peers: {e}")
            return {}
    
    def get_market_comparison(self, user_id: int, league_id: int, benchmark_symbol: str = "SPY",
                            period_days: int = 30) -> Dict[str, Any]:
        """
        Compare portfolio performance to market benchmark.
        
        Args:
            user_id: User ID
            league_id: League ID
            benchmark_symbol: Benchmark symbol (SPY, QQQ, etc.)
            period_days: Period to compare
            
        Returns:
            Market comparison metrics
        """
        try:
            perf = PerformanceAnalytics(self.db)
            
            # Get portfolio returns
            portfolio_returns = perf.calculate_returns(user_id, league_id, period_days)
            
            # Get benchmark returns (would need market data integration)
            # For now, placeholder
            benchmark_return = 0  # Would calculate from market data
            
            return {
                'portfolio_return': round(portfolio_returns.get('total_return_percent', 0), 2),
                'benchmark_return': round(benchmark_return, 2),
                'alpha': round(
                    portfolio_returns.get('total_return_percent', 0) - benchmark_return, 2
                ),
                'benchmark_symbol': benchmark_symbol,
                'period_days': period_days
            }
        except Exception as e:
            logger.error(f"Error comparing to market: {e}")
            return {}


class ComprehensiveAnalytics:
    """Unified interface for all portfolio analytics"""
    
    def __init__(self, db):
        """Initialize comprehensive analytics"""
        self.db = db
        self.performance = PerformanceAnalytics(db)
        self.risk = RiskAnalytics(db)
        self.attribution = AttributionAnalytics(db)
        self.benchmark = BenchmarkComparison(db)
    
    def get_full_analysis(self, user_id: int, league_id: int, period_days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive portfolio analysis.
        
        Args:
            user_id: User ID
            league_id: League ID
            period_days: Analysis period
            
        Returns:
            Complete analytics report
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'period_days': period_days,
            'performance': {
                'returns': self.performance.calculate_returns(user_id, league_id, period_days),
                'volatility_percent': self.performance.calculate_volatility(user_id, league_id, period_days),
                'sharpe_ratio': self.performance.calculate_sharpe_ratio(user_id, league_id, period_days),
                'max_drawdown': self.performance.calculate_max_drawdown(user_id, league_id, period_days)
            },
            'risk': {
                'var_95': self.risk.calculate_var(user_id, league_id, 0.95, period_days),
                'cvar_95': self.risk.calculate_cvar(user_id, league_id, 0.95, period_days)
            },
            'attribution': {
                'position_contribution': self.attribution.get_position_contribution(user_id, league_id),
                'sector_exposure': self.attribution.get_sector_exposure(user_id, league_id)
            },
            'benchmarks': {
                'peer_comparison': self.benchmark.get_peer_comparison(user_id, league_id, period_days),
                'market_comparison': self.benchmark.get_market_comparison(user_id, league_id, "SPY", period_days)
            }
        }
