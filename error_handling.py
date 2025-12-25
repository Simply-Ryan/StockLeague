"""
Enhanced Error Handling Framework for StockLeague
Provides comprehensive error handling, logging, and user-friendly messages
"""

import logging
import traceback
from functools import wraps
from typing import Tuple, Optional, Any, Dict
from flask import request, session
from datetime import datetime
import sqlite3
import json

# Configure error logger
error_logger = logging.getLogger('error_handler')
error_logger.setLevel(logging.ERROR)

# Audit logger for sensitive error tracking
audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.WARNING)


# ===== CUSTOM EXCEPTION CLASSES =====

class StockLeagueError(Exception):
    """Base exception for all StockLeague errors"""
    def __init__(self, message: str, code: int = 400, user_message: str = None):
        self.message = message
        self.code = code
        self.user_message = user_message or message
        super().__init__(self.message)


class ValidationError(StockLeagueError):
    """Invalid input or parameters"""
    def __init__(self, message: str, user_message: str = None):
        super().__init__(message, code=400, user_message=user_message or message)


class AuthenticationError(StockLeagueError):
    """Authentication failed"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, code=401, user_message="You must be logged in")


class AuthorizationError(StockLeagueError):
    """User not authorized for this action"""
    def __init__(self, message: str = "Not authorized"):
        super().__init__(message, code=403, user_message="You don't have permission for this action")


class NotFoundError(StockLeagueError):
    """Resource not found"""
    def __init__(self, resource: str):
        message = f"{resource} not found"
        super().__init__(message, code=404, user_message=f"{resource} not found")


class ConflictError(StockLeagueError):
    """Resource conflict (duplicate, state mismatch)"""
    def __init__(self, message: str, user_message: str = None):
        super().__init__(message, code=409, user_message=user_message or message)


class ThrottleError(StockLeagueError):
    """Rate limited or trade throttled"""
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message, code=429, user_message=message)
        self.retry_after = retry_after


class DatabaseError(StockLeagueError):
    """Database operation failed"""
    def __init__(self, message: str, user_message: str = "Database error occurred"):
        super().__init__(message, code=500, user_message=user_message)


class ExternalServiceError(StockLeagueError):
    """External service (like stock quote service) failed"""
    def __init__(self, service: str, original_error: str = None):
        message = f"External service error: {service}"
        if original_error:
            message += f" ({original_error})"
        super().__init__(message, code=503, user_message=f"Could not connect to {service}. Please try again later.")


class InsufficientFundsError(StockLeagueError):
    """User has insufficient funds/shares"""
    def __init__(self, action: str, needed: float, available: float):
        message = f"{action}: Need {needed}, have {available}"
        user_message = f"Insufficient {action}. You need ${needed:.2f} but have ${available:.2f}"
        super().__init__(message, code=400, user_message=user_message)


# ===== ERROR HANDLERS =====

def validate_required_fields(data: Dict, required_fields: list) -> Tuple[bool, Optional[str]]:
    """
    Validate that all required fields are present in data
    
    Args:
        data: Dictionary of data to validate
        required_fields: List of field names that must be present
    
    Returns:
        (is_valid, error_message)
    """
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    return True, None


def validate_numeric(value: Any, name: str, min_val: float = None, max_val: float = None) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate and convert numeric input
    
    Args:
        value: Value to validate
        name: Field name for error messages
        min_val: Minimum allowed value
        max_val: Maximum allowed value
    
    Returns:
        (is_valid, converted_value, error_message)
    """
    try:
        num = float(value)
        
        if min_val is not None and num < min_val:
            return False, None, f"{name} must be at least {min_val}"
        
        if max_val is not None and num > max_val:
            return False, None, f"{name} cannot exceed {max_val}"
        
        return True, num, None
    except (ValueError, TypeError):
        return False, None, f"{name} must be a valid number"


