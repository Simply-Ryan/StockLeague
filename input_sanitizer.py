"""
Input Sanitization & Validation Framework for StockLeague
Prevents XSS, SQL injection, and malformed data from reaching the application
"""

import re
import html
import logging
from typing import Optional, Any, Tuple, List, Dict
from urllib.parse import quote, unquote
import json

# Configure logger
sanitize_logger = logging.getLogger('sanitizer')
sanitize_logger.setLevel(logging.DEBUG)


# ===== SECURITY PATTERNS =====

class SecurityPatterns:
    """Regex patterns for validation"""
    
    # Stock symbols: 1-5 uppercase letters (plus ^ for options)
    SYMBOL_PATTERN = r'^[A-Z^]{1,5}$'
    
    # Usernames: 3-20 alphanumeric + underscore/hyphen
    USERNAME_PATTERN = r'^[a-zA-Z0-9_-]{3,20}$'
    
    # Email: basic validation
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # URL: basic validation
    URL_PATTERN = r'^https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+$'
    
    # Numbers only
    DIGITS_ONLY = r'^\d+$'
    
    # Positive integer
    POSITIVE_INT = r'^\d+$'
    
    # Decimal number
    DECIMAL_NUMBER = r'^-?\d+(\.\d+)?$'


# ===== STRING SANITIZATION =====

def sanitize_string(
    value: Optional[str],
    max_length: int = 1000,
    allow_special: bool = False,
    allow_whitespace: bool = True,
    lowercase: bool = False
) -> Optional[str]:
    """
    Sanitize string input
    
    Args:
        value: String to sanitize
        max_length: Maximum length
        allow_special: Allow special characters
        allow_whitespace: Preserve whitespace
        lowercase: Convert to lowercase
    
    Returns:
        Sanitized string or None if empty
    """
    if value is None or value == '':
        return None
    
    # Convert to string
    value = str(value)
    
    # Remove leading/trailing whitespace
    value = value.strip()
    
    if not value:
        return None
    
    # Limit length
    value = value[:max_length]
    
    # Convert to lowercase if requested
    if lowercase:
        value = value.lower()
    
    # Remove special characters if not allowed
    if not allow_special:
        if allow_whitespace:
            # Allow alphanumeric, spaces, and common punctuation
            value = re.sub(r'[^a-zA-Z0-9\s\-_.,]', '', value)
        else:
            # Allow only alphanumeric and underscore/hyphen
            value = re.sub(r'[^a-zA-Z0-9_-]', '', value)
    else:
        # Still remove potentially dangerous characters
        value = remove_dangerous_chars(value)
    
    return value if value else None


def sanitize_symbol(symbol: Optional[str]) -> Optional[str]:
    """
    Sanitize stock symbol
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'BRK.B')
    
    Returns:
        Sanitized symbol (uppercase) or None
    """
    if not symbol:
        return None
    
    symbol = str(symbol).strip().upper()
    
    # Remove any special characters except ^
    symbol = re.sub(r'[^A-Z0-9^]', '', symbol)
    
    # Validate length (1-5 chars + optional ^ for options)
    if len(symbol) < 1 or len(symbol) > 6:
        return None
    
    return symbol


def sanitize_username(username: Optional[str]) -> Optional[str]:
    """
    Sanitize username
    
    Args:
        username: Username
    
    Returns:
        Sanitized username or None
    """
    if not username:
        return None
    
    username = str(username).strip()
    
    # Allow alphanumeric, underscore, hyphen
    username = re.sub(r'[^a-zA-Z0-9_-]', '', username)
    
    # Check length (3-20 chars)
    if len(username) < 3 or len(username) > 20:
        return None
    
    return username


def sanitize_email(email: Optional[str]) -> Optional[str]:
    """
    Sanitize and validate email
    
    Args:
        email: Email address
    
    Returns:
        Sanitized email or None if invalid
    """
    if not email:
        return None
    
    email = str(email).strip().lower()
    
    # Remove any whitespace
    email = email.replace(' ', '')
    
    # Validate format
    if not re.match(SecurityPatterns.EMAIL_PATTERN, email):
        return None
    
    # Limit length
    if len(email) > 254:  # RFC 5321
        return None
    
    return email


def sanitize_url(url: Optional[str]) -> Optional[str]:
    """
    Sanitize and validate URL
    
    Args:
        url: URL string
    
    Returns:
        Sanitized URL or None if invalid
    """
    if not url:
        return None
    
    url = str(url).strip()
    
    # Must start with http:// or https://
    if not url.startswith(('http://', 'https://')):
        return None
    
    # Validate format
    if not re.match(SecurityPatterns.URL_PATTERN, url):
        return None
    
    # Limit length
    if len(url) > 2048:
        return None
    
    return url


