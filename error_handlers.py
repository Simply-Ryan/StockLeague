"""
Error handling utilities for StockLeague application.

This module provides standardized error handling patterns and decorators
to ensure consistent error reporting, logging, and user feedback across
all routes and operations.

Usage:
    @app.route("/example")
    @handle_db_errors
    def example_route():
        # Will automatically catch and log database errors
        db.get_user(user_id)
"""

import logging
import functools
from typing import Callable, Tuple, Optional, Dict, Any
from flask import jsonify, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


# ============================================================================
# ERROR CLASSES
# ============================================================================

class StockLeagueError(Exception):
    """Base exception for StockLeague application"""
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR", status_code: int = 500):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(StockLeagueError):
    """Raised when user input validation fails"""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, "VALIDATION_ERROR", status_code)


class NotFoundError(StockLeagueError):
    """Raised when a resource is not found"""
    def __init__(self, message: str, status_code: int = 404):
        super().__init__(message, "NOT_FOUND", status_code)


class PermissionError(StockLeagueError):
    """Raised when user doesn't have permission"""
    def __init__(self, message: str, status_code: int = 403):
        super().__init__(message, "PERMISSION_DENIED", status_code)


class DatabaseError(StockLeagueError):
    """Raised when database operation fails"""
    def __init__(self, message: str, original_error: Optional[Exception] = None, status_code: int = 500):
        self.original_error = original_error
        super().__init__(message, "DATABASE_ERROR", status_code)


class RateLimitError(StockLeagueError):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str, retry_after: int = 60, status_code: int = 429):
        self.retry_after = retry_after
        super().__init__(message, "RATE_LIMIT_EXCEEDED", status_code)


class ExternalServiceError(StockLeagueError):
    """Raised when external API call fails"""
    def __init__(self, message: str, service_name: str = "Unknown", status_code: int = 503):
        self.service_name = service_name
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", status_code)


# ============================================================================
# ERROR DECORATORS
# ============================================================================

def handle_db_errors(func: Callable) -> Callable:
    """
    Decorator to catch and log database errors in a route.
    
    Usage:
        @app.route("/user/<user_id>")
        @handle_db_errors
        def get_user_route(user_id):
            user = db.get_user(user_id)
            return jsonify(user)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DatabaseError as e:
            logger.error(f"Database error in {func.__name__}: {e.message}", exc_info=e.original_error)
            return jsonify({
                "error": e.message,
                "error_code": e.error_code
            }), e.status_code
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                "error": "Database operation failed",
                "error_code": "DATABASE_ERROR"
            }), 500
    return wrapper


def handle_validation_errors(func: Callable) -> Callable:
    """
    Decorator to catch and log validation errors in a route.
    
    Usage:
        @app.route("/validate", methods=["POST"])
        @handle_validation_errors
        def validate_route():
            # Validation errors will be caught and logged
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e.message}")
            return jsonify({
                "error": e.message,
                "error_code": e.error_code
            }), e.status_code
        except ValueError as e:
            logger.warning(f"Value error in {func.__name__}: {str(e)}")
            return jsonify({
                "error": "Invalid input provided",
                "error_code": "VALIDATION_ERROR"
            }), 400
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR"
            }), 500
    return wrapper