def validate_positive_integer(value: Any, name: str) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Validate positive integer input
    
    Args:
        value: Value to validate
        name: Field name for error messages
    
    Returns:
        (is_valid, converted_value, error_message)
    """
    try:
        num = int(value)
        if num <= 0:
            return False, None, f"{name} must be greater than 0"
        return True, num, None
    except (ValueError, TypeError):
        return False, None, f"{name} must be a positive whole number"


def validate_portfolio_context(user_id: int, context: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate portfolio context is properly set
    
    Args:
        user_id: User ID
        context: Portfolio context dictionary
    
    Returns:
        (is_valid, error_message)
    """
    if not context:
        return False, "No portfolio context found"
    
    if "type" not in context:
        return False, "Portfolio type not set"
    
    if context["type"] not in ["personal", "league"]:
        return False, "Invalid portfolio type"
    
    if context["type"] == "league":
        if "league_id" not in context:
            return False, "League ID missing"
        if not context["league_id"]:
            return False, "League ID not set"
    
    return True, None


def handle_database_error(error: Exception, operation: str = "database operation") -> Tuple[bool, str]:
    """
    Handle database errors with proper logging
    
    Args:
        error: The exception that occurred
        operation: Description of what was being attempted
    
    Returns:
        (success, error_message)
    """
    error_logger.error(f"Database error during {operation}: {str(error)}", exc_info=True)
    
    if isinstance(error, sqlite3.IntegrityError):
        return False, "Data integrity error. This action may create duplicate data."
    elif isinstance(error, sqlite3.OperationalError):
        return False, "Database operation failed. Please try again later."
    elif isinstance(error, sqlite3.ProgrammingError):
        return False, "Invalid database query. Please contact support."
    else:
        return False, f"Database error: {str(error)[:50]}"


def handle_external_service_error(service: str, error: Exception = None) -> ExternalServiceError:
    """
    Create formatted error for external service failures
    
    Args:
        service: Name of external service (e.g., "stock quote service")
        error: Original exception if available
    
    Returns:
        ExternalServiceError instance
    """
    error_logger.warning(f"External service error: {service}", exc_info=error)
    return ExternalServiceError(service, str(error) if error else None)


