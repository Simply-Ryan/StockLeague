"""
Utility Functions for StockLeague

Common helper functions used across the application.
"""

import json
from typing import Optional, Any, Dict, List
from functools import wraps
from flask import session, redirect
from datetime import datetime, timedelta


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
