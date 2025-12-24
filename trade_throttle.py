"""
Trade throttling and risk control utilities.

This module provides throttling mechanisms to prevent abuse and enforce
trading risk management, including:
- Per-user trade cooldowns
- Trade frequency limits
- Position size limits
- Daily loss limits (circuit breaker)
- Maximum concurrent positions
"""

import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any
from flask import session

logger = logging.getLogger(__name__)

# In-memory throttle store: (user_id) -> list of (timestamp, symbol, action, shares, price)
_trade_throttle_store: Dict[int, list] = {}

# In-memory position tracking: (user_id, symbol) -> current_shares
_position_tracker: Dict[Tuple[int, str], int] = {}

# In-memory daily loss tracker: (user_id) -> (date, daily_loss_amount)
_daily_loss_tracker: Dict[int, Tuple[str, float]] = {}


# ============================================================================
# TRADE THROTTLING FUNCTIONS
# ============================================================================

def check_trade_cooldown(user_id: int, symbol: str, cooldown_seconds: int = 2) -> Tuple[bool, Optional[str], int]:
    """
    Check if user has performed a trade recently (within cooldown period).
    
    Args:
        user_id: User ID
        symbol: Stock symbol
        cooldown_seconds: Seconds to wait between trades of same symbol
    
    Returns:
        (allowed: bool, message: Optional[str], remaining_cooldown: int)
    """
    current_time = datetime.now()
    
    # Initialize store if needed
    if user_id not in _trade_throttle_store:
        _trade_throttle_store[user_id] = []
    
    trades = _trade_throttle_store[user_id]
    
    # Check for recent trade of this symbol
    for trade_time, trade_symbol, _, _, _ in trades:
        if trade_symbol == symbol:
            time_since_trade = (current_time - trade_time).total_seconds()
            if time_since_trade < cooldown_seconds:
                remaining = cooldown_seconds - int(time_since_trade)
                return False, f"Please wait {remaining} second(s) before trading {symbol} again", remaining
    
    return True, None, 0


def check_trade_frequency(user_id: int, max_trades_per_minute: int = 10) -> Tuple[bool, Optional[str], int]:
    """
    Check if user has exceeded maximum trades per minute.
    
    Args:
        user_id: User ID
        max_trades_per_minute: Max trades allowed per minute
    
    Returns:
        (allowed: bool, message: Optional[str], remaining_cooldown: int)
    """
    current_time = datetime.now()
    cutoff_time = current_time - timedelta(seconds=60)
    
    # Initialize store if needed
    if user_id not in _trade_throttle_store:
        _trade_throttle_store[user_id] = []
    
    trades = _trade_throttle_store[user_id]
    
    # Count trades in last minute
    recent_trades = [t for t in trades if t[0] > cutoff_time]
    
    if len(recent_trades) >= max_trades_per_minute:
        # Calculate when the oldest trade expires
        oldest_trade_time = recent_trades[0][0]
        time_until_available = 60 - int((current_time - oldest_trade_time).total_seconds())
        return False, f"Trade frequency limit exceeded. Please wait {time_until_available} second(s)", time_until_available
    
    return True, None, 0


def check_position_size_limit(user_id: int, symbol: str, current_shares: int, 
                              new_shares: int, cash: float, price: float, 
                              max_position_pct: float = 25.0) -> Tuple[bool, Optional[str]]:
    """
    Check if a new position would exceed position size limits.
    
    Args:
        user_id: User ID
        symbol: Stock symbol
        current_shares: Current shares held of this symbol
        new_shares: Shares being added
        cash: Available cash
        price: Price per share
        max_position_pct: Max allowed position as % of portfolio
    
    Returns:
        (allowed: bool, message: Optional[str])
    """
    # Calculate new position value
    total_shares = current_shares + new_shares
    position_value = total_shares * price
    
    # Estimate total portfolio value (cash + position)
    # For accurate calc, should get all holdings but this is conservative
    estimated_portfolio_value = cash + position_value
    
    # Check position size percentage
    position_pct = (position_value / estimated_portfolio_value) * 100 if estimated_portfolio_value > 0 else 0
    
    if position_pct > max_position_pct:
        return False, f"Position would be {position_pct:.1f}% of portfolio. Max allowed: {max_position_pct}%"
    
    return True, None


