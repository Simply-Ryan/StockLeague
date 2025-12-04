# 📚 Database Manager API Reference

Quick reference for all available database methods in `database/db_manager.py`

---

## 🔐 User Management

### `create_user(username, password_hash)`
Creates a new user account.
```python
user_id = db.create_user("john_doe", hashed_password)
```

### `get_user(user_id)`
Get user by ID. Returns dict or None.
```python
user = db.get_user(session["user_id"])
cash = user["cash"]
```

### `get_user_by_username(username)`
Get user by username. Returns dict or None.
```python
user = db.get_user_by_username("john_doe")
```

### `update_cash(user_id, new_cash)`
Update user's cash balance.
```python
db.update_cash(user_id, 15000.50)
```

### `update_user_profile(user_id, **kwargs)`
Update profile fields (bio, avatar_url, is_public, email).
```python
db.update_user_profile(user_id, bio="Love trading!", is_public=1)
```

### `search_users(query, limit=20)`
Search users by username.
```python
results = db.search_users("john", limit=10)
```

---

## 💼 Trading & Portfolio

### `record_transaction(user_id, symbol, shares, price, transaction_type)`
Record a stock transaction.
```python
db.record_transaction(user_id, "AAPL", 10, 150.25, "buy")
```

### `get_transactions(user_id)`
Get all transactions for a user.
```python
transactions = db.get_transactions(user_id)
```

### `get_user_stocks(user_id)`
Get user's current stock holdings (with positive shares).
```python
stocks = db.get_user_stocks(user_id)
# Returns: [{"symbol": "AAPL", "shares": 10}, ...]
```

### `get_user_stock(user_id, symbol)`
Get user's holdings of a specific stock.
```python
stock = db.get_user_stock(user_id, "AAPL")
if stock:
    shares = stock["shares"]
```

---

## 👥 Friends System

### `send_friend_request(user_id, friend_id)`
Send a friend request. Returns True if successful, False if already exists.
```python
success = db.send_friend_request(current_user_id, target_user_id)
```

### `accept_friend_request(user_id, friend_id)`
Accept a pending friend request.
```python
db.accept_friend_request(current_user_id, requester_id)
```

### `decline_friend_request(user_id, friend_id)`
Decline a pending friend request.
```python
db.decline_friend_request(current_user_id, requester_id)
```

### `remove_friend(user_id, friend_id)`
Remove a friend (unfriend).
```python
db.remove_friend(current_user_id, friend_id)
```

### `get_friends(user_id)`
Get all accepted friends for a user.
```python
friends = db.get_friends(user_id)
# Returns: [{"id": 1, "username": "john", "avatar_url": "...", "last_active": "..."}, ...]
```

### `get_pending_friend_requests(user_id)`
Get pending friend requests (received).
```python
requests = db.get_pending_friend_requests(user_id)
```

### `get_sent_friend_requests(user_id)`
Get friend requests sent by user.
```python
sent = db.get_sent_friend_requests(user_id)
```

### `are_friends(user_id, friend_id)`
Check if two users are friends. Returns True/False.
```python
if db.are_friends(user1_id, user2_id):
    print("They are friends!")
```

---

## 🏆 League System

### `create_league(name, description, creator_id, league_type='public', starting_cash=10000.00, settings_json=None)`
Create a new league. Returns (league_id, invite_code).
```python
league_id, code = db.create_league(
    "My Trading League",
    "Compete with friends!",
    creator_id,
    league_type='private',
    starting_cash=50000.00
)
```

### `join_league(league_id, user_id)`
Join a league. Returns True if successful, False if already member.
```python
success = db.join_league(league_id, user_id)
```

### `leave_league(league_id, user_id)`
Leave a league.
```python
db.leave_league(league_id, user_id)
```

### `get_user_leagues(user_id)`
Get all leagues a user is a member of.
```python
leagues = db.get_user_leagues(user_id)
# Returns: [{"id": 1, "name": "League Name", "current_rank": 3, "score": 12500, ...}, ...]
```

### `get_league(league_id)`
Get league details.
```python
league = db.get_league(league_id)
name = league["name"]
```

### `get_league_by_invite_code(invite_code)`
Get league by invite code.
```python
league = db.get_league_by_invite_code("abc123xyz")
```

### `get_league_leaderboard(league_id)`
Get leaderboard for a league.
```python
leaderboard = db.get_league_leaderboard(league_id)
# Returns: [{"id": 1, "username": "john", "score": 15000, "current_rank": 1}, ...]
```

### `update_league_scores(league_id)`
Update scores and ranks for all members in a league.
```python
db.update_league_scores(league_id)
```

---

## 🔔 Notifications