# ===== NUMERIC SANITIZATION =====

def sanitize_integer(
    value: Any,
    min_val: Optional[int] = None,
    max_val: Optional[int] = None
) -> Optional[int]:
    """
    Sanitize and validate integer
    
    Args:
        value: Value to convert
        min_val: Minimum allowed value
        max_val: Maximum allowed value
    
    Returns:
        Integer or None if invalid
    """
    try:
        num = int(value)
    except (ValueError, TypeError):
        return None
    
    if min_val is not None and num < min_val:
        return None
    
    if max_val is not None and num > max_val:
        return None
    
    return num


def sanitize_positive_integer(value: Any) -> Optional[int]:
    """Sanitize positive integer"""
    num = sanitize_integer(value)
    return num if num and num > 0 else None


def sanitize_float(
    value: Any,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    decimal_places: int = 2
) -> Optional[float]:
    """
    Sanitize and validate float
    
    Args:
        value: Value to convert
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        decimal_places: Round to N decimal places
    
    Returns:
        Float or None if invalid
    """
    try:
        num = float(value)
    except (ValueError, TypeError):
        return None
    
    if min_val is not None and num < min_val:
        return None
    
    if max_val is not None and num > max_val:
        return None
    
    # Round to decimal places
    num = round(num, decimal_places)
    
    return num


def sanitize_currency(value: Any) -> Optional[float]:
    """Sanitize currency amount (0.00+, 2 decimal places)"""
    # Remove common currency symbols
    if isinstance(value, str):
        value = value.replace('$', '').replace(',', '').strip()
    
    return sanitize_float(value, min_val=0.0, decimal_places=2)


def sanitize_percentage(value: Any) -> Optional[float]:
    """Sanitize percentage (0-100)"""
    return sanitize_float(value, min_val=0.0, max_val=100.0)


# ===== XSS PREVENTION =====

def escape_html(text: Optional[str]) -> str:
    """
    Escape HTML special characters
    
    Args:
        text: Text to escape
    
    Returns:
        Escaped HTML-safe text
    """
    if not text:
        return ''
    
    return html.escape(str(text))


def strip_html_tags(text: Optional[str]) -> str:
    """
    Remove all HTML tags
    
    Args:
        text: Text containing HTML
    
    Returns:
        Text without tags
    """
    if not text:
        return ''
    
    # Remove all HTML tags
    text = re.sub(r'<[^>]+>', '', str(text))
    
    return text


def sanitize_html_input(text: Optional[str], max_length: int = 1000) -> str:
    """
    Sanitize text that might contain user HTML
    
    Args:
        text: User-provided text
        max_length: Maximum length
    
    Returns:
        Safe text for display
    """
    if not text:
        return ''
    
    # Remove HTML tags
    text = strip_html_tags(text)
    
    # Limit length
    text = text[:max_length]
    
    # Escape remaining special characters
    text = escape_html(text)
    
    return text


# ===== SQL INJECTION PREVENTION =====

def is_sql_injection_attempt(value: str) -> bool:
    """
    Detect common SQL injection patterns
    
    Args:
        value: Input string to check
    
    Returns:
        True if potential SQL injection detected
    """
    if not isinstance(value, str):
        return False
    
    # Common SQL keywords
    sql_keywords = [
        'UNION', 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP',
        'CREATE', 'ALTER', 'EXEC', 'SCRIPT', 'OR', 'AND'
    ]
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r"['\"]\s*(OR|AND)\s*['\"]",  # ' OR '
        r"--",                           # SQL comments
        r";\s*(SELECT|INSERT|UPDATE|DELETE)",  # Stacked queries
        r"\/\*.*?\*\/",                 # Multi-line comments
    ]
    
    value_upper = value.upper()
    
    # Check for keywords in suspicious context
    for keyword in sql_keywords:
        if keyword in value_upper:
            return True
    
    # Check for suspicious patterns
    for pattern in suspicious_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            return True
    
    return False


# ===== JSON & DICT SANITIZATION =====

def sanitize_json(json_str: Optional[str]) -> Optional[Dict]:
    """
    Safely parse and validate JSON
    
    Args:
        json_str: JSON string
    
    Returns:
        Parsed dictionary or None if invalid
    """
    if not json_str:
        return None
    
    try:
        data = json.loads(json_str)
        
        # Verify it's a dictionary
        if not isinstance(data, dict):
            return None
        
        return data
    except (json.JSONDecodeError, ValueError):
        return None


