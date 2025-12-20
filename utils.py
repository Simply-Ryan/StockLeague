"""
Utility Functions for StockLeague

Common helper functions used across the application.
"""

import json
import logging
from typing import Optional, Any, Dict, List, Tuple
from functools import wraps
from flask import session, redirect
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def safe_json_loads(data: Optional[str], default: Any = None) -> Any:
    """
    Safely parse JSON string with fallback value.
    
    Args:
        data: JSON string to parse, or None
        default: Value to return if parsing fails
        
    Returns:
        Parsed JSON data or default value
    """
    if not data:
        return default
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert value to integer.
    
    Args:
        value: Value to convert
        default: Default if conversion fails
        
    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float.
    
    Args:
        value: Value to convert
        default: Default if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def format_time_ago(timestamp: str) -> str:
    """
    Convert timestamp to human-readable 'time ago' format.
    
    Args:
        timestamp: ISO format timestamp string
        
    Returns:
        String like '5m ago', '2h ago', '3d ago'
    """
    if not timestamp:
        return ""
    
    try:
        # Handle various timestamp formats
        if 'T' in timestamp:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = datetime.strptime(timestamp.split('.')[0], '%Y-%m-%d %H:%M:%S')
        
        now = datetime.now()
        diff = now - dt.replace(tzinfo=None)
        
        if diff.days > 365:
            years = diff.days // 365
            return f"{years}y ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months}mo ago"
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds >= 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds >= 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"
    except (ValueError, TypeError, AttributeError):
        return timestamp


def format_large_number(value: float) -> str:
    """
    Format large numbers with K/M/B suffixes.
    
    Args:
        value: Numeric value
        
    Returns:
        Formatted string like '1.5M' or '23.4K'
    """
    try:
        value = float(value)
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.1f}B"
        elif value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        elif value >= 1_000:
            return f"{value / 1_000:.1f}K"
        else:
            return f"{value:.2f}"
    except (ValueError, TypeError):
        return str(value)


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change between two values.
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        Percentage change
    """
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / old_value) * 100


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to maximum length with suffix.
    
    Args:
        text: String to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated string
    """
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def sanitize_html(text: str) -> str:
    """
    Escape HTML special characters for safe display.
    
    Args:
        text: Text to sanitize
        
    Returns:
        Escaped text
    """
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;"))


def is_market_hours() -> bool:
    """
    Check if current time is within US market hours (9:30 AM - 4:00 PM EST).
    
    Returns:
        True if market is open
    """
    now = datetime.now()
    # Simple check - doesn't account for holidays or timezones perfectly
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= now <= market_close


def get_session_user_id() -> Optional[int]:
    """
    Get current user_id from session.
    
    Returns:
        User ID or None if not logged in
    """
    return session.get("user_id")


def batch_list(items: List[Any], batch_size: int) -> List[List[Any]]:
    """
    Split a list into batches of specified size.
    
    Args:
        items: List to split
        batch_size: Size of each batch
        
    Returns:
        List of batches
    """
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


# Common stock symbol lists for quick reference
POPULAR_SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'SPY']

SECTOR_SYMBOLS = {
    'Technology': ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'AMD', 'INTC', 'CRM'],
    'Finance': ['JPM', 'BAC', 'GS', 'V', 'MA', 'AXP', 'WFC', 'C'],
    'Healthcare': ['JNJ', 'PFE', 'UNH', 'ABBV', 'MRK', 'LLY', 'TMO', 'ABT'],
    'Consumer': ['AMZN', 'WMT', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'COST'],
    'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PSX', 'VLO', 'MPC'],
}


# ============ ENHANCED VALIDATION UTILITIES ============

def validate_positive_integer(value: Any, field_name: str = "value", min_val: int = 1, max_val: Optional[int] = None) -> Tuple[bool, Optional[int], str]:
    """Validate that a value is a positive integer.
    
    Args:
        value: Value to validate (can be string or number)
        field_name: Name of field for error messages
        min_val: Minimum allowed value (default 1)
        max_val: Maximum allowed value (optional)
    
    Returns:
        tuple: (is_valid, converted_value, error_message)
    """
    try:
        int_value = int(value)
        
        if int_value < min_val:
            return False, None, f"{field_name} must be at least {min_val}"
        
        if max_val is not None and int_value > max_val:
            return False, None, f"{field_name} cannot exceed {max_val}"
        
        return True, int_value, ""
    
    except (ValueError, TypeError):
        return False, None, f"{field_name} must be a valid whole number"


def validate_positive_float(value: Any, field_name: str = "value", min_val: float = 0) -> Tuple[bool, Optional[float], str]:
    """Validate that a value is a positive float.
    
    Args:
        value: Value to validate (can be string or number)
        field_name: Name of field for error messages
        min_val: Minimum allowed value
    
    Returns:
        tuple: (is_valid, converted_value, error_message)
    """
    try:
        float_value = float(value)
        
        if float_value < min_val:
            return False, None, f"{field_name} must be at least {min_val}"
        
        return True, float_value, ""
    
    except (ValueError, TypeError):
        return False, None, f"{field_name} must be a valid number"


