"""
Rate Limiting and Trade Throttling System for StockLeague
Prevents abuse, ensures fair play, and protects system resources
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Tuple, Dict, Optional
import threading

# Configure logger
throttle_logger = logging.getLogger('throttle')
throttle_logger.setLevel(logging.INFO)

# Thread lock for thread-safe operations
_lock = threading.RLock()


# ===== RATE LIMIT CONFIGURATION =====

class RateLimitConfig:
    """Configuration for different rate limit types"""
    
    # Trade rate limits (per user)
    TRADES_PER_MINUTE = 10
    TRADES_PER_HOUR = 100
    TRADES_PER_DAY = 500
    
    # Trade cooldown (seconds between trades of same symbol)
    TRADE_COOLDOWN_SECONDS = 2
    
    # Position limits
    MAX_POSITION_PERCENT = 25.0  # Max % of portfolio in single stock
    MAX_DAILY_LOSS_PERCENT = -5.0  # Max daily loss allowed
    
    # API rate limits
    API_CALLS_PER_MINUTE = 60
    API_CALLS_PER_HOUR = 1000
    
    # Account limits
    MAX_OPEN_ORDERS = 100
    MAX_POSITIONS = 50


# ===== TRADE THROTTLE TRACKER =====

class TradeThrottle:
    """Tracks trade frequency and enforces throttling"""
    
    def __init__(self):
        self.trades = defaultdict(list)  # user_id -> list of (timestamp, symbol, action)
        self.cooldowns = defaultdict(lambda: defaultdict(float))  # user_id -> symbol -> cooldown_until
        self.lock = threading.RLock()
    
    def record_trade(self, user_id: int, symbol: str, action: str):
        """
        Record a trade for throttling purposes
        
        Args:
            user_id: User executing trade
            symbol: Stock symbol
            action: Trade action (BUY, SELL)
        """
        with self.lock:
            current_time = time.time()
            self.trades[user_id].append((current_time, symbol, action))
            
            # Clean old trades (older than 1 hour)
            one_hour_ago = current_time - 3600
            self.trades[user_id] = [
                t for t in self.trades[user_id] if t[0] > one_hour_ago
            ]
    
    def get_recent_trades(self, user_id: int, seconds: int = 3600) -> list:
        """
        Get trades within last N seconds
        
        Args:
            user_id: User ID
            seconds: Time window in seconds
        
        Returns:
            List of trades (timestamp, symbol, action)
        """
        with self.lock:
            current_time = time.time()
            cutoff = current_time - seconds
            return [t for t in self.trades.get(user_id, []) if t[0] > cutoff]
    
    def get_trade_count(self, user_id: int, seconds: int = 60) -> int:
        """Get count of trades in last N seconds"""
        return len(self.get_recent_trades(user_id, seconds))
    
    def get_trades_by_symbol(self, user_id: int, symbol: str, seconds: int = 300) -> int:
        """Get count of trades for specific symbol in last N seconds"""
        recent = self.get_recent_trades(user_id, seconds)
        return sum(1 for t in recent if t[1] == symbol)
    
    def set_cooldown(self, user_id: int, symbol: str, cooldown_seconds: int):
        """Set cooldown for symbol"""
        with self.lock:
            cooldown_until = time.time() + cooldown_seconds
            self.cooldowns[user_id][symbol] = cooldown_until
    
    def is_on_cooldown(self, user_id: int, symbol: str) -> Tuple[bool, float]:
        """
        Check if symbol is on cooldown
        
        Returns:
            (is_on_cooldown, seconds_remaining)
        """
        with self.lock:
            cooldown_until = self.cooldowns[user_id].get(symbol, 0)
            current_time = time.time()
            
            if cooldown_until > current_time:
                remaining = cooldown_until - current_time
                return True, remaining
            else:
                # Clean up expired cooldown
                if symbol in self.cooldowns[user_id]:
                    del self.cooldowns[user_id][symbol]
                return False, 0


# Global throttle tracker
_trade_throttle = TradeThrottle()


# ===== RATE LIMIT CHECKS =====

def check_trade_frequency(user_id: int) -> Tuple[bool, Optional[str]]:
    """
    Check if user is trading too frequently
    
    Returns:
        (is_allowed, error_message)
    """
    trades_per_minute = _trade_throttle.get_trade_count(user_id, 60)
    trades_per_hour = _trade_throttle.get_trade_count(user_id, 3600)
    
    if trades_per_minute >= RateLimitConfig.TRADES_PER_MINUTE:
        return False, f"Maximum {RateLimitConfig.TRADES_PER_MINUTE} trades per minute. Please wait."
    
    if trades_per_hour >= RateLimitConfig.TRADES_PER_HOUR:
        return False, f"Maximum {RateLimitConfig.TRADES_PER_HOUR} trades per hour. Please wait."
    
    return True, None


def check_symbol_cooldown(user_id: int, symbol: str) -> Tuple[bool, Optional[str]]:
    """
    Check if symbol is on cooldown
    
    Returns:
        (is_allowed, error_message)
    """
    is_cooldown, remaining = _trade_throttle.is_on_cooldown(user_id, symbol)
    
    if is_cooldown:
        return False, f"Please wait {remaining:.1f} seconds before trading {symbol} again."
    
    return True, None


def check_position_size(
    current_shares: int,
    price: float,
    total_portfolio_value: float,
    symbol: str
) -> Tuple[bool, Optional[str]]:
    """
    Check if position size exceeds limits
    
    Args:
        current_shares: Current shares owned
        price: Stock price
        total_portfolio_value: Total portfolio value
        symbol: Stock symbol
    
    Returns:
        (is_allowed, error_message)
    """
    position_value = current_shares * price
    position_percent = (position_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
    
    if position_percent > RateLimitConfig.MAX_POSITION_PERCENT:
        return False, f"Position in {symbol} would be {position_percent:.1f}% of portfolio (max {RateLimitConfig.MAX_POSITION_PERCENT}%)"
    
    return True, None


def check_daily_loss(total_loss: float, portfolio_start_value: float) -> Tuple[bool, Optional[str]]:
    """
    Check if daily loss exceeds limit
    
    Args:
        total_loss: Total loss for the day (negative number)
        portfolio_start_value: Portfolio value at start of day
    
    Returns:
        (is_allowed, error_message)
    """
    if portfolio_start_value <= 0:
        return True, None
    
    loss_percent = (total_loss / portfolio_start_value * 100)
    
    if loss_percent < RateLimitConfig.MAX_DAILY_LOSS_PERCENT:
        return False, f"Daily loss ({loss_percent:.1f}%) exceeds limit ({RateLimitConfig.MAX_DAILY_LOSS_PERCENT}%)"
    
    return True, None


# ===== COMPREHENSIVE THROTTLE VALIDATION =====

def validate_trade_throttle(
    user_id: int,
    symbol: str,
    action: str,
    shares: int,
    price: float,
    current_shares: int = 0,
    cash: float = 0,
    current_daily_loss: float = 0,
    portfolio_value: float = 0,
    cooldown_seconds: int = RateLimitConfig.TRADE_COOLDOWN_SECONDS,
    max_trades_per_minute: int = RateLimitConfig.TRADES_PER_MINUTE,
    max_position_pct: float = RateLimitConfig.MAX_POSITION_PERCENT,
    max_daily_loss: float = RateLimitConfig.MAX_DAILY_LOSS_PERCENT
) -> Tuple[bool, Optional[str]]:
    """
    Comprehensive trade throttle validation
    
    Args:
        user_id: User executing trade
        symbol: Stock symbol
        action: Trade action (BUY, SELL)
        shares: Number of shares
        price: Stock price
        current_shares: Currently held shares
        cash: Available cash
        current_daily_loss: Current daily loss
        portfolio_value: Total portfolio value
        cooldown_seconds: Cooldown between same-symbol trades
        max_trades_per_minute: Maximum trades per minute
        max_position_pct: Maximum position size percent
        max_daily_loss: Maximum daily loss percent
    
    Returns:
        (is_allowed, error_message)
    """
    
    # Check 1: Trade frequency (per minute)
    trades_per_minute = _trade_throttle.get_trade_count(user_id, 60)
    if trades_per_minute >= max_trades_per_minute:
        return False, f"Trading too frequently. Max {max_trades_per_minute} per minute."
    
    # Check 2: Symbol cooldown
    is_cooldown, remaining = _trade_throttle.is_on_cooldown(user_id, symbol)
    if is_cooldown:
        return False, f"Please wait {remaining:.1f} seconds before trading {symbol}."
    
    # Check 3: Position size (for BUY action)
    if action.upper() == 'BUY' and portfolio_value > 0:
        new_shares = current_shares + shares
        new_position_value = new_shares * price
        position_percent = (new_position_value / portfolio_value * 100)
        
        if position_percent > max_position_pct:
            return False, f"Position would be {position_percent:.1f}% of portfolio (max {max_position_pct}%)"
    
    # Check 4: Sufficient shares (for SELL action)
    if action.upper() == 'SELL' and shares > current_shares:
        return False, f"Insufficient shares. Want to sell {shares}, own {current_shares}"
    
    # Check 5: Daily loss limit
    if current_daily_loss is not None and portfolio_value > 0:
        daily_loss_pct = (current_daily_loss / portfolio_value * 100)
        if daily_loss_pct < max_daily_loss:
            return False, f"Daily loss limit reached ({daily_loss_pct:.1f}%)"
    
    return True, None


# ===== THROTTLE INFO & STATUS =====

def get_throttle_info(user_id: int) -> Dict:
    """
    Get current throttle status for user
    
    Args:
        user_id: User ID
    
    Returns:
        Dictionary with throttle info
    """
    trades_per_minute = _trade_throttle.get_trade_count(user_id, 60)
    trades_per_hour = _trade_throttle.get_trade_count(user_id, 3600)
    
    return {
        'trades_per_minute': trades_per_minute,
        'max_trades_per_minute': RateLimitConfig.TRADES_PER_MINUTE,
        'trades_per_hour': trades_per_hour,
        'max_trades_per_hour': RateLimitConfig.TRADES_PER_HOUR,
        'trades_remaining_minute': max(0, RateLimitConfig.TRADES_PER_MINUTE - trades_per_minute),
        'trades_remaining_hour': max(0, RateLimitConfig.TRADES_PER_HOUR - trades_per_hour),
    }


def record_trade(user_id: int, symbol: str, action: str):
    """
    Record a trade for throttling
    
    Args:
        user_id: User ID
        symbol: Stock symbol
        action: Trade action (BUY, SELL)
    """
    _trade_throttle.record_trade(user_id, symbol, action)
    _trade_throttle.set_cooldown(user_id, symbol, RateLimitConfig.TRADE_COOLDOWN_SECONDS)
    
    throttle_logger.info(f"Trade recorded: user={user_id}, symbol={symbol}, action={action}")


def reset_user_throttle(user_id: int):
    """
    Reset throttle for user (admin function)
    
    Args:
        user_id: User ID to reset
    """
    with _trade_throttle.lock:
        _trade_throttle.trades[user_id] = []
        _trade_throttle.cooldowns[user_id] = {}
    
    throttle_logger.warning(f"Throttle reset for user {user_id}")


# ===== API RATE LIMITING =====

class APIRateLimiter:
    """Rate limiter for API endpoints"""
    
    def __init__(self):
        self.requests = defaultdict(list)  # user_id -> list of timestamps
        self.lock = threading.RLock()
    
    def is_rate_limited(
        self,
        user_id: int,
        calls_per_minute: int = RateLimitConfig.API_CALLS_PER_MINUTE
    ) -> Tuple[bool, float]:
        """
        Check if user has exceeded API rate limit
        
        Returns:
            (is_limited, retry_after_seconds)
        """
        with self.lock:
            current_time = time.time()
            cutoff = current_time - 60  # Last minute
            
            # Clean old requests
            self.requests[user_id] = [
                t for t in self.requests[user_id] if t > cutoff
            ]
            
            if len(self.requests[user_id]) >= calls_per_minute:
                oldest = min(self.requests[user_id])
                retry_after = oldest + 60 - current_time
                return True, max(0, retry_after)
            
            return False, 0
    
    def record_request(self, user_id: int):
        """Record API request"""
        with self.lock:
            self.requests[user_id].append(time.time())


# Global API rate limiter
_api_limiter = APIRateLimiter()


def check_api_rate_limit(user_id: int) -> Tuple[bool, Optional[str], Optional[float]]:
    """
    Check API rate limit for user
    
    Returns:
        (is_allowed, error_message, retry_after)
    """
    is_limited, retry_after = _api_limiter.is_rate_limited(user_id)
    
    if is_limited:
        return False, f"Rate limited. Try again in {retry_after:.0f} seconds.", retry_after
    
    _api_limiter.record_request(user_id)
    return True, None, None


if __name__ == '__main__':
    print("Rate limiting module loaded successfully")
