
import os
import random
import uuid
import json
from flask import Flask, flash, redirect, render_template, request, session, jsonify, send_file
from flask_session import Session
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from helpers import apology, lookup, usd, get_chart_data, get_popular_stocks, get_market_movers, get_stock_news, get_option_price_and_greeks, analyze_sentiment, fetch_news_finnhub, get_cached_or_fetch_news
from database.db_manager import DatabaseManager
from dotenv import load_dotenv
import threading
import time
from datetime import datetime
from collections import defaultdict
from league_modes import get_league_mode, get_available_modes, MODE_ABSOLUTE_VALUE
from league_rules import LeagueRuleEngine


# --- Login Required Decorator (move up) ---
def login_required(f):
    """
    Decorate routes to require login.
    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# Load environment variables
load_dotenv()

# Configure application
app = Flask(__name__)

# Secret key for session management (change in production!)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"

# Custom filters
app.jinja_env.filters["usd"] = usd
app.jinja_env.filters["abs"] = abs
app.jinja_env.filters["min"] = min
app.jinja_env.filters["max"] = max

# Add built-in functions to Jinja2 globals
app.jinja_env.globals.update(abs=abs, min=min, max=max)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- Chat Settings (Themes/Dark Mode) ---
@app.route("/chat/settings")
@login_required
def chat_settings():
    return render_template("chat_settings.html")

# --- Admin-only decorator ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        user = db.get_user(user_id)
        if not user or not user.get("is_admin"):
            return apology("Admins only", 403)
        return f(*args, **kwargs)
    return decorated_function

# --- Chat Admin Dashboard ---
@app.route("/admin/chat")
@login_required
@admin_required
def admin_chat():
    return render_template("admin_chat.html")

@app.route("/admin/api/chat/rooms")
@login_required
@admin_required
def admin_api_chat_rooms():
    # List all rooms and users (from in-memory for now)
    rooms = []
    for room, users in chat_users.items():
        rooms.append({"name": room, "users": list(users)})
    return jsonify({"rooms": rooms})

@app.route("/admin/api/chat/reports")
@login_required
@admin_required
def admin_api_chat_reports():
    # Placeholder: return empty for now
    return jsonify({"reports": []})

# --- Trading Event Chat Integration ---
def send_trade_alert_to_chat(user_id, symbol, shares, price, trade_type):
    """Send trade alerts to user's league chats"""
    user = db.get_user(user_id)
    username = user["username"] if user else "User"
    msg = f"{username} just {trade_type} {shares} shares of {symbol} at {usd(price)}."
    
    # Get user's leagues and send to each league chat
    leagues = db.get_user_leagues(user_id)
    for league in leagues:
        league_room = f'league_{league["id"]}'
        socketio.emit('chat_message', {
            'id': str(uuid.uuid4()),
            'user_id': None,
            'username': 'System',
            'message': msg,
            'time': datetime.now().strftime('%H:%M'),
            'reactions': {}
        }, room=league_room)
        # Persist to chat history
        db.insert_chat_message(league_room, 'System', msg)

# --- Real-Time Chat System ---
# In-memory chat storage (replace with DB for production)
chat_rooms = defaultdict(list)  # room -> list of messages
chat_users = defaultdict(set)   # room -> set of usernames
user_typing = defaultdict(set)  # room -> set of typing usernames
# Private/group chat management
private_rooms = defaultdict(set)  # room -> set of allowed usernames
# In-memory moderation (replace with DB for production)
muted_users = defaultdict(set)  # room -> set of muted usernames
banned_users = defaultdict(set) # room -> set of banned usernames
moderators = defaultdict(set)   # room -> set of moderator usernames

# In-memory notifications (replace with DB for production)
user_notifications = defaultdict(list)  # username -> list of notifications

@app.route("/chat")
@login_required
def chat():
    user_id = session.get("user_id")
    username = session.get("username", "User")
    conversations = db.get_user_conversations(user_id)
    return render_template("chat.html", conversations=conversations, username=username)

@app.route("/api/conversations")
@login_required
def api_conversations():
    user_id = session.get("user_id")
    conversations = db.get_user_conversations(user_id)
    return jsonify({"conversations": conversations})

# SocketIO events
@socketio.on('join_room')
def handle_join_room(data):
    room = data.get('room')
    username = session.get('username', 'User')
    user_id = session.get('user_id')
    
    if not room:
        return
    
    # Verify access to room
    if room.startswith('dm_'):
        # Direct message - verify user is part of the conversation
        parts = room.split('_')
        if len(parts) == 3:
            try:
                user1_id = int(parts[1])
                user2_id = int(parts[2])
                if user_id not in [user1_id, user2_id]:
                    emit('chat_notification', {'type': 'error', 'message': 'Access denied.'}, room=request.sid)
                    return
            except ValueError:
                return
    elif room.startswith('league_'):
        # League chat - verify user is member
        parts = room.split('_')
        if len(parts) == 2:
            try:
                league_id = int(parts[1])
                # Check if user is league member
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM league_members WHERE league_id = ? AND user_id = ?', (league_id, user_id))
                if not cursor.fetchone():
                    conn.close()
                    emit('chat_notification', {'type': 'error', 'message': 'You are not a member of this league.'}, room=request.sid)
                    return
                conn.close()
            except ValueError:
                return
    
    join_room(room)
    chat_users[room].add(username)
    emit('user_presence', list(chat_users[room]), room=room)
    # Load chat history from DB
    history = db.get_chat_history(room, limit=100)
    emit('chat_history', history, room=request.sid)

@socketio.on('leave_room')
def handle_leave_room(data):
    room = data.get('room')
    username = session.get('username', 'User')
    
    if not room:
        return
    
    leave_room(room)
    if room in chat_users:
        chat_users[room].discard(username)
        emit('user_presence', list(chat_users[room]), room=room)

# Create private/group room
@socketio.on('create_private_room')
def handle_create_private_room(data):
    room = data.get('room')
    creator = data.get('creator')
    members = set(data.get('members', []))
    if not room or not creator:
        return
    private_rooms[room] = members | {creator}
    moderators[room].add(creator)
    emit('chat_notification', {'type': 'system', 'message': f'Private room "{room}" created.'}, room=request.sid)

# Invite user to private/group room
@socketio.on('invite_to_room')
def handle_invite_to_room(data):
    room = data.get('room')
    inviter = data.get('inviter')
    invitee = data.get('invitee')
    if room and inviter and invitee:
        if inviter in moderators[room] or inviter in private_rooms[room]:
            private_rooms[room].add(invitee)
            emit('chat_notification', {'type': 'system', 'message': f'{invitee} was invited to {room} by {inviter}.'}, room=room)

@socketio.on('chat_message')
def handle_chat_message(data):
    room = data.get('room')
    username = session.get('username', 'User')
    user_id = session.get('user_id')
    message = data.get('message', '')
    
    if not room or not message:
        return
    
    msg_id = str(uuid.uuid4())
    msg = {
        'id': msg_id,
        'user_id': user_id,
        'username': username,
        'message': message,
        'time': datetime.now().strftime('%H:%M'),
        'reactions': {}
    }
    chat_rooms[room].append(msg)
    # Persist to DB
    db.insert_chat_message(room, username, message, user_id=user_id)
    emit('chat_message', msg, room=room)
# Moderation events
@socketio.on('mute_user')
def handle_mute_user(data):
    room = data.get('room', 'General')
    target = data.get('target')
    moderator = data.get('moderator')
    # Only moderators can mute
    if moderator in moderators[room]:
        muted_users[room].add(target)
        emit('chat_notification', {'type': 'system', 'message': f'{target} has been muted by {moderator}.'}, room=room)

@socketio.on('unmute_user')
def handle_unmute_user(data):
    room = data.get('room', 'General')
    target = data.get('target')
    moderator = data.get('moderator')
    if moderator in moderators[room]:
        muted_users[room].discard(target)
        emit('chat_notification', {'type': 'system', 'message': f'{target} has been unmuted by {moderator}.'}, room=room)

@socketio.on('ban_user')
def handle_ban_user(data):
    room = data.get('room', 'General')
    target = data.get('target')
    moderator = data.get('moderator')
    if moderator in moderators[room]:
        banned_users[room].add(target)
        chat_users[room].discard(target)
        emit('chat_notification', {'type': 'system', 'message': f'{target} has been banned by {moderator}.'}, room=room)

@socketio.on('unban_user')
def handle_unban_user(data):
    room = data.get('room', 'General')
    target = data.get('target')
    moderator = data.get('moderator')
    if moderator in moderators[room]:
        banned_users[room].discard(target)
        emit('chat_notification', {'type': 'system', 'message': f'{target} has been unbanned by {moderator}.'}, room=room)

@socketio.on('delete_message')
def handle_delete_message(data):
    room = data.get('room', 'General')
    msg_id = data.get('msgId')
    moderator = data.get('moderator')
    if moderator in moderators[room]:
        # Remove message from chat history
        chat_rooms[room] = [msg for msg in chat_rooms[room] if msg.get('id') != msg_id]
        emit('chat_history', chat_rooms[room], room=room)
        emit('chat_notification', {'type': 'system', 'message': f'A message was deleted by {moderator}.'}, room=room)

@socketio.on('report_message')
def handle_report_message(data):
    room = data.get('room', 'General')
    msg_id = data.get('msgId')
    reporter = data.get('reporter')
    # For demo, just notify moderators
    for mod in moderators[room]:
        emit('chat_notification', {'type': 'system', 'message': f'Message {msg_id} was reported by {reporter}.'}, room=room)

    # In-app notification for @mentions
    words = message.split()
    mentioned = [w[1:] for w in words if w.startswith('@') and len(w) > 1]
    for user in mentioned:
        if user in chat_users[room]:
            notif = {
                'type': 'mention',
                'from': username,
                'room': room,
                'message': message,
                'time': msg['time']
            }
            user_notifications[user].append(notif)
            emit('chat_notification', notif, room=room)
# SocketIO event for direct notification
@socketio.on('send_notification')
def handle_send_notification(data):
    user = data.get('user')
    notif = data.get('notification')
    if user and notif:
        user_notifications[user].append(notif)
        emit('chat_notification', notif, room=request.sid)

@socketio.on('chat_file')
def handle_chat_file(data):
    room = data.get('room')
    username = session.get('username', 'User')
    user_id = session.get('user_id')
    filename = data.get('filename', 'file')
    filedata = data.get('data', '')
    
    if not room:
        return
    
    msg_id = str(uuid.uuid4())
    msg = {
        'id': msg_id,
        'user_id': user_id,
        'username': username,
        'filename': filename,
        'data': filedata,
        'time': datetime.now().strftime('%H:%M'),
        'type': 'file'
    }
    chat_rooms[room].append(msg)
    # Persist to DB
    db.insert_chat_message(room, username, None, msg_type='file', filedata=filedata, filename=filename, user_id=user_id)
    emit('chat_file', msg, room=room)

@socketio.on('typing')
def handle_typing(data):
    room = data.get('room')
    username = session.get('username', 'User')
    
    if not room:
        return
    
    user_typing[room].add(username)
    emit('show_typing', {'username': username}, room=room)
    # Remove after short delay
    def remove_typing():
        time.sleep(2)
        user_typing[room].discard(username)
    threading.Thread(target=remove_typing).start()

@socketio.on('add_reaction')
def handle_add_reaction(data):
    room = data.get('room', 'General')
    msg_id = data.get('msgId')
    emoji = data.get('emoji')
    # Find message and add reaction
    for msg in chat_rooms[room]:
        if msg.get('id') == msg_id:
            msg.setdefault('reactions', {})
            msg['reactions'][emoji] = msg['reactions'].get(emoji, 0) + 1
            emit('add_reaction', {'msgId': msg_id, 'emoji': emoji}, room=room)
            break

@socketio.on('disconnect')
def handle_disconnect():
    # Remove user from all rooms
    username = session.get('username', 'User')
    for room in chat_users:
        if username in chat_users[room]:
            chat_users[room].discard(username)
            emit('user_presence', list(chat_users[room]), room=room)

# --- End Real-Time Chat System ---

# Initialize database manager
db = DatabaseManager()

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Store active stock subscriptions (symbol -> set of session_ids)
stock_subscriptions = {}


def create_portfolio_snapshot(user_id):
    """Create a snapshot of the user's current portfolio value"""
    import json
    
    # Get user's stocks and cash
    stocks = db.get_user_stocks(user_id)
    user = db.get_user(user_id)
    cash = user["cash"]
    
    # Calculate total portfolio value
    total_value = cash
    stocks_data = []
    
    for stock in stocks:
        quote = lookup(stock["symbol"])
        if quote:
            stock_value = stock["shares"] * quote["price"]
            total_value += stock_value
            stocks_data.append({
                "symbol": stock["symbol"],
                "shares": stock["shares"],
                "price": quote["price"],
                "value": stock_value
            })
    
    # Save snapshot
    stocks_json = json.dumps(stocks_data)
    db.create_snapshot(user_id, total_value, cash, stocks_json)