def validate_string_field(value: Any, field_name: str = "value", min_length: int = 1, max_length: Optional[int] = None) -> Tuple[bool, Optional[str], str]:
    """Validate that a value is a string with length constraints.
    
    Args:
        value: Value to validate
        field_name: Name of field for error messages
        min_length: Minimum required length
        max_length: Maximum allowed length (optional)
    
    Returns:
        tuple: (is_valid, converted_value, error_message)
    """
    if value is None:
        return False, None, f"{field_name} is required"
    
    str_value = str(value).strip()
    
    if len(str_value) < min_length:
        return False, None, f"{field_name} must be at least {min_length} characters"
    
    if max_length and len(str_value) > max_length:
        return False, None, f"{field_name} cannot exceed {max_length} characters"
    
    return True, str_value, ""


# ============ ENHANCED ERROR HANDLING ============

def safe_dict_get(data: Dict, key: str, default: Any = None, expected_type: Optional[type] = None) -> Any:
    """Safely get a value from a dictionary with type checking.
    
    Args:
        data: Dictionary to get from
        key: Key to retrieve
        default: Default value if key missing
        expected_type: Type to validate against (e.g., int, str, float)
    
    Returns:
        Value if found and type matches, default otherwise
    """
    if not isinstance(data, dict):
        logger.warning(f"safe_dict_get called with non-dict: {type(data)}")
        return default
    
    value = data.get(key, default)
    
    if expected_type and value is not None:
        if not isinstance(value, expected_type):
            logger.warning(f"Type mismatch for {key}: expected {expected_type.__name__}, got {type(value).__name__}")
            return default
    
    return value


def safe_calculation(func, *args, default: float = 0.0, log_error: bool = True) -> float:
    """Safely execute a calculation function with error handling.
    
    Args:
        func: Callable to execute
        *args: Arguments to pass to function
        default: Default return value if error occurs
        log_error: Whether to log the error
    
    Returns:
        Result from func or default value
    """
    try:
        return func(*args)
    except Exception as e:
        if log_error:
            logger.error(f"Calculation error in {getattr(func, '__name__', 'unknown')}: {e}", exc_info=True)
        return default


def float_equal(a: float, b: float, epsilon: float = 0.01) -> bool:
    """Compare two floats with tolerance for rounding errors.
    
    Args:
        a: First value
        b: Second value
        epsilon: Tolerance threshold (default 0.01 for cents)
    
    Returns:
        True if values are approximately equal
    """
    try:
        return abs(float(a) - float(b)) < epsilon
    except (ValueError, TypeError):
        return False


def log_trade_action(user_id: int, action: str, symbol: str, shares: float, price: float, context: str = "personal", notes: str = "") -> None:
    """Log a trading action with consistent formatting.
    
    Args:
        user_id: ID of user making the trade
        action: 'buy', 'sell', 'copy_buy', 'copy_sell', etc.
        symbol: Stock symbol
        shares: Number of shares
        price: Price per share
        context: 'personal' or 'league_{league_id}'
        notes: Additional notes (optional)
    """
    try:
        total_value = shares * price
        logger.info(
            f"TRADE | User: {user_id} | Action: {action} | Symbol: {symbol} | "
            f"Shares: {shares} | Price: {price:.2f} | Total: {total_value:.2f} | "
            f"Context: {context} | {notes}"
        )
    except Exception as e:
        logger.error(f"Error logging trade action: {e}")


def log_error_with_context(error: Exception, context: str = "", user_id: Optional[int] = None, **extra_data) -> None:
    """Log an error with contextual information.
    
    Args:
        error: Exception or error message
        context: Description of what was happening
        user_id: User ID if applicable
        **extra_data: Additional data to log
    """
    try:
        context_str = f" in {context}" if context else ""
        user_str = f" for user {user_id}" if user_id else ""
        
        logger.error(
            f"Error{context_str}{user_str}: {error}",
            exc_info=True,
            extra={'context_data': extra_data}
        )
    except Exception as e:
        logger.error(f"Error in error logging: {e}")


# ============================================================================
# RATE LIMITING
# ============================================================================

# In-memory store for rate limiting: {(user_id, endpoint): [(timestamp, request_count)]}
_rate_limit_store = {}


