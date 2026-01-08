"""
Leagues Blueprint - handles league management, creation, joining, leaderboards.
Extracted from main app.py for modularity.
"""

from flask import Blueprint, request, session, jsonify, flash, redirect, render_template
from functools import wraps
from datetime import datetime
import logging

from helpers import apology, lookup
from database.db_manager import DatabaseManager
from leaderboard_updates import update_and_broadcast_leaderboard, get_cached_leaderboard, invalidate_leaderboard_cache

leagues_bp = Blueprint("leagues", __name__)
logger = logging.getLogger(__name__)


def login_required(f):
    """Decorator that redirects to login if user is not authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@leagues_bp.route("/leagues")
@login_required
def leagues_list():
    """List all leagues user is a member of."""
    user_id = session["user_id"]
    db = DatabaseManager()
    
    try:
        leagues = db.get_user_leagues(user_id)
        return render_template("leagues.html", leagues=leagues)
    except Exception as e:
        logger.error(f"Error fetching leagues for user {user_id}: {e}")
        return apology("Error loading leagues", 500)


@leagues_bp.route("/leagues/create", methods=["GET", "POST"])
@login_required
def create_league():
    """Create a new league."""
    user_id = session["user_id"]
    db = DatabaseManager()
    
    if request.method == "POST":
        try:
            league_name = request.form.get("name", "").strip()
            starting_cash = request.form.get("starting_cash", "10000")
            max_members = request.form.get("max_members", "")
            description = request.form.get("description", "").strip()
            
            # Validate input
            if not league_name:
                flash("League name is required", "danger")
                return redirect("/leagues/create")
            
            if len(league_name) > 100:
                flash("League name is too long", "danger")
                return redirect("/leagues/create")
            
            try:
                starting_cash = float(starting_cash)
                if starting_cash <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                flash("Starting cash must be a positive number", "danger")
                return redirect("/leagues/create")
            
            if max_members:
                try:
                    max_members = int(max_members)
                    if max_members <= 0:
                        raise ValueError()
                except (ValueError, TypeError):
                    flash("Max members must be a positive number", "danger")
                    return redirect("/leagues/create")
            
            # Create league
            try:
                league_id = db.create_league(
                    creator_id=user_id,
                    name=league_name,
                    starting_cash=starting_cash,
                    max_members=max_members if max_members else None,
                    description=description
                )
                
                # Add creator as admin member
                db.add_league_member(league_id, user_id, is_admin=True)
                
                flash(f"League '{league_name}' created successfully!", "success")
                return redirect(f"/leagues/{league_id}")
            except Exception as e:
                logger.error(f"Error creating league: {e}")
                flash("Error creating league", "danger")
                return redirect("/leagues/create")
        
        except Exception as e:
            logger.error(f"Unexpected error in create_league: {e}")
            flash("Unexpected error", "danger")
            return redirect("/leagues/create")
    
    return render_template("create_league.html")


@leagues_bp.route("/leagues/<int:league_id>")
@login_required
def view_league(league_id):
    """View league details and members."""
    user_id = session["user_id"]
    db = DatabaseManager()
    
    try:
        league = db.get_league(league_id)
        if not league:
            return apology("League not found", 404)
        
        # Check if user is member
        member = db.get_league_member(league_id, user_id)
        if not member:
            return apology("Not a league member", 403)
        
        # Get members and leaderboard
        members = db.get_league_members(league_id)
        cached_leaderboard = get_cached_leaderboard(league_id)
        
        return render_template(
            "league.html",
            league=league,
            members=members,
            leaderboard=cached_leaderboard,
            is_admin=member.get("is_admin", False)
        )
    except Exception as e:
        logger.error(f"Error viewing league {league_id}: {e}")
        return apology("Error loading league", 500)


@leagues_bp.route("/leagues/join", methods=["POST"])
@login_required
def join_league():
    """Join a league using invite code."""
    user_id = session["user_id"]
    db = DatabaseManager()
    
    try:
        invite_code = request.form.get("invite_code", "").strip().upper()
        
        if not invite_code:
            flash("Invite code is required", "danger")
            return redirect("/leagues")
        
        # Find league by invite code
        league = db.get_league_by_invite_code(invite_code)
        if not league:
            flash("Invalid invite code", "danger")
            return redirect("/leagues")
        
        league_id = league["id"]
        
        # Check if already a member
        existing_member = db.get_league_member(league_id, user_id)
        if existing_member:
            flash("You are already a member of this league", "warning")
            return redirect(f"/leagues/{league_id}")
        
        # Check max members limit
        if league.get("max_members"):
            current_members = len(db.get_league_members(league_id))
            if current_members >= league["max_members"]:
                flash("This league is full", "danger")
                return redirect("/leagues")
        
        # Add user to league
        try:
            db.add_league_member(league_id, user_id, is_admin=False)
            
            # Create league portfolio for user
            db.create_league_portfolio(league_id, user_id, league["starting_cash"])
            
            flash(f"Successfully joined league '{league['name']}'!", "success")
            return redirect(f"/leagues/{league_id}")
        except Exception as e:
            logger.error(f"Error adding user to league: {e}")
            flash("Error joining league", "danger")
            return redirect("/leagues")
    
    except Exception as e:
        logger.error(f"Unexpected error in join_league: {e}")
        flash("Unexpected error", "danger")
        return redirect("/leagues")


@leagues_bp.route("/leagues/<int:league_id>/leave", methods=["POST"])
@login_required
def leave_league(league_id):
    """Leave a league."""
    user_id = session["user_id"]
    db = DatabaseManager()
    
    try:
        league = db.get_league(league_id)
        if not league:
            return apology("League not found", 404)
        
        member = db.get_league_member(league_id, user_id)
        if not member:
            return apology("Not a league member", 403)
        
        # Can't leave if only admin
        members = db.get_league_members(league_id)
        admin_count = sum(1 for m in members if m.get("is_admin"))
        if member.get("is_admin") and admin_count == 1:
            flash("You cannot leave as the only admin. Transfer ownership first.", "danger")
            return redirect(f"/leagues/{league_id}")
        
        # Remove user from league
        db.remove_league_member(league_id, user_id)
        
        flash(f"Left league '{league['name']}'", "success")
        return redirect("/leagues")
    
    except Exception as e:
        logger.error(f"Error leaving league: {e}")
        flash("Error leaving league", "danger")
        return redirect(f"/leagues/{league_id}")


@leagues_bp.route("/leagues/<int:league_id>/dashboard")
@login_required
def league_dashboard(league_id):
    """View league dashboard with portfolio and statistics."""
    user_id = session["user_id"]
    db = DatabaseManager()
    
    try:
        league = db.get_league(league_id)
        if not league:
            return apology("League not found", 404)
        
        member = db.get_league_member(league_id, user_id)
        if not member:
            return apology("Not a league member", 403)
        
        # Get user's league portfolio
        portfolio = db.get_league_portfolio(league_id, user_id)
        holdings = db.get_league_holdings(league_id, user_id)
        
        # Calculate portfolio value
        portfolio_value = portfolio.get("cash", 0) if portfolio else 0
        for holding in holdings:
            quote = lookup(holding["symbol"])
            if quote:
                portfolio_value += holding["shares"] * quote["price"]
        
        # Get leaderboard position
        cached_leaderboard = get_cached_leaderboard(league_id)
        user_rank = None
        for idx, entry in enumerate(cached_leaderboard, 1):
            if entry["user_id"] == user_id:
                user_rank = idx
                break
        
        return render_template(
            "league_dashboard.html",
            league=league,
            portfolio=portfolio,
            holdings=holdings,
            portfolio_value=portfolio_value,
            user_rank=user_rank,
            total_members=len(db.get_league_members(league_id))
        )
    except Exception as e:
        logger.error(f"Error loading league dashboard: {e}")
        return apology("Error loading dashboard", 500)


@leagues_bp.route("/api/league/<int:league_id>/leaderboard")
@login_required
def api_league_leaderboard(league_id):
    """Get league leaderboard as JSON."""
    user_id = session["user_id"]
    db = DatabaseManager()
    
    try:
        # Verify membership
        member = db.get_league_member(league_id, user_id)
        if not member:
            return jsonify({"error": "Not a league member"}), 403
        
        # Get cached or compute leaderboard
        leaderboard = get_cached_leaderboard(league_id)
        
        return jsonify({
            "success": True,
            "league_id": league_id,
            "leaderboard": leaderboard
        })
    except Exception as e:
        logger.error(f"Error fetching league leaderboard: {e}")
        return jsonify({"error": "Error fetching leaderboard"}), 500


@leagues_bp.route("/api/league/<int:league_id>", methods=["GET"])
@login_required
def api_get_league(league_id):
    """Get league info as JSON."""
    user_id = session["user_id"]
    db = DatabaseManager()
    
    try:
        league = db.get_league(league_id)
        if not league:
            return jsonify({"error": "League not found"}), 404
        
        member = db.get_league_member(league_id, user_id)
        if not member:
            return jsonify({"error": "Not a league member"}), 403
        
        return jsonify({
            "success": True,
            "league": {
                "id": league["id"],
                "name": league["name"],
                "creator_id": league["creator_id"],
                "starting_cash": league["starting_cash"],
                "max_members": league.get("max_members"),
                "member_count": len(db.get_league_members(league_id)),
                "created_at": league.get("created_at")
            }
        })
    except Exception as e:
        logger.error(f"Error fetching league info: {e}")
        return jsonify({"error": "Error fetching league"}), 500