def check_achievements(user_id):
    """Check and award achievements for a user"""
    user = db.get_user(user_id)
    transactions = db.get_transactions(user_id)
    
    # Get user's stocks
    stocks = db.get_user_stocks(user_id)
    
    # Calculate portfolio value
    portfolio_value = user["cash"]
    for stock in stocks:
        quote = lookup(stock["symbol"])
        if quote:
            portfolio_value += stock["shares"] * quote["price"]
    
    achievements_earned = []
    
    # First Trade Achievement
    if len(transactions) == 1:
        if not db.has_achievement(user_id, "first_trade"):
            db.award_achievement(user_id, "first_trade", "First Trade", "Made your first trade!")
            achievements_earned.append("First Trade")
    
    # Active Trader (10 trades)
    if len(transactions) >= 10:
        if not db.has_achievement(user_id, "active_trader"):
            db.award_achievement(user_id, "active_trader", "Active Trader", "Completed 10 trades!")
            achievements_earned.append("Active Trader")
    
    # Day Trader (50 trades)
    if len(transactions) >= 50:
        if not db.has_achievement(user_id, "day_trader"):
            db.award_achievement(user_id, "day_trader", "Day Trader", "Completed 50 trades!")
            achievements_earned.append("Day Trader")
    
    # Profit Maker ($1000 profit)
    profit = portfolio_value - 10000
    if profit >= 1000:
        if not db.has_achievement(user_id, "profit_maker"):
            db.award_achievement(user_id, "profit_maker", "Profit Maker", "Earned $1,000 in profit!")
            achievements_earned.append("Profit Maker")
    
    # Big Winner ($5000 profit)
    if profit >= 5000:
        if not db.has_achievement(user_id, "big_winner"):
            db.award_achievement(user_id, "big_winner", "Big Winner", "Earned $5,000 in profit!")
            achievements_earned.append("Big Winner")
    
    # Portfolio Builder (portfolio over $15k)
    if portfolio_value >= 15000:
        if not db.has_achievement(user_id, "portfolio_builder"):
            db.award_achievement(user_id, "portfolio_builder", "Portfolio Builder", "Portfolio value reached $15,000!")
            achievements_earned.append("Portfolio Builder")
    
    # Diversified (own 5+ different stocks)
    if len(stocks) >= 5:
        if not db.has_achievement(user_id, "diversified"):
            db.award_achievement(user_id, "diversified", "Diversified", "Own 5 different stocks!")
            achievements_earned.append("Diversified")
    
    # Create notifications for new achievements
    for achievement in achievements_earned:
        db.create_notification(
            user_id,
            "achievement",
            f"Achievement Unlocked: {achievement}!",
            f"Congratulations! You've earned the '{achievement}' achievement!",
            "/profile/" + user["username"]
        )
    
    return achievements_earned


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]
    
    # Get user's stocks
    stocks = db.get_user_stocks(user_id)
    
    # Get all transactions to calculate cost basis
    transactions = db.get_transactions(user_id)
    
    # Calculate cost basis for each stock
    cost_basis = {}
    for trans in transactions:
        symbol = trans["symbol"]
        if symbol not in cost_basis:
            cost_basis[symbol] = {"total_cost": 0, "shares": 0}
        
        if trans["type"] == "buy":
            cost_basis[symbol]["total_cost"] += trans["shares"] * trans["price"]
            cost_basis[symbol]["shares"] += trans["shares"]
        else:  # sell
            # Reduce proportionally
            if cost_basis[symbol]["shares"] > 0:
                avg_cost = cost_basis[symbol]["total_cost"] / cost_basis[symbol]["shares"]
                cost_basis[symbol]["total_cost"] -= abs(trans["shares"]) * avg_cost
                cost_basis[symbol]["shares"] -= abs(trans["shares"])
    
    # Get current prices and calculate totals
    total_value = 0
    total_gain_loss = 0
    
    for stock in stocks:
        quote = lookup(stock["symbol"])
        if quote:
            stock["price"] = quote["price"]
            stock["change_percent"] = quote.get("change_percent", 0)
            stock["total"] = stock["shares"] * quote["price"]
            total_value += stock["total"]
            
            # Calculate gain/loss
            if stock["symbol"] in cost_basis and cost_basis[stock["symbol"]]["shares"] > 0:
                avg_cost = cost_basis[stock["symbol"]]["total_cost"] / cost_basis[stock["symbol"]]["shares"]
                stock["avg_cost"] = avg_cost
                stock["gain_loss"] = stock["total"] - (stock["shares"] * avg_cost)
                stock["gain_loss_percent"] = ((stock["price"] - avg_cost) / avg_cost) * 100 if avg_cost > 0 else 0
                total_gain_loss += stock["gain_loss"]
            else:
                stock["avg_cost"] = stock["price"]
                stock["gain_loss"] = 0
                stock["gain_loss_percent"] = 0
        else:
            stock["price"] = 0
            stock["total"] = 0
            stock["gain_loss"] = 0
            stock["gain_loss_percent"] = 0
    
    # Get user's cash balance
    user = db.get_user(user_id)
    cash = user["cash"]
    
    # Calculate grand total and overall performance
    grand_total = cash + total_value
    starting_cash = 10000.00  # Default starting amount
    total_return = grand_total - starting_cash
    total_return_percent = (total_return / starting_cash) * 100 if starting_cash > 0 else 0
    
    # Get popular stocks for market overview (limited to 4 for speed)
    popular_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
    popular_stocks = []
    for symbol in popular_symbols:
        quote = lookup(symbol)
        if quote:
            popular_stocks.append(quote)
    
    # Get watchlist count only (don't fetch prices for speed)
    watchlist = db.get_watchlist(user_id)
    
    # Get portfolio history for chart
    portfolio_history = db.get_portfolio_history(user_id, days=30)
    
    return render_template("index.html", 
                         stocks=stocks, 
                         cash=cash, 
                         grand_total=grand_total,
                         total_value=total_value,
                         total_gain_loss=total_gain_loss,
                         total_return=total_return,
                         total_return_percent=total_return_percent,
                         popular_stocks=popular_stocks,
                         watchlist_count=len(watchlist),
                         portfolio_history=portfolio_history)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        
        # Validate input
        if not symbol:
            return apology("must provide symbol", 400)
        
        symbol = symbol.upper().strip()
        
        if not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("must provide positive number of shares", 400)
        
        shares = int(shares)
        
        # Look up stock quote
        quote = lookup(symbol)
        if not quote:
            return apology("invalid symbol", 400)
        
        # Calculate total cost
        price = quote["price"]
        total_cost = price * shares
        
        # Get user's cash
        user_id = session["user_id"]
        user = db.get_user(user_id)
        cash = user["cash"]
        
        # Check if user can afford
        if cash < total_cost:
            return apology("can't afford", 400)
        
        # Get optional strategy and notes
        strategy = request.form.get("strategy") or None
        notes = request.form.get("notes") or None
        
        # Record transaction
        txn_id = db.record_transaction(user_id, symbol, shares, price, "buy", strategy, notes)
        # Send trade alert to chat
        send_trade_alert_to_chat(user_id, symbol, shares, price, 'bought')
        
        # Update user's cash
        db.update_cash(user_id, cash - total_cost)
        
        # Execute copy trades for any followers
        _execute_copy_trades(user_id, symbol, shares, price, 'buy', txn_id)
        
        # Create portfolio snapshot
        create_portfolio_snapshot(user_id)
        
        # Emit real-time portfolio update
        user_updated = db.get_user(user_id)
        stocks_updated = db.get_user_stocks(user_id)
        portfolio_value = user_updated["cash"]
        for stock in stocks_updated:
            q = lookup(stock["symbol"])
            if q:
                portfolio_value += stock["shares"] * q["price"]
        
        socketio.emit('portfolio_update', {
            'cash': user_updated["cash"],
            'total_value': portfolio_value,
            'stocks': [{'symbol': s["symbol"], 'shares': s["shares"]} for s in stocks_updated]
        }, room=f'user_{user_id}')
        
        # Emit order execution notification
        socketio.emit('order_executed', {
            'type': 'buy',
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'total': total_cost,
            'timestamp': datetime.now().isoformat()
        }, room=f'user_{user_id}')
        
        # Check for achievements
        achievements = check_achievements(user_id)
        
        # Update challenge progress
        _update_user_challenge_progress(user_id)
        
        # Update trader stats
        db.update_trader_stats(user_id)
        
        flash(f"Bought {shares} shares of {symbol} for {usd(total_cost)}!")
        if achievements:
            for achievement in achievements:
                flash(f"🏆 Achievement Unlocked: {achievement}!", "success")
        
        return redirect("/")
    
    else:
        # Pre-fill symbol if provided in query string
        symbol = request.args.get("symbol", "").upper()
        return render_template("buy.html", symbol=symbol)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    transactions = db.get_transactions(user_id)
    
    return render_template("history.html", transactions=transactions)


@app.route("/analytics")
@login_required
def analytics():
    """Show advanced portfolio analytics"""
    from helpers import calculate_portfolio_analytics, calculate_portfolio_performance_history
    
    user_id = session["user_id"]
    
    # Calculate analytics
    analytics_data = calculate_portfolio_analytics(user_id, db)
    
    # Get performance history for chart
    performance_history = calculate_portfolio_performance_history(user_id, db, days=90)
    
    # Format performance history for charts
    perf_chart = []
    if performance_history:
        for point in performance_history:
            perf_chart.append({
                'date': point['date'].split()[0] if isinstance(point['date'], str) else point['date'].strftime('%Y-%m-%d'),
                'value': float(point['total_value'])
            })
    
    return render_template("analytics.html", 
                         analytics=analytics_data,
                         performance_history=perf_chart)


@app.route("/api/analytics/<int:user_id>")
@login_required
def get_analytics_api(user_id):
    """Get analytics data as JSON"""
    from helpers import calculate_portfolio_analytics
    
    # Check if requesting own data or is admin
    if session["user_id"] != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    analytics_data = calculate_portfolio_analytics(user_id, db)
    return jsonify(analytics_data)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Validate input
        if not username:
            return apology("must provide username", 403)
        
        if not password:
            return apology("must provide password", 403)
        
        # Query database for username
        user = db.get_user_by_username(username)
        
        # Ensure username exists and password is correct
        if not user or not check_password_hash(user["hash"], password):
            return apology("invalid username and/or password", 403)
        
        # Remember which user has logged in
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        
        flash("Logged in successfully!")
        return redirect("/")
    
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    flash("Logged out successfully!")
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        
        if not symbol:
            return apology("must provide symbol", 400)
        
        quote = lookup(symbol.upper())
        
        if not quote:
            return apology("invalid symbol", 400)
        
        # Get chart data for the last 30 days
        chart_data = get_chart_data(symbol.upper(), days=30)
        
        # Check if in watchlist
        user_id = session["user_id"]
        in_watchlist = db.is_in_watchlist(user_id, symbol.upper())
        
        # Get stock news
        news = get_stock_news(symbol.upper(), limit=5)
        
        # Check for triggered alerts
        triggered = db.check_alerts(user_id, symbol.upper(), quote['price'])
        if triggered:
            for alert in triggered:
                flash(f"🔔 Alert triggered: {symbol.upper()} {'reached above' if alert['alert_type'] == 'above' else 'fell below'} {usd(alert['target_price'])}!", "info")
        
        return render_template("quoted.html", quote=quote, chart_data=chart_data, in_watchlist=in_watchlist, news=news)
    
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        
        # Validate input
        if not username:
            return apology("must provide username", 400)
        
        if not password:
            return apology("must provide password", 400)
        
        if not confirmation:
            return apology("must confirm password", 400)
        
        if password != confirmation:
            return apology("passwords must match", 400)
        
        # Check if username already exists
        if db.get_user_by_username(username):
            return apology("username already exists", 400)
        
        # Hash password and insert user
        hash = generate_password_hash(password)
        user_id = db.create_user(username, hash)
        
        # Log user in
        session["user_id"] = user_id
        session["username"] = username
        
        flash("Registered successfully!")
        return redirect("/")
    
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]
    
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        
        # Validate input
        if not symbol:
            return apology("must provide symbol", 400)
        
        if not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("must provide positive number of shares", 400)
        
        shares = int(shares)
        
        # Check if user owns enough shares
        stock = db.get_user_stock(user_id, symbol)
        if not stock or stock["shares"] < shares:
            return apology("not enough shares", 400)
        
        # Look up current price
        quote = lookup(symbol)
        if not quote:
            return apology("invalid symbol", 400)
        
        price = quote["price"]
        total_value = price * shares
        
        # Get optional strategy and notes
        strategy = request.form.get("strategy") or None
        notes = request.form.get("notes") or None
        
        # Record transaction
        txn_id = db.record_transaction(user_id, symbol, -shares, price, "sell", strategy, notes)
        # Send trade alert to chat
        send_trade_alert_to_chat(user_id, symbol, shares, price, 'sold')
        
        # Update user's cash
        user = db.get_user(user_id)
        db.update_cash(user_id, user["cash"] + total_value)
        
        # Execute copy trades for any followers
        _execute_copy_trades(user_id, symbol, shares, price, 'sell', txn_id)
        
        # Create portfolio snapshot
        create_portfolio_snapshot(user_id)
        
        # Emit real-time portfolio update
        user_updated = db.get_user(user_id)
        stocks_updated = db.get_user_stocks(user_id)
        portfolio_value = user_updated["cash"]
        for stock in stocks_updated:
            q = lookup(stock["symbol"])
            if q:
                portfolio_value += stock["shares"] * q["price"]
        
        socketio.emit('portfolio_update', {
            'cash': user_updated["cash"],
            'total_value': portfolio_value,
            'stocks': [{'symbol': s["symbol"], 'shares': s["shares"]} for s in stocks_updated]
        }, room=f'user_{user_id}')
        
        # Emit order execution notification
        socketio.emit('order_executed', {
            'type': 'sell',
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'total': total_value,
            'timestamp': datetime.now().isoformat()
        }, room=f'user_{user_id}')
        
        # Check for achievements
        achievements = check_achievements(user_id)
        
        # Update challenge progress
        _update_user_challenge_progress(user_id)
        
        # Update trader stats
        db.update_trader_stats(user_id)
        
        flash(f"Sold {shares} shares of {symbol} for {usd(total_value)}!")
        if achievements:
            for achievement in achievements:
                flash(f"🏆 Achievement Unlocked: {achievement}!", "success")
        
        return redirect("/")
    
    else:
        # Get user's stocks for dropdown
        stocks = db.get_user_stocks(user_id)
        return render_template("sell.html", stocks=stocks)


