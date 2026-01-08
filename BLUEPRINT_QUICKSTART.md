# 🚀 Quick Start Guide - Blueprint Architecture

**Status**: ✅ Production Ready  
**Last Updated**: January 8, 2026

---

## For Developers

### Starting the App

**Option 1: Traditional (using existing app.py)**
```bash
cd /workspaces/StockLeague
python app.py
# App starts on http://localhost:5000
```

**Option 2: Using Factory Pattern**
```bash
python app_factory.py
# Creates app with default 'development' config
```

**Option 3: Custom Config**
```python
from app_factory import create_app

# Production
app = create_app('production')

# Testing
app = create_app('testing')

# Development (default)
app = create_app()
```

---

### Adding a New Route

**Step 1**: Identify which blueprint it belongs to
- Authentication? → `blueprints/auth_bp.py`
- Portfolio? → `blueprints/portfolio_bp.py`
- Trading? → `blueprints/trades_bp.py`
- Leagues? → `blueprints/leagues_bp.py`
- Chat? → `blueprints/chat_bp.py`
- Other? → Create new blueprint

**Step 2**: Add route to blueprint
```python
# In blueprints/trades_bp.py
@trades_bp.route("/my-new-route", methods=["GET", "POST"])
@login_required
def my_new_route():
    """New route description."""
    user_id = session["user_id"]
    db = DatabaseManager()
    
    try:
        # Your logic here
        return render_template("template.html")
    except Exception as e:
        logger.error(f"Error: {e}")
        return apology("Error occurred", 500)
```

**Step 3**: Test it!
```bash
curl http://localhost:5000/my-new-route
```

---

### Creating a New Blueprint

**Step 1**: Create blueprint file
```bash
# blueprints/mynew_bp.py
```

**Step 2**: Implement blueprint
```python
from flask import Blueprint, request, session, render_template, redirect
from functools import wraps
import logging

mynew_bp = Blueprint("mynew", __name__)
logger = logging.getLogger(__name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

@mynew_bp.route("/my-route")
@login_required
def my_route():
    """Route description."""
    return render_template("template.html")
```

**Step 3**: Register in blueprints/__init__.py
```python
from blueprints.mynew_bp import mynew_bp

__all__ = [..., 'mynew_bp']
```

**Step 4**: Register in app.py (or app_factory.py)
```python
from blueprints.mynew_bp import mynew_bp
app.register_blueprint(mynew_bp)
```

---

### Database Operations

All blueprints use the same pattern:

```python
from database.db_manager import DatabaseManager

db = DatabaseManager()  # Fresh connection per request

try:
    # Read
    user = db.get_user(user_id)
    
    # Write (atomic)
    success, error, txn_id = db.execute_buy_trade_atomic(...)
    
    if not success:
        return apology(error, 400)
    
    return redirect("/")
    
except Exception as e:
    logger.error(f"DB error: {e}")
    return apology("Database error", 500)
finally:
    # Connection closed automatically
    pass
```

---

### WebSocket Events

For real-time updates:

```python
from blueprints.chat_bp import register_chat_events

# In your blueprint module
def my_event_handler():
    """Handle a WebSocket event."""
    
    @socketio.on('my_event')
    def handle_my_event(data):
        user_id = session.get('user_id')
        message = data.get('message')
        
        try:
            # Process event
            emit('response', {'status': 'ok'}, room=f'user_{user_id}')
        except Exception as e:
            logger.error(f"Error: {e}")
            emit('error', {'message': str(e)})
```

---

### Error Handling Pattern

```python
@trades_bp.route("/buy", methods=["POST"])
@login_required
def buy():
    try:
        # Validate input
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Symbol required", 400)
        
        # Get data
        db = DatabaseManager()
        quote = lookup(symbol)
        if not quote:
            return apology("Invalid symbol", 400)
        
        # Execute operation
        success, error, _ = db.execute_buy_trade_atomic(...)
        if not success:
            return apology(error, 400)
        
        flash(f"Bought {symbol}!", "success")
        return redirect("/")
        
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        return apology("Database error", 500)
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return apology("Invalid input", 400)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return apology("Unexpected error", 500)
```

---

## For Testing

### Unit Testing a Blueprint

```python
import pytest
from app_factory import create_app

@pytest.fixture
def app():
    app = create_app('testing')
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_buy_route(client, app):
    with app.test_request_context():
        # Create test user
        from database.db_manager import DatabaseManager
        db = DatabaseManager()
        user_id = db.create_user("testuser", "test@test.com", "password")
        
        # Test route
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post('/buy', data={
            'symbol': 'AAPL',
            'shares': 10
        })
        
        assert response.status_code == 302  # Redirect on success
```

### Integration Testing

