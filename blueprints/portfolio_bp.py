from flask import Blueprint, request, session, jsonify, flash, redirect, render_template, current_app
from database.db_manager import DatabaseManager
from helpers import lookup, apology
from datetime import datetime, timedelta
from redis_cache_manager import CacheKey, CacheConfig

portfolio_bp = Blueprint("portfolio", __name__)


def _get_active_context():
    ctx = session.get("portfolio_context")
    if not ctx:
        ctx = {"type": "personal", "league_id": None, "league_name": None}
        session["portfolio_context"] = ctx
        session.modified = True
    return ctx


def _set_portfolio_context(context_type, league_id=None, league_name=None):
    context = {"type": context_type, "league_id": league_id, "league_name": league_name}
    session["portfolio_context"] = context
    session.modified = True


@portfolio_bp.route("/debug/portfolio")
def debug_portfolio():
    """Debug endpoint to check portfolio context and cash (migrated)."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "unauthorized"}), 403

    db = DatabaseManager()
    context = _get_active_context()

    user = db.get_user(user_id)
    personal_cash = user.get("cash")

    league_portfolios = []
    leagues = db.get_user_leagues(user_id)
    for league in leagues:
        lp = db.get_league_portfolio(league["id"], user_id)
        league_portfolios.append({
            "league_id": league["id"],
            "league_name": league["name"],
            "cash": lp["cash"] if lp else "No portfolio"
        })

    # Get current context cash
    if context["type"] == "personal":
        current_cash = personal_cash
    else:
        league_id = context.get("league_id")
        portfolio = db.get_league_portfolio(league_id, user_id)
        current_cash = portfolio["cash"] if portfolio else 0

    return jsonify({
        "user_id": user_id,
        "username": user["username"],
        "current_context": context,
        "personal_cash": personal_cash,
        "league_portfolios": league_portfolios,
        "current_context_cash": current_cash
    })


@portfolio_bp.route("/portfolio/switch", methods=["POST"])
def switch_portfolio_context():
    """Switch active portfolio context (migrated)."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    if request.is_json:
        context_type = request.json.get("context_type")
        league_id = request.json.get("league_id")
    else:
        context_type = request.form.get("context_type")
        league_id = request.form.get("league_id")

    if context_type == "personal":
        _set_portfolio_context("personal")
        if request.is_json:
            return jsonify({"success": True, "context": "personal", "name": "Personal Portfolio"})
        flash("Switched to Personal Portfolio", "success")
        return redirect(request.referrer or "/")

    # League context
    try:
        league_id = int(league_id)
    except Exception:
        flash("Invalid league", "danger")
        return redirect(request.referrer or "/")

    db = DatabaseManager()
    league = db.get_league(league_id)
    if not league:
        flash("League not found", "danger")
        return redirect(request.referrer or "/")

    _set_portfolio_context("league", league_id=league_id, league_name=league.get("name"))
    flash(f"Switched to league {league.get('name')}", "success")
    return redirect(request.referrer or "/")


@portfolio_bp.route("/portfolio/reset_cash", methods=["POST"])
def reset_cash():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    new_cash = request.form.get("new_cash", type=float)
    if new_cash is None or new_cash < 0:
        flash("Invalid cash amount.", "danger")
        return redirect("/portfolio")

    db = DatabaseManager()
    db.execute("UPDATE portfolios SET cash = ?, total_value = ? WHERE user_id = ? AND type = 'personal'", (new_cash, new_cash, user_id))
    db.execute("UPDATE analytics SET total_gain_loss = 0, total_return = 0, total_return_percent = 0 WHERE user_id = ? AND portfolio_type = 'personal'", (user_id,))

    flash("Cash amount and analytics have been reset.", "success")
    return redirect("/portfolio")


@portfolio_bp.route("/api/portfolio/value")
def api_portfolio_value():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "unauthorized"}), 403

    # Get context (personal or league)
    context = _get_active_context()
    league_id = context.get("league_id") if context.get("type") == "league" else 0
    
    # Try cache first
    try:
        cache_key = CacheKey.portfolio(user_id, league_id)
        cached = current_app.cache.get(cache_key)
        if cached:
            cached['from_cache'] = True
            return jsonify(cached), 200
    except Exception:
        # Cache not available, fall through
        pass

    db = DatabaseManager()
    
    if context.get("type") == "league":
        # League portfolio
        league_portfolio = db.get_league_portfolio(league_id, user_id)
        if not league_portfolio:
            return jsonify({"error": "No portfolio in this league"}), 404
        
        portfolio_value = league_portfolio.get("cash", 0)
        holdings_data = league_portfolio.get("stocks_json", {})
        
        holdings = []
        for symbol, shares in holdings_data.items():
            quote = lookup(symbol)
            if quote:
                stock_value = shares * quote["price"]
                portfolio_value += stock_value
                holdings.append({
                    'symbol': symbol,
                    'shares': shares,
                    'price': quote["price"],
                    'value': stock_value,
                })
    else:
        # Personal portfolio
        user = db.get_user(user_id)
        stocks = db.get_user_stocks(user_id)

        portfolio_value = user.get("cash", 0)
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
                })

    result = {
        "portfolio_value": portfolio_value,
        "holdings": holdings,
        "from_cache": False,
        "context": context.get("type")
    }
    
    # Cache the result
    try:
        cache_key = CacheKey.portfolio(user_id, league_id)
        current_app.cache.set(cache_key, result, ttl=CacheConfig.PORTFOLIO_TTL)
    except Exception:
        # Cache not available
        pass
    
    return jsonify(result), 200