@app.route("/add_cash", methods=["GET", "POST"])
@login_required
def add_cash():
    """Add cash to account"""
    if request.method == "POST":
        amount = request.form.get("amount")
        
        if not amount:
            return apology("must provide amount", 400)
        
        try:
            amount = float(amount)
            if amount <= 0:
                return apology("must provide positive amount", 400)
        except ValueError:
            return apology("invalid amount", 400)
        
        user_id = session["user_id"]
        user = db.get_user(user_id)
        db.update_cash(user_id, user["cash"] + amount)
        
        flash(f"Added {usd(amount)} to your account!")
        return redirect("/")
    
    else:
        return render_template("add_cash.html")


@app.route("/leaderboard")
@login_required
def leaderboard():
    """Show leaderboard of all traders"""
    # Get all users
    conn = db.get_connection()
    cursor = conn.cursor()
    users_data = cursor.execute("SELECT id, username, cash FROM users ORDER BY username").fetchall()
    conn.close()
    
    leaderboard_data = []
    starting_cash = 10000.00
    
    for user_data in users_data:
        user_id = user_data["id"]
        username = user_data["username"]
        cash = user_data["cash"]
        
        # Get user's stocks
        stocks = db.get_user_stocks(user_id)
        
        # Calculate total value
        total_value = cash
        for stock in stocks:
            quote = lookup(stock["symbol"])
            if quote:
                total_value += stock["shares"] * quote["price"]
        
        # Calculate return
        total_return = total_value - starting_cash
        return_percent = (total_return / starting_cash) * 100 if starting_cash > 0 else 0
        
        leaderboard_data.append({
            "username": username,
            "total_value": total_value,
            "total_return": total_return,
            "return_percent": return_percent
        })
    
    # Sort by total value descending
    leaderboard_data.sort(key=lambda x: x["total_value"], reverse=True)
    
    # Get current user's username
    current_user_id = session["user_id"]
    current_user = db.get_user(current_user_id)
    current_username = current_user["username"]
    
    return render_template("leaderboard.html", 
                         leaderboard=leaderboard_data,
                         current_user=current_username)


@app.route("/leagues")
@login_required
def leagues():
    """Show all leagues"""
    user_id = session["user_id"]
    
    # Get user's leagues
    user_leagues = db.get_user_leagues(user_id)
    
    # Get active public leagues
    public_leagues = db.get_active_leagues(limit=20)
    
    return render_template("leagues.html",
                         user_leagues=user_leagues,
                         public_leagues=public_leagues)


@app.route("/leagues/create", methods=["GET", "POST"])
@login_required
def create_league():
    """Create a new league"""
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description", "")
        league_type = request.form.get("league_type", "public")
        starting_cash = float(request.form.get("starting_cash", 10000))
        duration_days = int(request.form.get("duration_days", 30))
        mode = request.form.get("mode", "absolute_value")
        
        if not name:
            return apology("must provide league name", 400)
        
        user_id = session["user_id"]
        
        # Build settings and rules
        settings = {
            'duration_days': duration_days,
            'auto_reset': request.form.get("auto_reset") == "on"
        }
        
        # Build rules based on mode
        rules = {
            'starting_cash': starting_cash,
        }
        
        # Mode-specific rules
        if mode == 'limited_capital':
            rules['max_positions'] = int(request.form.get("max_positions", 10))
            rules['max_position_percent'] = float(request.form.get("max_position_percent", 25))
            rules['transaction_fee_percent'] = float(request.form.get("fee_percent", 0.1))
        
        league_id, invite_code = db.create_league(
            name=name,
            description=description,
            creator_id=user_id,
            league_type=league_type,
            starting_cash=starting_cash,
            settings_json=json.dumps(settings)
        )
        
        # Update mode and rules
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE leagues SET mode = ?, rules_json = ?, lifecycle_state = 'active'
            WHERE id = ?
        """, (mode, json.dumps(rules), league_id))
        conn.commit()
        conn.close()
        
        # Create creator's league portfolio
        db.create_league_portfolio(league_id, user_id, starting_cash)
        
        # Start the season
        db.start_league_season(league_id, duration_days)
        
        flash(f"League created! Invite code: {invite_code}", "success")
        return redirect(f"/leagues/{league_id}")
    
    # GET - show form with mode options
    modes = get_available_modes()
    return render_template("create_league.html", available_modes=modes)



@app.route("/leagues/<int:league_id>")
@login_required
def league_detail(league_id):
    """Show league details and leaderboard"""
    user_id = session["user_id"]
    
    league = db.get_league(league_id)
    if not league:
        return apology("league not found", 404)
    
    # Check if user is a member
    members = db.get_league_members(league_id)
    is_member = any(m['id'] == user_id for m in members)
    is_admin = any(m['id'] == user_id and m['is_admin'] for m in members)
    
    # Update scores if active
    if league['is_active']:
        db.update_league_scores(league_id)
    
    # Get leaderboard
    leaderboard = db.get_league_leaderboard(league_id)
    
    return render_template("league_detail.html",
                         league=league,
                         members=members,
                         leaderboard=leaderboard,
                         is_member=is_member,
                         is_admin=is_admin)


@app.route("/leagues/join", methods=["POST"])
@login_required
def join_league():
    """Join a league by ID or invite code"""
    user_id = session["user_id"]
    
    league_id = request.form.get("league_id")
    invite_code = request.form.get("invite_code")
    
    if invite_code:
        league = db.get_league_by_invite_code(invite_code)
        if not league:
            return apology("invalid invite code", 404)
        league_id = league['id']
    elif not league_id:
        return apology("must provide league ID or invite code", 400)
    
    league_id = int(league_id)
    league = db.get_league(league_id)
    
    if not league:
        return apology("league not found", 404)
    
    # Check lifecycle state - can only join during draft, open, or active states
    lifecycle_state = league.get('lifecycle_state', 'active')
    if lifecycle_state == 'finished':
        return apology("cannot join a finished league", 400)
    if lifecycle_state == 'locked':
        return apology("league registration is locked", 400)
    
    # Join the league membership
    success = db.join_league(league_id, user_id)
    
    if success:
        # Create isolated league portfolio with starting cash
        starting_cash = league.get('starting_cash', 10000.0)
        db.create_league_portfolio(league_id, user_id, starting_cash)
        
        flash("Successfully joined league!", "success")
        return redirect(f"/leagues/{league_id}")
    else:
        return apology("already a member or error joining", 400)


@app.route("/leagues/<int:league_id>/leave", methods=["POST"])
@login_required
def leave_league(league_id):
    """Leave a league"""
    user_id = session["user_id"]
    
    db.leave_league(league_id, user_id)
    flash("You have left the league", "info")
    
    return redirect("/leagues")


@app.route("/leagues/<int:league_id>/end", methods=["POST"])
@login_required
def end_league_season(league_id):
    """End the current season (admin only)"""
    user_id = session["user_id"]
    
    # Check if user is admin
    members = db.get_league_members(league_id)
    is_admin = any(m['id'] == user_id and m['is_admin'] for m in members)
    
    if not is_admin:
        return apology("only league admins can end seasons", 403)
    
    winners = db.end_league_season(league_id)
    
    flash("Season ended! Winners have been notified.", "success")
    return redirect(f"/leagues/{league_id}")


@app.route("/leagues/<int:league_id>/restart", methods=["POST"])
@login_required
def restart_league_season(league_id):
    """Start a new season (admin only)"""
    user_id = session["user_id"]
    
    # Check if user is admin
    members = db.get_league_members(league_id)
    is_admin = any(m['id'] == user_id and m['is_admin'] for m in members)
    
    if not is_admin:
        return apology("only league admins can restart seasons", 403)
    
    duration_days = int(request.form.get("duration_days", 30))
    db.start_league_season(league_id, duration_days)
    
    flash(f"New season started! Duration: {duration_days} days", "success")
    return redirect(f"/leagues/{league_id}")


@app.route("/leagues/<int:league_id>/trade", methods=["GET", "POST"])
@login_required
def league_trade(league_id):
    """Trade stocks within a league context"""
    user_id = session["user_id"]
    
    league = db.get_league(league_id)
    if not league:
        return apology("league not found", 404)
    
    # Check if user is a member
    members = db.get_league_members(league_id)
    is_member = any(m['id'] == user_id for m in members)
    if not is_member:
        return apology("you must join this league to trade", 403)
    
    # Check lifecycle state - can only trade when active
    lifecycle_state = league.get('lifecycle_state', 'active')
    if lifecycle_state != 'active':
        return apology(f"trading is not allowed in {lifecycle_state} state", 400)
    
    # Check if portfolio is locked
    if db.is_league_portfolio_locked(league_id, user_id):
        return apology("your portfolio is locked", 400)
    
    # Get league portfolio
    portfolio = db.get_league_portfolio(league_id, user_id)
    if not portfolio:
        # Create portfolio if missing (migration case)
        db.create_league_portfolio(league_id, user_id, league.get('starting_cash', 10000.0))
        portfolio = db.get_league_portfolio(league_id, user_id)
    
    # Get current holdings
    holdings = db.get_league_holdings(league_id, user_id)
    
    # Get mode and rules
    mode_name = league.get('mode') or 'absolute_value'
    rules_config = None
    if league.get('rules_json'):
        try:
            rules_config = json.loads(league['rules_json'])
        except (json.JSONDecodeError, TypeError):
            pass
    
    mode = get_league_mode(mode_name, rules_config)
    rule_engine = LeagueRuleEngine(rules_config)
    
    if request.method == "POST":
        symbol = request.form.get("symbol", "").upper()
        shares_str = request.form.get("shares", "")
        trade_type = request.form.get("trade_type", "buy")
        
        if not symbol:
            return apology("must provide symbol", 400)
        if not shares_str or not shares_str.isdigit() or int(shares_str) <= 0:
            return apology("must provide positive number of shares", 400)
        
        shares = int(shares_str)
        
        # Get current price
        quote = lookup(symbol)
        if not quote:
            return apology("invalid symbol", 400)
        
        price = quote["price"]
        trade_value = shares * price
        
        # Validate trade using rule engine
        is_valid, error = rule_engine.validate_order(
            symbol, shares, price, trade_type, 
            portfolio, holdings
        )
        if not is_valid:
            return apology(error, 400)
        
        # Also validate using mode-specific rules
        is_valid, error = mode.validate_trade(
            symbol, shares, price, trade_type,
            portfolio, holdings
        )
        if not is_valid:
            return apology(error, 400)
        
        # Calculate fee
        fee = rule_engine.calculate_fee(trade_value)
        
        if trade_type == "buy":
            total_cost = trade_value + fee
            if total_cost > portfolio['cash']:
                return apology("insufficient funds", 400)
            
            # Update league portfolio
            new_cash = portfolio['cash'] - total_cost
            db.update_league_cash(league_id, user_id, new_cash)
            db.update_league_holding(league_id, user_id, symbol, shares, price)
            db.record_league_transaction(league_id, user_id, symbol, shares, price, "buy", fee)
            
            flash(f"Bought {shares} shares of {symbol} for {usd(trade_value)} (fee: {usd(fee)})", "success")
            
        elif trade_type == "sell":
            # Check if user has enough shares
            holding = next((h for h in holdings if h['symbol'] == symbol), None)
            current_shares = holding['shares'] if holding else 0
            if shares > current_shares:
                return apology("not enough shares", 400)
            
            # Update league portfolio
            proceeds = trade_value - fee
            new_cash = portfolio['cash'] + proceeds
            db.update_league_cash(league_id, user_id, new_cash)
            db.update_league_holding(league_id, user_id, symbol, -shares, price)
            db.record_league_transaction(league_id, user_id, symbol, -shares, price, "sell", fee)
            
            flash(f"Sold {shares} shares of {symbol} for {usd(proceeds)} (after {usd(fee)} fee)", "success")
        
        # Update league scores after trade
        db.update_league_scores_v2(league_id, lambda s: lookup(s).get('price') if lookup(s) else None)
        
        # Emit real-time update
        socketio.emit('league_score_update', {
            'league_id': league_id,
            'user_id': user_id
        }, room=f'league_{league_id}')
        
        return redirect(f"/leagues/{league_id}/trade")
    
    # GET - show trade form
    # Enrich holdings with current prices
    for h in holdings:
        quote = lookup(h['symbol'])
        if quote:
            h['price'] = quote['price']
            h['value'] = h['shares'] * quote['price']
            h['gain_loss'] = (quote['price'] - h['avg_cost']) * h['shares']
    
    # Calculate total portfolio value
    total_value = portfolio['cash']
    for h in holdings:
        total_value += h.get('value', 0)
    
    return render_template("league_trade.html",
                         league=league,
                         portfolio=portfolio,
                         holdings=holdings,
                         total_value=total_value,
                         mode=mode,
                         rule_summary=rule_engine.get_rule_summary(),
                         allowed_symbols=mode.get_allowed_symbols())


@app.route("/leagues/<int:league_id>/activate", methods=["POST"])
@login_required
def activate_league(league_id):
    """Activate the league for trading (admin only)"""
    user_id = session["user_id"]
    
    # Check if user is admin
    members = db.get_league_members(league_id)
    is_admin = any(m['id'] == user_id and m['is_admin'] for m in members)
    
    if not is_admin:
        return apology("only league admins can activate the league", 403)
    
    league = db.get_league(league_id)
    if not league:
        return apology("league not found", 404)
    
    current_state = league.get('lifecycle_state', 'draft')
    
    # Can only activate from draft, open, or locked states
    if current_state not in ['draft', 'open', 'locked']:
        return apology(f"cannot activate from {current_state} state", 400)
    
    # Set to active
    db.set_league_lifecycle_state(league_id, 'active')
    
    # Also update season start if not already set
    if not league.get('season_start'):
        db.start_league_season(league_id, 30)  # Default 30 days
    
    flash("League activated! Trading is now open.", "success")
    return redirect(f"/leagues/{league_id}")


@app.route("/leagues/<int:league_id>/dashboard")
@login_required
def league_dashboard(league_id):
    """Enhanced league dashboard with rankings and analytics"""
    user_id = session["user_id"]
    
    league = db.get_league(league_id)
    if not league:
        return apology("league not found", 404)
    
    # Check if user is a member
    members = db.get_league_members(league_id)
    is_member = any(m['id'] == user_id for m in members)
    
    if not is_member and league.get('league_type') != 'public':
        return apology("you must be a member to view this dashboard", 403)
    
    # Update scores
    db.update_league_scores_v2(league_id, lambda s: lookup(s).get('price') if lookup(s) else None)
    
    # Get leaderboard with enriched data
    leaderboard = db.get_league_leaderboard(league_id)
    
    # Enrich leaderboard with additional data
    starting_cash = league.get('starting_cash', 10000.0)
    for entry in leaderboard:
        portfolio = db.get_league_portfolio(league_id, entry['id'])
        if portfolio:
            entry['cash'] = portfolio['cash']
            # Calculate total value
            holdings = db.get_league_holdings(league_id, entry['id'])
            total_value = portfolio['cash']
            for h in holdings:
                quote = lookup(h['symbol'])
                if quote:
                    total_value += h['shares'] * quote['price']
            entry['total_value'] = total_value
            entry['return_pct'] = ((total_value - starting_cash) / starting_cash * 100) if starting_cash > 0 else 0
        else:
            entry['total_value'] = starting_cash
            entry['return_pct'] = 0
    
    # Get recent transactions
    recent_transactions = db.get_league_transactions(league_id, limit=20)
    
    # Get user's portfolio if member
    user_portfolio = None
    user_holdings = []
    if is_member:
        user_portfolio = db.get_league_portfolio(league_id, user_id)
        user_holdings = db.get_league_holdings(league_id, user_id)
        for h in user_holdings:
            quote = lookup(h['symbol'])
            if quote:
                h['price'] = quote['price']
                h['value'] = h['shares'] * quote['price']
    
    # Get mode info
    mode_name = league.get('mode') or 'absolute_value'
    mode = get_league_mode(mode_name)
    
    return render_template("league_dashboard.html",
                         league=league,
                         leaderboard=leaderboard,
                         recent_transactions=recent_transactions,
                         user_portfolio=user_portfolio,
                         user_holdings=user_holdings,
                         is_member=is_member,
                         mode_description=mode.get_description(),
                         starting_cash=starting_cash)





@app.route("/challenges")
@login_required
def challenges():
    """Show all challenges"""
    user_id = session["user_id"]
    
    # Get user's active challenges
    user_challenges = db.get_user_challenges(user_id)
    
    # Get all active challenges
    all_challenges = db.get_active_challenges(limit=50)
    
    # Separate challenges user is participating in vs available
    participating_ids = {c['id'] for c in user_challenges}
    available_challenges = [c for c in all_challenges if c['id'] not in participating_ids]
    
    return render_template("challenges.html",
                         user_challenges=user_challenges,
                         available_challenges=available_challenges)


@app.route("/challenges/create", methods=["GET", "POST"])
@login_required
def create_challenge():
    """Create a new challenge"""
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description", "")
        challenge_type = request.form.get("challenge_type")
        duration_days = int(request.form.get("duration_days", 7))
        
        if not name or not challenge_type:
            return apology("must provide challenge name and type", 400)
        
        # Build rules based on challenge type
        rules = {}
        if challenge_type == "profit_target":
            rules['target_profit'] = float(request.form.get("target_profit", 1000))
        elif challenge_type == "trade_volume":
            rules['target_trades'] = int(request.form.get("target_trades", 10))
        elif challenge_type == "portfolio_value":
            rules['target_value'] = float(request.form.get("target_value", 15000))
        elif challenge_type == "sector_focus":
            rules['target_sector'] = request.form.get("target_sector", "Technology")
            rules['min_trades'] = int(request.form.get("min_trades", 5))
        
        # Build reward
        reward = {
            'cash': float(request.form.get("reward_cash", 0)),
            'achievement': request.form.get("reward_achievement", ""),
            'badge': request.form.get("reward_badge", "")
        }
        
        user_id = session["user_id"]
        
        # Create challenge
        challenge_id = db.create_challenge(
            name=name,
            description=description,
            challenge_type=challenge_type,
            rules=rules,
            creator_id=user_id,
            duration_days=duration_days,
            reward=reward
        )
        
        flash(f'Challenge "{name}" created successfully!', "success")
        return redirect(f"/challenges/{challenge_id}")
    
    return render_template("create_challenge.html")


@app.route("/challenges/<int:challenge_id>")
@login_required
def challenge_detail(challenge_id):
    """Show challenge details"""
    user_id = session["user_id"]
    
    # Get challenge details
    challenge = db.get_challenge(challenge_id)
    if not challenge:
        return apology("challenge not found", 404)
    
    # Get leaderboard
    leaderboard = db.get_challenge_leaderboard(challenge_id, limit=100)
    
    # Check if user is participating
    is_participating = any(entry['user_id'] == user_id for entry in leaderboard)
    user_entry = next((entry for entry in leaderboard if entry['user_id'] == user_id), None)
    
    # Calculate time remaining
    from datetime import datetime
    end_time = datetime.strptime(challenge['end_time'], '%Y-%m-%d %H:%M:%S')
    now = datetime.now()
    time_remaining = end_time - now
    days_remaining = max(0, time_remaining.days)
    hours_remaining = max(0, time_remaining.seconds // 3600)
    
    return render_template("challenge_detail.html",
                         challenge=challenge,
                         leaderboard=leaderboard,
                         is_participating=is_participating,
                         user_entry=user_entry,
                         days_remaining=days_remaining,
                         hours_remaining=hours_remaining)


@app.route("/challenges/<int:challenge_id>/join", methods=["POST"])
@login_required
def join_challenge(challenge_id):
    """Join a challenge"""
    user_id = session["user_id"]
    
    # Check if challenge exists and is active
    challenge = db.get_challenge(challenge_id)
    if not challenge:
        return apology("challenge not found", 404)
    
    if not challenge['is_active']:
        return apology("challenge is no longer active", 400)
    
    # Join challenge
    success = db.join_challenge(challenge_id, user_id)
    
    if success:
        flash(f'You joined "{challenge["name"]}"! Good luck!', "success")
    else:
        flash("You are already participating in this challenge", "warning")
    
    return redirect(f"/challenges/{challenge_id}")


@app.route("/challenges/<int:challenge_id>/leave", methods=["POST"])
@login_required
def leave_challenge(challenge_id):
    """Leave a challenge"""
    user_id = session["user_id"]
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM challenge_participants
        WHERE challenge_id = ? AND user_id = ?
    """, (challenge_id, user_id))
    conn.commit()
    conn.close()
    
    flash("You left the challenge", "info")
    return redirect("/challenges")