def safe_database_operation(func):
    """
    Decorator to safely execute database operations with error handling
    
    Usage:
        @safe_database_operation
        def my_db_function():
            return db.some_operation()
    
    Returns:
        (success, result_or_error)
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return True, result
        except Exception as e:
            success, error_msg = handle_database_error(e, func.__name__)
            return success, error_msg
    return wrapper


# ===== TRADE-SPECIFIC ERROR HANDLING =====

def validate_sell_trade(
    user_id: int,
    symbol: str,
    shares: int,
    current_shares: int,
    price: float
) -> Tuple[bool, Optional[str]]:
    """
    Comprehensive validation for sell trades
    
    Args:
        user_id: User attempting the trade
        symbol: Stock symbol
        shares: Shares to sell
        current_shares: Shares currently owned
        price: Current stock price
    
    Returns:
        (is_valid, error_message)
    """
    # Validate symbol
    if not symbol:
        return False, "Must provide stock symbol"
    
    symbol = symbol.upper().strip()
    if not symbol.isalpha():
        return False, "Invalid stock symbol format"
    
    # Validate shares
    valid, converted_shares, error_msg = validate_positive_integer(shares, "Shares")
    if not valid:
        return False, error_msg
    
    # Validate sufficient shares
    if converted_shares > current_shares:
        return False, f"Insufficient shares. You own {current_shares} but want to sell {converted_shares}"
    
    # Validate price
    if not price or price <= 0:
        return False, "Invalid stock price"
    
    return True, None


def validate_buy_trade(
    user_id: int,
    symbol: str,
    shares: int,
    price: float,
    available_cash: float
) -> Tuple[bool, Optional[str]]:
    """
    Comprehensive validation for buy trades
    
    Args:
        user_id: User attempting the trade
        symbol: Stock symbol
        shares: Shares to buy
        price: Current stock price
        available_cash: Cash available for trading
    
    Returns:
        (is_valid, error_message)
    """
    # Validate symbol
    if not symbol:
        return False, "Must provide stock symbol"
    
    symbol = symbol.upper().strip()
    if not symbol.isalpha():
        return False, "Invalid stock symbol format"
    
    # Validate shares
    valid, converted_shares, error_msg = validate_positive_integer(shares, "Shares")
    if not valid:
        return False, error_msg
    
    # Validate price
    if not price or price <= 0:
        return False, "Invalid stock price"
    
    # Calculate total cost
    total_cost = converted_shares * price
    
    # Validate sufficient funds
    if total_cost > available_cash:
        return False, f"Insufficient funds. Trade costs ${total_cost:.2f} but you have ${available_cash:.2f}"
    
    return True, None


# ===== INPUT SANITIZATION =====

def sanitize_string(value: str, max_length: int = 1000, allow_special: bool = False) -> Optional[str]:
    """
    Sanitize string input
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        allow_special: Whether to allow special characters
    
    Returns:
        Sanitized string or None if empty
    """
    if not value:
        return None
    
    # Convert to string and strip whitespace
    value = str(value).strip()
    
    # Limit length
    value = value[:max_length]
    
    if not allow_special:
        # Remove special characters except common ones
        import re
        value = re.sub(r'[^a-zA-Z0-9\s\-_.:]', '', value)
    
    return value if value else None


def sanitize_symbol(symbol: str) -> Optional[str]:
    """
    Sanitize stock symbol (uppercase, no special chars)
    
    Args:
        symbol: Stock symbol to sanitize
    
    Returns:
        Sanitized symbol or None
    """
    if not symbol:
        return None
    
    symbol = str(symbol).strip().upper()
    
    # Only allow letters and numbers
    import re
    symbol = re.sub(r'[^A-Z0-9]', '', symbol)
    
    return symbol if symbol else None


def escape_html(text: str) -> str:
    """
    Escape HTML special characters to prevent XSS
    
    Args:
        text: Text to escape
    
    Returns:
        Escaped text safe for HTML
    """
    import html
    return html.escape(str(text))


# ===== LOGGING & AUDIT TRAIL =====

def log_trade_attempt(
    user_id: int,
    action: str,
    symbol: str,
    shares: int,
    price: float,
    status: str,
    error_msg: str = None
):
    """
    Log trade attempts for audit trail
    
    Args:
        user_id: User executing trade
        action: Action type (BUY, SELL, etc.)
        symbol: Stock symbol
        shares: Number of shares
        price: Stock price
        status: Result (SUCCESS, FAILED, THROTTLED)
        error_msg: Error message if failed
    """
    try:
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': action,
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'status': status,
            'error': error_msg
        }
        
        if status == 'SUCCESS':
            audit_logger.info(f"Trade executed: {json.dumps(log_entry)}")
        else:
            audit_logger.warning(f"Trade failed: {json.dumps(log_entry)}")
    except Exception as e:
        error_logger.error(f"Error logging trade attempt: {e}")


def log_auth_attempt(username: str, success: bool, reason: str = None):
    """
    Log authentication attempts
    
    Args:
        username: Username attempting login
        success: Whether authentication succeeded
        reason: Reason if failed
    """
    try:
        status = "SUCCESS" if success else "FAILED"
        message = f"Auth {status}: {username}"
        if reason:
            message += f" ({reason})"
        
        if success:
            audit_logger.info(message)
        else:
            audit_logger.warning(message)
    except Exception as e:
        error_logger.error(f"Error logging auth attempt: {e}")


# ===== CONVERSION & FORMATTING =====

def convert_cents_to_dollars(cents: int) -> float:
    """Convert cents to dollars"""
    return cents / 100.0


def format_currency(amount: float) -> str:
    """Format amount as currency string"""
    return f"${amount:,.2f}"


def get_error_display_message(error_code: int, original_message: str = None) -> str:
    """
    Get user-friendly error message based on error code
    
    Args:
        error_code: HTTP error code
        original_message: Original error message
    
    Returns:
        User-friendly error message
    """
    messages = {
        400: "Invalid input. Please check your data and try again.",
        401: "You must be logged in to perform this action.",
        403: "You don't have permission to perform this action.",
        404: "The resource you're looking for was not found.",
        409: "There's a conflict with your request. Please try again.",
        429: "You're making requests too quickly. Please slow down.",
        500: "An unexpected error occurred. Please try again later.",
        503: "The service is temporarily unavailable. Please try again later."
    }
    
    return messages.get(error_code, original_message or "An error occurred")


if __name__ == '__main__':
    # Example usage
    print("Error handling module loaded successfully")