def rate_limit(max_requests: int = 10, time_window: int = 60, endpoint_key: str = None):
    """
    Rate limiting decorator to prevent abuse on specific endpoints.
    
    Args:
        max_requests: Max requests allowed in time window
        time_window: Time window in seconds
        endpoint_key: Custom key for rate limiting (default: route path)
        
    Returns:
        Decorator function
        
    Example:
        @app.route("/buy", methods=["POST"])
        @rate_limit(max_requests=5, time_window=60)
        def buy():
            # Max 5 buy requests per minute per user
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import session, abort
            
            try:
                user_id = session.get("user_id")
                if not user_id:
                    # Not logged in - no rate limiting
                    return f(*args, **kwargs)
                
                key = endpoint_key or f.__name__
                rate_key = (user_id, key)
                current_time = datetime.now()
                
                # Get or initialize rate limit entry
                if rate_key not in _rate_limit_store:
                    _rate_limit_store[rate_key] = []
                
                # Remove old requests outside time window
                requests = _rate_limit_store[rate_key]
                cutoff_time = current_time - timedelta(seconds=time_window)
                requests[:] = [req_time for req_time in requests if req_time > cutoff_time]
                
                # Check if limit exceeded
                if len(requests) >= max_requests:
                    logger.warning(f"Rate limit exceeded for user {user_id} on endpoint {key}")
                    abort(429)  # Too Many Requests
                
                # Add current request
                requests.append(current_time)
                
                # Continue to route handler
                return f(*args, **kwargs)
            
            except Exception as e:
                logger.error(f"Error in rate limiting decorator: {e}")
                # If rate limiter fails, allow request through
                return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def clear_rate_limit_cache(user_id: int = None):
    """Clear rate limit cache for user or all users.
    
    Args:
        user_id: User ID to clear (None = clear all)
    """
    global _rate_limit_store
    
    try:
        if user_id is None:
            _rate_limit_store.clear()
            logger.info("Cleared all rate limit caches")
        else:
            # Clear all entries for this user
            keys_to_delete = [key for key in _rate_limit_store if key[0] == user_id]
            for key in keys_to_delete:
                del _rate_limit_store[key]
            logger.info(f"Cleared rate limit cache for user {user_id}")
    except Exception as e:
        logger.error(f"Error clearing rate limit cache: {e}")


# ============================================================================
# INPUT SANITIZATION & VALIDATION
# ============================================================================

import html
import re


def sanitize_xss(data: str, max_length: int = 1000) -> str:
    """Sanitize user input to prevent XSS attacks.
    
    Args:
        data: User input string
        max_length: Max allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(data, str):
        return ""
    
    # Truncate if too long
    data = data[:max_length]
    
    # HTML escape special characters
    data = html.escape(data)
    
    # Remove any control characters
    data = ''.join(char for char in data if ord(char) >= 32 or char in '\n\r\t')
    
    return data


def validate_symbol(symbol: str) -> Tuple[bool, str]:
    """Validate stock symbol format.
    
    Args:
        symbol: Stock symbol to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not symbol:
        return False, "Symbol cannot be empty"
    
    symbol = symbol.strip().upper()
    
    if len(symbol) < 1 or len(symbol) > 10:
        return False, "Symbol must be 1-10 characters"
    
    # Symbols should be alphanumeric
    if not re.match(r'^[A-Z0-9\-\.]+$', symbol):
        return False, "Symbol contains invalid characters"
    
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email cannot be empty"
    
    email = email.strip().lower()
    
    if len(email) > 254:
        return False, "Email is too long"
    
    # Basic email validation regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    return True, ""


def validate_username(username: str) -> Tuple[bool, str]:
    """Validate username format.
    
    Args:
        username: Username to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username:
        return False, "Username cannot be empty"
    
    username = username.strip()
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(username) > 50:
        return False, "Username must be at most 50 characters"
    
    # Username should be alphanumeric with underscores/hyphens
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, hyphens, and underscores"
    
    return True, ""


def sanitize_input(data: str, field_type: str = "text") -> Tuple[str, bool]:
    """Sanitize and validate user input based on field type.
    
    Args:
        data: User input
        field_type: Type of field ('symbol', 'email', 'username', 'text', 'number')
        
    Returns:
        Tuple of (sanitized_value, is_valid)
    """
    if field_type == "symbol":
        is_valid, _ = validate_symbol(data)
        return data.strip().upper() if is_valid else "", is_valid
    
    elif field_type == "email":
        is_valid, _ = validate_email(data)
        return data.strip().lower() if is_valid else "", is_valid
    
    elif field_type == "username":
        is_valid, _ = validate_username(data)
        return data.strip() if is_valid else "", is_valid
    
    elif field_type == "number":
        try:
            # For numbers, validate it's numeric
            float(data)
            return data.strip(), True
        except (ValueError, TypeError):
            return "", False
    
    else:  # "text"
        # Generic text sanitization
        return sanitize_xss(data), True


def prevent_sql_injection(value: str) -> str:
    """Prepare value for safe SQL usage (escape single quotes).
    
    Note: This is a helper. Always use parameterized queries with ? instead!
    
    Args:
        value: Value to escape
        
    Returns:
        Escaped value
    """
    if not isinstance(value, str):
        return ""
    
    # Escape single quotes by doubling them
    return value.replace("'", "''")



