"""
Trades Blueprint - handles buy/sell operations and advanced orders.
Extracted from main app.py for modularity.
"""

from flask import Blueprint, request, session, jsonify, flash, redirect, render_template
from functools import wraps
from datetime import datetime, timedelta
import logging

from helpers import apology, lookup, usd
from database.db_manager import DatabaseManager
from utils import rate_limit
from trade_throttle import validate_trade_throttle, record_trade
from business_logic_integration import log_trade, store_metrics
from leaderboard_updates import update_and_broadcast_leaderboard, invalidate_leaderboard_cache

trades_bp = Blueprint("trades", __name__)

logger = logging.getLogger(__name__)
FLOAT_EPSILON = 0.01


def login_required(f):
    """Decorator that redirects to login if user is not authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def _get_active_portfolio_context():
    """Get current portfolio context from session."""
    ctx = session.get("portfolio_context")
    if not ctx:
        ctx = {"type": "personal", "league_id": None, "league_name": None}
        session["portfolio_context"] = ctx
        session.modified = True
    return ctx


def _validate_portfolio_context(user_id, context):
    """Validate portfolio context is valid for the user."""
    db = DatabaseManager()
    
    if context["type"] == "personal":
        return True, None
    elif context["type"] == "league":
        league_id = context.get("league_id")
        if not league_id:
            return False, "Invalid league context"
        
        member = db.get_league_member(league_id, user_id)
        if not member:
            return False, "Not a member of this league"
        
        return True, None
    else:
        return False, "Unknown context type"


def _get_portfolio_cash(user_id, context):
    """Get available cash for the active portfolio context."""
    db = DatabaseManager()
    
    if context["type"] == "personal":
        user = db.get_user(user_id)
        return user.get("cash", 0) if user else 0
    else:
        league_id = context.get("league_id")
        portfolio = db.get_league_portfolio(league_id, user_id)
        return portfolio.get("cash", 0) if portfolio else 0


def _send_trade_alert_to_chat(socketio, user_id, symbol, shares, price, trade_type):
    """Send trade alert to chat room (if available)."""
    try:
        db = DatabaseManager()
        user = db.get_user(user_id)
        if not user:
            return
        
        message = f"📈 {user['username']} {trade_type} {shares} shares of {symbol} @ {usd(price)}"
        socketio.emit('trade_alert', {
            'username': user['username'],
            'trade_type': trade_type,
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'message': message
        }, room='general_chat')
    except Exception as e:
        logger.warning(f"Could not send trade alert: {e}")


def _execute_copy_trades(db, socketio, user_id, symbol, shares, price, trade_type, txn_id):
    """Execute copy trades for followers (if enabled)."""
    try:
        followers = db.get_copy_trading_followers(user_id)
        for follower in followers:
            follower_id = follower.get("follower_id")
            allocation = follower.get("allocation", 100) / 100.0
            
            copy_shares = int(shares * allocation)
            if copy_shares <= 0:
                continue
            
            copy_cash = _get_portfolio_cash(follower_id, {"type": "personal"})
            copy_cost = copy_shares * price
            
            if copy_cash >= copy_cost:
                try:
                    if trade_type == "buy":
                        success, error_msg, _ = db.execute_buy_trade_atomic(
                            follower_id, symbol, copy_shares, price, "copy_trade", None
                        )
                    else:
                        success, error_msg, _ = db.execute_sell_trade_atomic(
                            follower_id, symbol, copy_shares, price, "copy_trade", None
                        )
                    
                    if success:
                        logger.info(f"Copy trade executed: {follower_id} {trade_type} {copy_shares} {symbol}")
                except Exception as e:
                    logger.warning(f"Could not execute copy trade for follower {follower_id}: {e}")
    except Exception as e:
        logger.warning(f"Could not process copy trades: {e}")


def _create_portfolio_snapshot(db, user_id):
    """Create a snapshot of the user's portfolio."""
    try:
        user = db.get_user(user_id)
        stocks = db.get_user_stocks(user_id)
        
        portfolio_data = {
            "cash": user.get("cash", 0),
            "stocks": stocks,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in session or cache
        session["portfolio_snapshot"] = portfolio_data
        session.modified = True
    except Exception as e:
        logger.warning(f"Could not create portfolio snapshot: {e}")


def _check_achievements(db, user_id):
    """Check for new achievements (simplified)."""
    try:
        achievements = db.get_user_achievements(user_id)
        return [a.get("name") for a in achievements]
    except Exception as e:
        logger.warning(f"Could not check achievements: {e}")
        return []


@trades_bp.route("/buy", methods=["GET", "POST"])
@login_required
@rate_limit(max_requests=20, time_window=60, endpoint_key="buy")
def buy():
    """Buy shares of stock."""
    from flask_socketio import SocketIO
    
    user_id = session["user_id"]
    context = _get_active_portfolio_context()
    db = DatabaseManager()
    
    if request.method == "POST":
        try:
            # Validate portfolio context
            valid, error_msg = _validate_portfolio_context(user_id, context)
            if not valid:
                logger.warning(f"Invalid portfolio context for user {user_id}: {error_msg}")
                return apology(error_msg, 403)
            
            symbol = request.form.get("symbol")
            shares_str = request.form.get("shares")
            
            # Validate input
            if not symbol:
                return apology("must provide symbol", 400)
            
            symbol = symbol.upper().strip()
            
            if not shares_str:
                return apology("must provide number of shares", 400)
            
            # Convert and validate shares
            try:
                shares = int(shares_str)
                if shares <= 0:
                    return apology("must provide positive number of shares", 400)
            except ValueError:
                logger.debug(f"Invalid shares input from user {user_id}: {shares_str}")
                return apology("shares must be a valid whole number", 400)
            
            # Look up stock quote
            quote = lookup(symbol)
            if not quote:
                return apology("invalid symbol", 400)
            
            # Calculate total cost
            price = quote["price"]
            total_cost = price * shares
            
            # Get user's cash from active portfolio
            cash = _get_portfolio_cash(user_id, context)
            user = db.get_user(user_id)
            
            if not user:
                logger.error(f"User {user_id} not found in database")
                return apology("user not found", 500)
            
            # Check if user can afford
            if cash < total_cost - FLOAT_EPSILON:
                logger.debug(f"User {user_id} insufficient funds: need {total_cost}, have {cash}")
                return apology(f"can't afford: need {usd(total_cost)}, have {usd(cash)}", 400)
            
            # Get current shares of this symbol
            if context["type"] == "personal":
                current_stocks = db.get_user_stocks(user_id)
            else:
                current_stocks = db.get_league_holdings(context["league_id"], user_id)
            
            current_shares = next((s["shares"] for s in current_stocks if s["symbol"] == symbol), 0)
            
            # Validate trade throttle
            throttle_valid, throttle_message = validate_trade_throttle(
                user_id=user_id,
                symbol=symbol,
                action="buy",
                shares=shares,
                price=price,
                current_shares=current_shares,
                cash=cash,
                current_daily_loss=0,
                cooldown_seconds=2,
                max_trades_per_minute=10,
                max_position_pct=25.0,
                max_daily_loss=-5000.0
            )
            
            if not throttle_valid:
                logger.warning(f"Trade throttled for user {user_id}: {throttle_message}")
                return apology(throttle_message, 429)
            
            # Get optional strategy and notes
            strategy = request.form.get("strategy") or None
            notes = request.form.get("notes") or None
            
            # Execute trade based on context
            try:
                if context["type"] == "personal":
                    success, error_msg, txn_id = db.execute_buy_trade_atomic(
                        user_id, symbol, shares, price, strategy, notes
                    )
                    if not success:
                        logger.warning(f"Buy trade failed for user {user_id}: {error_msg}")
                        return apology(error_msg, 400)
                    
                    # Record successful trade
                    record_trade(user_id, symbol, "buy", shares, price)
                    logger.info(f"BUY | User: {user_id} | Symbol: {symbol} | Shares: {shares}")
                else:
                    success, error_msg, txn_id = db.execute_league_trade_atomic(
                        context["league_id"], user_id, symbol, "BUY", shares, price
                    )
                    if not success:
                        logger.warning(f"Buy trade failed: {error_msg}")
                        return apology(error_msg, 400)
                    
                    record_trade(user_id, symbol, "buy", shares, price)
                    logger.info(f"BUY (LEAGUE) | League: {context['league_id']} | User: {user_id} | Symbol: {symbol}")
                    
                    # Log to activity feed
                    try:
                        league = db.get_league(context["league_id"])
                        user_obj = db.get_user(user_id)
                        log_trade(
                            league_id=context["league_id"],
                            user_id=user_id,
                            username=user_obj["username"],
                            trade_type="BUY",
                            symbol=symbol,
                            shares=shares,
                            price=price
                        )
                        store_metrics(context["league_id"], user_id)
                    except Exception as e:
                        logger.warning(f"Could not log trade: {e}")
            except Exception as e:
                logger.error(f"Database error during buy transaction: {e}", exc_info=True)
                return apology(f"database error: {str(e)[:50]}", 500)
            
            # Create portfolio snapshot (personal only)
            if context["type"] == "personal":
                _create_portfolio_snapshot(db, user_id)
            
            # Check for achievements
            try:
                achievements = _check_achievements(db, user_id)
            except Exception as e:
                logger.warning(f"Could not check achievements: {e}")
                achievements = []
            
            # Flash success message
            context_str = f" in {context['league_name']}" if context["type"] == "league" else ""
            flash(f"Bought {shares} shares of {symbol} for {usd(total_cost)}{context_str}!")
            if achievements:
                for achievement in achievements:
                    flash(f"🏆 Achievement Unlocked: {achievement}!", "success")
            
            return redirect("/")
        
        except Exception as e:
            logger.error(f"Unexpected error in buy route: {e}", exc_info=True)
            return apology(f"unexpected error: {str(e)[:50]}", 500)
    
    # GET request - show buy form
    return render_template("buy.html")


@trades_bp.route("/sell", methods=["GET", "POST"])
@login_required
@rate_limit(max_requests=20, time_window=60, endpoint_key="sell")
def sell():
    """Sell shares of stock."""
    user_id = session["user_id"]
    context = _get_active_portfolio_context()
    db = DatabaseManager()
    
    if request.method == "POST":
        try:
            # Validate portfolio context
            valid, error_msg = _validate_portfolio_context(user_id, context)
            if not valid:
                return apology(error_msg, 403)
            
            symbol = request.form.get("symbol")
            shares_str = request.form.get("shares")
            
            if not symbol or not shares_str:
                return apology("must provide symbol and shares", 400)
            
            symbol = symbol.upper().strip()
            
            try:
                shares = int(shares_str)
                if shares <= 0:
                    return apology("must provide positive number of shares", 400)
            except ValueError:
                return apology("shares must be a valid whole number", 400)
            
            # Look up stock quote
            quote = lookup(symbol)
            if not quote:
                return apology("invalid symbol", 400)
            
            # Get current holdings
            if context["type"] == "personal":
                stocks = db.get_user_stocks(user_id)
            else:
                stocks = db.get_league_holdings(context["league_id"], user_id)
            
            current_shares = next((s["shares"] for s in stocks if s["symbol"] == symbol), 0)
            
            if current_shares < shares:
                return apology(f"don't have enough shares: have {current_shares}, want to sell {shares}", 400)
            
            # Execute sell
            price = quote["price"]
            total_proceeds = price * shares
            
            try:
                if context["type"] == "personal":
                    success, error_msg, txn_id = db.execute_sell_trade_atomic(
                        user_id, symbol, shares, price, None, None
                    )
                else:
                    success, error_msg, txn_id = db.execute_league_trade_atomic(
                        context["league_id"], user_id, symbol, "SELL", shares, price
                    )
                
                if not success:
                    return apology(error_msg, 400)
                
                record_trade(user_id, symbol, "sell", shares, price)
                logger.info(f"SELL | User: {user_id} | Symbol: {symbol} | Shares: {shares}")
                
                context_str = f" in {context['league_name']}" if context["type"] == "league" else ""
                flash(f"Sold {shares} shares of {symbol} for {usd(total_proceeds)}{context_str}!")
                
                return redirect("/")
            except Exception as e:
                logger.error(f"Database error during sell: {e}", exc_info=True)
                return apology(f"database error: {str(e)[:50]}", 500)
        
        except Exception as e:
            logger.error(f"Unexpected error in sell route: {e}", exc_info=True)
            return apology(f"unexpected error: {str(e)[:50]}", 500)
    
    # GET - show sell form with user's holdings
    if context["type"] == "personal":
        stocks = db.get_user_stocks(user_id)
    else:
        stocks = db.get_league_holdings(context["league_id"], user_id)
    
    return render_template("sell.html", stocks=stocks)


@trades_bp.route("/edit_portfolio", methods=["GET", "POST"])
@login_required
def edit_portfolio():
    """Edit portfolio (admin/league creator only)."""
    user_id = session["user_id"]
    db = DatabaseManager()
    
    # This is typically an admin function
    user = db.get_user(user_id)
    if not user or not user.get("is_admin"):
        return apology("admin access required", 403)
    
    if request.method == "POST":
        # Implementation would go here
        pass
    
    return render_template("edit_portfolio.html")


# Additional advanced order routes can be added here as needed
# (e.g., /advanced-orders, /advanced-orders/create, etc.)