### `create_notification(user_id, notification_type, title, content, related_data=None)`
Create a notification for a user.
```python
db.create_notification(
    user_id,
    "friend_request",
    "New Friend Request",
    "John wants to be your friend!",
    json.dumps({"friend_id": 123})
)
```

**Notification Types:**
- `friend_request` - Friend request received
- `friend_accepted` - Friend request accepted
- `league_invite` - League invitation
- `league_rank_change` - Rank changed in league
- `achievement` - Achievement unlocked
- `challenge` - New challenge available
- `trade_milestone` - Trading milestone reached

### `get_notifications(user_id, unread_only=False)`
Get notifications for a user.
```python
all_notifications = db.get_notifications(user_id)
unread = db.get_notifications(user_id, unread_only=True)
```

### `mark_notification_read(notification_id)`
Mark a notification as read.
```python
db.mark_notification_read(notification_id)
```

### `mark_all_notifications_read(user_id)`
Mark all notifications as read for a user.
```python
db.mark_all_notifications_read(user_id)
```

---

## 📊 Usage Examples

### Complete Friend Request Flow
```python
# User A sends request to User B
db.send_friend_request(user_a_id, user_b_id)

# Create notification for User B
db.create_notification(
    user_b_id,
    "friend_request",
    "New Friend Request",
    f"{user_a_name} wants to be your friend!"
)

# User B accepts
db.accept_friend_request(user_b_id, user_a_id)

# Create notification for User A
db.create_notification(
    user_a_id,
    "friend_accepted",
    "Friend Request Accepted",
    f"{user_b_name} accepted your friend request!"
)

# Get friends list
friends = db.get_friends(user_a_id)
```

### Complete League Flow
```python
# Create league
league_id, invite_code = db.create_league(
    "Tech Traders",
    "Trading league for tech enthusiasts",
    creator_id,
    league_type='public'
)

# Friend joins league
db.join_league(league_id, friend_id)

# Notify friend
db.create_notification(
    friend_id,
    "league_joined",
    "Joined League",
    f"You joined {league_name}!"
)

# Get leaderboard
leaderboard = db.get_league_leaderboard(league_id)

# Update scores (call this after trades)
db.update_league_scores(league_id)
```

### Check Permissions
```python
# Before showing friend's portfolio
if db.are_friends(current_user_id, target_user_id):
    portfolio = get_user_portfolio(target_user_id)
else:
    # Show limited info or redirect
    pass

# Before allowing league access
league = db.get_league(league_id)
if league["league_type"] == "private":
    # Check if user is member
    user_leagues = db.get_user_leagues(current_user_id)
    is_member = any(l["id"] == league_id for l in user_leagues)
    if not is_member:
        # Redirect or show error
        pass
```

---

## 🎯 Common Patterns

### Dashboard Data Loading
```python
@app.route("/")
@login_required
def index():
    user_id = session["user_id"]
    
    # Portfolio data
    user = db.get_user(user_id)
    stocks = db.get_user_stocks(user_id)
    
    # Social data
    friends_count = len(db.get_friends(user_id))
    pending_requests = len(db.get_pending_friend_requests(user_id))
    
    # League data
    leagues = db.get_user_leagues(user_id)
    
    # Notifications
    unread_notifications = len(db.get_notifications(user_id, unread_only=True))
    
    return render_template("index.html",
        user=user,
        stocks=stocks,
        friends_count=friends_count,
        pending_requests=pending_requests,
        leagues=leagues,
        unread_notifications=unread_notifications
    )
```

### Transaction Recording with Notifications
```python
def buy_stock(user_id, symbol, shares, price):
    # Record transaction
    db.record_transaction(user_id, symbol, shares, price, "buy")
    
    # Update cash
    user = db.get_user(user_id)
    new_cash = user["cash"] - (shares * price)
    db.update_cash(user_id, new_cash)
    
    # Update league scores
    leagues = db.get_user_leagues(user_id)
    for league in leagues:
        db.update_league_scores(league["id"])
    
    # Check for achievements (implement later)
    # check_trading_achievements(user_id)
    
    return True
```

---

## 🔧 Database Connection Management

The DatabaseManager automatically handles connections:
- Creates connection for each operation
- Closes connection after operation
- Uses `sqlite3.Row` for dict-like access
- Handles foreign keys and constraints

**Thread Safety:** Each request gets its own connection.

**Performance:** Indexes are created automatically on initialization.

---

## 🚀 Future Additions

Methods to be added in future sprints:
- Challenge system methods
- Achievement checking
- Portfolio snapshot creation
- Leaderboard caching
- Social feed queries
- Message threading
- User blocking
- Reporting system

---

This reference will be updated as new methods are added!