@app.route("/challenges/<int:challenge_id>/update", methods=["POST"])
@login_required
def update_challenge_score(challenge_id):
    """Manually update challenge score (admin only)"""
    user_id = session["user_id"]
    
    # Check if user is challenge creator
    challenge = db.get_challenge(challenge_id)
    if not challenge or challenge['creator_id'] != user_id:
        return apology("unauthorized", 403)
    
    # Recalculate all participant scores
    from datetime import datetime
    _update_all_challenge_scores(challenge_id)
    
    flash("Challenge scores updated!", "success")
    return redirect(f"/challenges/{challenge_id}")


@app.route("/about")
def about():
    """Show about page"""
    return render_template("about.html")


@app.route("/profile/<username>")
@login_required
def profile(username):
    """Show user profile"""
    # Get the profile user
    conn = db.get_connection()
    cursor = conn.cursor()
    profile_user = cursor.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    
    if not profile_user:
        return apology("user not found", 404)
    
    # Check if profile is public or if it's the user's own profile
    current_user_id = session["user_id"]
    is_own_profile = (profile_user["id"] == current_user_id)
    
    if not is_own_profile and not profile_user["is_public"]:
        return apology("this profile is private", 403)
    
    # Get user's stocks
    stocks = db.get_user_stocks(profile_user["id"])
    
    # Calculate portfolio value
    total_value = profile_user["cash"]
    for stock in stocks:
        quote = lookup(stock["symbol"])
        if quote:
            stock["price"] = quote["price"]
            stock["change_percent"] = quote.get("change_percent", 0)
            stock["total"] = stock["shares"] * quote["price"]
            total_value += stock["total"]
    
    # Calculate stats
    starting_cash = 10000.00
    total_return = total_value - starting_cash
    return_percent = (total_return / starting_cash) * 100 if starting_cash > 0 else 0
    
    # Get transaction count
    transactions = db.get_transactions(profile_user["id"])
    
    stats = {
        "portfolio_value": total_value,
        "total_return": total_return,
        "return_percent": return_percent,
        "transaction_count": len(transactions)
    }
    
    # Get recent transactions
    recent_transactions = transactions[:10] if transactions else []
    
    # Get friends
    friends = db.get_friends(profile_user["id"])
    
    # Check if current user is friends with profile user
    is_friend = db.are_friends(current_user_id, profile_user["id"]) if not is_own_profile else False
    
    # Check if friend request is pending
    friend_request_pending = False
    if not is_own_profile and not is_friend:
        conn = db.get_connection()
        cursor = conn.cursor()
        pending = cursor.execute("""
            SELECT id FROM friend_requests 
            WHERE sender_id = ? AND receiver_id = ? AND status = 'pending'
        """, (current_user_id, profile_user["id"])).fetchone()
        friend_request_pending = pending is not None
        conn.close()
    
    return render_template("profile.html",
                         profile_user=profile_user,
                         is_own_profile=is_own_profile,
                         stats=stats,
                         stocks=stocks,
                         recent_transactions=recent_transactions,
                         friends=friends,
                         is_friend=is_friend,
                         friend_request_pending=friend_request_pending)


@app.route("/settings")
@login_required
def settings():
    """Show settings page"""
    user_id = session["user_id"]
    user = db.get_user(user_id)
    return render_template("settings.html", user=user)


@app.route("/settings/profile", methods=["POST"])
@login_required
def update_profile():
    """Update user profile"""
    user_id = session["user_id"]
    email = request.form.get("email")
    bio = request.form.get("bio")
    is_public = 1 if request.form.get("is_public") else 0
    
    # Update profile
    db.update_user_profile(user_id, email=email, bio=bio, is_public=is_public)
    
    flash("Profile updated successfully!")
    return redirect("/settings")


@app.route("/settings/password", methods=["POST"])
@login_required
def change_password():
    """Change user password"""
    user_id = session["user_id"]
    current_password = request.form.get("current_password")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")
    
    # Validate input
    if not current_password or not new_password or not confirm_password:
        return apology("must provide all fields", 400)
    
    if new_password != confirm_password:
        return apology("new passwords don't match", 400)
    
    if len(new_password) < 6:
        return apology("password must be at least 6 characters", 400)
    
    # Verify current password
    user = db.get_user(user_id)
    if not check_password_hash(user["hash"], current_password):
        return apology("current password is incorrect", 403)
    
    # Update password
    new_hash = generate_password_hash(new_password)
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET hash = ? WHERE id = ?", (new_hash, user_id))
    conn.commit()
    conn.close()
    
    flash("Password changed successfully!")
    return redirect("/settings")