def handle_all_errors(func: Callable) -> Callable:
    """
    Decorator to catch all errors in a route with comprehensive logging.
    
    Usage:
        @app.route("/complex_operation", methods=["POST"])
        @handle_all_errors
        def complex_route():
            # All exceptions will be caught, logged, and returned as JSON
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e.message}")
            return jsonify({
                "error": e.message,
                "error_code": e.error_code,
                "status": "validation_error"
            }), e.status_code
        except NotFoundError as e:
            logger.warning(f"Not found error in {func.__name__}: {e.message}")
            return jsonify({
                "error": e.message,
                "error_code": e.error_code,
                "status": "not_found"
            }), e.status_code
        except PermissionError as e:
            logger.warning(f"Permission error in {func.__name__}: {e.message}")
            return jsonify({
                "error": e.message,
                "error_code": e.error_code,
                "status": "permission_denied"
            }), e.status_code
        except RateLimitError as e:
            logger.warning(f"Rate limit error in {func.__name__}: {e.message}")
            response = jsonify({
                "error": e.message,
                "error_code": e.error_code,
                "status": "rate_limit_exceeded",
                "retry_after": e.retry_after
            })
            response.status_code = e.status_code
            response.headers['Retry-After'] = str(e.retry_after)
            return response
        except DatabaseError as e:
            logger.error(f"Database error in {func.__name__}: {e.message}", exc_info=e.original_error)
            return jsonify({
                "error": "Database operation failed",
                "error_code": e.error_code,
                "status": "database_error"
            }), e.status_code
        except ExternalServiceError as e:
            logger.error(f"External service error in {func.__name__}: {e.message} (service: {e.service_name})")
            return jsonify({
                "error": e.message,
                "error_code": e.error_code,
                "status": "external_service_error",
                "service": e.service_name
            }), e.status_code
        except HTTPException as e:
            # Let Flask handle HTTP exceptions
            return e
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR",
                "status": "error"
            }), 500
    return wrapper


# ============================================================================
# ERROR LOGGING UTILITIES
# ============================================================================

def log_trading_error(user_id: int, action: str, symbol: str, error: Exception, context: Dict[str, Any] = None):
    """
    Log a trading error with context information.
    
    Args:
        user_id: User ID attempting the trade
        action: Type of action (buy, sell, etc.)
        symbol: Stock symbol
        error: The exception that occurred
        context: Additional context data
    """
    context = context or {}
    logger.error(
        f"TRADING_ERROR | User: {user_id} | Action: {action} | Symbol: {symbol} | "
        f"Error: {str(error)} | Context: {context}",
        exc_info=error
    )


def log_database_error(operation: str, error: Exception, context: Dict[str, Any] = None):
    """
    Log a database error with operation details.
    
    Args:
        operation: Name of the database operation
        error: The exception that occurred
        context: Additional context data
    """
    context = context or {}
    logger.error(
        f"DATABASE_ERROR | Operation: {operation} | Error: {str(error)} | Context: {context}",
        exc_info=error
    )


def log_authentication_error(endpoint: str, reason: str, context: Dict[str, Any] = None):
    """
    Log an authentication error.
    
    Args:
        endpoint: The endpoint being accessed
        reason: Reason for the failure
        context: Additional context data
    """
    context = context or {}
    ip_address = request.remote_addr if request else "unknown"
    logger.warning(
        f"AUTH_ERROR | Endpoint: {endpoint} | Reason: {reason} | IP: {ip_address} | Context: {context}"
    )


def log_rate_limit_hit(user_id: int, endpoint: str, limit: int, window: int):
    """
    Log when a rate limit is hit.
    
    Args:
        user_id: User ID
        endpoint: The endpoint being rate limited
        limit: The rate limit (number of requests)
        window: The time window in seconds
    """
    logger.warning(
        f"RATE_LIMIT_HIT | User: {user_id} | Endpoint: {endpoint} | Limit: {limit}/{window}s"
    )


# ============================================================================
# ERROR SUMMARY & METRICS
# ============================================================================

class ErrorMetrics:
    """Collect error metrics for monitoring"""
    
    def __init__(self):
        self.errors_by_type = {}
        self.errors_by_endpoint = {}
        self.total_errors = 0
    
    def record_error(self, error_type: str, endpoint: str):
        """Record an error"""
        self.total_errors += 1
        self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
        self.errors_by_endpoint[endpoint] = self.errors_by_endpoint.get(endpoint, 0) + 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get error summary"""
        return {
            "total_errors": self.total_errors,
            "errors_by_type": self.errors_by_type,
            "errors_by_endpoint": self.errors_by_endpoint
        }


# Global metrics instance
metrics = ErrorMetrics()


def register_error_with_metrics(error_type: str, endpoint: str):
    """Register an error with the metrics system"""
    metrics.record_error(error_type, endpoint)