def check_daily_loss_limit(user_id: int, current_daily_loss: float, 
                           max_daily_loss: float = -5000.0) -> Tuple[bool, Optional[str]]:
    """
    Check if user has hit daily loss limit (circuit breaker).
    
    Args:
        user_id: User ID
        current_daily_loss: Current P&L for the day (negative = loss)
        max_daily_loss: Max allowed loss for the day (should be negative)
    
    Returns:
        (allowed: bool, message: Optional[str])
    """
    # max_daily_loss should be negative (e.g., -5000 means max loss of $5000)
    if current_daily_loss <= max_daily_loss:
        return False, f"Daily loss limit reached (${abs(current_daily_loss):.2f} loss). Trading suspended for today."
    
    return True, None


def record_trade(user_id: int, symbol: str, action: str, shares: int, price: float):
    """
    Record a completed trade for throttling purposes.
    
    Args:
        user_id: User ID
        symbol: Stock symbol
        action: 'buy' or 'sell'
        shares: Number of shares traded
        price: Price per share
    """
    if user_id not in _trade_throttle_store:
        _trade_throttle_store[user_id] = []
    
    # Record with timestamp
    _trade_throttle_store[user_id].append((datetime.now(), symbol, action, shares, price))
    
    # Keep only last 100 trades (clean up old data)
    if len(_trade_throttle_store[user_id]) > 100:
        _trade_throttle_store[user_id] = _trade_throttle_store[user_id][-100:]
    
    logger.debug(f"Recorded trade for user {user_id}: {action} {shares} {symbol} @ ${price}")


def get_user_trade_history(user_id: int, minutes: int = 60) -> list:
    """
    Get user's trades within the specified time window.
    
    Args:
        user_id: User ID
        minutes: Time window in minutes
    
    Returns:
        List of trades: [(timestamp, symbol, action, shares, price), ...]
    """
    if user_id not in _trade_throttle_store:
        return []
    
    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    trades = _trade_throttle_store[user_id]
    
    return [t for t in trades if t[0] > cutoff_time]


def clear_user_throttle_data(user_id: int):
    """Clear throttle data for a user (useful for testing)."""
    if user_id in _trade_throttle_store:
        del _trade_throttle_store[user_id]
    
    logger.debug(f"Cleared throttle data for user {user_id}")


# ============================================================================
# COMPOSITE VALIDATION FUNCTION
# ============================================================================

def validate_trade_throttle(
    user_id: int,
    symbol: str,
    action: str,
    shares: int,
    price: float,
    current_shares: int,
    cash: float,
    current_daily_loss: float,
    cooldown_seconds: int = 2,
    max_trades_per_minute: int = 10,
    max_position_pct: float = 25.0,
    max_daily_loss: float = -5000.0,
    **kwargs
) -> Tuple[bool, Optional[str]]:
    """
    Comprehensive throttle validation combining all checks.
    
    Args:
        user_id: User ID
        symbol: Stock symbol
        action: 'buy' or 'sell'
        shares: Number of shares
        price: Price per share
        current_shares: Current holding of this symbol
        cash: Available cash
        current_daily_loss: Current day's P&L (negative = loss)
        cooldown_seconds: Cooldown between trades
        max_trades_per_minute: Max trades per minute
        max_position_pct: Max position as % of portfolio
        max_daily_loss: Max allowed loss (negative value)
        **kwargs: Additional parameters for compatibility
    
    Returns:
        (allowed: bool, message: Optional[str])
    """
    # Check 1: Trade cooldown
    allowed, message, _ = check_trade_cooldown(user_id, symbol, cooldown_seconds)
    if not allowed:
        return False, message
    
    # Check 2: Trade frequency
    allowed, message, _ = check_trade_frequency(user_id, max_trades_per_minute)
    if not allowed:
        return False, message
    
    # Check 3: Position size limit (for buys only)
    if action.lower() == 'buy':
        allowed, message = check_position_size_limit(
            user_id, symbol, current_shares, shares, cash, price, max_position_pct
        )
        if not allowed:
            return False, message
    
    # Check 4: Daily loss limit
    allowed, message = check_daily_loss_limit(user_id, current_daily_loss, max_daily_loss)
    if not allowed:
        return False, message
    
    # All checks passed
    return True, None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_throttle_stats(user_id: int) -> Dict[str, Any]:
    """Get throttle statistics for a user."""
    trades = get_user_trade_history(user_id)
    
    # Count by action
    buys = sum(1 for t in trades if t[2] == 'buy')
    sells = sum(1 for t in trades if t[2] == 'sell')
    
    # Unique symbols
    symbols = set(t[1] for t in trades)
    
    return {
        "total_trades": len(trades),
        "buys": buys,
        "sells": sells,
        "unique_symbols": len(symbols),
        "symbols": list(symbols),
        "window": "last 60 minutes"
    }