@app.route("/settings/reset", methods=["POST"])
@login_required
def reset_portfolio():
    """Reset user portfolio"""
    user_id = session["user_id"]
    
    # Delete all transactions and reset cash
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
    cursor.execute("UPDATE users SET cash = 10000.00 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    flash("Portfolio reset successfully! You now have $10,000 to trade.")
    return redirect("/")


@app.route("/friends")
@login_required
def friends():
    """Show friends page"""
    user_id = session["user_id"]
    search_query = request.args.get("search", "").strip()
    
    # Get user's friends
    friends_list = db.get_friends(user_id)
    
    # Add portfolio values to friends
    for friend in friends_list:
        stocks = db.get_user_stocks(friend["id"])
        total_value = friend["cash"]
        for stock in stocks:
            quote = lookup(stock["symbol"])
            if quote:
                total_value += stock["shares"] * quote["price"]
        friend["portfolio_value"] = total_value
    
    # Get pending friend requests
    pending_requests = db.get_friend_requests(user_id)
    
    # Search for users if query provided
    search_results = []
    if search_query:
        search_results = db.search_users(search_query, user_id)
        
        # Add friend status to search results
        for user in search_results:
            user["is_friend"] = db.are_friends(user_id, user["id"])
            
            # Check for pending request
            conn = db.get_connection()
            cursor = conn.cursor()
            pending = cursor.execute("""
                SELECT id FROM friends 
                WHERE user_id = ? AND friend_id = ? AND status = 'pending'
            """, (user_id, user["id"])).fetchone()
            user["request_pending"] = pending is not None
            conn.close()
    
    return render_template("friends.html",
                         friends=friends_list,
                         pending_requests=pending_requests,
                         search_query=search_query,
                         search_results=search_results)


@app.route("/send_friend_request", methods=["POST"])
@login_required
def send_friend_request():
    """Send friend request"""
    user_id = session["user_id"]
    friend_id = request.form.get("friend_id")
    
    if not friend_id:
        return apology("must provide friend id", 400)
    
    try:
        friend_id = int(friend_id)
    except ValueError:
        return apology("invalid friend id", 400)
    
    if friend_id == user_id:
        return apology("cannot add yourself as friend", 400)
    
    # Check if already friends
    if db.are_friends(user_id, friend_id):
        flash("You are already friends!")
        return redirect(request.referrer or "/friends")
    
    # Send friend request
    db.send_friend_request(user_id, friend_id)
    
    # Create notification for recipient
    sender = db.get_user(user_id)
    import json
    db.create_notification(
        friend_id,
        "friend_request",
        "New Friend Request",
        f"{sender['username']} sent you a friend request!",
        json.dumps({"from_user_id": user_id, "username": sender["username"]})
    )
    
    flash("Friend request sent!")
    return redirect(request.referrer or "/friends")


@app.route("/accept_friend", methods=["POST"])
@login_required
def accept_friend():
    """Accept friend request"""
    request_id = request.form.get("request_id")
    # Also support getting ID from URL path var if refactoring to RESTful
    if not request_id:
        # Fallback for old forms
        pass

    if not request_id:
        # Try to find friend request from user_id if passed
        # This is needed because the notification button passes the user_id, not request_id!
        # We need to find the pending request_id between current user and the friend_id
        friend_id = request.view_args.get('friend_id') if request.view_args else None
        # Actually simplest is to handle it here if we change the route signature or params
        
    if not request_id:
        return apology("must provide request id", 400)
    
    try:
        request_id = int(request_id)
    except ValueError:
        return apology("invalid request id", 400)
    
    # Get request details before accepting
    conn = db.get_connection()
    cursor = conn.cursor()
    friend_request = cursor.execute(
        "SELECT user_id, friend_id FROM friends WHERE id = ?", (request_id,)
    ).fetchone()
    conn.close()
    
    if friend_request:
        sender_id = friend_request["user_id"]
        receiver_id = friend_request["friend_id"]
        
        # Accept friend request
        db.accept_friend_request_by_id(request_id)
        
        # Create notification for sender
        receiver = db.get_user(receiver_id)
        import json
        db.create_notification(
            sender_id,
            "friend_accepted",
            "Friend Request Accepted",
            f"{receiver['username']} accepted your friend request!",
            json.dumps({"from_user_id": receiver_id, "username": receiver["username"]})
        )
    
    flash("Friend request accepted!")
    return redirect("/friends")

# New routes for handling accept/decline via user_id (from notification)
@app.route("/friends/accept/<int:friend_id>", methods=["POST"])
@login_required
def accept_friend_by_id(friend_id):
    """Accept friend request by user id"""
    user_id = session["user_id"]
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Find the pending request
    request_row = cursor.execute("""
        SELECT id FROM friends 
        WHERE user_id = ? AND friend_id = ? AND status = 'pending'
    """, (friend_id, user_id)).fetchone()
    conn.close()
    
    if not request_row:
        flash("Friend request not found or already handled.")
        return redirect("/notifications")
        
    # Call existing accept logic or duplicate it (simpler to call DB directly here)
    db.accept_friend_request_by_id(request_row['id'])
    
    # Notify sender
    receiver = db.get_user(user_id)
    import json
    db.create_notification(
        friend_id,
        "friend_accepted",
        "Friend Request Accepted",
        f"{receiver['username']} accepted your friend request!",
        json.dumps({"from_user_id": user_id, "username": receiver["username"]})
    )
    
    flash(f"Friend request accepted!")
    return redirect("/notifications")

@app.route("/friends/decline/<int:friend_id>", methods=["POST"])
@login_required
def decline_friend_by_id(friend_id):
    """Decline friend request by user id"""
    user_id = session["user_id"]
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Find the pending request
    request_row = cursor.execute("""
        SELECT id FROM friends 
        WHERE user_id = ? AND friend_id = ? AND status = 'pending'
    """, (friend_id, user_id)).fetchone()
    conn.close()
    
    if request_row:
        db.decline_friend_request_by_id(request_row['id'])
        flash("Friend request declined.")
    else:
        flash("Request not found.")
        
    return redirect("/notifications")


@app.route("/decline_friend", methods=["POST"])
@login_required
def decline_friend():
    """Decline friend request"""
    request_id = request.form.get("request_id")
    
    if not request_id:
        return apology("must provide request id", 400)
    
    try:
        request_id = int(request_id)
    except ValueError:
        return apology("invalid request id", 400)
    
    # Decline friend request
    db.decline_friend_request_by_id(request_id)
    
    flash("Friend request declined.")
    return redirect("/friends")


@app.route("/remove_friend", methods=["POST"])
@login_required
def remove_friend():
    """Remove friend"""
    user_id = session["user_id"]
    friend_id = request.form.get("friend_id")
    
    if not friend_id:
        return apology("must provide friend id", 400)
    
    try:
        friend_id = int(friend_id)
    except ValueError:
        return apology("invalid friend id", 400)
    
    # Remove friend
    db.remove_friend(user_id, friend_id)
    
    flash("Friend removed.")
    return redirect(request.referrer or "/friends")


@app.route("/notifications")
@login_required
def notifications():
    """Show user notifications"""
    user_id = session["user_id"]
    import json
    
    # Get notifications
    notifications_list = db.get_notifications(user_id, limit=20)
    
    # Process notifications content and related_data
    for notif in notifications_list:
        # Standardize fields if they're missing or named differently in dict
        if 'content' not in notif and 'message' in notif:
            notif['content'] = notif['message']
        if 'notification_type' not in notif and 'type' in notif:
            notif['notification_type'] = notif['type']
            
        # Parse JSON related_data
        if notif.get('related_data'):
            try:
                # If it looks like JSON, parse it
                if notif['related_data'].strip().startswith('{'):
                    data = json.loads(notif['related_data'])
                    notif['related_data_json'] = data
                    # Extract ID for template convenience
                    if 'from_user_id' in data:
                        notif['related_data'] = data['from_user_id']
                    elif 'league_id' in data:
                        notif['related_data'] = data['league_id']
                    elif 'challenge_id' in data:
                        notif['related_data'] = data['challenge_id']
                    elif 'trader_id' in data:
                        notif['related_data'] = data['trader_id']
                    elif 'achievement_id' in data:
                        notif['related_data'] = data['achievement_id']
                else:
                    # Legacy: it might be a URL or ID string
                    # Leave is as is, or try to extract ID?
                    # If it's "/friends", related_data stays "/friends".
                    # Our new template expects an ID for friend_request.
                    # This might break old notifications, but new ones will work.
                    notif['related_data_json'] = {}
            except (json.JSONDecodeError, TypeError):
                notif['related_data_json'] = {}
        
    # Count unread
    unread_count = sum(1 for n in notifications_list if not n["is_read"])
    
    return render_template("notifications.html",
                         notifications=notifications_list,
                         unread_count=unread_count)


@app.route("/notifications/mark_read/<int:notif_id>", methods=["POST"])
@login_required
def mark_notification_read(notif_id):
    """Mark a notification as read"""
    db.mark_notification_read(notif_id)
    return redirect("/notifications")


@app.route("/notifications/mark_all_read", methods=["POST"])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read"""
    user_id = session["user_id"]
    db.mark_all_notifications_read(user_id)
    flash("All notifications marked as read!")
    return redirect("/notifications")


@app.route("/notifications/delete/<int:notif_id>", methods=["POST"])
@login_required
def delete_notification(notif_id):
    """Delete a notification"""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notifications WHERE id = ?", (notif_id,))
    conn.commit()
    conn.close()
    return redirect("/notifications")


@app.route("/api/notifications/count")
@login_required
def notifications_count():
    """Get unread notifications count (for navbar badge)"""
    user_id = session["user_id"]
    notifications_list = db.get_notifications(user_id)
    unread_count = sum(1 for n in notifications_list if not n["is_read"])
    return {"count": unread_count}


@app.route("/api/notifications/recent")
@login_required
def notifications_recent():
    """Get recent notifications for dropdown with action support"""
    from datetime import datetime
    import json as json_module
    user_id = session["user_id"]
    notifications_list = db.get_notifications(user_id, limit=5)
    
    # Format notifications for JSON response
    formatted_notifications = []
    for notif in notifications_list:
        # Format timestamp
        created_at = notif.get("created_at", "")
        if created_at:
            try:
                dt = datetime.strptime(created_at.split('.')[0], '%Y-%m-%d %H:%M:%S')
                # Calculate time ago
                now = datetime.now()
                diff = now - dt
                if diff.days > 0:
                    time_ago = f"{diff.days}d ago"
                elif diff.seconds >= 3600:
                    time_ago = f"{diff.seconds // 3600}h ago"
                elif diff.seconds >= 60:
                    time_ago = f"{diff.seconds // 60}m ago"
                else:
                    time_ago = "Just now"
            except (ValueError, TypeError):
                time_ago = created_at
        else:
            time_ago = ""
        
        # Parse related_data if present
        related_data = None
        action_url = ""
        
        if notif.get("related_data"):
            try:
                # Try parsing as JSON
                if notif["related_data"].strip().startswith('{'):
                    related_data = json_module.loads(notif["related_data"])
                else:
                    # Legacy: treat as direct URL
                    action_url = notif["related_data"]
                    related_data = {"raw": notif["related_data"]}
            except (json_module.JSONDecodeError, TypeError):
                # Fallback
                action_url = notif["related_data"]
                related_data = {"raw": notif["related_data"]}
        
        # Determine notification type and actions
        notif_type = notif.get("notification_type", "")
        actions = []
        
        # Add actions based on notification type
        if notif_type == "friend_request":
            if related_data and "from_user_id" in related_data:
                actions = [
                    {"type": "accept", "label": "Accept", "url": f"/friends/accept/{related_data['from_user_id']}", "style": "success"},
                    {"type": "decline", "label": "Decline", "url": f"/friends/decline/{related_data['from_user_id']}", "style": "danger"}
                ]
        elif notif_type == "league_invite":
            if related_data and "league_id" in related_data:
                actions = [
                    {"type": "join", "label": "Join League", "url": f"/leagues/{related_data['league_id']}", "style": "primary"}
                ]
        elif notif_type == "challenge_invite":
            if related_data and "challenge_id" in related_data:
                actions = [
                    {"type": "join", "label": "Join Challenge", "url": f"/challenges/{related_data['challenge_id']}", "style": "primary"}
                ]
        elif notif_type == "trade_copy":
            if related_data and "from_user_id" in related_data:
                actions = [
                    {"type": "view", "label": "View Profile", "url": f"/profile/{related_data['from_user_id']}", "style": "info"}
                ]
            elif related_data and "trader_id" in related_data: # Legacy support
                actions = [
                     {"type": "view", "label": "View Trader", "url": f"/profile/{related_data['trader_id']}", "style": "info"}
                ]
        
        # Determine action_url from type if not legacy
        if not action_url and related_data:
            if notif_type == "league_result" and "league_id" in related_data:
                action_url = f"/leagues/{related_data['league_id']}"
            elif notif_type == "challenge_complete" and "challenge_id" in related_data:
                action_url = f"/challenges/{related_data['challenge_id']}"
            elif notif_type == "new_follower" and "from_user_id" in related_data:
                action_url = f"/profile/{related_data['from_user_id']}"
        
        formatted_notifications.append({
            "id": notif.get("id"),
            "type": notif_type,
            "title": notif.get("title", ""),
            "message": notif.get("content", ""),
            "created_at": time_ago,
            "is_read": notif.get("is_read", 0),
            "related_data": related_data,
            "actions": actions,
            "action_url": action_url
        })
    
    return {"notifications": formatted_notifications}


@app.route("/api/portfolio/value")
@login_required
def api_portfolio_value():
    """Get current portfolio value with live prices"""
    user_id = session["user_id"]
    user = db.get_user(user_id)
    stocks = db.get_user_stocks(user_id)
    
    portfolio_value = user["cash"]
    holdings = []
    
    for stock in stocks:
        quote = lookup(stock["symbol"])
        if quote:
            stock_value = stock["shares"] * quote["price"]
            portfolio_value += stock_value
            holdings.append({
                'symbol': stock["symbol"],
                'shares': stock["shares"],
                'price': quote["price"],
                'value': stock_value,
                'change_percent': quote.get('change_percent', 0)
            })
    
    return jsonify({
        'cash': user["cash"],
        'total_value': portfolio_value,
        'holdings': holdings,
        'timestamp': datetime.now().isoformat()
    })


@app.route("/api/theme", methods=["POST"])
@login_required
def save_theme():
    """Save user theme preference"""
    user_id = session["user_id"]
    theme = request.json.get("theme", "dark")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET theme = ? WHERE id = ?", (theme, user_id))
    conn.commit()
    conn.close()
    
    return {"success": True}


@app.route("/api/chart/<symbol>")
def get_chart_api(symbol):
    """Get candlestick data with technical indicators for charting"""
    from helpers import get_technical_indicators
    
    timeframe = request.args.get('timeframe', 'D')
    days = int(request.args.get('days', 90))
    
    data = get_technical_indicators(symbol, timeframe, days)
    
    if not data:
        return jsonify({'error': 'Unable to fetch chart data'}), 404
    
    return jsonify(data)


@app.route("/achievements")
@login_required
def achievements():
    """Show achievements page"""
    user_id = session["user_id"]
    
    # Get user's achievements
    earned_achievements = db.get_achievements(user_id)
    earned_keys = [a["achievement_key"] for a in earned_achievements]
    
    # Define all possible achievements
    total_count = 7  # Total number of achievements
    earned_count = len(earned_achievements)
    
    return render_template("achievements.html",
                         earned_keys=earned_keys,
                         earned_count=earned_count,
                         total_count=total_count)


@app.route("/watchlist")
@login_required
def watchlist():
    """Show user's watchlist"""
    user_id = session["user_id"]
    
    # Get watchlist
    watchlist_items = db.get_watchlist(user_id)
    
    # Add current prices
    for item in watchlist_items:
        quote = lookup(item["symbol"])
        if quote:
            item["current_price"] = quote["price"]
            item["change"] = quote["change"]
            item["change_percent"] = quote["change_percent"]
            item["company_name"] = quote["name"]
        else:
            item["current_price"] = 0
            item["change"] = 0
            item["change_percent"] = 0
            item["company_name"] = item["symbol"]
    
    return render_template("watchlist.html", watchlist=watchlist_items)


@app.route("/watchlist/add", methods=["POST"])
@login_required
def add_to_watchlist():
    """Add stock to watchlist"""
    user_id = session["user_id"]
    symbol = request.form.get("symbol")
    notes = request.form.get("notes")
    
    if not symbol:
        return apology("must provide symbol", 400)
    
    symbol = symbol.upper()
    
    # Verify symbol is valid
    quote = lookup(symbol)
    if not quote:
        return apology("invalid symbol", 400)
    
    # Add to watchlist
    success = db.add_to_watchlist(user_id, symbol, quote["price"], notes)
    
    if success:
        flash(f"Added {symbol} to your watchlist!")
    else:
        flash(f"{symbol} is already in your watchlist!")
    
    return redirect("/watchlist")


@app.route("/watchlist/remove", methods=["POST"])
@login_required
def remove_from_watchlist():
    """Remove stock from watchlist"""
    user_id = session["user_id"]
    symbol = request.form.get("symbol")
    
    if not symbol:
        return apology("must provide symbol", 400)
    
    db.remove_from_watchlist(user_id, symbol.upper())
    
    flash(f"Removed {symbol} from your watchlist!")
    return redirect(request.referrer or "/watchlist")


@app.route("/feed")
@login_required
def activity_feed():
    """Show activity feed from friends"""
    user_id = session["user_id"]
    
    # Get friend activity
    activities = db.get_friend_activity(user_id, limit=50)
    
    # Get reactions for each activity
    for activity in activities:
        activity['reactions'] = db.get_activity_reactions(activity['id'])
        activity['user_reaction'] = db.get_user_activity_reaction(activity['id'], user_id)
    
    return render_template("feed.html", activities=activities)


@app.route("/api/activity/<int:activity_id>/react", methods=["POST"])
@login_required
def react_to_activity(activity_id):
    """Add or update emoji reaction to an activity"""
    user_id = session["user_id"]
    emoji = request.json.get("emoji")
    
    if not emoji:
        return jsonify({"error": "Emoji is required"}), 400
    
    # Validate emoji
    valid_emojis = ['👍', '❤️', '😂', '😮', '🔥', '🚀', '💰', '🎯']
    if emoji not in valid_emojis:
        return jsonify({"error": "Invalid emoji"}), 400
    
    # Add or update reaction
    db.add_activity_reaction(activity_id, user_id, emoji)
    
    # Get updated reaction counts
    reactions = db.get_activity_reactions(activity_id)
    
    return jsonify({
        "success": True,
        "reactions": reactions
    })


@app.route("/api/activity/<int:activity_id>/unreact", methods=["POST"])
@login_required
def unreact_to_activity(activity_id):
    """Remove emoji reaction from an activity"""
    user_id = session["user_id"]
    
    db.remove_activity_reaction(activity_id, user_id)
    
    # Get updated reaction counts
    reactions = db.get_activity_reactions(activity_id)
    
    return jsonify({
        "success": True,
        "reactions": reactions
    })


@app.route("/compare")
@login_required
def compare_portfolios():
    """Compare portfolio with friends or market"""
    user_id = session["user_id"]
    
    # Get user's friends for comparison
    friends = db.get_friends(user_id)
    
    # Get user's portfolio history
    user_history = db.get_portfolio_history(user_id, days=30)
    
    # Get comparison data if friend selected
    compare_username = request.args.get('username')
    compare_history = []
    compare_user = None
    
    if compare_username:
        compare_user = db.get_user_by_username(compare_username)
        if compare_user:
            compare_history = db.get_portfolio_history(compare_user['id'], days=30)
    
    # Get current stats for both users
    user = db.get_user(user_id)
    user_stocks = db.get_user_stocks(user_id)
    user_total = user['cash']
    for stock in user_stocks:
        quote = lookup(stock['symbol'])
        if quote:
            user_total += stock['shares'] * quote['price']
    
    compare_total = 0
    if compare_user:
        compare_stocks = db.get_user_stocks(compare_user['id'])
        compare_total = compare_user['cash']
        for stock in compare_stocks:
            quote = lookup(stock['symbol'])
            if quote:
                compare_total += stock['shares'] * quote['price']
    
    return render_template("compare.html",
                         friends=friends,
                         user_history=user_history,
                         compare_history=compare_history,
                         compare_user=compare_user,
                         user_total=user_total,
                         compare_total=compare_total)


@app.route("/explore")
@login_required
def explore():
    """Explore and discover stocks"""
    # Get market movers
    market_movers = get_market_movers()
    
    # Get popular stocks
    popular = get_popular_stocks()
    
    # Sector ETFs for exploration
    sectors = [
        {'symbol': 'XLK', 'name': 'Technology'},
        {'symbol': 'XLF', 'name': 'Financial'},
        {'symbol': 'XLV', 'name': 'Healthcare'},
        {'symbol': 'XLE', 'name': 'Energy'},
        {'symbol': 'XLY', 'name': 'Consumer Discretionary'},
        {'symbol': 'XLP', 'name': 'Consumer Staples'},
        {'symbol': 'XLI', 'name': 'Industrial'},
        {'symbol': 'XLB', 'name': 'Materials'}
    ]
    
    # Enrich sectors with current prices
    for sector in sectors:
        quote = lookup(sector['symbol'])
        if quote:
            sector['price'] = quote['price']
            sector['change_percent'] = quote.get('change_percent', 0)
    
    return render_template("explore.html",
                         market_movers=market_movers,
                         popular_stocks=popular,
                         sectors=sectors)


@app.route("/alerts")
@login_required
def alerts():
    """Show and manage price alerts"""
    user_id = session["user_id"]
    
    # Get active alerts
    active_alerts = db.get_user_alerts(user_id, status='active')
    triggered_alerts = db.get_user_alerts(user_id, status='triggered')
    
    # Enrich with current prices
    for alert in active_alerts:
        quote = lookup(alert['symbol'])
        if quote:
            alert['current_price'] = quote['price']
            alert['distance'] = quote['price'] - alert['target_price']
            alert['distance_percent'] = (alert['distance'] / alert['target_price'] * 100) if alert['target_price'] > 0 else 0
    
    return render_template("alerts.html", 
                         active_alerts=active_alerts,
                         triggered_alerts=triggered_alerts)


@app.route("/alerts/create", methods=["POST"])
@login_required
def create_alert():
    """Create a new price alert"""
    user_id = session["user_id"]
    
    symbol = request.form.get("symbol")
    target_price = request.form.get("target_price")
    alert_type = request.form.get("alert_type")
    
    if not symbol or not target_price or not alert_type:
        return apology("must provide all fields", 400)
    
    # Validate symbol
    quote = lookup(symbol.upper())
    if not quote:
        return apology("invalid symbol", 400)
    
    try:
        target_price = float(target_price)
        if target_price <= 0:
            return apology("target price must be positive", 400)
    except ValueError:
        return apology("invalid target price", 400)
    
    if alert_type not in ['above', 'below']:
        return apology("invalid alert type", 400)
    
    # Create alert
    db.create_alert(user_id, symbol.upper(), target_price, alert_type)
    
    flash(f"Alert created for {symbol.upper()} at {usd(target_price)}!")
    return redirect("/alerts")


@app.route("/alerts/delete/<int:alert_id>", methods=["POST"])
@login_required
def delete_alert(alert_id):
    """Delete a price alert"""
    user_id = session["user_id"]
    db.delete_alert(alert_id, user_id)
    
    flash("Alert deleted!")
    return redirect("/alerts")


@app.route("/strategies")
@login_required
def strategies():
    """Show trading strategies performance"""
    user_id = session["user_id"]
    
    # Get strategy performance
    strategies_data = db.get_strategies_performance(user_id)
    
    # Get all transactions grouped by strategy
    transactions = db.get_transactions(user_id)
    
    # Calculate profit/loss for each strategy
    for strategy in strategies_data:
        strategy_name = strategy['strategy']
        strategy_transactions = [t for t in transactions if t.get('strategy') == strategy_name]
        
        # Calculate P&L (simplified - actual trades)
        total_spent = sum(t['shares'] * t['price'] for t in strategy_transactions if t['type'] == 'buy')
        total_received = sum(abs(t['shares']) * t['price'] for t in strategy_transactions if t['type'] == 'sell')
        strategy['profit_loss'] = total_received - total_spent
    
    return render_template("strategies.html", strategies=strategies_data)


# ============================================================================
# NEWS & SENTIMENT ROUTES
# ============================================================================

@app.route("/news")
@login_required
def news_feed():
    """Show news feed with sentiment analysis"""
    from helpers import get_cached_or_fetch_news
    
    user_id = session["user_id"]
    
    # Get user's portfolio symbols for personalized news
    portfolio = db.get_portfolio_breakdown(user_id)
    portfolio_symbols = [item['symbol'] for item in portfolio] if portfolio else []
    
    # Get user's news preferences
    pref_symbols = db.get_user_news_preferences(user_id)
    all_symbols = list(set(portfolio_symbols + pref_symbols))
    
    # Fetch news for user's symbols
    stock_news = []
    for symbol in all_symbols[:10]:  # Limit to 10 symbols to avoid rate limits
        symbol_news = get_cached_or_fetch_news(symbol, db)
        stock_news.extend(symbol_news[:3])  # Top 3 per symbol
    
    # Get general market news
    general_news = get_cached_or_fetch_news(None, db)
    
    # Combine and sort by date
    all_news = stock_news + general_news
    all_news.sort(key=lambda x: x.get('published_at', ''), reverse=True)
    
    # Limit total articles
    all_news = all_news[:50]
    
    # Get sentiment summary
    sentiment_summary = db.get_sentiment_summary()
    
    return render_template("news.html",
                         news=all_news,
                         sentiment_summary=sentiment_summary,
                         tracked_symbols=all_symbols)


@app.route("/news/<symbol>")
@login_required
def stock_news(symbol):
    """Show news for a specific stock with sentiment"""
    from helpers import get_cached_or_fetch_news
    
    symbol = symbol.upper()
    
    # Get stock quote
    quote = lookup(symbol)
    if not quote:
        return apology("Invalid symbol", 400)
    
    # Fetch news
    news = get_cached_or_fetch_news(symbol, db, force_refresh=True)
    
    # Get sentiment summary for this stock
    sentiment_summary = db.get_sentiment_summary(symbol)
    
    return render_template("stock_news.html",
                         symbol=symbol,
                         quote=quote,
                         news=news,
                         sentiment_summary=sentiment_summary)


@app.route("/news/preferences/add", methods=["POST"])
@login_required
def add_news_preference():
    """Add a symbol to news feed"""
    user_id = session["user_id"]
    symbol = request.form.get("symbol", "").upper()
    
    if not symbol:
        return apology("Symbol required", 400)
    
    # Validate symbol
    quote = lookup(symbol)
    if not quote:
        return apology("Invalid symbol", 400)
    
    db.add_news_preference(user_id, symbol)
    flash(f"Added {symbol} to your news feed", "success")
    
    return redirect("/news")


@app.route("/news/preferences/remove/<symbol>", methods=["POST"])
@login_required
def remove_news_preference(symbol):
    """Remove a symbol from news feed"""
    user_id = session["user_id"]
    symbol = symbol.upper()
    
    db.remove_news_preference(user_id, symbol)
    flash(f"Removed {symbol} from your news feed", "success")
    
    return redirect("/news")


@app.route("/api/news/<symbol>")
@login_required
def api_stock_news(symbol):
    """Get news for a symbol as JSON"""
    from helpers import get_cached_or_fetch_news
    
    symbol = symbol.upper()
    news = get_cached_or_fetch_news(symbol, db)
    sentiment = db.get_sentiment_summary(symbol)
    
    return jsonify({
        'symbol': symbol,
        'news': news,
        'sentiment': sentiment
    })


@app.route("/api/sentiment/overall")
@login_required
def api_overall_sentiment():
    """Get overall market sentiment as JSON"""
    sentiment = db.get_sentiment_summary()
    return jsonify(sentiment)


# ============================================================================
# SOCIAL TRADING ROUTES
# ============================================================================

@app.route("/traders")
@login_required
def traders():
    """Show top traders leaderboard"""
    user_id = session["user_id"]
    
    # Get sorting parameter
    sort_by = request.args.get('sort', 'total_return')
    
    # Get top traders
    top_traders = db.get_top_traders(limit=50, order_by=sort_by)
    
    # Check who user is following
    following = db.get_following(user_id)
    following_ids = [f['id'] for f in following]
    
    # Check who user is copying
    copying = db.get_copying(user_id)
    copying_ids = [c['trader_id'] for c in copying]
    
    return render_template("traders.html",
                         traders=top_traders,
                         following_ids=following_ids,
                         copying_ids=copying_ids,
                         sort_by=sort_by)


@app.route("/trader/<int:trader_id>")
@login_required
def trader_profile(trader_id):
    """Show detailed trader profile"""
    user_id = session["user_id"]
    
    # Get trader info
    trader = db.get_user(trader_id)
    if not trader:
        return apology("Trader not found", 404)
    
    # Get trader stats
    stats = db.get_trader_stats(trader_id)
    if not stats:
        # Calculate stats if not cached
        db.update_trader_stats(trader_id)
        stats = db.get_trader_stats(trader_id)
    
    # Get recent transactions
    transactions = db.get_transactions(trader_id, limit=20)
    
    # Get portfolio
    portfolio = db.get_portfolio_breakdown(trader_id)
    
    # Enrich with current prices
    for holding in portfolio:
        quote = lookup(holding['symbol'])
        if quote:
            holding['current_price'] = quote['price']
            holding['current_value'] = holding['shares'] * quote['price']
    
    # Check if current user is following
    is_following = db.is_following(user_id, trader_id)
    
    # Check if current user is copying
    copy_settings = db.get_copy_trading_settings(user_id, trader_id)
    is_copying = copy_settings is not None
    
    # Get followers and copiers
    followers = db.get_followers(trader_id)
    copiers = db.get_active_copiers(trader_id)
    
    return render_template("trader_profile.html",
                         trader=trader,
                         stats=stats,
                         transactions=transactions,
                         portfolio=portfolio,
                         is_following=is_following,
                         is_copying=is_copying,
                         copy_settings=copy_settings,
                         followers=followers,
                         copiers=copiers,
                         is_own_profile=(user_id == trader_id))


@app.route("/copy_trading")
@login_required
def copy_trading():
    """View and manage copy trading settings"""
    user_id = session["user_id"]
    top_traders = db.get_top_traders()
    active_copiers = db.get_active_copiers(user_id)
    return render_template("copy_trading.html", top_traders=top_traders, active_copiers=active_copiers)


@app.route("/follow_trader", methods=["POST"])
@login_required
def follow_trader():
    user_id = session["user_id"]
    trader_id = request.form.get("trader_id")
    db.follow_trader(user_id, trader_id)
    return redirect("/copy_trading")


@app.route("/unfollow_trader", methods=["POST"])
@login_required
def unfollow_trader():
    user_id = session["user_id"]
    trader_id = request.form.get("trader_id")
    db.unfollow_trader(user_id, trader_id)
    return redirect("/copy_trading")


@app.route("/start_copy_trading", methods=["POST"])
@login_required
def start_copy_trading():
    user_id = session["user_id"]
    trader_id = request.form.get("trader_id")
    allocation_pct = request.form.get("allocation_pct", 10)  # Default 10%
    max_trade = request.form.get("max_trade", 1000)  # Default $1000
    copy_buys = True
    copy_sells = True
    db.start_copy_trading(user_id, trader_id, allocation_pct, max_trade, copy_buys, copy_sells)
    return redirect("/copy_trading")


@app.route("/stop_copy_trading", methods=["POST"])
@login_required
def stop_copy_trading():
    user_id = session["user_id"]
    copier_id = request.form.get("copier_id")
    db.stop_copy_trading(user_id, copier_id)
    return redirect("/copy_trading")


# ============================================================================
# OPTIONS TRADING ROUTES
# ============================================================================

@app.route("/options")
@login_required
def options():
    """Show options trading interface"""
    user_id = session["user_id"]
    
    # Get user's open options positions
    positions = db.get_user_options_positions(user_id, status='open')
    
    # Enrich positions with current prices and Greeks
    for position in positions:
        option_data = get_option_price_and_greeks(
            position['symbol'],
            position['strike_price'],
            position['expiration_date'],
            position['option_type']
        )
        
        if option_data:
            position['current_premium'] = option_data['price']
            position['greeks'] = option_data['greeks']
            position['days_to_expiration'] = option_data['days_to_expiration']
            position['intrinsic_value'] = option_data['intrinsic_value']
            position['extrinsic_value'] = option_data['extrinsic_value']
            
            # Calculate P&L
            position['total_cost'] = position['contracts'] * position['avg_premium'] * 100
            position['current_value'] = position['contracts'] * position['current_premium'] * 100
            position['unrealized_pl'] = position['current_value'] - position['total_cost']
            position['unrealized_pl_pct'] = (position['unrealized_pl'] / position['total_cost'] * 100) if position['total_cost'] > 0 else 0
    
    # Get recent options transactions
    transactions = db.get_options_transactions(user_id, limit=20)
    
    return render_template("options.html", positions=positions, transactions=transactions)


@app.route("/options/chain/<symbol>")
@login_required
def options_chain(symbol):
    """Get options chain for a symbol"""
    symbol = symbol.upper()
    
    # Get current stock price
    quote = lookup(symbol)
    if not quote:
        return apology("Invalid symbol", 400)
    
    current_price = quote['price']
    
    # Get or generate available expiration dates (weekly + monthly)
    from datetime import datetime, timedelta
    
    expiration_dates = []
    current_date = datetime.now()
    
    # Generate next 8 weekly expirations (Fridays)
    days_until_friday = (4 - current_date.weekday()) % 7
    if days_until_friday == 0:
        days_until_friday = 7
    
    for i in range(8):
        exp_date = current_date + timedelta(days=days_until_friday + (i * 7))
        expiration_dates.append(exp_date.strftime('%Y-%m-%d'))
    
    # Generate next 4 monthly expirations (3rd Friday)
    for i in range(1, 5):
        target_month = current_date.month + i
        target_year = current_date.year + (target_month - 1) // 12
        target_month = ((target_month - 1) % 12) + 1
        
        # Find 3rd Friday
        first_day = datetime(target_year, target_month, 1)
        first_friday = 4 - first_day.weekday()
        if first_friday <= 0:
            first_friday += 7
        third_friday = first_day + timedelta(days=first_friday + 14)
        
        exp_date_str = third_friday.strftime('%Y-%m-%d')
        if exp_date_str not in expiration_dates:
            expiration_dates.append(exp_date_str)
    
    # Get selected expiration date (default to first one)
    selected_expiration = request.args.get('expiration', expiration_dates[0])
    
    # Generate strike prices around current price
    strikes = []
    strike_step = 5 if current_price > 100 else (2.5 if current_price > 50 else 1)
    
    for i in range(-5, 6):  # 5 strikes OTM, ATM, 5 strikes ITM
        strike = round((current_price + (i * strike_step)) / strike_step) * strike_step
        strikes.append(strike)
    
    # Get or create options contracts and calculate prices
    chain = {'calls': [], 'puts': []}
    
    for strike in strikes:
        # Calls
        call_contract_id = db.create_options_contract(symbol, strike, selected_expiration, 'call')
        call_data = get_option_price_and_greeks(symbol, strike, selected_expiration, 'call', current_price)
        
        if call_data:
            chain['calls'].append({
                'contract_id': call_contract_id,
                'strike': strike,
                'bid': round(call_data['price'] * 0.98, 2),  # Simulate bid-ask spread
                'ask': round(call_data['price'] * 1.02, 2),
                'last': call_data['price'],
                'delta': call_data['greeks']['delta'],
                'gamma': call_data['greeks']['gamma'],
                'theta': call_data['greeks']['theta'],
                'vega': call_data['greeks']['vega'],
                'volume': random.randint(10, 500),  # Simulated volume
                'open_interest': random.randint(100, 5000),
                'in_the_money': call_data['in_the_money']
            })
        
        # Puts
        put_contract_id = db.create_options_contract(symbol, strike, selected_expiration, 'put')
        put_data = get_option_price_and_greeks(symbol, strike, selected_expiration, 'put', current_price)
        
        if put_data:
            chain['puts'].append({
                'contract_id': put_contract_id,
                'strike': strike,
                'bid': round(put_data['price'] * 0.98, 2),
                'ask': round(put_data['price'] * 1.02, 2),
                'last': put_data['price'],
                'delta': put_data['greeks']['delta'],
                'gamma': put_data['greeks']['gamma'],
                'theta': put_data['greeks']['theta'],
                'vega': put_data['greeks']['vega'],
                'volume': random.randint(10, 500),
                'open_interest': random.randint(100, 5000),
                'in_the_money': put_data['in_the_money']
            })
    
    return render_template("options_chain.html",
                          symbol=symbol,
                          current_price=current_price,
                          expiration_dates=expiration_dates,
                          selected_expiration=selected_expiration,
                          chain=chain,
                          quote=quote)


@app.route("/options/buy", methods=["POST"])
@login_required
def buy_option():
    """Buy options contracts"""
    user_id = session["user_id"]
    
    contract_id = request.form.get("contract_id")
    contracts = request.form.get("contracts")
    premium = request.form.get("premium")
    
    # Validate inputs
    if not contract_id or not contracts or not premium:
        return apology("Missing required fields", 400)
    
    try:
        contract_id = int(contract_id)
        contracts = int(contracts)
        premium = float(premium)
    except ValueError:
        return apology("Invalid input", 400)
    
    if contracts <= 0:
        return apology("Must buy at least 1 contract", 400)
    
    # Execute buy
    success, message = db.buy_option(user_id, contract_id, contracts, premium)
    
    if not success:
        return apology(message, 400)
    
    flash(message, "success")
    return redirect("/options")


@app.route("/options/sell", methods=["POST"])
@login_required
def sell_option():
    """Sell options contracts"""
    user_id = session["user_id"]
    
    position_id = request.form.get("position_id")
    contracts = request.form.get("contracts")
    premium = request.form.get("premium")
    
    # Validate inputs
    if not position_id or not contracts or not premium:
        return apology("Missing required fields", 400)
    
    try:
        position_id = int(position_id)
        contracts = int(contracts)
        premium = float(premium)
    except ValueError:
        return apology("Invalid input", 400)
    
    if contracts <= 0:
        return apology("Must sell at least 1 contract", 400)
    
    # Execute sell
    success, message = db.sell_option(user_id, position_id, contracts, premium)
    
    if not success:
        return apology(message, 400)
    
    flash(message, "success")
    return redirect("/options")


# ============================================================================
# WebSocket Events for Real-time Stock Updates
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    
    # Join user-specific room for personalized updates
    user_id = session.get('user_id')
    if user_id:
        join_room(f'user_{user_id}')
        
        # Send initial portfolio state
        try:
            user = db.get_user(user_id)
            stocks = db.get_user_stocks(user_id)
            portfolio_value = user["cash"]
            for stock in stocks:
                q = lookup(stock["symbol"])
                if q:
                    portfolio_value += stock["shares"] * q["price"]
            
            emit('portfolio_update', {
                'cash': user["cash"],
                'total_value': portfolio_value,
                'stocks': [{'symbol': s["symbol"], 'shares': s["shares"]} for s in stocks]
            })
        except Exception as e:
            print(f"Error sending initial portfolio state: {e}")
    emit('connection_response', {'status': 'connected'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection and cleanup subscriptions"""
    print(f"Client disconnected: {request.sid}")
    # Remove client from all stock subscriptions
    for symbol in list(stock_subscriptions.keys()):
        if request.sid in stock_subscriptions[symbol]:
            stock_subscriptions[symbol].remove(request.sid)
            if not stock_subscriptions[symbol]:
                del stock_subscriptions[symbol]


@socketio.on('subscribe_stock')
def handle_subscribe(data):
    """Subscribe to real-time updates for a stock"""
    symbol = data.get('symbol', '').upper()
    if not symbol:
        return
    
    # Add client to subscription list for this stock
    if symbol not in stock_subscriptions:
        stock_subscriptions[symbol] = set()
    stock_subscriptions[symbol].add(request.sid)
    
    # Join room for this stock
    join_room(symbol)
    
    # Send immediate price update with extended data
    quote = lookup(symbol, force_refresh=True)
    if quote:
        emit('stock_update', {
            'symbol': symbol,
            'price': quote['price'],
            'change': quote['change'],
            'change_percent': quote['change_percent'],
            'volume': quote.get('volume', 0),
            'high': quote.get('high', quote['price']),
            'low': quote.get('low', quote['price']),
            'open': quote.get('open', quote['price']),
            'timestamp': datetime.now().isoformat()
        })
    
    print(f"Client {request.sid} subscribed to {symbol}")


@socketio.on('unsubscribe_stock')
def handle_unsubscribe(data):
    """Unsubscribe from real-time updates for a stock"""
    symbol = data.get('symbol', '').upper()
    if not symbol:
        return
    
    # Remove client from subscription
    if symbol in stock_subscriptions and request.sid in stock_subscriptions[symbol]:
        stock_subscriptions[symbol].remove(request.sid)
        if not stock_subscriptions[symbol]:
            del stock_subscriptions[symbol]
    
    # Leave room
    leave_room(symbol)
    print(f"Client {request.sid} unsubscribed from {symbol}")


@socketio.on('get_chart_data')
def handle_get_chart_data(data):
    """Get candlestick chart data for a symbol"""
    symbol = data.get('symbol', '').upper()
    timeframe = data.get('timeframe', '1D')  # 1D, 5D, 1M, 3M, 1Y
    
    if not symbol:
        return
    
    try:
        chart_data = get_chart_data(symbol, timeframe)
        emit('chart_data', {
            'symbol': symbol,
            'timeframe': timeframe,
            'data': chart_data
        })
    except Exception as e:
        emit('chart_error', {'error': str(e)})


def _update_user_challenge_progress(user_id):
    """Update user's progress in all active challenges after a trade"""
    user_challenges = db.get_user_challenges(user_id)
    
    for challenge in user_challenges:
        if not challenge['completed']:
            score = _calculate_challenge_score(challenge, user_id)
            db.update_challenge_progress(challenge['id'], user_id, score)
            
            # Check if challenge is completed
            if db.check_challenge_completion(challenge['id'], user_id):
                reward = db.complete_challenge(challenge['id'], user_id)
                
                # Award reward
                if reward and reward.get('cash', 0) > 0:
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE users SET cash = cash + ? WHERE id = ?
                    """, (reward['cash'], user_id))
                    conn.commit()
                    conn.close()
                
                # Send notification
                db.add_notification(
                    user_id,
                    'challenge_complete',
                    'Challenge Completed!',
                    f'You completed "{challenge["name"]}"! Reward: ${reward.get("cash", 0):.2f}',
                    f'/challenges/{challenge["id"]}'
                )


def _execute_copy_trades(trader_id, symbol, shares, price, trade_type, txn_id):
    """Execute copy trades for all active copiers of a trader"""
    copiers = db.get_active_copiers(trader_id)
    
    for copier in copiers:
        try:
            follower_id = copier['follower_id']
            
            # Check if they want to copy this type of trade
            if (trade_type == 'buy' and not copier['copy_buys']) or \
               (trade_type == 'sell' and not copier['copy_sells']):
                continue
            
            # Get follower's cash
            follower = db.get_user(follower_id)
            follower_cash = follower['cash']
            
            # Calculate proportional shares based on allocation percentage
            allocation_pct = copier['allocation_percentage'] / 100
            max_trade = copier['max_trade_amount']
            
            # Calculate copy shares (proportional to allocation)
            copy_shares = max(1, int(shares * allocation_pct))
            copy_cost = copy_shares * price
            
            # Apply max trade limit
            if copy_cost > max_trade:
                copy_shares = int(max_trade / price)
                copy_cost = copy_shares * price
            
            if copy_shares <= 0:
                continue
            
            # Execute the copy trade
            if trade_type == 'buy':
                if follower_cash >= copy_cost:
                    # Record transaction
                    copied_txn_id = db.record_transaction(
                        follower_id, symbol, copy_shares, price, 'buy',
                        strategy='copy_trade', notes=f'Copied from {db.get_user(trader_id)["username"]}'
                    )
                    
                    # Update cash
                    db.update_cash(follower_id, follower_cash - copy_cost)
                    
                    # Record copied trade
                    db.record_copied_trade(follower_id, trader_id, txn_id, copied_txn_id,
                                          symbol, copy_shares, price, 'buy')
                    
                    # Notify follower
                    db.add_notification(
                        follower_id,
                        'copy_trade',
                        'Copy Trade Executed',
                        f'Copied trade: Bought {copy_shares} shares of {symbol} for {usd(copy_cost)}',
                        f'/history'
                    )
            
            elif trade_type == 'sell':
                # Check if follower owns the stock
                portfolio = db.get_portfolio_breakdown(follower_id)
                holding = next((h for h in portfolio if h['symbol'] == symbol), None)
                
                if holding and holding['shares'] >= copy_shares:
                    # Record transaction
                    copied_txn_id = db.record_transaction(
                        follower_id, symbol, copy_shares, price, 'sell',
                        strategy='copy_trade', notes=f'Copied from {db.get_user(trader_id)["username"]}'
                    )
                    
                    # Update cash
                    proceeds = copy_shares * price
                    db.update_cash(follower_id, follower_cash + proceeds)
                    
                    # Record copied trade
                    db.record_copied_trade(follower_id, trader_id, txn_id, copied_txn_id,
                                          symbol, copy_shares, price, 'sell')
                    
                    # Notify follower
                    db.add_notification(
                        follower_id,
                        'copy_trade',
                        'Copy Trade Executed',
                        f'Copied trade: Sold {copy_shares} shares of {symbol} for {usd(proceeds)}',
                        f'/history'
                    )
        
        except Exception as e:
            print(f"Error executing copy trade for follower {copier['follower_id']}: {e}")
            continue


def _update_all_challenge_scores(challenge_id):
    """Update scores for all participants in a challenge"""
    challenge = db.get_challenge(challenge_id)
    if not challenge:
        return
    
    leaderboard = db.get_challenge_leaderboard(challenge_id)
    
    for entry in leaderboard:
        user_id = entry['user_id']
        score = _calculate_challenge_score(challenge, user_id)
        db.update_challenge_progress(challenge_id, user_id, score)
        
        # Check if challenge is completed
        if not entry['completed'] and db.check_challenge_completion(challenge_id, user_id):
            reward = db.complete_challenge(challenge_id, user_id)
            
            # Award reward
            if reward and reward.get('cash', 0) > 0:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET cash = cash + ? WHERE id = ?
                """, (reward['cash'], user_id))
                conn.commit()
                conn.close()
            
            # Send notification
            db.add_notification(
                user_id,
                'challenge_complete',
                'Challenge Completed!',
                f'You completed "{challenge["name"]}"! Score: {score:.2f}',
                f'/challenges/{challenge_id}'
            )


def _calculate_challenge_score(challenge, user_id):
    """Calculate user's score for a challenge"""
    challenge_type = challenge['challenge_type']
    rules = challenge['rules']
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get user's join time
    cursor.execute("""
        SELECT joined_at FROM challenge_participants
        WHERE challenge_id = ? AND user_id = ?
    """, (challenge['id'], user_id))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return 0
    
    joined_at = result['joined_at']
    
    if challenge_type == 'profit_target':
        # Calculate profit since joining
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN type = 'sell' THEN shares * price ELSE -shares * price END) as net_profit
            FROM transactions
            WHERE user_id = ? AND timestamp >= ?
        """, (user_id, joined_at))
        result = cursor.fetchone()
        score = result['net_profit'] if result and result['net_profit'] else 0
    
    elif challenge_type == 'trade_volume':
        # Count trades since joining
        cursor.execute("""
            SELECT COUNT(*) as trade_count
            FROM transactions
            WHERE user_id = ? AND timestamp >= ?
        """, (user_id, joined_at))
        result = cursor.fetchone()
        score = result['trade_count'] if result else 0
    
    elif challenge_type == 'portfolio_value':
        # Get current portfolio value
        user = db.get_user(user_id)
        stocks = db.get_user_stocks(user_id)
        
        total_value = user['cash']
        for stock in stocks:
            quote = lookup(stock['symbol'])
            if quote:
                total_value += stock['shares'] * quote['price']
        
        score = total_value
    
    elif challenge_type == 'sector_focus':
        # Count trades in target sector
        target_sector = rules.get('target_sector', 'Technology')
        # Simplified - just count all trades (real implementation would check sectors)
        cursor.execute("""
            SELECT COUNT(*) as trade_count
            FROM transactions
            WHERE user_id = ? AND timestamp >= ?
        """, (user_id, joined_at))
        result = cursor.fetchone()
        score = result['trade_count'] if result else 0
    
    else:
        score = 0
    
    conn.close()
    return score


def background_price_updater():
    """Background thread to update stock prices periodically"""
    while True:
        try:
            time.sleep(30)  # Update every 30 seconds
            
            # Get all subscribed symbols
            symbols = list(stock_subscriptions.keys())
            
            if not symbols:
                continue
            
            print(f"Updating prices for {len(symbols)} symbols...")
            
            # Fetch updated prices
            for symbol in symbols:
                quote = lookup(symbol, force_refresh=True)
                if quote and symbol in stock_subscriptions:
                    # Emit to all clients in this stock's room with extended data
                    socketio.emit('stock_update', {
                        'symbol': symbol,
                        'price': quote['price'],
                        'change': quote['change'],
                        'change_percent': quote['change_percent'],
                        'volume': quote.get('volume', 0),
                        'high': quote.get('high', quote['price']),
                        'low': quote.get('low', quote['price']),
                        'open': quote.get('open', quote['price']),
                        'timestamp': datetime.now().isoformat()
                    }, room=symbol)
        
        except Exception as e:
            print(f"Error in background price updater: {e}")


# Start background thread for price updates
price_update_thread = threading.Thread(target=background_price_updater, daemon=True)
price_update_thread.start()


def background_options_expiration_checker():
    """Background thread to check and process expired options"""
    from datetime import datetime
    
    while True:
        try:
            time.sleep(3600)  # Check every hour
            
            current_date = datetime.now().strftime('%Y-%m-%d')
            current_hour = datetime.now().hour
            
            # Process expirations at market close (4 PM ET, adjust for your timezone)
            if current_hour == 16:  # 4 PM
                print(f"Checking for options expiring on {current_date}...")
                
                # Get current prices for all stocks with expiring options
                conn = db.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT DISTINCT symbol
                    FROM options_contracts
                    WHERE expiration_date = ?
                """, (current_date,))
                
                symbols = [row['symbol'] for row in cursor.fetchall()]
                conn.close()
                
                if symbols:
                    print(f"Processing expirations for {len(symbols)} symbols...")
                    
                    # Get current prices
                    current_prices = {}
                    for symbol in symbols:
                        quote = lookup(symbol, force_refresh=True)
                        if quote:
                            current_prices[symbol] = quote['price']
                    
                    # Process expirations
                    processed = db.expire_options(current_date, current_prices)
                    print(f"Processed {processed} options positions")
        
        except Exception as e:
            print(f"Error in options expiration checker: {e}")


# Start background thread for options expiration
expiration_thread = threading.Thread(target=background_options_expiration_checker, daemon=True)
expiration_thread.start()


if __name__ == "__main__":
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)