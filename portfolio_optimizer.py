"""
Portfolio Calculation Optimization Module

Provides efficient portfolio value calculations with caching to avoid
repeated stock price lookups. Significantly improves performance for
frequently-accessed portfolio data.
"""

import logging
import time
from functools import lru_cache
from datetime import datetime, timedelta
from helpers import lookup
from utils import safe_calculation, safe_dict_get

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL_SECONDS = 300  # 5 minutes
PRICE_CACHE_TTL = 60    # 1 minute for price quotes


class PortfolioCalculator:
    """Efficient portfolio value calculator with caching."""
    
    def __init__(self, db):
        """Initialize calculator with database manager.
        
        Args:
            db: DatabaseManager instance
        """
        self.db = db
        self._price_cache = {}
        self._portfolio_cache = {}
        self._last_cache_clear = time.time()
    
    def _get_cached_price(self, symbol):
        """Get stock price from cache or lookup, with TTL.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
        
        Returns:
            Price float or None if unavailable
        """
        now = time.time()
        
        # Check if cached and not expired
        if symbol in self._price_cache:
            price, timestamp = self._price_cache[symbol]
            if now - timestamp < PRICE_CACHE_TTL:
                return price
        
        # Look up fresh price
        try:
            quote = lookup(symbol)
            if quote:
                price = quote.get('price')
                self._price_cache[symbol] = (price, now)
                return price
        except Exception as e:
            logger.warning(f"Error looking up price for {symbol}: {e}")
        
        return None
    
    def calculate_personal_portfolio_value(self, user_id):
        """Calculate total personal portfolio value efficiently.
        
        Args:
            user_id: User ID
        
        Returns:
            dict: {
                'total_value': float,
                'cash': float,
                'invested_value': float,
                'holdings_count': int,
                'error': str or None
            }
        """
        try:
            user = self.db.get_user(user_id)
            if not user:
                return {
                    'total_value': 0,
                    'cash': 0,
                    'invested_value': 0,
                    'holdings_count': 0,
                    'error': 'User not found'
                }
            
            cash = safe_dict_get(user, 'cash', 0, float)
            stocks = self.db.get_user_stocks(user_id)
            
            invested_value = 0
            holdings_count = 0
            
            for stock in stocks:
                symbol = safe_dict_get(stock, 'symbol', '')
                shares = safe_dict_get(stock, 'shares', 0, int)
                
                if symbol and shares > 0:
                    price = self._get_cached_price(symbol)
                    if price:
                        invested_value += shares * price
                        holdings_count += 1
                    else:
                        # Use average cost as fallback
                        avg_cost = safe_dict_get(stock, 'avg_cost', 0, float)
                        if avg_cost:
                            invested_value += shares * avg_cost
                            holdings_count += 1
            
            return {
                'total_value': cash + invested_value,
                'cash': cash,
                'invested_value': invested_value,
                'holdings_count': holdings_count,
                'error': None
            }
        
        except Exception as e:
            logger.error(f"Error calculating personal portfolio for user {user_id}: {e}", exc_info=True)
            return {
                'total_value': 0,
                'cash': 0,
                'invested_value': 0,
                'holdings_count': 0,
                'error': str(e)
            }
    
    def calculate_league_portfolio_value(self, league_id, user_id):
        """Calculate total league portfolio value efficiently.
        
        Args:
            league_id: League ID
            user_id: User ID in league
        
        Returns:
            dict: {
                'total_value': float,
                'cash': float,
                'invested_value': float,
                'holdings_count': int,
                'error': str or None
            }
        """
        try:
            portfolio = self.db.get_league_portfolio(league_id, user_id)
            if not portfolio:
                return {
                    'total_value': 0,
                    'cash': 0,
                    'invested_value': 0,
                    'holdings_count': 0,
                    'error': 'No portfolio found'
                }
            
            cash = safe_dict_get(portfolio, 'cash', 0, float)
            holdings = self.db.get_league_holdings(league_id, user_id)
            
            invested_value = 0
            holdings_count = 0
            
            for holding in holdings:
                symbol = safe_dict_get(holding, 'symbol', '')
                shares = safe_dict_get(holding, 'shares', 0, int)
                
                if symbol and shares > 0:
                    price = self._get_cached_price(symbol)
                    if price:
                        invested_value += shares * price
                        holdings_count += 1
                    else:
                        # Use average cost as fallback
                        avg_cost = safe_dict_get(holding, 'avg_cost', 0, float)
                        if avg_cost:
                            invested_value += shares * avg_cost
                            holdings_count += 1
            
            return {
                'total_value': cash + invested_value,
                'cash': cash,
                'invested_value': invested_value,
                'holdings_count': holdings_count,
                'error': None
            }
        
        except Exception as e:
            logger.error(f"Error calculating league portfolio {league_id} for user {user_id}: {e}", exc_info=True)
            return {
                'total_value': 0,
                'cash': 0,
                'invested_value': 0,
                'holdings_count': 0,
                'error': str(e)
            }
    
    def calculate_with_holdings(self, user_id, league_id=None):
        """Calculate portfolio value and return detailed holdings.
        
        Args:
            user_id: User ID
            league_id: League ID (if calculating league portfolio)
        
        Returns:
            dict: {
                'total_value': float,
                'cash': float,
                'invested_value': float,
                'holdings': [
                    {
                        'symbol': str,
                        'shares': int,
                        'price': float,
                        'value': float,
                        'avg_cost': float
                    },
                    ...
                ],
                'error': str or None
            }
        """
        try:
            if league_id:
                portfolio = self.db.get_league_portfolio(league_id, user_id)
                if not portfolio:
                    return {
                        'total_value': 0,
                        'cash': 0,
                        'invested_value': 0,
                        'holdings': [],
                        'error': 'No portfolio found'
                    }
                
                cash = safe_dict_get(portfolio, 'cash', 0, float)
                holdings_data = self.db.get_league_holdings(league_id, user_id)
            else:
                user = self.db.get_user(user_id)
                if not user:
                    return {
                        'total_value': 0,
                        'cash': 0,
                        'invested_value': 0,
                        'holdings': [],
                        'error': 'User not found'
                    }
                
                cash = safe_dict_get(user, 'cash', 0, float)
                holdings_data = self.db.get_user_stocks(user_id)
            
            invested_value = 0
            holdings = []
            
            for holding in holdings_data:
                symbol = safe_dict_get(holding, 'symbol', '')
                shares = safe_dict_get(holding, 'shares', 0, int)
                avg_cost = safe_dict_get(holding, 'avg_cost', 0, float)
                
                if symbol and shares > 0:
                    price = self._get_cached_price(symbol)
                    if not price:
                        price = avg_cost  # Fallback
                    
                    if price:
                        value = shares * price
                        invested_value += value
                        
                        holdings.append({
                            'symbol': symbol,
                            'shares': shares,
                            'price': price,
                            'value': value,
                            'avg_cost': avg_cost
                        })
            
            return {
                'total_value': cash + invested_value,
                'cash': cash,
                'invested_value': invested_value,
                'holdings': holdings,
                'error': None
            }
        
        except Exception as e:
            logger.error(f"Error calculating portfolio with holdings: {e}", exc_info=True)
            return {
                'total_value': 0,
                'cash': 0,
                'invested_value': 0,
                'holdings': [],
                'error': str(e)
            }
    
    def clear_price_cache(self):
        """Clear the price cache (e.g., after a trade)."""
        self._price_cache.clear()
        logger.debug("Price cache cleared")
    
    def clear_all_caches(self):
        """Clear all caches."""
        self._price_cache.clear()
        self._portfolio_cache.clear()
        logger.debug("All caches cleared")


def get_portfolio_calculator(db):
    """Factory function to get a portfolio calculator instance.
    
    Args:
        db: DatabaseManager instance
    
    Returns:
        PortfolioCalculator instance
    """
    return PortfolioCalculator(db)