def sanitize_dict(data: Dict, allowed_keys: List[str] = None) -> Dict:
    """
    Sanitize dictionary by filtering keys and values
    
    Args:
        data: Dictionary to sanitize
        allowed_keys: List of allowed keys (None = allow all)
    
    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return {}
    
    sanitized = {}
    
    for key, value in data.items():
        # Filter keys if whitelist provided
        if allowed_keys and key not in allowed_keys:
            continue
        
        # Sanitize string values
        if isinstance(value, str):
            sanitized[key] = sanitize_html_input(value)
        elif isinstance(value, (int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, allowed_keys)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_html_input(v) if isinstance(v, str) else v
                for v in value
            ]
        else:
            sanitized[key] = None
    
    return sanitized


# ===== UTILITY FUNCTIONS =====

def remove_dangerous_chars(text: str) -> str:
    """Remove potentially dangerous characters"""
    dangerous_chars = '<>"\';\\/'
    for char in dangerous_chars:
        text = text.replace(char, '')
    return text


def truncate_text(text: Optional[str], max_length: int) -> str:
    """Truncate text to maximum length"""
    if not text:
        return ''
    
    text = str(text)
    if len(text) > max_length:
        text = text[:max_length-3] + '...'
    
    return text


def normalize_whitespace(text: Optional[str]) -> str:
    """Normalize whitespace in text"""
    if not text:
        return ''
    
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', str(text))
    
    # Strip leading/trailing whitespace
    return text.strip()


# ===== VALIDATION HELPERS =====

def validate_and_sanitize(
    value: Any,
    value_type: str,
    **kwargs
) -> Tuple[bool, Optional[Any], Optional[str]]:
    """
    Validate and sanitize input based on type
    
    Args:
        value: Value to validate
        value_type: Type of validation ('string', 'symbol', 'email', etc.)
        **kwargs: Additional parameters for sanitization
    
    Returns:
        (is_valid, sanitized_value, error_message)
    """
    try:
        if value_type == 'string':
            sanitized = sanitize_string(value, **kwargs)
        elif value_type == 'symbol':
            sanitized = sanitize_symbol(value)
        elif value_type == 'username':
            sanitized = sanitize_username(value)
        elif value_type == 'email':
            sanitized = sanitize_email(value)
        elif value_type == 'url':
            sanitized = sanitize_url(value)
        elif value_type == 'integer':
            sanitized = sanitize_integer(value, **kwargs)
        elif value_type == 'positive_int':
            sanitized = sanitize_positive_integer(value)
        elif value_type == 'float':
            sanitized = sanitize_float(value, **kwargs)
        elif value_type == 'currency':
            sanitized = sanitize_currency(value)
        elif value_type == 'percentage':
            sanitized = sanitize_percentage(value)
        else:
            return False, None, f"Unknown validation type: {value_type}"
        
        if sanitized is None:
            return False, None, f"Invalid {value_type}"
        
        return True, sanitized, None
    
    except Exception as e:
        error_msg = f"Validation error: {str(e)}"
        sanitize_logger.error(error_msg)
        return False, None, error_msg


# ===== INPUT VALIDATION DECORATORS =====

def require_validated_params(required_params: Dict[str, str]):
    """
    Decorator to validate and sanitize Flask request parameters
    
    Args:
        required_params: Dict mapping param name to validation type
                        e.g., {'symbol': 'symbol', 'shares': 'positive_int'}
    
    Usage:
        @require_validated_params({'symbol': 'symbol', 'shares': 'positive_int'})
        def buy():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            from flask import request, abort
            
            params = {}
            for param_name, param_type in required_params.items():
                value = request.form.get(param_name)
                
                is_valid, sanitized, error = validate_and_sanitize(value, param_type)
                if not is_valid:
                    abort(400, description=f"Invalid {param_name}: {error}")
                
                params[param_name] = sanitized
            
            # Add sanitized params to kwargs
            kwargs['validated_params'] = params
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


if __name__ == '__main__':
    print("Input sanitization module loaded successfully")
    
    # Test examples
    print("\n=== Sanitization Examples ===")
    print(f"Symbol: {sanitize_symbol('aapl')} (expect: AAPL)")
    print(f"Email: {sanitize_email('Test@EXAMPLE.COM')} (expect: test@example.com)")
    print(f"Username: {sanitize_username('valid_user-123')} (expect: valid_user-123)")
    print(f"String: {sanitize_string('hello  world  ')} (expect: hello world)")
    print(f"HTML: {sanitize_html_input('<script>alert(\"xss\")</script>')} (expect: escaped)")
