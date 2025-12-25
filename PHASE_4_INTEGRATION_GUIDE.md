# Phase 4 Integration Guide
**How to Integrate Stability & Scalability Modules**

---

## 🎯 Quick Start

Three new modules are ready to use. This guide shows how to integrate them into your Flask app.

---

## Module 1: Error Handling (`error_handling.py`)

### Import Statements
```python
from error_handling import (
    # Exception classes
    StockLeagueError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    ThrottleError,
    DatabaseError,
    ExternalServiceError,
    InsufficientFundsError,
    
    # Validation functions
    validate_required_fields,
    validate_numeric,
    validate_positive_integer,
    validate_portfolio_context,
    validate_sell_trade,
    validate_buy_trade,
    
    # Error handlers
    handle_database_error,
    handle_external_service_error,
    safe_database_operation,
    
    # Logging
    log_trade_attempt,
    log_auth_attempt,
    
    # Utilities
    format_currency,
    get_error_display_message,
)
```

### Example 1: Basic Trade Validation
```python
from error_handling import validate_sell_trade

@app.route("/sell", methods=["POST"])
@login_required
def sell():
    user_id = session["user_id"]
    symbol = request.form.get("symbol").upper().strip()
    shares = int(request.form.get("shares"))
    price = lookup(symbol)["price"]
    
    # Get current holdings
    stock = db.get_user_stock(user_id, symbol)
    current_shares = stock["shares"] if stock else 0
    
    # Validate
    is_valid, error_msg = validate_sell_trade(
        user_id=user_id,
        symbol=symbol,
        shares=shares,
        current_shares=current_shares,
        price=price
    )
    
    if not is_valid:
        return apology(error_msg, 400)
    
    # Execute trade...
```

### Example 2: Using Safe Database Decorator
```python
from error_handling import safe_database_operation

@safe_database_operation
def create_user_transaction(user_id, symbol, shares, price):
    return db.record_transaction(user_id, symbol, shares, price, 'buy')

# Usage:
success, result_or_error = create_user_transaction(1, 'AAPL', 50, 150.00)
if success:
    txn_id = result_or_error
else:
    print(f"Error: {result_or_error}")
```

### Example 3: Database Error Handling
```python
from error_handling import handle_database_error

try:
    db.record_transaction(user_id, symbol, shares, price, 'buy')
except Exception as e:
    success, error_msg = handle_database_error(e, "recording transaction")
    return apology(error_msg, 500)
```

---

## Module 2: Rate Limiting (`rate_limiter.py`)

### Import Statements
```python
from rate_limiter import (
    # Configuration
    RateLimitConfig,
    
    # Main throttle class
    TradeThrottle,
    
    # Throttle checking functions
    check_trade_frequency,
    check_symbol_cooldown,
    check_position_size,
    check_daily_loss,
    validate_trade_throttle,
    
    # Throttle management
    get_throttle_info,
    record_trade,
    reset_user_throttle,
    
    # API rate limiting
    APIRateLimiter,
    check_api_rate_limit,
)
```

### Example 1: Comprehensive Trade Throttle
```python
from rate_limiter import validate_trade_throttle, record_trade

@app.route("/buy", methods=["POST"])
@login_required
def buy():
    user_id = session["user_id"]
    symbol = request.form.get("symbol").upper()
    shares = int(request.form.get("shares"))
    price = lookup(symbol)["price"]
    
    # Get user portfolio
    user = db.get_user(user_id)
    stocks = db.get_user_stocks(user_id)
    portfolio_value = user["cash"] + sum(s["shares"] * lookup(s["symbol"])["price"] for s in stocks)
    
    # Validate throttle
    is_allowed, error = validate_trade_throttle(
        user_id=user_id,
        symbol=symbol,
        action='BUY',
        shares=shares,
        price=price,
        current_shares=next((s["shares"] for s in stocks if s["symbol"] == symbol), 0),
        cash=user["cash"],
        portfolio_value=portfolio_value
    )
    
    if not is_allowed:
        return apology(error, 429)  # 429 = Too Many Requests
    
    # Execute trade...
    # If successful:
    record_trade(user_id, symbol, 'BUY')
```

