# StockLeague - Complete Project Documentation

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [Data Models](#data-models)
5. [Key Features](#key-features)
6. [API Reference](#api-reference)
7. [Deployment Guide](#deployment-guide)

---

## Project Overview

**StockLeague** is a gamified social paper trading platform built with Flask (Python) and SQLite. It enables users to:

- Trade stocks in a risk-free environment with virtual money
- Compete with friends in leagues and challenges
- Follow and copy trades from top traders
- Earn achievements and climb leaderboards
- Share trades on social feeds with reactions
- Discuss strategies in real-time chat

**Technology Stack**:
- Backend: Python 3.8+, Flask, Flask-SocketIO
- Frontend: HTML5, CSS3, Bootstrap 5, JavaScript (ES6+)
- Database: SQLite with WAL mode
- APIs: Yahoo Finance (yfinance), Finnhub (news & sentiment)
- Real-time: WebSocket via Socket.IO

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser / Client                      │
│              (HTML + JS + Bootstrap 5)                   │
└────────────────────┬────────────────────────────────────┘
                     │ (HTTP + WebSocket)
        ┌────────────┴────────────┐
        ▼                         ▼
    REST Routes           WebSocket Events
    (/buy, /sell)        (subscribe_stock)
        │                         │
        └────────────┬────────────┘
                     ▼
        ┌─────────────────────────┐
        │   Flask Application     │
        │  (app.py + blueprints)  │
        │  - Auth Routes          │
        │  - Trading Routes       │
        │  - League Routes        │
        │  - Social Routes        │
        │  - API Endpoints        │
        └────────────┬────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
    DatabaseM.   Helpers.py   Advanced League
    (db_manager) (yfinance,   (rules, stats,
                  Finnhub)     achievements)
        │
        ▼
    ┌──────────────────────────────┐
    │   SQLite Database            │
    │  - users, holdings, leagues  │
    │  - leaderboards, chat        │
    │  - notifications, achievements│
    └──────────────────────────────┘
```

### Modular Organization

```
StockLeague/
├── app.py (4,838 lines)
│   ├── Login/Auth (moved to blueprints/auth_bp.py)
│   ├── Trading Routes (/buy, /sell)
│   ├── League Management (/leagues/*)
│   ├── Portfolio Viewing (/dashboard, /quote)
│   ├── Social Features (friends, followers, chat)
│   ├── Advanced Systems (tournaments, challenges, achievements)
│   └── WebSocket Handlers (SocketIO)
│
├── blueprints/
│   ├── auth_bp.py - Authentication routes
│   ├── portfolio_bp.py - Portfolio management
│   ├── api_bp.py - REST API endpoints
│   └── explore_bp.py - Stock exploration
│
├── database/
│   ├── db_manager.py (3,993 lines) - All database operations
│   ├── league_schema_upgrade.py - Schema migrations
│   └── stocks.db - SQLite database file
│
├── static/
│   ├── avatars/ - User profile pictures
│   └── js/ - Client-side JavaScript
│
├── templates/
│   ├── layout.html - Base template
│   ├── dashboard.html - Trading dashboard
│   ├── leagues.html - League management
│   ├── chat.html - Real-time chat
│   └── ... (20+ other templates)
│
├── helpers.py - Utility functions
│   ├── lookup() - Get stock quotes
│   ├── usd() - Currency formatting
│   ├── get_chart_data() - Historical data
│   └── analyze_sentiment() - News sentiment
│
└── league_rules.py - Trading rule validation
```

---

## Core Components

### 1. Authentication System (auth_bp.py)

**Routes**:
- `GET/POST /login` - User login
- `POST /logout` - User logout  
- `GET/POST /register` - New user registration

**Password Security**:
- Passwords hashed with Werkzeug's `generate_password_hash()`
- Password verification with `check_password_hash()`
- Session-based authentication

**Flow**:
```
User Submits Credentials
    ↓
Hash Password
    ↓
Check Against DB
    ↓
Create Session
    ↓
Redirect to Dashboard
```

### 2. Trading System

#### Portfolio Context Model

The key innovation is the **Portfolio Context** - a single user can trade in multiple contexts:

```python
context = {
    "type": "personal" | "league",
    "league_id": None | <int>,
    "league_name": None | "<str>"
}
```

**Personal Portfolio**:
- Stored in `users.cash` and `holdings` table
- User's main paper trading account
- Starting: $10,000

**League Portfolio**:
- Stored in `league_portfolios` and `league_holdings`
- Isolated from personal portfolio
- Can have different starting cash per league
- Used only within that league's context

#### Trading Flow

```
User Clicks "Buy"
    ↓
Validate Input
    ↓
Get Active Context
    ↓
Look Up Stock Quote (yfinance)
    ↓
Calculate Cost = shares × price
    ↓
Check Cash Balance (context-aware)
    ├─ Personal: user.cash
    └─ League: league_portfolios.cash
    ↓
IF sufficient funds:
    ├─ Record Transaction
    ├─ Update Cash
    ├─ Update Holdings
    ├─ Create Portfolio Snapshot
    ├─ Execute Copy Trades
    ├─ Broadcast SocketIO Update
    └─ Flash Success
ELSE:
    └─ Return Error
```

**Buy Route**: `POST /buy`
```python
@app.route("/buy", methods=["POST"])
@login_required
def buy():
    # 1. Get active portfolio context
    context = get_active_portfolio_context()
    
    # 2. Validate context (user is league member, league is active)
    valid, error = validate_portfolio_context(user_id, context)
    
    # 3. Get symbol, shares, strategy
    symbol = request.form.get("symbol").upper()
    shares = int(request.form.get("shares"))
    
    # 4. Look up stock
    quote = lookup(symbol)
    
    # 5. Get cash from context
    cash = get_portfolio_cash(user_id, context)
    total_cost = quote["price"] * shares
    
    # 6. Check affordability
    if cash < total_cost:
        return apology("insufficient funds", 400)
    
    # 7. Record transaction (personal or league)
    if context["type"] == "personal":
        db.record_transaction(user_id, symbol, shares, quote["price"], "buy")
        db.update_cash(user_id, cash - total_cost)
        create_portfolio_snapshot(user_id)
        _execute_copy_trades(user_id, symbol, shares, quote["price"], 'buy')
    else:
        league_id = context["league_id"]
        db.record_league_transaction(league_id, user_id, symbol, shares, quote["price"], "buy")
        db.update_league_cash(league_id, user_id, cash - total_cost)
        db.update_league_holding(league_id, user_id, symbol, shares, quote["price"])
    
    # 8. Broadcast updates
    socketio.emit('portfolio_update', {...}, room=f'user_{user_id}')
    
    return redirect("/")
```

**Sell Route**: `POST /sell`
- Similar to buy but inverse: adds cash, reduces holdings

### 3. League System

#### League Lifecycle

```
DRAFT ──────→ OPEN ──────→ LOCKED ──────→ ACTIVE ──────→ FINISHED
  │             │            │             │
  │ Settings    │ Registration│ No new joins │ Trading  │ Season ends
  │ Configurable│ Available   │ Available    │ Enabled  │
  └─────────────┴────────────┴─────────────┴──────────┴
```

#### League Creation

```python
@app.route("/leagues/create", methods=["POST"])
def create_league():
    name = request.form.get("name")
    starting_cash = float(request.form.get("starting_cash", 10000))
    mode = request.form.get("mode", "absolute_value")
    
    # Create league
    league_id = db.create_league(
        name=name,
        creator_id=user_id,
        starting_cash=starting_cash
    )
    
    # Create founder's portfolio
    db.create_league_portfolio(league_id, user_id, starting_cash)
    
    return redirect(f"/leagues/{league_id}")
```

#### League Membership

**Join League**:
1. User enters invite code or league ID
2. Check league is accepting members
3. Add to `league_members` table
4. Create isolated `league_portfolios` entry with starting cash
5. Broadcast activity to league chat

**Leave League**:
1. Remove from `league_members`
2. Delete all associated data (holdings, portfolios, transactions)
3. Transfer ownership if user is creator
4. Auto-delete league if no members remain

#### League Leaderboard

Ranking by portfolio value: `cash + (shares × current_price)`

```python
def get_league_leaderboard(league_id):
    members = db.get_league_members(league_id)
    leaderboard = []
    
    for member in members:
        portfolio = db.get_league_portfolio(league_id, member['id'])
        holdings = db.get_league_holdings(league_id, member['id'])
        
        total_value = portfolio['cash']
        for holding in holdings:
            quote = lookup(holding['symbol'])
            total_value += holding['shares'] * quote['price']
        
        leaderboard.append({
            'username': member['username'],
            'total_value': total_value,
            'score': total_value  # Can be customized per mode
        })
    
    # Sort by score descending
    leaderboard.sort(key=lambda x: x['score'], reverse=True)
    return leaderboard
```

**Caching**: Leaderboards cached in `leaderboards` table with:
- `leaderboard_type`: "global" or "league_<id>"
- `period`: "all" (can extend to daily, weekly)
- `data_json`: Serialized leaderboard array
- Updates via background job every 5 minutes

### 4. Database Layer (db_manager.py)

**Design Pattern**: Lightweight wrapper around SQLite

```python
class DatabaseManager:
    def __init__(self, db_path="database/stocks.db"):
        self.db_path = db_path
        self.init_db()  # Create/upgrade schema
    
    def get_connection(self):
        """Get DB connection with PRAGMA settings"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Dict-like rows
        conn.execute('PRAGMA foreign_keys = ON')  # Referential integrity
        conn.execute('PRAGMA journal_mode = WAL')  # Better concurrency
        return conn
    
    def init_db(self):
        """Create all required tables on startup"""
        # 1. Core tables (users, holdings, transactions)
        # 2. League tables (leagues, league_members, league_portfolios)
        # 3. Social tables (friends, notifications, chat_messages)
        # 4. Advanced tables (achievements, tournaments, challenges)
```

**Key Operations**:

| Operation | Method | Notes |
|-----------|--------|-------|
| Create User | `create_user(username, hash)` | Returns user_id |
| Get User | `get_user(user_id)` | Returns dict with cash, bio, etc. |
| Record Trade | `record_transaction(user_id, symbol, shares, price, type)` | Type: "buy" or "sell" |
| Get Holdings | `get_user_stocks(user_id)` | List of {symbol, shares, purchase_price} |
| Update Cash | `update_cash(user_id, amount)` | Directly set cash balance |
| Create League | `create_league(name, creator_id, starting_cash)` | Returns league_id |
| Get League Members | `get_league_members(league_id)` | List of user dicts |
| Create Portfolio Snapshot | `create_snapshot(user_id, total_value, cash, stocks_json)` | For historical tracking |

### 5. Real-time Chat System (SocketIO)

**Chat Rooms**:
- `league_<id>` - League chat (accessible only to league members)
- `dm_<user1_id>_<user2_id>` - Direct messages

**Events**:
```javascript
// Client sends message
socket.emit('chat_message', {
    room: 'league_5',
    message: 'Just bought 100 shares of AAPL!'
});

// Server broadcasts to room
socketio.emit('chat_message', msg, room='league_5')

// All clients in room receive
socket.on('chat_message', function(msg) {
    // Display in chat interface
});
```

**Moderation**:
- Admins can mute/ban users
- Muted users can't send messages
- Banned users removed from room
- Messages persisted to `chat_messages` table

### 6. Social Features

#### Friends System

```
Pending → Accepted → (can remove)
  ↓
User B receives notification
Clicks Accept/Decline
```

**Tables**:
- `friends` table with status: "pending" or "accepted"

**Flow**:
```
1. User A sends friend request to User B
2. Create record: friends(user_id=A, friend_id=B, status='pending')
3. Notification sent to B
4. B clicks Accept:
   - Update status to 'accepted'
   - Create notification back to A
5. Now A and B can see each other's activity
```

#### Followers & Copy Trading

**Copy Trading**: Auto-execute trades from followed traders

```python
# User X follows Trader Y and enables copy trading
db.start_copy_trading(
    follower_id=X,
    trader_id=Y,
    allocation_pct=10,  # Allocate 10% of X's portfolio
    max_trade=1000      # Max $1000 per trade
)

# When Trader Y buys 100 AAPL @ $150:
# Trader Y executes: -$15,000 from Y's account
# User X's System:
#   allocation = 15000 * 10% = $1500
#   shares = min(1500/150, max_trade/150)
#         = min(10, 6.67) = 6 shares
#   Cost = 6 * $150 = $900
#   X loses $900, gains 6 AAPL shares
```

#### Activity Feed

Users can post achievements and trades that friends see with emoji reactions:

```
User posts achievement → 👍 ❤️ 😂 🔥 🚀
(Emoji counts shown)
```

### 7. Advanced League System

#### League Modes

**Absolute Value** (default):
- Leaderboard by portfolio value
- Formula: `cash + ∑(shares × price)`

**Limited Capital**:
- Enforces max position size
- Imposes trading fees
- Limits portfolio concentration

**Time Weighted**:
- Longer-held positions score higher
- Discourages short-term trading

#### Achievements & Badges

**System**:
1. Achievements defined in `league_achievements` table
2. User earns by meeting criteria
3. Badge appears on profile/leaderboard
4. Different rarity levels: common, rare, epic, legendary

**Examples**:
- "First Trade" - Awarded after first trade
- "Big Winner" - Portfolio value > $15,000
- "Day Trader" - 50+ trades completed
- "Diversified" - Hold 5+ different stocks

#### Tournaments

**Bracket Tournament**:
1. Create tournament (creator sets duration)
2. Users register
3. System pairs members in round 1
4. Each pair competes for set period
5. Winner advances to next round
6. Final winner gets trophy

---

## Data Models

### Core Tables

#### users
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    hash TEXT NOT NULL,
    email TEXT,
    cash NUMERIC DEFAULT 10000.00,
    bio TEXT,
    avatar_url TEXT,
    is_public INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP
);
```

#### holdings
```sql
CREATE TABLE holdings (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    shares INTEGER NOT NULL,
    purchase_price NUMERIC NOT NULL,
    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, symbol)
);
```

#### transactions
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    shares INTEGER NOT NULL,
    price NUMERIC NOT NULL,
    type TEXT NOT NULL,  -- 'buy' or 'sell'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### leagues
```sql
CREATE TABLE leagues (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    creator_id INTEGER NOT NULL,
    league_type TEXT DEFAULT 'public',
    starting_cash NUMERIC DEFAULT 10000.00,
    status TEXT DEFAULT 'active',  -- active, finished, draft
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creator_id) REFERENCES users(id)
);
```

#### league_members
```sql
CREATE TABLE league_members (
    id INTEGER PRIMARY KEY,
    league_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    is_admin INTEGER DEFAULT 0,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (league_id) REFERENCES leagues(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(league_id, user_id)
);
```

#### league_portfolios
```sql
CREATE TABLE league_portfolios (
    id INTEGER PRIMARY KEY,
    league_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    cash NUMERIC NOT NULL,
    FOREIGN KEY (league_id) REFERENCES leagues(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(league_id, user_id)
);
```

#### league_holdings
```sql
CREATE TABLE league_holdings (
    id INTEGER PRIMARY KEY,
    league_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    shares INTEGER NOT NULL,
    avg_cost NUMERIC NOT NULL,
    FOREIGN KEY (league_id) REFERENCES leagues(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(league_id, user_id, symbol)
);
```

#### leaderboards
```sql
CREATE TABLE leaderboards (
    id INTEGER PRIMARY KEY,
    leaderboard_type TEXT NOT NULL,
    period TEXT NOT NULL,
    data_json TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(leaderboard_type, period)  -- ← FIX: Enables ON CONFLICT
);
```

---

## Key Features

### 1. Real-time Stock Quotes

**Technology**: Yahoo Finance (yfinance)

```python
def lookup(symbol):
    ticker = yf.Ticker(symbol.upper())
    data = ticker.fast_info  # Faster than full info
    
    return {
        "symbol": symbol,
        "name": data.get('longName'),
        "price": data.get('lastPrice'),
        "change": price - previous_close,
        "change_percent": (change / previous_close) * 100
    }
```

**Caching**: 30-second cache to reduce API calls

### 2. Portfolio Snapshots

Daily snapshots track portfolio value over time for performance charts

```python
create_portfolio_snapshot(user_id)
# Stores: {user_id, total_value, cash, stocks_json, timestamp}
```

Used for:
- 30-day portfolio value graph
- Return calculations
- Performance metrics

### 3. Options Trading (Coming Soon)

Framework in place:
- `options_positions` table
- `options_contracts` table
- Black-Scholes pricing (`get_option_price_and_greeks()`)
- Greeks calculation (Delta, Gamma, Theta, Vega, Rho)

### 4. Sentiment Analysis

News articles analyzed for sentiment (positive/neutral/negative)

```python
analyze_sentiment(text)
# Uses VADER sentiment analyzer
# Returns: {'label': 'positive', 'score': 0.85}
```

### 5. Technical Indicators

Chart data includes:
- Moving averages (MA)
- Relative Strength Index (RSI)
- MACD
- Bollinger Bands

---

## API Reference

### REST Endpoints

#### Trading
- `POST /buy` - Buy stocks
- `POST /sell` - Sell stocks
- `GET /quote` - Get stock quote (with news)
- `POST /watch` - Add to watchlist
- `POST /watchlist/remove` - Remove from watchlist

#### Portfolio
- `GET /dashboard` - View portfolio
- `GET /history` - View trade history
- `GET /analytics` - Advanced analytics
- `POST /edit_portfolio` - Reset portfolio

#### Leagues
- `GET /leagues` - View all leagues
- `POST /leagues/create` - Create league
- `GET /leagues/<id>` - View league
- `POST /leagues/join` - Join league
- `POST /leagues/<id>/leave` - Leave league
- `POST /leagues/<id>/trade` - Trade in league
- `POST /leagues/<id>/end` - End season (admin)

#### Social
- `GET /friends` - View friends
- `POST /send_friend_request` - Request friend
- `POST /accept_friend` - Accept request
- `POST /remove_friend` - Remove friend
- `GET /profile/<username>` - View profile

#### Admin
- `GET /admin/chat` - Chat moderation dashboard
- `POST /admin/users/<id>/warn` - Issue warning

### WebSocket Events

#### Client → Server
```javascript
socket.emit('subscribe_stock', {symbol: 'AAPL'});
socket.emit('unsubscribe_stock', {symbol: 'AAPL'});
socket.emit('chat_message', {room: 'league_5', message: 'text'});
socket.emit('join_room', {room: 'league_5'});
socket.emit('leave_room', {room: 'league_5'});
```

#### Server → Client
```javascript
socket.on('stock_update', (data) => {
    // {symbol, price, change, change_percent, timestamp}
});

socket.on('portfolio_update', (data) => {
    // {cash, total_value, stocks}
});

socket.on('chat_message', (msg) => {
    // {id, username, message, time, reactions}
});

socket.on('league_member_kicked', (data) => {
    // {league_id, user_id}
});
```

---

## Deployment Guide

### Requirements
- Python 3.8+
- pip (package manager)
- 100MB disk space (database + assets)

### Installation

```bash
# Clone repository
git clone <repo>
cd StockLeague

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Create database
python -c "from database.db_manager import DatabaseManager; db = DatabaseManager()"

# Run development server
python app.py
# Visit http://localhost:5000
```

### Environment Variables

Create `.env` file:
```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DATABASE_URL=sqlite:///instance/stocks.db
FINNHUB_API_KEY=your-finnhub-key
REDIS_URL=redis://localhost:6379/0  # Optional
```

### Production Deployment

```bash
# Use production server (Gunicorn)
pip install gunicorn
gunicorn --workers 4 --bind 0.0.0.0:8000 app:app

# OR use waitress for Windows
pip install waitress
waitress-serve --port=8000 app:app

# Set up Nginx reverse proxy
# Configure SSL with Let's Encrypt
# Set FLASK_ENV=production
# Migrate to PostgreSQL for scalability
```

### Database Backups

```bash
# Backup SQLite database
cp instance/stocks.db instance/stocks.db.backup

# Or automate with cron
0 2 * * * /usr/bin/sqlite3 /path/to/stocks.db ".backup '/path/to/backup/stocks-$(date +%Y%m%d).db'"
```

---

## Performance Optimization

### Current Bottlenecks
1. Leaderboard calculation (loops through all users)
2. Stock quotes (API calls not cached long enough)
3. Portfolio value calculation (multiple DB queries)

### Optimizations Applied
- Leaderboard caching in `leaderboards` table
- Stock price cache (30 seconds)
- Portfolio snapshots for historical data
- WAL mode for SQLite (better concurrency)
- Foreign key optimization with indexes

### Future Optimizations
1. Redis caching layer for quote prices
2. Batch stock price updates
3. Portfolio value calculated server-side
4. Indexed leaderboard snapshots
5. Migrate to PostgreSQL (production)

---

## Security Considerations

### Current Security Measures
- Password hashing with Werkzeug
- Session-based authentication
- CSRF protection (Flask default)
- SQL parameterization (no SQL injection)
- Input validation on all routes
- Foreign key constraints enforced

### Recommended Enhancements
- Rate limiting on API endpoints
- Request signing for admin operations
- Audit logging for trades
- Two-factor authentication
- HTTPS/TLS enforcement
- Content Security Policy headers
- CORS whitelist

---

## Testing

### Unit Tests
```bash
# Run existing tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_league_admin.py::test_kick_user
```

### Manual Testing
```bash
# 1. Create two test users
# 2. Create a league
# 3. One user joins, trades
# 4. Check leaderboard updates
# 5. Verify notifications sent
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'flask'"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "Database is locked"
```bash
# Another process is accessing DB
pkill -f "python app.py"
# Then restart
```

### Stock prices not updating
```bash
# Check internet connection
# Check yfinance availability
# Verify symbols are valid
python -c "from helpers import lookup; print(lookup('AAPL'))"
```

---

## Future Roadmap

### Phase 2 (Next)
- [ ] Options trading (framework exists)
- [ ] Margin trading
- [ ] Stop-loss orders
- [ ] Cryptocurrency support

### Phase 3
- [ ] Mobile app (React Native)
- [ ] Advanced charting (TradingView)
- [ ] Broker integration (paper trading API)
- [ ] Market simulation (VIX events, flash crashes)

### Phase 4
- [ ] Machine learning predictions
- [ ] Algorithmic trading bots
- [ ] Backtesting engine
- [ ] Real money integration

---

## Contributors & Credits

**Built with**: Flask, SQLite, Bootstrap, Yahoo Finance, Finnhub API

**Key Components**:
- Authentication: Flask-Session, Werkzeug
- Real-time: Flask-SocketIO, Socket.IO
- Charts: Chart.js, Lightweight Charts
- Icons: Font Awesome

---

## License

Educational use - see LICENSE file

---

**Documentation Version**: 1.0  
**Last Updated**: December 19, 2025  
**Review Status**: Comprehensive Code Review Complete
