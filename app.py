import os
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from helpers import apology, lookup, usd, get_chart_data, get_popular_stocks, get_market_movers, get_stock_news
from database.db_manager import DatabaseManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure application
app = Flask(__name__)

# Secret key for session management (change in production!)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Initialize database manager
db = DatabaseManager()

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


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
    
    # Get popular stocks for market overview
    popular_stocks = get_popular_stocks()
    
    # Get watchlist preview (top 4 items)
    watchlist = db.get_watchlist(user_id)
    for item in watchlist[:4]:
        quote = lookup(item["symbol"])
        if quote:
            item["price"] = quote["price"]
            item["change_percent"] = quote.get("change_percent", 0)
    
    # Get portfolio history for chart
    portfolio_history = db.get_portfolio_history(user_id, days=30)
    
    # Get market movers
    market_movers = get_market_movers()
    
    return render_template("index.html", 
                         stocks=stocks, 
                         cash=cash, 
                         grand_total=grand_total,
                         total_value=total_value,
                         total_gain_loss=total_gain_loss,
                         total_return=total_return,
                         total_return_percent=total_return_percent,
                         popular_stocks=popular_stocks,
                         watchlist=watchlist[:4],
                         portfolio_history=portfolio_history,
                         market_movers=market_movers)


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
        
        # Record transaction
        db.record_transaction(user_id, symbol, shares, price, "buy")
        
        # Update user's cash
        db.update_cash(user_id, cash - total_cost)
        
        # Create portfolio snapshot
        create_portfolio_snapshot(user_id)
        
        # Check for achievements
        achievements = check_achievements(user_id)
        
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
        
        # Record transaction
        db.record_transaction(user_id, symbol, -shares, price, "sell")
        
        # Update user's cash
        user = db.get_user(user_id)
        db.update_cash(user_id, user["cash"] + total_value)
        
        # Create portfolio snapshot
        create_portfolio_snapshot(user_id)
        
        # Check for achievements
        achievements = check_achievements(user_id)
        
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
                SELECT id FROM friend_requests 
                WHERE sender_id = ? AND receiver_id = ? AND status = 'pending'
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
    db.create_notification(
        friend_id,
        "friend_request",
        "New Friend Request",
        f"{sender['username']} sent you a friend request!",
        f"/friends"
    )
    
    flash("Friend request sent!")
    return redirect(request.referrer or "/friends")


@app.route("/accept_friend", methods=["POST"])
@login_required
def accept_friend():
    """Accept friend request"""
    request_id = request.form.get("request_id")
    
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
        db.create_notification(
            sender_id,
            "friend_accepted",
            "Friend Request Accepted",
            f"{receiver['username']} accepted your friend request!",
            f"/profile/{receiver['username']}"
        )
    
    flash("Friend request accepted!")
    return redirect("/friends")


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
    
    # Get notifications
    notifications_list = db.get_notifications(user_id, limit=20)
    
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
    
    return render_template("feed.html", activities=activities)


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


@app.route("/analytics")
@login_required
def analytics():
    """Show comprehensive analytics dashboard"""
    user_id = session["user_id"]
    
    # Get trading statistics
    stats = db.get_trading_stats(user_id)
    
    # Get portfolio breakdown
    portfolio_breakdown = db.get_portfolio_breakdown(user_id)
    
    # Enrich with current prices and calculate values
    total_portfolio_value = 0
    for item in portfolio_breakdown:
        quote = lookup(item['symbol'])
        if quote:
            item['price'] = quote['price']
            item['value'] = item['shares'] * quote['price']
            total_portfolio_value += item['value']
    
    # Calculate percentages
    for item in portfolio_breakdown:
        if total_portfolio_value > 0:
            item['percentage'] = (item['value'] / total_portfolio_value) * 100
        else:
            item['percentage'] = 0
    
    # Sort by value
    portfolio_breakdown.sort(key=lambda x: x.get('value', 0), reverse=True)
    
    # Get user's transactions for best/worst trades
    transactions = db.get_transactions(user_id)
    
    # Calculate best and worst trades (buys only, compare to current price)
    trade_performance = []
    for trans in transactions:
        if trans['type'] == 'buy':
            quote = lookup(trans['symbol'])
            if quote:
                buy_value = trans['shares'] * trans['price']
                current_value = trans['shares'] * quote['price']
                gain_loss = current_value - buy_value
                gain_loss_percent = (gain_loss / buy_value * 100) if buy_value > 0 else 0
                
                trade_performance.append({
                    'symbol': trans['symbol'],
                    'shares': trans['shares'],
                    'buy_price': trans['price'],
                    'current_price': quote['price'],
                    'gain_loss': gain_loss,
                    'gain_loss_percent': gain_loss_percent,
                    'timestamp': trans['timestamp']
                })
    
    # Sort for best and worst
    best_trades = sorted(trade_performance, key=lambda x: x['gain_loss_percent'], reverse=True)[:5]
    worst_trades = sorted(trade_performance, key=lambda x: x['gain_loss_percent'])[:5]
    
    # Get portfolio history for performance chart
    portfolio_history = db.get_portfolio_history(user_id, days=90)
    
    return render_template("analytics.html",
                         stats=stats,
                         portfolio_breakdown=portfolio_breakdown,
                         total_portfolio_value=total_portfolio_value,
                         best_trades=best_trades,
                         worst_trades=worst_trades,
                         portfolio_history=portfolio_history)


if __name__ == "__main__":
    app.run(debug=True)