### Example 2: Display Throttle Info
```python
@app.route("/api/throttle-info")
@login_required
def api_throttle_info():
    from rate_limiter import get_throttle_info
    user_id = session["user_id"]
    return get_throttle_info(user_id)

# Returns: {
#     'trades_per_minute': 5,
#     'max_trades_per_minute': 10,
#     'trades_per_hour': 45,
#     'max_trades_per_hour': 100,
#     'trades_remaining_minute': 5,
#     'trades_remaining_hour': 55,
# }
```

### Example 3: Adjusting Rate Limits
```python
# In production, you might allow premium users higher limits:
from rate_limiter import validate_trade_throttle

premium_user = db.get_user(user_id)

if premium_user["is_premium"]:
    # Premium users get 20 trades/min instead of 10
    max_trades_per_minute = 20
else:
    max_trades_per_minute = 10

is_allowed, error = validate_trade_throttle(
    user_id=user_id,
    symbol=symbol,
    action='BUY',
    shares=shares,
    price=price,
    max_trades_per_minute=max_trades_per_minute  # Custom limit
)
```

---

## Module 3: Input Sanitization (`input_sanitizer.py`)

### Import Statements
```python
from input_sanitizer import (
    # String sanitization
    sanitize_string,
    sanitize_symbol,
    sanitize_username,
    sanitize_email,
    sanitize_url,
    sanitize_html_input,
    strip_html_tags,
    escape_html,
    
    # Numeric sanitization
    sanitize_integer,
    sanitize_positive_integer,
    sanitize_float,
    sanitize_currency,
    sanitize_percentage,
    
    # Security checks
    is_sql_injection_attempt,
    validate_and_sanitize,
    sanitize_dict,
    sanitize_json,
    
    # Utilities
    remove_dangerous_chars,
    truncate_text,
    normalize_whitespace,
    
    # Decorators
    require_validated_params,
)
```

### Example 1: Sanitize Form Input
```python
from input_sanitizer import sanitize_symbol, sanitize_positive_integer

@app.route("/buy", methods=["POST"])
@login_required
def buy():
    # Sanitize all form inputs
    symbol = sanitize_symbol(request.form.get("symbol"))
    shares = sanitize_positive_integer(request.form.get("shares"))
    
    # Validate
    if not symbol:
        return apology("Invalid stock symbol", 400)
    if not shares:
        return apology("Invalid share amount", 400)
    
    # Now symbol and shares are safe to use
    # symbol is uppercase with no special chars
    # shares is a positive integer
```

### Example 2: Sanitize User Input for Display
```python
from input_sanitizer import sanitize_html_input, truncate_text

# User comment that might have HTML/JS
user_comment = request.form.get("comment")

# Sanitize for display
safe_comment = sanitize_html_input(user_comment, max_length=500)
# All HTML tags removed, special chars escaped

# Display safely
return render_template("post.html", comment=safe_comment)
```

### Example 3: Validate Multiple Fields
```python
from input_sanitizer import validate_and_sanitize

# Validate and sanitize form data
symbol_valid, symbol, symbol_error = validate_and_sanitize(
    request.form.get("symbol"), 'symbol'
)
shares_valid, shares, shares_error = validate_and_sanitize(
    request.form.get("shares"), 'positive_int'
)
price_valid, price, price_error = validate_and_sanitize(
    request.form.get("limit_price"), 'float', min_val=0.01, max_val=100000
)

if not symbol_valid:
    return apology(symbol_error, 400)
if not shares_valid:
    return apology(shares_error, 400)
if not price_valid:
    return apology(price_error, 400)

# All inputs validated and safe
```

### Example 4: Using Decorator
```python
from input_sanitizer import require_validated_params

@app.route("/buy", methods=["POST"])
@login_required
@require_validated_params({
    'symbol': 'symbol',
    'shares': 'positive_int',
    'limit_price': 'float'
})
def buy(validated_params):
    symbol = validated_params['symbol']
    shares = validated_params['shares']
    limit_price = validated_params['limit_price']
    
    # All parameters already validated and sanitized
```

---

## Integration Checklist