```python
def test_league_workflow(client, app):
    """Test complete league creation and trading workflow."""
    with app.test_request_context():
        from database.db_manager import DatabaseManager
        db = DatabaseManager()
        
        # Create users
        user1_id = db.create_user("user1", "user1@test.com", "pass")
        user2_id = db.create_user("user2", "user2@test.com", "pass")
        
        # Test as user1
        with client.session_transaction() as sess:
            sess['user_id'] = user1_id
        
        # Create league
        response = client.post('/leagues/create', data={
            'name': 'Test League',
            'starting_cash': 10000
        })
        assert response.status_code == 302
        
        # Get league ID from response
        league_id = 1  # Simplified
        
        # Test as user2
        with client.session_transaction() as sess:
            sess['user_id'] = user2_id
        
        # Join league
        response = client.post('/leagues/join', data={
            'invite_code': 'TEST123'  # Get real code
        })
        assert response.status_code == 302
```

---

## For DevOps/Deployment

### Environment Configuration

```bash
# .env file
SECRET_KEY=your-secret-key-here
DEBUG=False
FLASK_ENV=production
DATABASE_URL=sqlite:///database/stocks.db
```

### Docker Deployment

```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app_factory.py"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stockleague-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: stockleague
  template:
    metadata:
      labels:
        app: stockleague
    spec:
      containers:
      - name: stockleague
        image: stockleague:latest
        ports:
        - containerPort: 5000
        env:
        - name: FLASK_ENV
          value: "production"
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: secret-key
```

---

## Architecture Reference

### Blueprint Responsibilities

| Blueprint | Purpose | Routes | Status |
|-----------|---------|--------|--------|
| auth_bp | User authentication | login, register, logout | ✅ |
| portfolio_bp | Portfolio management | portfolio/switch, debug/portfolio | ✅ |
| trades_bp | Buy/sell operations | buy, sell, edit_portfolio | ✅ |
| leagues_bp | League management | leagues/*, /api/league/* | ✅ |
| chat_bp | Real-time messaging | chat, /api/conversations | ✅ |
| explore_bp | Stock discovery | explore, search | ✅ |
| api_bp | API endpoints | /api/* | ✅ |

### Extension Points

Where to add new features:

- **New authentication method?** → `auth_bp`
- **New trade type?** → `trades_bp` or create `advanced_orders_bp`
- **New league feature?** → `leagues_bp`
- **New chat feature?** → `chat_bp`
- **New API endpoint?** → `api_bp` or create `v2_api_bp`
- **UI/Page feature?** → `explore_bp` or create new blueprint

---

## Troubleshooting

### Blueprint not loading?

```bash
# Check imports
python -c "from blueprints import auth_bp; print('✓ Loads')"

# Check app.py registration
grep -n "register_blueprint" app.py

# Run with verbose logging
python app.py -v
```

### Routes not working?

```bash
# List all routes
python -c "from app import app; print([r.rule for r in app.url_map.iter_rules()])"

# Test specific route
curl -X GET http://localhost:5000/leagues
```

### Database connection issues?

```python
from database.db_manager import DatabaseManager
db = DatabaseManager()
print(f"Connected: {db.get_connection()}")
```

### WebSocket not connecting?

```javascript
// In browser console
socket.on('connect', function() {
    console.log('✓ Connected');
});
socket.on('error', function(data) {
    console.log('✗ Error:', data);
});
```

---

## Best Practices

### ✅ DO

- ✅ Use fresh DatabaseManager() per request
- ✅ Validate all input
- ✅ Use appropriate HTTP status codes
- ✅ Log important events
- ✅ Handle exceptions gracefully
- ✅ Use atomic transactions
- ✅ Close connections properly
- ✅ Document your routes
- ✅ Write tests for new features
- ✅ Keep blueprints focused

### ❌ DON'T

- ❌ Hardcode user IDs
- ❌ Trust user input
- ❌ Leave connections open
- ❌ Mix concerns in one blueprint
- ❌ Forget error handling
- ❌ Emit to all users (use rooms)
- ❌ Commit large blobs to git
- ❌ Modify app.py directly for new routes
- ❌ Skip logging
- ❌ Ignore security headers

---

## Additional Resources

- 📖 [BLUEPRINT_REFACTORING_PHASE1.md](BLUEPRINT_REFACTORING_PHASE1.md) - Detailed technical docs
- 📖 [.github/copilot-instructions.md](.github/copilot-instructions.md) - Architecture patterns
- 📖 [IMPLEMENTATION_PLAN_NEXT.md](IMPLEMENTATION_PLAN_NEXT.md) - Development roadmap
- 📖 [TIER2_REFACTORING_COMPLETE.md](TIER2_REFACTORING_COMPLETE.md) - Completion summary
- 🔗 [Flask Blueprints](https://flask.palletsprojects.com/en/latest/blueprints/) - Official docs
- 🔗 [Application Factory](https://flask.palletsprojects.com/en/latest/patterns/appfactories/) - Flask docs

---

**Questions?** Check the documentation or review existing blueprint implementations.

**Found a bug?** Create an issue with example code and stack trace.

**Need help?** Review similar routes in existing blueprints for patterns.