### Step 1: Add Imports to app.py
```python
# At the top of app.py
from error_handling import (
    validate_sell_trade, validate_buy_trade,
    log_trade_attempt, validate_portfolio_context
)
from rate_limiter import validate_trade_throttle, record_trade, get_throttle_info
from input_sanitizer import sanitize_symbol, sanitize_positive_integer
```

### Step 2: Update Trading Routes (sell, buy, etc.)
- [ ] Add input sanitization at route start
- [ ] Add trade validation
- [ ] Add throttle validation
- [ ] Add error logging
- [ ] Test with valid inputs
- [ ] Test with invalid inputs
- [ ] Test error messages

### Step 3: Add New API Endpoints
- [ ] `/api/throttle-info` - Get user's throttle status
- [ ] Test endpoint returns correct format

### Step 4: Update Error Handling
- [ ] Replace generic try-except with specific error types
- [ ] Update error messages to be user-friendly
- [ ] Test error cases

### Step 5: Testing
- [ ] Run unit tests: `pytest tests/test_trading_routes.py -v`
- [ ] Test error handling with various inputs
- [ ] Test rate limiting with rapid requests
- [ ] Test sanitization with special characters
- [ ] Monitor logs for errors

### Step 6: Deployment
- [ ] Deploy to staging
- [ ] Run smoke tests
- [ ] Monitor throttle patterns
- [ ] Adjust limits if needed
- [ ] Deploy to production

---

## Performance Tips

### 1. Cache Expensive Operations
```python
# Example: Cache portfolio value calculation
@functools.lru_cache(maxsize=1000, ttl=60)
def get_portfolio_value(user_id):
    user = db.get_user(user_id)
    stocks = db.get_user_stocks(user_id)
    value = user["cash"] + sum(s["shares"] * lookup(s["symbol"])["price"] for s in stocks)
    return value
```

### 2. Async Rate Limit Checks
```python
# Rate limiting is already O(1), no need for async
# But database queries can be async:
@app.route("/buy", methods=["POST"])
@login_required
async def buy():
    user = await db_async.get_user(user_id)
    # ... rest of logic
```

### 3. Monitor Throttle Patterns
```python
# Log throttle rejections for monitoring
def record_throttle_rejection(user_id, reason):
    throttle_logger.warning(f"Throttled {user_id}: {reason}")
```

---

## Customization

### Adjust Rate Limits
```python
# In error_handling.py or at app startup:
from rate_limiter import RateLimitConfig

RateLimitConfig.TRADES_PER_MINUTE = 20  # Instead of 10
RateLimitConfig.MAX_POSITION_PERCENT = 50  # Instead of 25
```

### Custom Error Messages
```python
# In error_handling.py or your routes:
def get_user_friendly_error(error_code, user_context):
    if error_code == 429:
        if user_context.is_premium:
            return "Premium users can make 100 trades per minute."
        else:
            return "Upgrade to premium for higher trade limits."
```

### Additional Sanitization Rules
```python
# Add to input_sanitizer.py:
def sanitize_league_name(name):
    """Custom sanitizer for league names"""
    name = sanitize_string(name, max_length=50)
    # Add more rules as needed
    return name
```

---

## Troubleshooting

### "Rate limit exceeded" appearing too early?
- Check `RateLimitConfig.TRADES_PER_MINUTE` setting
- Check if cooldown is too aggressive
- Look at throttle logs

### Sanitization rejecting valid input?
- Check the regex patterns in `SecurityPatterns`
- Adjust `max_length` parameters
- Add allowed characters for your use case

### Error messages confusing users?
- Update messages in `get_error_display_message()`
- Add more context to validation errors
- Test with real users

---

## Support & Questions

### Error Handling Questions
- See `error_handling.py` documentation
- Check `PHASE_4_IMPLEMENTATION_COMPLETE.md` examples

### Rate Limiting Questions
- See `rate_limiter.py` docstrings
- Check RateLimitConfig for adjustable values
- Monitor throttle logs

### Sanitization Questions
- See `input_sanitizer.py` examples
- Check SecurityPatterns for validation rules
- Test with `sanitization_examples()` at module bottom

---

**Status**: 🟢 READY TO INTEGRATE  
**Estimated Time**: 2-3 hours  
**Complexity**: LOW (isolated modules)  
**Risk Level**: VERY LOW (no schema changes)

Start integrating today! 🚀
