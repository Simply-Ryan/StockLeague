"""
StockLeague Flask application.

This module defines the Flask app, routes, Socket.IO integration, and
high-level application behavior. The file is intentionally the main
entrypoint and contains multiple route groups (auth, portfolio, leagues,
admin, explore, and API endpoints). For maintainability, consider
refactoring large route groups into separate Blueprints (e.g. `auth`,
`explore`, `api`, `admin`) in the future.
"""

# Standard library imports
import os
import json
import time
import uuid
import random
import sqlite3
import threading
import re
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps
import logging

# Third-party imports
from flask import Flask, flash, redirect, render_template, request, session, jsonify, send_file, url_for
from flask_session import Session
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

# Local imports
from helpers import apology, lookup, usd, get_chart_data, get_popular_stocks, get_market_movers, get_stock_news, get_option_price_and_greeks, analyze_sentiment, fetch_news_finnhub, get_cached_or_fetch_news
from database.db_manager import DatabaseManager
from database.league_schema_upgrade import upgrade_leagues_table, create_league_seasons_table, create_league_member_stats_table, create_league_divisions_table, create_tournament_tables, create_team_tables, create_achievement_tables, create_quest_tables, create_analytics_tables, create_fairplay_tables, create_league_activity_feed_table
from database.advanced_league_features import AdvancedLeagueDB
from league_modes import get_league_mode, get_available_modes, MODE_ABSOLUTE_VALUE
from league_rules import LeagueRuleEngine
from advanced_league_system import AdvancedLeagueManager, RatingSystem, AchievementEngine, QuestSystem, FairPlayEngine, AnalyticsCalculator
from utils import rate_limit, sanitize_xss, validate_symbol, validate_email, validate_username, sanitize_input

# --- Constants ---
FLOAT_EPSILON = 0.01  # Used for floating-point comparisons in trading logic



# --- Login Required Decorator (move up) ---
def login_required(f):
    """Decorator that redirects to login if user is not authenticated.

    Use this on routes that require an authenticated user. Example:
        @app.route('/dashboard')
        @login_required
        def dashboard():
            ...

    This is intentionally simple and relies on `session['user_id']`.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# --- Admin-only decorator ---
def admin_required(f):
    """Decorator to restrict a route to admin users.

    This decorator validates that a user is logged in and that their
    account has `is_admin` set. It also caches the user object in the
    session for subsequent requests.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))

        # Cache user data in session
        if 'user' not in session:
            user = db.get_user(user_id)
            if not user or not user.get('is_admin'):
                return redirect(url_for('index'))
            session['user'] = user

        return f(*args, **kwargs)
    return decorated_function


# ============ PORTFOLIO CONTEXT HELPERS ============

def get_active_portfolio_context():
    """Get the active portfolio context from session."""
    context = session.get("portfolio_context")
    if not context:
        # Default to personal portfolio
        context = {"type": "personal", "league_id": None, "league_name": None}
        session["portfolio_context"] = context
        session.modified = True
    return context


def set_portfolio_context(context_type, league_id=None, league_name=None):
    """Set the active portfolio context."""
    context = {
        "type": context_type,
        "league_id": league_id,
        "league_name": league_name
    }
    session["portfolio_context"] = context
    session.modified = True
    logging.debug(f"DEBUG set_portfolio_context: Set context to {context}")


def get_portfolio_cash(user_id, context):
    """Get cash for the active portfolio context."""
    logging.info(f"get_portfolio_cash CALLED: context={context}")
    
    if context["type"] == "personal":
        user = db.get_user(user_id)
        if not user:
            logging.error(f"ERROR get_portfolio_cash: User not found for user_id={user_id}")
            # Return default cash for new users
            return 10000.0
        cash = user["cash"]
        logging.debug(f"DEBUG get_portfolio_cash: Personal portfolio - user_id={user_id}, cash=${cash}")
        return cash
    else:
        league_id = context.get("league_id")
        if not league_id:
            logging.error(f"DEBUG get_portfolio_cash: ERROR - No league_id in context! context={context}")
            return 0
        portfolio = db.get_league_portfolio(league_id, user_id)
        if not portfolio:
            logging.error(f"DEBUG get_portfolio_cash: ERROR - No portfolio found for league_id={league_id}, user_id={user_id}")
            return 0
        cash = portfolio["cash"]
        logging.debug(f"DEBUG get_portfolio_cash: League portfolio - league_id={league_id}, user_id={user_id}, cash=${cash}, portfolio={portfolio}")
        return cash


def get_portfolio_stocks(user_id, context):
    """Get stocks for the active portfolio context."""
    if context["type"] == "personal":
        return db.get_user_stocks(user_id)
    else:
        # League stocks are stored in league_holdings table
        league_id = context.get("league_id")
        if not league_id:
            return []
        return db.get_league_holdings(league_id, user_id)


def validate_portfolio_context(user_id, context):
    """Validate that user can trade in the current portfolio context."""
    if context["type"] == "personal":
        return True, None
    
    league_id = context.get("league_id")
    if not league_id:
        return False, "No league selected"
    
    # Check if user is member of league
    league = db.get_league(league_id)
    if not league:
        return False, "League not found"
    
    # Check if league is active
    if league.get("status") != "active":
        return False, f"League is {league.get('status', 'inactive')}"
    
    # Check if user is member
    members = db.get_league_members(league_id)
    member_ids = [m["id"] for m in members]
    if user_id not in member_ids:
        return False, "You are not a member of this league"
    
    return True, None


def push_recent_quote(symbol, limit=10):
    """Push a symbol into session-based recent quotes list (most-recent first)."""
    if not symbol:
        return
    recent = session.get('recent_quotes', [])
    symbol = symbol.upper()
    # remove if exists
    recent = [s for s in recent if s != symbol]
    recent.insert(0, symbol)
    # cap list
    recent = recent[:limit]
    session['recent_quotes'] = recent
    session.modified = True


# Load environment variables
load_dotenv()

# Ensure logs directory exists
import os as _os
_logs_dir = 'logs'
if not _os.path.exists(_logs_dir):
    _os.makedirs(_logs_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
app_logger = logging.getLogger(__name__)

# Configure application
app = Flask(__name__)

# Secret key for session management (change in production!)
SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secret-key')
app.config['SECRET_KEY'] = SECRET_KEY

# Custom filters
app.jinja_env.filters["usd"] = usd
app.jinja_env.filters["abs"] = abs
app.jinja_env.filters["min"] = min
app.jinja_env.filters["max"] = max

# Add timestamp formatting filter
from utils import format_timestamp, get_user_timezone_offset
def jinja_format_timestamp(dt, include_time=False):
    """Jinja2 filter for formatting timestamps"""
    if not dt:
        return ""
    # Get timezone from session if available
    tz_offset = None
    if "user_id" in session:
        tz_offset = get_user_timezone_offset(session["user_id"])
    return format_timestamp(dt, include_time=include_time, timezone_offset=tz_offset or -5)

app.jinja_env.filters["format_timestamp"] = jinja_format_timestamp

# Add built-in functions to Jinja2 globals
app.jinja_env.globals.update(abs=abs, min=min, max=max)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


# Context processor for portfolio context
@app.context_processor
def inject_portfolio_context():
    """Make portfolio context and user leagues available to all templates."""
    if session.get("user_id"):
        context = get_active_portfolio_context()
        user_leagues = db.get_user_leagues(session["user_id"])
        return {
            "active_context": context,
            "get_user_leagues": lambda user_id: db.get_user_leagues(user_id)
        }
    return {
        "active_context": {"type": "personal", "league_id": None, "league_name": None},
        "get_user_leagues": lambda user_id: []
    }


# --- Chat Settings (Themes/Dark Mode) ---
@app.route("/chat/settings")
@login_required
def chat_settings():

    return render_template("chat_settings.html")

# ============ AVATAR UPLOAD ============
ALLOWED_AVATAR_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_avatar_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS

@app.route("/settings/avatar", methods=["POST"])
@login_required
def upload_avatar():
    import base64
    from io import BytesIO
    from PIL import Image
    
    user_id = session["user_id"]
    
    # Check for cropped image data (canvas base64)
    cropped_image = request.form.get("cropped_image")
    
    if cropped_image:
        try:
            # Parse base64 data
            if "," in cropped_image:
                cropped_image = cropped_image.split(",")[1]
            
            # Decode base64
            image_data = base64.b64decode(cropped_image)
            image = Image.open(BytesIO(image_data))
            
            # Ensure it's RGB (convert if needed)
            if image.mode in ('RGBA', 'LA', 'P'):
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = rgb_image
            
            # Save cropped image
            filename = f"user_{user_id}_{int(time.time())}.jpg"
            avatar_folder = os.path.join(app.root_path, "static", "avatars")
            
            try:
                os.makedirs(avatar_folder, exist_ok=True)
            except OSError as e:
                logger.error(f"Error creating avatar folder: {e}")
                flash("Server error. Please try again later.")
                return redirect(url_for("settings"))
            
            filepath = os.path.join(avatar_folder, filename)
            image.save(filepath, "JPEG", quality=95)
            
            avatar_url = f"/static/avatars/{filename}"
            db.update_user_profile(user_id, avatar_url=avatar_url)
            flash("Profile picture updated successfully!")
            return redirect(url_for("settings"))
            
        except Exception as e:
            logger.error(f"Error processing cropped image: {e}")
            flash("Error processing image. Please try again.")
            return redirect(url_for("settings"))
    
    # Handle regular file upload
    if "avatar" not in request.files:
        flash("No file part")
        return redirect(url_for("settings"))
    file = request.files["avatar"]
    if file.filename == "":
        flash("No selected file")
        return redirect(url_for("settings"))
    if file and allowed_avatar_file(file.filename):
        # Validate file size (limit to 2MB)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > 2 * 1024 * 1024:  # 2MB limit
            flash("File size exceeds 2MB limit.")
            return redirect(url_for("settings"))
        
        ext = file.filename.rsplit(".", 1)[1].lower()
        filename = f"user_{user_id}_{int(time.time())}.{ext}"
        avatar_folder = os.path.join(app.root_path, "static", "avatars")
        try:
            os.makedirs(avatar_folder, exist_ok=True)
        except OSError as e:
            logger.error(f"Error creating avatar folder: {e}")
            flash("Server error. Please try again later.")
            return redirect(url_for("settings"))
        filepath = os.path.join(avatar_folder, filename)
        file.save(filepath)
        avatar_url = f"/static/avatars/{filename}"
        db.update_user_profile(user_id, avatar_url=avatar_url)
        flash("Avatar updated successfully!")
        return redirect(url_for("settings"))
    else:
        flash("Invalid file type. Allowed: png, jpg, jpeg, gif.")
        return redirect(url_for("settings"))

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


# --- League admin actions: kick/mute/set-admin ---
@app.route('/leagues/<int:league_id>/admin/kick', methods=['POST'])
@login_required
def league_admin_kick(league_id):
    user_id = session.get('user_id')
    target_user_id = request.form.get('target_user_id') or request.json.get('target_user_id') if request.is_json else None
    if not target_user_id:
        return jsonify({'error': 'target_user_id is required'}), 400
    try:
        target_user_id = int(target_user_id)
    except ValueError:
        return jsonify({'error': 'invalid target_user_id'}), 400

    db = DatabaseManager()
    # Check requester is admin
    if not db.is_user_league_admin(league_id, user_id):
        return jsonify({'error': 'permission denied'}), 403

    # Prevent kicking the creator or self
    league = db.get_league(league_id)
    if league and league.get('creator_id') == target_user_id:
        return jsonify({'error': 'cannot remove league creator'}), 400

    db.remove_league_member(league_id, target_user_id)

    # Notify via socket and create notification
    room = f'league_{league_id}'
    socketio.emit('league_member_kicked', {'league_id': league_id, 'user_id': target_user_id}, room=room)
    db.create_notification(target_user_id, 'league_kicked', 'Removed from league', f'You were removed from league "{league.get("name")}"', f'/leagues/{league_id}')

    return jsonify({'ok': True})


@app.route('/leagues/<int:league_id>/admin/mute', methods=['POST'])
@login_required
def league_admin_mute(league_id):
    user_id = session.get('user_id')
    payload = request.get_json() or request.form
    target_user_id = payload.get('target_user_id')
    minutes = payload.get('minutes') or payload.get('duration_minutes')
    if not target_user_id:
        return jsonify({'error': 'target_user_id is required'}), 400
    try:
        target_user_id = int(target_user_id)
    except ValueError:
        return jsonify({'error': 'invalid target_user_id'}), 400

    db = DatabaseManager()
    if not db.is_user_league_admin(league_id, user_id):
        return jsonify({'error': 'permission denied'}), 403

    from datetime import datetime, timedelta
    muted_until = None
    try:
        if minutes:
            muted_until = (datetime.now() + timedelta(minutes=int(minutes))).isoformat()
    except Exception:
        muted_until = None

    db.set_league_moderation(league_id, target_user_id, is_muted=True, muted_until=muted_until)
    room = f'league_{league_id}'
    socketio.emit('league_member_muted', {'league_id': league_id, 'user_id': target_user_id, 'muted_until': muted_until}, room=room)
    db.create_notification(target_user_id, 'league_muted', 'You were muted', f'You were muted in league "{db.get_league(league_id).get("name")}"', f'/leagues/{league_id}')
    return jsonify({'ok': True})


@app.route('/leagues/<int:league_id>/admin/unmute', methods=['POST'])
@login_required
def league_admin_unmute(league_id):
    user_id = session.get('user_id')
    payload = request.get_json() or request.form
    target_user_id = payload.get('target_user_id')
    if not target_user_id:
        return jsonify({'error': 'target_user_id is required'}), 400
    try:
        target_user_id = int(target_user_id)
    except ValueError:
        return jsonify({'error': 'invalid target_user_id'}), 400

    db = DatabaseManager()
    if not db.is_user_league_admin(league_id, user_id):
        return jsonify({'error': 'permission denied'}), 403

    db.set_league_moderation(league_id, target_user_id, is_muted=False, muted_until=None)
    room = f'league_{league_id}'
    socketio.emit('league_member_unmuted', {'league_id': league_id, 'user_id': target_user_id}, room=room)
    db.create_notification(target_user_id, 'league_unmuted', 'You were unmuted', f'You were unmuted in league "{db.get_league(league_id).get("name")}"', f'/leagues/{league_id}')
    return jsonify({'ok': True})


@app.route('/leagues/<int:league_id>/admin/set_admin', methods=['POST'])
@login_required
def league_admin_set_admin(league_id):
    user_id = session.get('user_id')
    payload = request.get_json() or request.form
    target_user_id = payload.get('target_user_id')
    is_admin = payload.get('is_admin')
    if not target_user_id or is_admin is None:
        return jsonify({'error': 'target_user_id and is_admin are required'}), 400
    try:
        target_user_id = int(target_user_id)
        is_admin = bool(int(is_admin)) if isinstance(is_admin, str) and is_admin.isdigit() else bool(is_admin)
    except Exception:
        return jsonify({'error': 'invalid parameters'}), 400

    db = DatabaseManager()
    if not db.is_user_league_admin(league_id, user_id):
        return jsonify({'error': 'permission denied'}), 403

    db.set_league_member_admin(league_id, target_user_id, is_admin=is_admin)
    room = f'league_{league_id}'
    socketio.emit('league_member_admin_changed', {'league_id': league_id, 'user_id': target_user_id, 'is_admin': is_admin}, room=room)
    db.create_notification(target_user_id, 'league_admin_changed', 'Admin status changed', f'Your admin status in "{db.get_league(league_id).get("name")}" was set to {is_admin}', f'/leagues/{league_id}')
    return jsonify({'ok': True})

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
                # Check if user is league member with error handling
                try:
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute('SELECT 1 FROM league_members WHERE league_id = ? AND user_id = ?', (league_id, user_id))
                    if not cursor.fetchone():
                        conn.close()
                        emit('chat_notification', {'type': 'error', 'message': 'You are not a member of this league.'}, room=request.sid)
                        return
                    conn.close()
                except Exception as e:
                    logging.error(f"Error checking league membership for user {user_id} in league {league_id}: {e}")
                    emit('chat_notification', {'type': 'error', 'message': 'Error accessing league.'}, room=request.sid)
                    return
            except ValueError:
                return
    
    join_room(room)
    chat_users[room].add(username)
    emit('user_presence', list(chat_users[room]), room=room)
    # Load chat history from DB with error handling
    try:
        history = db.get_chat_history(room, limit=100)
        emit('chat_history', history, room=request.sid)
        
        # For league chats, also load recent activities
        if room.startswith('league_'):
            try:
                league_id = int(room.split('_')[1])
                conn = db.get_connection()
                cursor = conn.cursor()
                
                # Get recent activities (last 20)
                cursor.execute('''
                    SELECT id, user_id, username, activity_type, title, description, metadata, created_at
                    FROM league_activity_feed
                    WHERE league_id = ?
                    ORDER BY created_at DESC
                    LIMIT 20
                ''', (league_id,))
                
                activities = []
                for row in cursor.fetchall():
                    import json
                    activities.append({
                        'id': row[0],
                        'username': row[2],
                        'activity_type': row[3],
                        'title': row[4],
                        'description': row[5],
                        'metadata': json.loads(row[6]) if row[6] else {},
                        'created_at': row[7]
                    })
                
                conn.close()
                
                # Emit activities in reverse chronological order (oldest first)
                for activity in reversed(activities):
                    emit('chat_activity', activity, room=request.sid)
            except Exception as e:
                logging.error(f"Error loading activities for league {league_id}: {e}")
    except Exception as e:
        logging.error(f"Error loading chat history for room {room}: {e}")
        emit('chat_history', [], room=request.sid)

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
    message = data.get('message', '')  # Ensure 'message' is retrieved from 'data'
    username = data.get('username', 'Unknown')  # Default to 'Unknown' if 'username' is not provided
    msg = data.get('msg', {'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})  # Default 'msg' with current time

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
advanced_league_db = AdvancedLeagueDB(db)

# Initialize advanced league system schema (run migrations if needed)
def init_advanced_league_system():
    """Initialize the advanced league system schema in the database."""
    try:
        logging.info("Initializing advanced league system schema...")
        # Get database connection
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Ensure users table has timezone_offset column
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN timezone_offset INTEGER DEFAULT -5")
            conn.commit()
        except Exception:
            # Column already exists or other error
            pass
        
        # Run all schema upgrade functions
        upgrade_leagues_table(cursor)
        create_league_seasons_table(cursor)
        create_league_member_stats_table(cursor)
        create_league_divisions_table(cursor)
        create_tournament_tables(cursor)
        create_team_tables(cursor)
        create_achievement_tables(cursor)
        create_quest_tables(cursor)
        create_analytics_tables(cursor)
        create_fairplay_tables(cursor)
        create_league_activity_feed_table(cursor)
        
        conn.commit()
        conn.close()
        logging.info("Advanced league system schema initialized successfully")
        
        # Initialize advanced league features
        advanced_league_db.init_h2h_tables()
        advanced_league_db.init_season_tables()
        advanced_league_db.init_division_tables()
        advanced_league_db.init_enhanced_activity_feed()
        logging.info("Advanced league features initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing advanced league system: {e}")

# Run initialization on startup
init_advanced_league_system()

# Initialize AdvancedLeagueManager
league_manager = AdvancedLeagueManager(db)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Store active stock subscriptions (symbol -> set of session_ids)
stock_subscriptions = {}

# Register modular blueprints for better organization. These are
# incremental refactors — routes are preserved but moved into
# `blueprints/explore_bp.py` and `blueprints/api_bp.py`.
try:
    from blueprints.explore_bp import explore_bp
    from blueprints.api_bp import api_bp
    from blueprints.auth_bp import auth_bp
    from blueprints.portfolio_bp import portfolio_bp
    app.register_blueprint(explore_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(portfolio_bp)
except Exception:
    # If blueprints cannot be imported for any reason, fall back to
    # the original in-file route implementations (they remain present
    # for compatibility). The try/except avoids startup failure.
    pass


def create_portfolio_snapshot(user_id):
    """Create a snapshot of the user's current portfolio value using transaction for consistency"""
    import json
    
    try:
        # Use database transaction to ensure atomicity
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get user's stocks and cash within single transaction for consistency
        cursor.execute("SELECT id, username, cash FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            conn.close()
            logging.warning(f"create_portfolio_snapshot: User {user_id} not found")
            return
        
        user_dict = dict(user_row)
        cash = user_dict["cash"]
        
        cursor.execute("SELECT symbol, shares FROM user_stocks WHERE user_id = ?", (user_id,))
        stocks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
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
    except Exception as e:
        logging.error(f"Error creating portfolio snapshot for user {user_id}: {e}")


def check_achievements(user_id):
    """Check and award achievements for a user"""
    user = db.get_user(user_id)
    if not user:
        logging.warning(f"check_achievements: User {user_id} not found")
        return
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
def home():
    """Show landing/home page - public route"""
    return render_template("home.html")


@app.route("/home")
def home_alias():
    """Alias for home page"""
    return render_template("home.html")


@app.route("/dashboard")
@login_required
def dashboard():
    """Show trading dashboard - private route"""
    user_id = session["user_id"]
    
    # Get active portfolio context
    context = get_active_portfolio_context()
    logging.debug(f"DEBUG DASHBOARD: user_id={user_id}, context={context}")
    
    # Get stocks and transactions based on active portfolio
    stocks = get_portfolio_stocks(user_id, context)
    
    # Get transactions based on context
    if context["type"] == "personal":
        transactions = db.get_transactions(user_id)
    else:
        league_id = context["league_id"]
        transactions = db.get_league_transactions(league_id, user_id)
    
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
            stock["total_value"] = stock["shares"] * quote["price"]
            total_value += stock["total_value"]
            
            # Calculate gain/loss
            if stock["symbol"] in cost_basis and cost_basis[stock["symbol"]]["shares"] > 0:
                avg_cost = cost_basis[stock["symbol"]]["total_cost"] / cost_basis[stock["symbol"]]["shares"]
                stock["avg_cost"] = avg_cost
                stock["gain_loss"] = stock["total_value"] - (stock["shares"] * avg_cost)
                stock["percent_gain_loss"] = ((stock["price"] - avg_cost) / avg_cost) * 100 if avg_cost > 0 else 0
                total_gain_loss += stock["gain_loss"]
            else:
                stock["avg_cost"] = stock["price"]
                stock["gain_loss"] = 0
                stock["percent_gain_loss"] = 0
        else:
            stock["price"] = 0
            stock["total_value"] = 0
            stock["gain_loss"] = 0
            stock["percent_gain_loss"] = 0
    
    # Get cash balance from active portfolio
    cash = get_portfolio_cash(user_id, context)
    logging.debug(f"DEBUG: Rendering dashboard with cash=${cash} for user {user_id} in context {context}")
    
    # Calculate grand total and overall performance
    grand_total = cash + total_value
    # Get starting cash based on context
    if context["type"] == "personal":
        starting_cash = 10000.00  # Default starting amount
    else:
        league = db.get_league(context["league_id"])
        starting_cash = league.get("starting_cash", 10000.00) if league else 10000.00
    total_return = grand_total - starting_cash
    total_percent_change = (total_return / starting_cash) * 100 if starting_cash > 0 else 0
    
    # Get portfolio history for chart (personal only for now)
    if context["type"] == "personal":
        portfolio_history = db.get_portfolio_history(user_id, days=30)
        # Format for chart
        portfolio_dates = []
        portfolio_values = []
        if portfolio_history:
            for entry in portfolio_history:
                portfolio_dates.append(entry.get("date", ""))
                portfolio_values.append(entry.get("value", 0))
    else:
        portfolio_history = []  # TODO: Implement league portfolio history
        portfolio_dates = []
        portfolio_values = []

    return render_template("dashboard.html", 
                         stocks=stocks, 
                         cash=cash, 
                         grand_total=grand_total,
                         total_value=total_value,
                         total_gain_loss=total_gain_loss,
                         total_return=total_return,
                         total_percent_change=total_percent_change,
                         portfolio_history=portfolio_history,
                         portfolio_dates=portfolio_dates,
                         portfolio_values=portfolio_values,
                         transactions=transactions,
                         active_context=context)


@app.route("/index")
@login_required
def index():
    """Redirect legacy /index to /dashboard"""
    return redirect("/dashboard")


@app.route("/buy", methods=["GET", "POST"])
@login_required
@rate_limit(max_requests=20, time_window=60, endpoint_key="buy")
def buy():
    """Buy shares of stock"""
    user_id = session["user_id"]
    context = get_active_portfolio_context()
    
    if request.method == "POST":
        try:
            # Validate portfolio context
            valid, error_msg = validate_portfolio_context(user_id, context)
            if not valid:
                app_logger.warning(f"Invalid portfolio context for user {user_id}: {error_msg}")
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
                app_logger.debug(f"Invalid shares input from user {user_id}: {shares_str}")
                return apology("shares must be a valid whole number", 400)
            
            # Look up stock quote
            quote = lookup(symbol)
            if not quote:
                # Try searching for similar company names/symbols via Yahoo search
                from helpers import search_tickers
                suggestions = search_tickers(symbol)
                if suggestions:
                    # Render the quote form again with suggestions for the user to pick
                    return render_template("quote.html", suggestions=suggestions, previous_query=symbol, recent_quotes=session.get('recent_quotes', []))
                else:
                    app_logger.debug(f"Invalid symbol: {symbol}")
                    return apology("invalid symbol", 400)
            
            # Calculate total cost
            price = quote["price"]
            total_cost = price * shares
            
            # Get user's cash from active portfolio
            cash = get_portfolio_cash(user_id, context)
            user = db.get_user(user_id)
            
            if not user:
                app_logger.error(f"User {user_id} not found in database")
                return apology("user not found", 500)
            
            # Check if user can afford (with epsilon for floating point comparison)
            if cash < total_cost - FLOAT_EPSILON:
                app_logger.debug(f"User {user_id} insufficient funds: need {total_cost}, have {cash}")
                return apology(f"can't afford: need {usd(total_cost)}, have {usd(cash)}", 400)
            
            # Get optional strategy and notes
            strategy = request.form.get("strategy") or None
            notes = request.form.get("notes") or None
            
            # Handle transaction based on portfolio context
            try:
                if context["type"] == "personal":
                    # Personal portfolio - use personal tables
                    txn_id = db.record_transaction(user_id, symbol, shares, price, "buy", strategy, notes)
                    db.update_cash(user_id, cash - total_cost)
                    # Execute copy trades for any followers
                    _execute_copy_trades(user_id, symbol, shares, price, 'buy', txn_id)
                    app_logger.info(f"BUY | User: {user_id} | Symbol: {symbol} | Shares: {shares} | Price: {price} | Total: {total_cost}")
                else:
                    # League portfolio - use league tables
                    league_id = context["league_id"]
                    txn_id = db.record_league_transaction(league_id, user_id, symbol, shares, price, "buy")
                    db.update_league_cash(league_id, user_id, cash - total_cost)
                    db.update_league_holding(league_id, user_id, symbol, shares, price)
                    app_logger.info(f"BUY (LEAGUE) | League: {league_id} | User: {user_id} | Symbol: {symbol} | Shares: {shares}")
            except Exception as e:
                app_logger.error(f"Database error during buy transaction for user {user_id}: {e}", exc_info=True)
                return apology(f"database error: {str(e)[:50]}", 500)
            
            # Send trade alert to chat (for both contexts)
            try:
                send_trade_alert_to_chat(user_id, symbol, shares, price, 'bought')
            except Exception as e:
                app_logger.warning(f"Could not send trade alert for user {user_id}: {e}")
                # Don't fail the trade if chat alert fails
            
            # Create portfolio snapshot (personal only for now)
            if context["type"] == "personal":
                try:
                    create_portfolio_snapshot(user_id)
                except Exception as e:
                    app_logger.warning(f"Could not create portfolio snapshot for user {user_id}: {e}")
            
            # Emit real-time portfolio update based on context
            try:
                if context["type"] == "personal":
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
                else:
                    # League portfolio update
                    league_id = context["league_id"]
                    league_portfolio = db.get_league_portfolio(league_id, user_id)
                    league_holdings = db.get_league_holdings(league_id, user_id)
                    portfolio_value = league_portfolio["cash"] if league_portfolio else 0
                    for holding in league_holdings:
                        q = lookup(holding["symbol"])
                        if q:
                            portfolio_value += holding["shares"] * q["price"]
                    
                    socketio.emit('portfolio_update', {
                        'cash': league_portfolio["cash"] if league_portfolio else 0,
                        'total_value': portfolio_value,
                        'stocks': [{'symbol': h["symbol"], 'shares': h["shares"]} for h in league_holdings]
                    }, room=f'user_{user_id}')
            except Exception as e:
                app_logger.warning(f"Could not emit portfolio update for user {user_id}: {e}")
            
            # Emit order execution notification
            try:
                socketio.emit('order_executed', {
                    'type': 'buy',
                    'symbol': symbol,
                    'shares': shares,
                    'price': price,
                    'total': total_cost,
                    'timestamp': datetime.now().isoformat()
                }, room=f'user_{user_id}')
            except Exception as e:
                app_logger.warning(f"Could not emit order execution notification for user {user_id}: {e}")
            
            # Check for achievements (personal only)
            if context["type"] == "personal":
                try:
                    achievements = check_achievements(user_id)
                except Exception as e:
                    app_logger.warning(f"Could not check achievements for user {user_id}: {e}")
                    achievements = []
            else:
                achievements = []
            
            # Update challenge progress and stats (personal only)
            if context["type"] == "personal":
                try:
                    _update_user_challenge_progress(user_id)
                    db.update_trader_stats(user_id)
                except Exception as e:
                    app_logger.warning(f"Could not update user stats for user {user_id}: {e}")
            
            # Flash success message
            context_str = f" in {context['league_name']}" if context["type"] == "league" else ""
            flash(f"Bought {shares} shares of {symbol} for {usd(total_cost)}{context_str}!")
            if achievements:
                for achievement in achievements:
                    flash(f"🏆 Achievement Unlocked: {achievement}!", "success")
            
            return redirect("/")
        
        except Exception as e:
            app_logger.error(f"Unexpected error in buy route for user {user_id}: {e}", exc_info=True)
            return apology(f"unexpected error: {str(e)[:50]}", 500)
    
    else:
        # GET request - show buy form
        try:
            stocks = get_portfolio_stocks(user_id, context)
            # Pre-fill symbol if provided in query string
            symbol = request.args.get("symbol", "").upper()
            return render_template("buy.html", symbol=symbol, active_context=context, stocks=stocks)
        except Exception as e:
            app_logger.error(f"Error rendering buy form for user {user_id}: {e}", exc_info=True)
            return apology("could not load buy form", 500)


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


@app.route("/debug/portfolio")
@login_required
def debug_portfolio():
    """Debug endpoint to check portfolio context and cash"""
    user_id = session["user_id"]
    context = get_active_portfolio_context()
    
    # Get personal cash
    user = db.get_user(user_id)
    personal_cash = user["cash"]
    
    # Get league portfolios
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
    current_cash = get_portfolio_cash(user_id, context)
    
    # Debug portfolio endpoint moved into `blueprints/portfolio_bp.py`.
    # See that module for the implementation.
    return jsonify({
        "notice": "moved to blueprints/portfolio_bp.py"
    })


# Auth routes have been moved into `blueprints/auth_bp.py`.
# The original in-file implementations were removed to keep the
# application modular. See `blueprints/auth_bp.py` for the logic.


@app.route("/trade", methods=["GET", "POST"])
@login_required
@rate_limit(max_requests=30, time_window=60, endpoint_key="trade")
def trade():
    """Get stock quote and trade stocks"""
    user_id = session["user_id"]
    
    if request.method == "POST":
        try:
            symbol = request.form.get("symbol")
            
            if not symbol:
                return apology("must provide symbol", 400)
            
            symbol = symbol.upper().strip()
            
            # Look up quote with error handling
            try:
                quote = lookup(symbol)
            except Exception as e:
                app_logger.error(f"Error looking up symbol {symbol}: {e}", exc_info=True)
                return apology("error looking up symbol, please try again", 500)
            
            if not quote:
                # Try searching for similar company names/symbols
                try:
                    from helpers import search_tickers
                    suggestions = search_tickers(symbol)
                    if suggestions:
                        return render_template("quote.html", suggestions=suggestions, previous_query=symbol)
                except Exception as e:
                    app_logger.warning(f"Error searching tickers for {symbol}: {e}")
                
                return apology("invalid symbol", 400)
            
            # Get chart data with error handling
            try:
                chart_data = get_chart_data(symbol, days=30)
            except Exception as e:
                app_logger.warning(f"Error getting chart data for {symbol}: {e}")
                chart_data = None
            
            # Check if in watchlist with error handling
            try:
                in_watchlist = db.is_in_watchlist(user_id, symbol)
            except Exception as e:
                app_logger.warning(f"Error checking watchlist for user {user_id}: {e}")
                in_watchlist = False
            
            # Get stock news with error handling
            try:
                news = get_stock_news(symbol, limit=5)
            except Exception as e:
                app_logger.warning(f"Error getting news for {symbol}: {e}")
                news = []
            
            # Check for triggered alerts with error handling
            try:
                triggered = db.check_alerts(user_id, symbol, quote['price'])
                if triggered:
                    for alert in triggered:
                        try:
                            flash(f"🔔 Alert triggered: {symbol} {'reached above' if alert['alert_type'] == 'above' else 'fell below'} {usd(alert['target_price'])}!", "info")
                        except Exception as e:
                            app_logger.warning(f"Error flashing alert: {e}")
            except Exception as e:
                app_logger.warning(f"Error checking alerts for user {user_id}, symbol {symbol}: {e}")
            
            # Record recent quote with error handling
            try:
                push_recent_quote(symbol)
            except Exception as e:
                app_logger.warning(f"Error pushing recent quote for {symbol}: {e}")
            
            # Get user's cash balance and portfolio context
            try:
                user = db.get_user(user_id)
                user_cash = user['cash'] if user else 0
            except Exception as e:
                app_logger.error(f"Error getting user {user_id}: {e}", exc_info=True)
                return apology("could not fetch user data", 500)
            
            # Get portfolio context and holdings
            try:
                context = get_active_portfolio_context()
                all_stocks = db.get_user_stocks(user_id)
                user_shares = 0
                for stock in all_stocks:
                    if stock['symbol'] == symbol:
                        user_shares = stock['shares']
                        break
            except Exception as e:
                app_logger.error(f"Error getting portfolio context for user {user_id}: {e}", exc_info=True)
                context = {"type": "personal"}
                all_stocks = []
                user_shares = 0
            
            try:
                return render_template("trade.html", quote=quote, chart_data=chart_data or {}, in_watchlist=in_watchlist, 
                                     news=news, recent_quotes=session.get('recent_quotes', []), user_cash=user_cash, 
                                     user_shares=user_shares, active_context=context, all_stocks=all_stocks)
            except Exception as e:
                app_logger.error(f"Error rendering trade template: {e}", exc_info=True)
                return apology("could not load trade page", 500)
        
        except Exception as e:
            app_logger.error(f"Unexpected error in trade route (POST) for user {user_id}: {e}", exc_info=True)
            return apology("unexpected error", 500)
    
    else:
        # GET request - support query param: /trade?symbol=MSFT
        try:
            symbol = request.args.get('symbol')
            
            if symbol:
                symbol = symbol.upper().strip()
                
                # Look up quote
                try:
                    quote = lookup(symbol)
                except Exception as e:
                    app_logger.error(f"Error looking up symbol {symbol}: {e}", exc_info=True)
                    return apology("error looking up symbol, please try again", 500)
                
                if not quote:
                    # Try searching for similar company names/symbols
                    try:
                        from helpers import search_tickers
                        suggestions = search_tickers(symbol)
                        if suggestions:
                            return render_template("quote.html", suggestions=suggestions, previous_query=symbol, 
                                                 recent_quotes=session.get('recent_quotes', []))
                    except Exception as e:
                        app_logger.warning(f"Error searching tickers for {symbol}: {e}")
                    
                    return apology("invalid symbol", 400)

                # Get chart data
                try:
                    chart_data = get_chart_data(symbol, days=30)
                except Exception as e:
                    app_logger.warning(f"Error getting chart data for {symbol}: {e}")
                    chart_data = None

                # Check if in watchlist
                try:
                    in_watchlist = db.is_in_watchlist(user_id, symbol)
                except Exception as e:
                    app_logger.warning(f"Error checking watchlist for user {user_id}: {e}")
                    in_watchlist = False

                # Get stock news
                try:
                    news = get_stock_news(symbol, limit=5)
                except Exception as e:
                    app_logger.warning(f"Error getting news for {symbol}: {e}")
                    news = []

                # Check for triggered alerts
                try:
                    triggered = db.check_alerts(user_id, symbol, quote['price'])
                    if triggered:
                        for alert in triggered:
                            try:
                                flash(f"🔔 Alert triggered: {symbol} {'reached above' if alert['alert_type'] == 'above' else 'fell below'} {usd(alert['target_price'])}!", "info")
                            except Exception as e:
                                app_logger.warning(f"Error flashing alert: {e}")
                except Exception as e:
                    app_logger.warning(f"Error checking alerts for user {user_id}, symbol {symbol}: {e}")

                # Record recent quote
                try:
                    push_recent_quote(symbol)
                except Exception as e:
                    app_logger.warning(f"Error pushing recent quote for {symbol}: {e}")

                # Get user's cash balance and portfolio context
                try:
                    user = db.get_user(user_id)
                    user_cash = user['cash'] if user else 0
                except Exception as e:
                    app_logger.error(f"Error getting user {user_id}: {e}", exc_info=True)
                    return apology("could not fetch user data", 500)
                
                # Get portfolio context and holdings
                try:
                    context = get_active_portfolio_context()
                    all_stocks = db.get_user_stocks(user_id)
                    user_shares = 0
                    for stock in all_stocks:
                        if stock['symbol'] == symbol:
                            user_shares = stock['shares']
                            break
                except Exception as e:
                    app_logger.error(f"Error getting portfolio context for user {user_id}: {e}", exc_info=True)
                    context = {"type": "personal"}
                    all_stocks = []
                    user_shares = 0

                try:
                    return render_template("trade.html", quote=quote, chart_data=chart_data or {}, in_watchlist=in_watchlist, 
                                         news=news, recent_quotes=session.get('recent_quotes', []), user_cash=user_cash, 
                                         user_shares=user_shares, active_context=context, all_stocks=all_stocks)
                except Exception as e:
                    app_logger.error(f"Error rendering trade template: {e}", exc_info=True)
                    return apology("could not load trade page", 500)

            # No symbol provided - show empty quote form
            return render_template("quote.html", recent_quotes=session.get('recent_quotes', []))
        
        except Exception as e:
            app_logger.error(f"Unexpected error in trade route (GET) for user {user_id}: {e}", exc_info=True)
            return apology("unexpected error", 500)


# Registration route moved to `blueprints/auth_bp.py`.

# Keep /quote as backward compatibility redirect
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote_redirect():
    """Backward compatibility redirect to /trade"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if symbol:
            return redirect(f"/trade?symbol={symbol}")
        return redirect("/trade")
    symbol = request.args.get("symbol")
    if symbol:
        return redirect(f"/trade?symbol={symbol}")
    return redirect("/trade")


@app.route("/sell", methods=["GET", "POST"])
@login_required
@rate_limit(max_requests=20, time_window=60, endpoint_key="sell")
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]
    context = get_active_portfolio_context()
    
    if request.method == "POST":
        try:
            # Validate portfolio context
            valid, error_msg = validate_portfolio_context(user_id, context)
            if not valid:
                app_logger.warning(f"Invalid portfolio context for user {user_id}: {error_msg}")
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
                app_logger.debug(f"Invalid shares input from user {user_id}: {shares_str}")
                return apology("shares must be a valid whole number", 400)
            
            # Get stock holding based on portfolio context
            try:
                if context["type"] == "personal":
                    stock = db.get_user_stock(user_id, symbol)
                else:
                    league_id = context["league_id"]
                    stock = db.get_league_holding(league_id, user_id, symbol)
            except Exception as e:
                app_logger.error(f"Error fetching stock holding for user {user_id}, symbol {symbol}: {e}", exc_info=True)
                return apology("could not fetch holding information", 500)
            
            if not stock or int(stock["shares"]) < shares:
                app_logger.debug(f"User {user_id} insufficient shares of {symbol}: want {shares}, have {stock['shares'] if stock else 0}")
                return apology("not enough shares", 400)
            
            # Look up current price
            quote = lookup(symbol)
            if not quote:
                app_logger.debug(f"Invalid symbol for sell: {symbol}")
                return apology("invalid symbol", 400)
            
            price = quote["price"]
            total_value = price * shares
            
            # Get optional strategy and notes
            strategy = request.form.get("strategy") or None
            notes = request.form.get("notes") or None
            
            # Handle transaction based on portfolio context
            try:
                if context["type"] == "personal":
                    # Personal portfolio
                    txn_id = db.record_transaction(user_id, symbol, -shares, price, "sell", strategy, notes)
                    user = db.get_user(user_id)
                    if not user:
                        app_logger.error(f"User {user_id} not found in database")
                        return apology("user not found", 500)
                    db.update_cash(user_id, user["cash"] + total_value)
                    # Execute copy trades for any followers
                    _execute_copy_trades(user_id, symbol, shares, price, 'sell', txn_id)
                    app_logger.info(f"SELL | User: {user_id} | Symbol: {symbol} | Shares: {shares} | Price: {price} | Total: {total_value}")
                else:
                    # League portfolio
                    league_id = context["league_id"]
                    txn_id = db.record_league_transaction(league_id, user_id, symbol, shares, price, "sell")
                    cash = get_portfolio_cash(user_id, context)
                    db.update_league_cash(league_id, user_id, cash + total_value)
                    db.update_league_holding(league_id, user_id, symbol, -shares, price)
                    app_logger.info(f"SELL (LEAGUE) | League: {league_id} | User: {user_id} | Symbol: {symbol} | Shares: {shares}")
            except Exception as e:
                app_logger.error(f"Database error during sell transaction for user {user_id}: {e}", exc_info=True)
                return apology(f"database error: {str(e)[:50]}", 500)
            
            # Send trade alert to chat (non-critical)
            try:
                send_trade_alert_to_chat(user_id, symbol, shares, price, 'sold')
            except Exception as e:
                app_logger.warning(f"Could not send trade alert for user {user_id}: {e}")
            
            # Create portfolio snapshot (personal only, non-critical)
            if context["type"] == "personal":
                try:
                    create_portfolio_snapshot(user_id)
                except Exception as e:
                    app_logger.warning(f"Could not create portfolio snapshot for user {user_id}: {e}")
            
            # Emit real-time portfolio update (non-critical)
            try:
                if context["type"] == "personal":
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
                else:
                    # League portfolio update
                    league_id = context["league_id"]
                    league_portfolio = db.get_league_portfolio(league_id, user_id)
                    league_holdings = db.get_league_holdings(league_id, user_id)
                    portfolio_value = league_portfolio["cash"] if league_portfolio else 0
                    for holding in league_holdings:
                        q = lookup(holding["symbol"])
                        if q:
                            portfolio_value += holding["shares"] * q["price"]
                    
                    socketio.emit('portfolio_update', {
                        'cash': league_portfolio["cash"] if league_portfolio else 0,
                        'total_value': portfolio_value,
                        'stocks': [{'symbol': h["symbol"], 'shares': h["shares"]} for h in league_holdings]
                    }, room=f'user_{user_id}')
            except Exception as e:
                app_logger.warning(f"Could not emit portfolio update for user {user_id}: {e}")
            
            # Emit order execution notification (non-critical)
            try:
                socketio.emit('order_executed', {
                    'type': 'sell',
                    'symbol': symbol,
                    'shares': shares,
                    'price': price,
                    'total': total_value,
                    'timestamp': datetime.now().isoformat()
                }, room=f'user_{user_id}')
            except Exception as e:
                app_logger.warning(f"Could not emit order execution notification for user {user_id}: {e}")
            
            # Check for achievements and update stats (personal only, non-critical)
            if context["type"] == "personal":
                try:
                    achievements = check_achievements(user_id)
                    _update_user_challenge_progress(user_id)
                    db.update_trader_stats(user_id)
                except Exception as e:
                    app_logger.warning(f"Could not update achievements/stats for user {user_id}: {e}")
                    achievements = []
            else:
                achievements = []
            
            # Flash success message
            context_str = f" in {context['league_name']}" if context["type"] == "league" else ""
            flash(f"Sold {shares} shares of {symbol} for {usd(total_value)}{context_str}!")
            if achievements:
                for achievement in achievements:
                    flash(f"🏆 Achievement Unlocked: {achievement}!", "success")
            
            return redirect("/")
        
        except Exception as e:
            app_logger.error(f"Unexpected error in sell route for user {user_id}: {e}", exc_info=True)
            return apology(f"unexpected error: {str(e)[:50]}", 500)
    
    else:
        # GET request - show sell form
        try:
            stocks = get_portfolio_stocks(user_id, context)
            return render_template("sell.html", stocks=stocks, active_context=context)
        except Exception as e:
            app_logger.error(f"Error rendering sell form for user {user_id}: {e}", exc_info=True)
            return apology("could not load sell form", 500)


@app.route("/edit_portfolio", methods=["GET", "POST"])
@login_required
def edit_portfolio():
    """Edit personal portfolio balance. This resets holdings and analytics for the user."""
    user_id = session["user_id"]
    context = get_active_portfolio_context()

    # SECURITY: Prevent modifying league portfolio cash (that would be cheating!)
    if context["type"] != "personal":
        flash("Cannot modify league portfolio cash directly. League portfolios can only be changed through trading.", "danger")
        return redirect("/")

    if request.method == "POST":
        amount = request.form.get("amount")

        if not amount:
            return apology("must provide amount", 400)

        try:
            amount = float(amount)
            if amount < 0:
                return apology("amount cannot be negative", 400)
        except ValueError:
            return apology("invalid amount", 400)

        # Use centralized DB method to reset personal portfolio and set new cash
        try:
            db.reset_personal_portfolio(
                user_id,
                amount,
                performed_by=session.get('user_id'),
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                reason=None
            )
        except Exception:
            # If reset fails for some reason, return an error
            return apology('failed to reset portfolio', 500)

        # Clear any potential caching issues by forcing session update
        session.modified = True

        flash(f"Successfully reset your portfolio and set cash to {usd(amount)}!", "success")
        return redirect("/")

    else:
        # Get current personal cash for display
        current_cash = get_portfolio_cash(user_id, context)
        return render_template("edit_portfolio.html", current_cash=current_cash, active_context=context)


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


@app.route("/api/leaderboard/global")
@login_required
def api_leaderboard_global():
    """Return global leaderboard as JSON.

    This endpoint reads from the `leaderboards` cache table when available.
    Supports pagination via `limit` and `offset` query params.
    Falls back to live computation if cache is missing.
    """
    # Pagination parameters
    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"error": "invalid pagination parameters"}), 400

    # Try to load cached leaderboard
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT data_json FROM leaderboards WHERE leaderboard_type = ? AND period = ?", ("global", "all"))
    row = cursor.fetchone()
    if row and row[0]:
        try:
            data = json.loads(row[0])
            # Apply pagination
            paged = data[offset:offset+limit]
            return jsonify(leaderboard=paged, total=len(data))
        except Exception:
            # Fall through to live compute
            pass

    # Live compute fallback (slower)
    users_data = cursor.execute("SELECT id, username, cash FROM users ORDER BY username").fetchall()

    leaderboard_data = []
    starting_cash = 10000.00

    for user_data in users_data:
        user_id = user_data[0]
        username = user_data[1]
        cash = user_data[2]

        # Get user's stocks
        stocks = db.get_user_stocks(user_id)

        # Calculate total value
        total_value = cash
        for stock in stocks:
            # Support both dict rows and tuple rows
            symbol = stock.get("symbol") if isinstance(stock, dict) else stock[2]
            shares = stock.get("shares") if isinstance(stock, dict) else stock[3]
            quote = lookup(symbol)
            if quote:
                total_value += shares * quote["price"]

        total_return = total_value - starting_cash
        return_percent = (total_return / starting_cash) * 100 if starting_cash > 0 else 0

        leaderboard_data.append({
            "username": username,
            "total_value": round(total_value, 2),
            "total_return": round(total_return, 2),
            "return_percent": round(return_percent, 2)
        })

    leaderboard_data.sort(key=lambda x: x["total_value"], reverse=True)
    conn.close()

    # Return paginated slice
    return jsonify(leaderboard=leaderboard_data[offset:offset+limit], total=len(leaderboard_data))


@app.route("/api/leaderboard/league/<int:league_id>")
@login_required
def api_leaderboard_league(league_id):
    """Return a league leaderboard as JSON."""
    # Try cached first (period 'all' for now)
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT data_json FROM leaderboards WHERE leaderboard_type = ? AND period = ?", (f"league_{league_id}", "all"))
    row = cursor.fetchone()
    if row and row[0]:
        try:
            data = json.loads(row[0])
            conn.close()
            return jsonify(leaderboard=data)
        except Exception:
            pass

    leaderboard = db.get_league_leaderboard(league_id)
    return jsonify(leaderboard=leaderboard)


def compute_and_cache_global_leaderboard():
    """Compute the global leaderboard and cache it into `leaderboards` table.

    This function writes a JSON array into the `leaderboards` table with
    `leaderboard_type` = 'global' and `period` = 'all'.
    """
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        users_data = cursor.execute("SELECT id, username, cash FROM users ORDER BY username").fetchall()

        leaderboard_data = []
        starting_cash = 10000.00

        for user_data in users_data:
            user_id = user_data[0]
            username = user_data[1]
            cash = user_data[2]

            stocks = db.get_user_stocks(user_id)
            total_value = cash
            for stock in stocks:
                symbol = stock.get("symbol") if isinstance(stock, dict) else stock[2]
                shares = stock.get("shares") if isinstance(stock, dict) else stock[3]
                quote = lookup(symbol)
                if quote:
                    total_value += shares * quote["price"]

            total_return = total_value - starting_cash
            return_percent = (total_return / starting_cash) * 100 if starting_cash > 0 else 0

            leaderboard_data.append({
                "username": username,
                "total_value": round(total_value, 2),
                "total_return": round(total_return, 2),
                "return_percent": round(return_percent, 2)
            })

        leaderboard_data.sort(key=lambda x: x["total_value"], reverse=True)

        data_json = json.dumps(leaderboard_data)

        # Upsert into leaderboards table
        cursor.execute(
            "INSERT INTO leaderboards (leaderboard_type, period, data_json, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(leaderboard_type, period) DO UPDATE SET data_json = excluded.data_json, updated_at = CURRENT_TIMESTAMP",
            ("global", "all", data_json)
        )

        # Also write compact snapshots to leaderboard_snapshots (league_id NULL for global)
        try:
            # Insert each snapshot row; snapshot_at defaults to CURRENT_TIMESTAMP
            for rank, entry in enumerate(leaderboard_data, start=1):
                # find user id in same connection
                try:
                    cursor.execute("SELECT id FROM users WHERE username = ?", (entry['username'],))
                    user_row = cursor.fetchone()
                    user_id = user_row[0] if user_row else None
                except Exception:
                    user_id = None

                cursor.execute(
                    "INSERT INTO leaderboard_snapshots (league_id, user_id, username, rank, total_value) VALUES (?, ?, ?, ?, ?)",
                    (None, user_id, entry['username'], rank, entry['total_value'])
                )
        except Exception:
            # Best-effort snapshot; don't fail the whole job
            pass

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("Error computing/caching global leaderboard:", e)
        return False


def compute_and_cache_league_leaderboards(limit=100):
    """Compute leaderboards for active leagues and store compact snapshots.

    For each active league, retrieve the leaderboard via `db.get_league_leaderboard`
    and write per-member rows to `leaderboard_snapshots`. Also upsert a cached
    JSON entry into the `leaderboards` table with key `league_<id>`.
    """
    try:
        leagues = db.get_active_leagues(limit=limit)
        conn = db.get_connection()
        cursor = conn.cursor()

        for league in leagues:
            league_id = league.get('id') if isinstance(league, dict) else league[0]
            # get leaderboard entries (list of dicts)
            leaderboard = db.get_league_leaderboard(league_id)

            # Upsert JSON cache for this league
            try:
                data_json = json.dumps(leaderboard)
                cursor.execute(
                    "INSERT INTO leaderboards (leaderboard_type, period, data_json, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
                    "ON CONFLICT(leaderboard_type, period) DO UPDATE SET data_json = excluded.data_json, updated_at = CURRENT_TIMESTAMP",
                    (f"league_{league_id}", "all", data_json)
                )
            except Exception:
                pass

            # Insert compact snapshots
            try:
                for entry in leaderboard:
                    user_id = entry.get('id')
                    username = entry.get('username')
                    rank = entry.get('current_rank') or None
                    # prefer score if present, otherwise 0
                    total_value = entry.get('score') if entry.get('score') is not None else 0
                    cursor.execute(
                        "INSERT INTO leaderboard_snapshots (league_id, user_id, username, rank, total_value) VALUES (?, ?, ?, ?, ?)",
                        (league_id, user_id, username, rank, total_value)
                    )
            except Exception:
                pass

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("Error computing league snapshots:", e)
        return False


def start_leaderboard_worker(interval_seconds=300):
    """Start a background thread that updates the global leaderboard periodically.

    Default interval is 300 seconds (5 minutes).
    """
    def worker():
        import time
        while True:
            try:
                compute_and_cache_global_leaderboard()
            except Exception as e:
                print("Leaderboard worker error:", e)
            time.sleep(interval_seconds)

    t = threading.Thread(target=worker, daemon=True)
    t.start()


# Start the leaderboard worker when running directly (not under test/WSGI)
if __name__ != "__main__":
    # When imported by tests or WSGI servers, don't auto-start.
    pass


@app.route("/portfolio/switch", methods=["POST"])
@login_required
def switch_portfolio_context():
    # Handed over to `blueprints/portfolio_bp.py` for modular routing.
    # Keep a minimal fallback to avoid import-time failures.
    return redirect(url_for('portfolio.debug_portfolio'))


@app.route("/leagues")
@login_required
def leagues():
    """Show all leagues"""
    user_id = session["user_id"]
    
    # Get user's leagues
    user_leagues = db.get_user_leagues(user_id)
    
    # Get active public leagues
    public_leagues = db.get_active_leagues(limit=20)
    
    # Get active context
    context = get_active_portfolio_context()
    
    # Compute visible public leagues server-side to avoid template-time filtering
    joined_ids = [l['id'] for l in user_leagues]
    visible_public = [l for l in public_leagues if l.get('id') not in joined_ids]

    return render_template("leagues.html",
                         user_leagues=user_leagues,
                         public_leagues=public_leagues,
                         visible_public=visible_public,
                         active_context=context)


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
        
        # Update mode and rules with error handling
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE leagues SET mode = ?, rules_json = ?, lifecycle_state = 'active'
                WHERE id = ?
            """, (mode, json.dumps(rules), league_id))
        except sqlite3.OperationalError:
            # Fallback if columns don't exist - just update lifecycle_state
            try:
                cursor.execute("""
                    UPDATE leagues SET lifecycle_state = 'active'
                    WHERE id = ?
                """, (league_id,))
            except sqlite3.OperationalError:
                pass
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
    
    # Get leaderboard with portfolio values
    leaderboard = db.get_league_leaderboard_with_values(
        league_id,
        lambda symbol: lookup(symbol).get('price') if lookup(symbol) else None
    )
    
    return render_template("league_detail.html",
                         league=league,
                         members=members,
                         leaderboard=leaderboard,
                         is_member=is_member,
                         is_admin=is_admin)


@app.route("/leagues/<int:league_id>/preview")
@login_required
def league_preview(league_id):
    """Return a small JSON preview for a league (used by client-side modal)."""
    league = db.get_league(league_id)
    if not league:
        return jsonify({"error": "not found"}), 404

    # Top 3 leaderboard entries
    try:
        top = db.get_league_leaderboard(league_id)[:3]
    except Exception:
        top = []

    members = db.get_league_members(league_id)
    preview = {
        "id": league["id"],
        "name": league.get("name"),
        "description": league.get("description"),
        "starting_cash": league.get("starting_cash"),
        "is_active": league.get("is_active"),
        "top": [{"username": e.get("username"), "total_value": e.get("total_value")} for e in top],
        "member_count": len(members),
        "rules": league.get("rules_json") if league.get("rules_json") else None
    }

    return jsonify(preview)


@app.route("/leagues/<int:league_id>/track_view", methods=["POST"])
@login_required
def league_track_view(league_id):
    """Basic analytics: increment view counter for a league.

    Uses a JSON file in `instance/league_analytics.json` to avoid DB migrations.
    This is lightweight and non-atomic; for high-traffic apps replace with Redis or DB.
    """
    analytics_path = os.path.join(app.instance_path, "league_analytics.json")
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except Exception:
        pass

    data = {}
    try:
        if os.path.exists(analytics_path):
            with open(analytics_path, "r", encoding="utf-8") as f:
                data = json.load(f)
    except Exception:
        data = {}

    key = str(league_id)
    entry = data.get(key, {"views": 0, "joins": 0})
    entry["views"] = entry.get("views", 0) + 1
    data[key] = entry

    try:
        with open(analytics_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

    return jsonify({"ok": True, "views": entry["views"]})


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
        
        # Log activity to league activity feed
        user = db.get_user(user_id)
        username = user.get('username') if user else 'Unknown'
        activity_id = db.add_league_activity(
            league_id=league_id,
            activity_type='joined',
            title=f'{username} joined the league',
            description=f'{username} has joined the league!',
            user_id=user_id,
            metadata={'starting_cash': starting_cash}
        )
        
        # Emit real-time activity update
        emit_league_activity(league_id, {
            'id': activity_id,
            'username': username,
            'user_avatar': user.get('avatar_url') if user else None,
            'activity_type': 'joined',
            'title': f'{username} joined the league',
            'description': f'{username} has joined the league!',
            'created_at': datetime.now().isoformat(),
            'metadata': {'starting_cash': starting_cash}
        })
        
        flash("Successfully joined league!", "success")
        return redirect(f"/leagues/{league_id}")
    else:
        return apology("already a member or error joining", 400)


@app.route("/leagues/<int:league_id>/leave", methods=["POST"])
@login_required
def leave_league(league_id):
    """Leave a league"""
    user_id = session["user_id"]
    
    # Get league info before leaving (to check if owner)
    league = db.get_league(league_id)
    is_owner = league and league.get('creator_id') == user_id
    
    # Leave the league
    db.leave_league(league_id, user_id)
    
    # Check if league still exists (might be auto-deleted)
    league_after = db.get_league(league_id)
    
    if league_after is None:
        flash("You have left the league. League was deleted as it has no members.", "info")
    elif is_owner:
        flash("You have left the league. Ownership has been transferred to the next member.", "info")
    else:
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
        
        # Check rate limiting (max 100 trades per hour per league)
        allowed, trades_remaining, reset_seconds = db.check_trade_rate_limit(league_id, user_id, max_trades_per_hour=100)
        if not allowed:
            minutes_remaining = (reset_seconds + 59) // 60  # Round up to nearest minute
            return apology(f"Trade rate limit exceeded. Please wait {minutes_remaining} minutes.", 429)
        
        # Get current price
        quote = lookup(symbol)
        if not quote:
            return apology("invalid symbol", 400)
        
        price = quote["price"]
        trade_value = shares * price
        
        # Use comprehensive trade validation
        is_valid, error = db.validate_league_trade(league_id, user_id, symbol, trade_type.upper(), shares, price)
        if not is_valid:
            return apology(error, 400)
        
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
        
        # Execute trade atomically to prevent concurrent trade race conditions
        success, error_msg, txn_id = db.execute_league_trade_atomic(
            league_id, user_id, symbol, trade_type.upper(), shares, price, fee
        )
        
        if not success:
            return apology(error_msg or "Trade failed", 400)
        
        # Log activity to league activity feed after successful atomic trade
        user = db.get_user(user_id)
        username = user.get('username') if user else 'Unknown'
        
        if trade_type == "buy":
            activity_id = db.add_league_activity(
                league_id=league_id,
                activity_type='trade',
                title=f'{username} bought {shares} {symbol}',
                description=f'Purchased {shares} shares of {symbol} at {usd(price)} per share',
                user_id=user_id,
                metadata={'symbol': symbol, 'shares': shares, 'price': price, 'type': 'buy', 'total': trade_value}
            )
            
            emit_league_activity(league_id, {
                'id': activity_id,
                'username': username,
                'user_avatar': user.get('avatar_url') if user else None,
                'activity_type': 'trade',
                'title': f'{username} bought {shares} {symbol}',
                'description': f'Purchased {shares} shares of {symbol} at {usd(price)} per share',
                'created_at': datetime.now().isoformat(),
                'metadata': {'symbol': symbol, 'shares': shares, 'price': price, 'type': 'buy', 'total': trade_value}
            })
            
            flash(f"Bought {shares} shares of {symbol} for {usd(trade_value)} (fee: {usd(fee)})", "success")
            
        elif trade_type == "sell":
            proceeds = trade_value - fee
            activity_id = db.add_league_activity(
                league_id=league_id,
                activity_type='trade',
                title=f'{username} sold {shares} {symbol}',
                description=f'Sold {shares} shares of {symbol} at {usd(price)} per share',
                user_id=user_id,
                metadata={'symbol': symbol, 'shares': shares, 'price': price, 'type': 'sell', 'total': proceeds}
            )
            
            emit_league_activity(league_id, {
                'id': activity_id,
                'username': username,
                'user_avatar': user.get('avatar_url') if user else None,
                'activity_type': 'trade',
                'title': f'{username} sold {shares} {symbol}',
                'description': f'Sold {shares} shares of {symbol} at {usd(price)} per share',
                'created_at': datetime.now().isoformat(),
                'metadata': {'symbol': symbol, 'shares': shares, 'price': price, 'type': 'sell', 'total': proceeds}
            })
            
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
    
    # Enrich leaderboard with additional data and calculate league statistics
    starting_cash = league.get('starting_cash', 10000.0)
    total_portfolio_value = 0
    total_returns = 0
    total_transactions = 0
    highest_gain_member = None
    highest_gain_value = float('-inf')
    highest_loss_member = None
    highest_loss_value = float('inf')
    best_performer = None
    best_return_pct = float('-inf')
    most_active_member = None
    most_active_count = 0
    
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
            
            # Update league statistics
            total_portfolio_value += total_value
            total_returns += (total_value - starting_cash)
            
            # Track highest gain/loss
            gain_loss = total_value - starting_cash
            if gain_loss > highest_gain_value:
                highest_gain_value = gain_loss
                highest_gain_member = entry['username']
            if gain_loss < highest_loss_value:
                highest_loss_value = gain_loss
                highest_loss_member = entry['username']
            
            # Track best performer
            if entry['return_pct'] > best_return_pct:
                best_return_pct = entry['return_pct']
                best_performer = entry['username']
            
            # Count transactions per member
            member_transactions = db.get_league_transactions(league_id, user_id=entry['id'])
            transaction_count = len(member_transactions) if member_transactions else 0
            entry['transaction_count'] = transaction_count
            total_transactions += transaction_count
            
            if transaction_count > most_active_count:
                most_active_count = transaction_count
                most_active_member = entry['username']
        else:
            entry['total_value'] = starting_cash
            entry['return_pct'] = 0
            entry['transaction_count'] = 0
    
    # Calculate average portfolio value
    num_members = len(leaderboard) if leaderboard else 1
    average_portfolio_value = total_portfolio_value / num_members if num_members > 0 else 0
    
    # Build league statistics dict
    league_stats = {
        'total_portfolio_value': total_portfolio_value,
        'average_portfolio_value': average_portfolio_value,
        'total_returns': total_returns,
        'average_return': total_returns / num_members if num_members > 0 else 0,
        'total_transactions': total_transactions,
        'num_members': num_members,
        'highest_gain_member': highest_gain_member,
        'highest_gain_value': highest_gain_value if highest_gain_value != float('-inf') else 0,
        'highest_loss_member': highest_loss_member,
        'highest_loss_value': highest_loss_value if highest_loss_value != float('inf') else 0,
        'best_performer': best_performer,
        'best_return_pct': best_return_pct if best_return_pct != float('-inf') else 0,
        'most_active_member': most_active_member,
        'most_active_count': most_active_count
    }
    
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
                         league_stats=league_stats,
                         recent_transactions=recent_transactions,
                         user_portfolio=user_portfolio,
                         user_holdings=user_holdings,
                         is_member=is_member,
                         mode_description=mode.get_description(),
                         starting_cash=starting_cash)





# ============ ADVANCED LEAGUE SYSTEM ROUTES ============

@app.route("/leagues/advanced")
@login_required
def leagues_advanced():
    """Show advanced leagues page with new features"""
    user_id = session["user_id"]
    
    # Get user's leagues
    user_leagues_list = db.get_user_leagues(user_id)
    
    # Get featured leagues
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.*, 
               COUNT(DISTINCT lm.user_id) as member_count,
               u.username as creator_name
        FROM leagues l
        LEFT JOIN league_members lm ON l.id = lm.league_id
        LEFT JOIN users u ON l.creator_id = u.id
        WHERE l.visibility = 'public' AND l.lifecycle_state = 'active'
        ORDER BY member_count DESC
        LIMIT 6
    """)
    featured_leagues = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Get stats
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM leagues WHERE visibility = 'public'")
    total_leagues = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM league_members")
    global_players = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM league_seasons WHERE is_active = 1")
    seasons_running = cursor.fetchone()[0]
    conn.close()
    
    return render_template("leagues_advanced.html",
                         user_leagues_list=user_leagues_list,
                         featured_leagues=featured_leagues,
                         total_leagues=total_leagues,
                         user_leagues=len(user_leagues_list),
                         global_players=global_players,
                         seasons_running=seasons_running)


@app.route("/league/<int:league_id>/detail")
@login_required
def league_detail_advanced(league_id):
    """Show advanced league detail page with all features"""
    user_id = session["user_id"]
    
    league = db.get_league(league_id)
    if not league:
        return apology("league not found", 404)
    
    # Check if user is member
    is_member = db.is_league_member(user_id, league_id)
    
    # Get league details
    members = db.get_league_members(league_id)
    leaderboard = db.get_league_leaderboard(league_id)
    
    # Get advanced stats if AdvancedLeagueManager is available
    try:
        # Get league member statistics
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, rank, score, trades_count, win_rate, volatility, sharpe_ratio, max_drawdown
            FROM league_member_stats
            WHERE league_id = ?
            ORDER BY rank ASC
        """, (league_id,))
        advanced_stats = [dict(row) for row in cursor.fetchall()]
        conn.close()
    except:
        advanced_stats = []
    
    # Get achievements for this league
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT la.id, la.key, la.name, la.description, la.rarity, COUNT(DISTINCT lab.user_id) as unlock_count
            FROM league_achievements la
            LEFT JOIN league_badges lab ON la.id = lab.achievement_id
            WHERE la.league_id = ?
            GROUP BY la.id
            ORDER BY la.rarity DESC
        """, (league_id,))
        achievements = [dict(row) for row in cursor.fetchall()]
        conn.close()
    except:
        achievements = []
    
    # Get tournaments for this league
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tournaments
            WHERE league_id = ?
            ORDER BY start_date DESC
            LIMIT 5
        """, (league_id,))
        tournaments = [dict(row) for row in cursor.fetchall()]
        conn.close()
    except:
        tournaments = []
    
    return render_template("league_detail.html",
                         league=league,
                         is_member=is_member,
                         members=members,
                         leaderboard=leaderboard,
                         advanced_stats=advanced_stats,
                         achievements=achievements,
                         tournaments=tournaments)


@app.route("/tournaments")
@login_required
def tournaments():
    """Show all tournaments"""
    user_id = session["user_id"]
    
    # Get active tournaments
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, l.name as league_name, l.id as league_id,
               COUNT(DISTINCT tp.user_id) as participant_count
        FROM tournaments t
        LEFT JOIN leagues l ON t.league_id = l.id
        LEFT JOIN tournament_participants tp ON t.id = tp.tournament_id
        WHERE t.status = 'active'
        GROUP BY t.id
        ORDER BY t.start_date DESC
    """)
    active_tournaments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Get user's tournament participations
    user_tournaments = db.execute("""
        SELECT DISTINCT t.*, l.name as league_name
        FROM tournaments t
        LEFT JOIN league_members lm ON lm.league_id = t.league_id
        LEFT JOIN tournament_participants tp ON t.id = tp.tournament_id AND tp.user_id = ?
        LEFT JOIN leagues l ON t.league_id = l.id
        WHERE (lm.user_id = ? AND lm.league_id = t.league_id) OR tp.user_id = ?
        ORDER BY t.start_date DESC
    """, (user_id, user_id, user_id))
    
    return render_template("tournaments.html",
                         active_tournaments=active_tournaments,
                         user_tournaments=user_tournaments)


@app.route("/tournament/<int:tournament_id>")
@login_required
def tournament_detail(tournament_id):
    """Show tournament details and bracket"""
    user_id = session["user_id"]
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get tournament info
    cursor.execute("""
        SELECT t.*, l.name as league_name, l.id as league_id
        FROM tournaments t
        LEFT JOIN leagues l ON t.league_id = l.id
        WHERE t.id = ?
    """, (tournament_id,))
    tournament = dict(cursor.fetchone())
    
    if not tournament:
        return apology("tournament not found", 404)
    
    # Get participants
    cursor.execute("""
        SELECT tp.*, u.username
        FROM tournament_participants tp
        LEFT JOIN users u ON tp.user_id = u.id
        WHERE tp.tournament_id = ?
        ORDER BY tp.rank ASC
    """, (tournament_id,))
    participants = [dict(row) for row in cursor.fetchall()]
    
    # Get matches
    cursor.execute("""
        SELECT * FROM tournament_matches
        WHERE tournament_id = ?
        ORDER BY round ASC, match_number ASC
    """, (tournament_id,))
    matches = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Check if user is participating
    is_participant = any(p['user_id'] == user_id for p in participants)
    
    return render_template("tournament_detail.html",
                         tournament=tournament,
                         participants=participants,
                         matches=matches,
                         is_participant=is_participant)


@app.route("/achievements")
@login_required
def achievements():
    """Show achievements and badges"""
    user_id = session["user_id"]
    
    # Get user's achievements across all leagues
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get user's earned badges
    cursor.execute("""
        SELECT lab.*, la.name, la.description, la.icon, la.rarity, l.name as league_name
        FROM league_badges lab
        LEFT JOIN league_achievements la ON lab.achievement_id = la.id
        LEFT JOIN leagues l ON la.league_id = l.id
        WHERE lab.user_id = ?
        ORDER BY lab.unlocked_at DESC
    """, (user_id,))
    user_badges = [dict(row) for row in cursor.fetchall()]
    
    # Get all available achievements
    cursor.execute("""
        SELECT la.*, COUNT(DISTINCT lab.user_id) as unlock_count
        FROM league_achievements la
        LEFT JOIN league_badges lab ON la.id = lab.achievement_id AND lab.user_id = ?
        GROUP BY la.id
        ORDER BY la.rarity DESC, la.name ASC
    """, (user_id,))
    all_achievements = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Group achievements by rarity
    achievements_by_rarity = {}
    for ach in all_achievements:
        rarity = ach.get('rarity', 'common')
        if rarity not in achievements_by_rarity:
            achievements_by_rarity[rarity] = []
        achievements_by_rarity[rarity].append(ach)
    
    # Count stats
    total_badges = len(user_badges)
    total_achievements = len(all_achievements)
    unlock_rate = (total_badges / max(total_achievements, 1)) * 100 if total_achievements > 0 else 0
    
    return render_template("achievements.html",
                         user_badges=user_badges,
                         achievements_by_rarity=achievements_by_rarity,
                         total_badges=total_badges,
                         total_achievements=total_achievements,
                         unlock_rate=int(unlock_rate))


@app.route("/api/league/<int:league_id>")
@login_required
def api_league_details(league_id):
    """API endpoint for league details"""
    league = db.get_league(league_id)
    if not league:
        return jsonify({"error": "League not found"}), 404
    
    members = db.get_league_members(league_id)
    
    return jsonify({
        "id": league.get("id"),
        "name": league.get("name"),
        "description": league.get("description"),
        "member_count": len(members),
        "competition_mode": league.get("competition_mode_name"),
        "league_tier": league.get("league_tier", "Bronze"),
        "lifecycle_state": league.get("lifecycle_state", "Active"),
        "prize_pool": league.get("prize_pool", 0),
        "creator_name": league.get("creator_name", "Unknown")
    })


@app.route("/api/league/<int:league_id>/leaderboard")
@login_required
def api_league_leaderboard(league_id):
    """API endpoint for real-time leaderboard"""
    leaderboard = db.get_league_leaderboard_with_values(
        league_id,
        lambda symbol: lookup(symbol).get('price') if lookup(symbol) else None
    )
    
    return jsonify({
        "leaderboard": [
            {
                "rank": entry.get("current_rank"),
                "username": entry.get("username"),
                "score": entry.get("score"),
                "portfolio_value": entry.get("total_value"),
                "return_pct": entry.get("return_pct")
            }
            for entry in leaderboard
        ]
    })


@app.route("/api/league/<int:league_id>/activity-feed")
@login_required
def api_league_activity_feed(league_id):
    """API endpoint for league activity feed"""
    try:
        # Get pagination parameters
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        
        # Validate limits
        if limit < 1 or limit > 100:
            limit = 20
        if offset < 0:
            offset = 0
        
        # Check league exists
        league = db.get_league(league_id)
        if not league:
            return jsonify({"error": "League not found"}), 404
        
        # Get activity feed and total count
        activities = db.get_league_activity_feed(league_id, limit=limit, offset=offset)
        total_count = db.get_league_activity_count(league_id)
        
        # Enrich activities with user information
        for activity in activities:
            if activity['user_id']:
                user = db.get_user(activity['user_id'])
                if user:
                    activity['username'] = user.get('username')
                    activity['user_avatar'] = user.get('avatar_url')
            
            # Format timestamp
            if isinstance(activity['created_at'], str):
                activity['created_at'] = activity['created_at']
            else:
                activity['created_at'] = activity['created_at'].isoformat() if hasattr(activity['created_at'], 'isoformat') else str(activity['created_at'])
        
        return jsonify({
            "activities": activities,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count
        })
    
    except Exception as e:
        logging.error(f"Error fetching activity feed for league {league_id}: {e}")
        return jsonify({"error": "Failed to fetch activity feed"}), 500


@app.route("/api/league/<int:league_id>/analytics")
@login_required
def api_league_analytics(league_id):
    """API endpoint for league analytics"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get league-wide metrics
        cursor.execute("""
            SELECT 
                AVG(sharpe_ratio) as avg_sharpe,
                AVG(max_drawdown) as avg_drawdown,
                AVG(win_rate) as avg_win_rate,
                SUM(trades_count) as total_trades,
                COUNT(*) as member_count
            FROM league_member_stats
            WHERE league_id = ?
        """, (league_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return jsonify({
            "avg_sharpe_ratio": result[0] or 0,
            "avg_max_drawdown": result[1] or 0,
            "avg_win_rate": result[2] or 0,
            "total_trades": result[3] or 0,
            "member_count": result[4] or 0
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
    # Handle both formats: with and without fractional seconds
    end_time_str = challenge['end_time']
    if '.' in end_time_str:
        # Remove fractional seconds if present
        end_time_str = end_time_str.split('.')[0]
    end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
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

    # Get user badges
    badges = db.get_user_badges(profile_user["id"])

    # Get user achievements
    achievements = db.get_achievements(profile_user["id"])
    
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
            SELECT id FROM friends 
            WHERE user_id = ? AND friend_id = ? AND status = 'pending'
        """, (current_user_id, profile_user["id"])).fetchone()
        friend_request_pending = pending is not None
        conn.close()
    
    # Can the current user award a badge to this profile?
    can_award_badge = False
    if not is_own_profile:
        current_user = db.get_user(current_user_id)
        if current_user and current_user.get("is_admin"):
            can_award_badge = True

    return render_template("profile.html",
                         profile_user=profile_user,
                         is_own_profile=is_own_profile,
                         stats=stats,
                         stocks=stocks,
                         recent_transactions=recent_transactions,
                         friends=friends,
                         is_friend=is_friend,
                         friend_request_pending=friend_request_pending,
                         badges=badges,
                         achievements=achievements,
                         can_award_badge=can_award_badge)


@app.route("/settings")
@login_required
def settings():
    """Show settings page"""
    user_id = session["user_id"]
    user = db.get_user(user_id)
    if not user:
        flash("User not found", "danger")
        return redirect("/login")
    return render_template("settings.html", user=user)


@app.route("/settings/profile", methods=["POST"])
@login_required
def update_profile():
    """Update user profile"""
    user_id = session["user_id"]
    email = request.form.get("email", "").strip()
    bio = request.form.get("bio", "").strip()
    is_public = 1 if request.form.get("is_public") else 0
    theme = request.form.get("theme") or "dark"
    
    # Validation
    if email and not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        flash("Invalid email address", "danger")
        return redirect("/settings")
    
    if bio and len(bio) > 200:
        flash("Bio must be 200 characters or less", "danger")
        return redirect("/settings")
    
    # Update profile
    db.update_user_profile(
        user_id, 
        email=email if email else None, 
        bio=bio, 
        is_public=is_public, 
        theme=theme
    )
    
    flash("Profile updated successfully!", "success")
    return redirect("/settings")


@app.route("/settings/password", methods=["POST"])
@login_required
def change_password():
    """Change user password"""
    user_id = session["user_id"]
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    
    # Validate input
    if not current_password:
        return apology("must provide current password", 400)
    if not new_password:
        return apology("must provide new password", 400)
    if not confirm_password:
        return apology("must confirm new password", 400)
    
    if new_password != confirm_password:
        return apology("new passwords don't match", 400)
    
    if len(new_password) < 6:
        return apology("password must be at least 6 characters", 400)
    
    if current_password == new_password:
        return apology("new password must be different from current password", 400)
    
    # Verify current password
    user = db.get_user(user_id)
    if not user or not check_password_hash(user["hash"], current_password):
        return apology("current password is incorrect", 403)
    
    # Update password with proper hashing
    new_hash = generate_password_hash(new_password)
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET hash = ? WHERE id = ?", (new_hash, user_id))
    conn.commit()
    conn.close()
    
    flash("Password changed successfully!", "success")
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


@app.route("/settings/delete-account", methods=["POST"])
@login_required
def delete_account():
    """Delete user account and all associated data"""
    user_id = session["user_id"]
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Delete user data in order (respect foreign key constraints)
        # 1. Delete from chat-related tables
        cursor.execute("DELETE FROM chat_messages WHERE room LIKE ?", (f"%user_{user_id}%",))
        
        # 2. Delete from transactions and portfolio
        cursor.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM user_stocks WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM portfolio_snapshots WHERE user_id = ?", (user_id,))
        
        # 3. Delete from league-related tables
        cursor.execute("DELETE FROM league_portfolio WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM league_holdings WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM league_transactions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM league_members WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM league_member_stats WHERE user_id = ?", (user_id,))
        
        # 4. Delete from challenge-related tables
        cursor.execute("DELETE FROM challenge_participants WHERE user_id = ?", (user_id,))
        
        # 5. Delete from social/friend tables
        cursor.execute("DELETE FROM friends WHERE user_id = ? OR friend_id = ?", (user_id, user_id))
        
        # 6. Delete from achievement tables
        cursor.execute("DELETE FROM user_achievements WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM user_badges WHERE user_id = ?", (user_id,))
        
        # 7. Delete from notifications and watchlist
        cursor.execute("DELETE FROM watchlist WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
        
        # 8. Delete the user account itself
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        
        # Clear session
        session.clear()
        
        flash("Your account has been permanently deleted. We're sorry to see you go!", "warning")
        return redirect("/")
    
    except Exception as e:
        logging.error(f"Error deleting account for user {user_id}: {e}")
        flash("Error deleting account. Please try again later.", "danger")
        return redirect("/settings")


# Route to reset cash and analytics
@app.route("/portfolio/reset_cash", methods=["POST"])
@login_required
def reset_cash():
    # Implementation moved to `blueprints/portfolio_bp.py`.
    return redirect(url_for('portfolio.debug_portfolio'))


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
    # Moved to `blueprints/portfolio_bp.py` for better modularity.
    return jsonify({"notice": "moved to blueprints/portfolio_bp.py"})
    

@app.route("/api/market/status")
def api_market_status():
    """Get current market status"""
    try:
        from utils import is_market_hours, format_timestamp, get_user_timezone_offset, convert_time_to_user_tz
        from datetime import datetime, timedelta
        
        # Get user timezone if authenticated
        timezone_offset = None
        if "user_id" in session:
            timezone_offset = get_user_timezone_offset(session["user_id"])
        else:
            timezone_offset = get_user_timezone_offset()  # Default to -5 EST
        
        is_open = is_market_hours()
        current_time = datetime.now()
        next_open = None
        
        if not is_open:
            # Calculate next market open
            if current_time.weekday() >= 5:  # Weekend
                # Calculate days until Monday
                days_until_monday = 7 - current_time.weekday()
                next_open_time = current_time + timedelta(days=days_until_monday)
                next_open_time = next_open_time.replace(hour=9, minute=30, second=0, microsecond=0)
            else:  # Weekday but after hours
                # Market opens tomorrow at 9:30 AM
                next_open_time = current_time + timedelta(days=1)
                next_open_time = next_open_time.replace(hour=9, minute=30, second=0, microsecond=0)
            
            # Convert to user's timezone and format nicely
            user_tz_time = convert_time_to_user_tz(next_open_time, timezone_offset)
            next_open = format_timestamp(user_tz_time, include_time=True)
        
        return jsonify({
            "is_open": is_open,
            "next_open": next_open,
            "current_time": current_time.isoformat(),
            "timezone_offset": timezone_offset
        })
    except Exception as e:
        print(f"Error checking market status: {e}")
        return jsonify({"is_open": True, "next_open": None, "error": str(e)}), 500


@app.route("/api/theme", methods=["POST"])
@login_required
def save_theme():
    """Save user theme preference"""
    try:
        user_id = session["user_id"]
        theme = request.json.get("theme", "dark")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET theme = ? WHERE id = ?", (theme, user_id))
        conn.commit()
        conn.close()
        
        return {"success": True}
    except Exception as e:
        logging.error(f"Error saving theme: {e}")
        return {"success": False, "error": str(e)}, 500


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


# Route to add stock to watchlist
@app.route("/watch", methods=["POST"])
@login_required
def add_to_watchlist():
    user_id = session.get("user_id")
    symbol = request.form.get("symbol", type=str).upper()
    shares = request.form.get("shares", type=int)

    if not symbol:
        flash("Stock symbol is required.", "danger")
        return redirect("/quote")

    db_local = DatabaseManager()
    conn = db_local.get_connection()
    cursor = conn.cursor()
    # Add to watchlist
    cursor.execute("INSERT INTO watchlist (user_id, symbol, shares) VALUES (?, ?, ?) ON CONFLICT(user_id, symbol) DO UPDATE SET shares = excluded.shares", (user_id, symbol, shares))
    conn.commit()
    conn.close()

    flash(f"{symbol} has been added to your watchlist.", "success")
    return redirect("/quote")


@app.route("/api/watchlist/add", methods=["POST"])
def api_add_to_watchlist():
    """API endpoint to add stock to watchlist (JSON)"""
    # Check if user is logged in
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Must be logged in to add to watchlist"}), 401
    
    user_id = session["user_id"]
    data = request.get_json()
    symbol = (data.get("symbol") or "").upper()
    shares = data.get("shares", 1)
    
    if not symbol:
        return jsonify({"success": False, "message": "Stock symbol is required"}), 400
    
    # Verify symbol is valid
    quote = lookup(symbol)
    if not quote:
        return jsonify({"success": False, "message": f"Invalid symbol: {symbol}"}), 400
    
    try:
        db_local = DatabaseManager()
        conn = db_local.get_connection()
        cursor = conn.cursor()
        # Add to watchlist
        cursor.execute(
            "INSERT INTO watchlist (user_id, symbol, shares) VALUES (?, ?, ?) ON CONFLICT(user_id, symbol) DO UPDATE SET shares = excluded.shares",
            (user_id, symbol, shares)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": f"{symbol} added to watchlist",
            "symbol": symbol,
            "name": quote.get("name", symbol)
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error adding to watchlist: {str(e)}"}), 500


@app.route("/api/search")
def api_search():
    """API endpoint for stock search suggestions"""
    query = request.args.get('q', '').strip().upper()
    limit = request.args.get('limit', 15, type=int)
    
    if not query or len(query) < 1:
        return jsonify({"results": []}), 200
    
    try:
        # Use the search_tickers function from helpers
        from helpers import search_tickers
        suggestions = search_tickers(query, limit=limit)
        
        # Format results
        results = [
            {
                "symbol": s.get("symbol", ""),
                "name": s.get("name", "")
            }
            for s in suggestions
        ]
        
        return jsonify({"results": results}), 200
    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({"results": []}), 200


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


@app.route("/news")
@login_required
def news():
    """
    News feed: show general market news and user's tracked symbols.
    Uses cached news when available and falls back to fetching fresh news.
    """
    user_id = session.get('user_id')

    # Get tracked symbols for the user
    try:
        tracked_symbols = db.get_user_news_preferences(user_id)
    except Exception:
        tracked_symbols = []

    # Fetch general market news (cached or fresh)
    try:
        news_articles = get_cached_or_fetch_news(None, db)
    except Exception as e:
        # Fallback to empty list on error
        print(f"Error getting general news: {e}")
        news_articles = []

    # Compute sentiment summary
    sentiment_summary = {
        'positive': {'count': 0, 'percentage': 0},
        'neutral': {'count': 0, 'percentage': 0},
        'negative': {'count': 0, 'percentage': 0}
    }
    total = len(news_articles) or 0
    for a in news_articles:
        label = a.get('sentiment_label') or a.get('sentiment', {}).get('label') or 'neutral'
        if label == 'positive':
            sentiment_summary['positive']['count'] += 1
        elif label == 'negative':
            sentiment_summary['negative']['count'] += 1
        else:
            sentiment_summary['neutral']['count'] += 1

    if total > 0:
        sentiment_summary['positive']['percentage'] = (sentiment_summary['positive']['count'] / total) * 100
        sentiment_summary['neutral']['percentage'] = (sentiment_summary['neutral']['count'] / total) * 100
        sentiment_summary['negative']['percentage'] = (sentiment_summary['negative']['count'] / total) * 100

    return render_template('news.html', news=news_articles, tracked_symbols=tracked_symbols, sentiment_summary=sentiment_summary)


@app.route('/news/<symbol>')
@login_required
def news_for_symbol(symbol):
    """Show news and sentiment for a specific stock symbol."""
    user_id = session.get('user_id')
    sym = (symbol or '').upper()

    # Get symbol news (cached or fresh)
    try:
        articles = get_cached_or_fetch_news(sym, db)
    except Exception as e:
        print(f"Error getting news for {sym}: {e}")
        articles = []

    # Get quote if possible for header
    try:
        quote = lookup(sym)
    except Exception:
        quote = None

    # Aggregate sentiment summary for symbol
    sentiment_summary = {
        'positive': {'count': 0, 'percentage': 0},
        'neutral': {'count': 0, 'percentage': 0},
        'negative': {'count': 0, 'percentage': 0}
    }
    total = len(articles) or 0
    for a in articles:
        label = a.get('sentiment_label') or a.get('sentiment', {}).get('label') or 'neutral'
        if label == 'positive':
            sentiment_summary['positive']['count'] += 1
        elif label == 'negative':
            sentiment_summary['negative']['count'] += 1
        else:
            sentiment_summary['neutral']['count'] += 1

    if total > 0:
        sentiment_summary['positive']['percentage'] = (sentiment_summary['positive']['count'] / total) * 100
        sentiment_summary['neutral']['percentage'] = (sentiment_summary['neutral']['count'] / total) * 100
        sentiment_summary['negative']['percentage'] = (sentiment_summary['negative']['count'] / total) * 100

    return render_template('stock_news.html', news=articles, symbol=sym, quote=quote, sentiment_summary=sentiment_summary)


@app.route('/news/preferences/add', methods=['POST'])
@login_required
def news_preferences_add():
    user_id = session.get('user_id')
    symbol = request.form.get('symbol') or request.json.get('symbol') if request.is_json else request.form.get('symbol')
    if not symbol:
        return redirect(url_for('news'))
    symbol = symbol.upper().strip()
    try:
        db.add_news_preference(user_id, symbol)
    except Exception as e:
        print(f"Error adding news preference: {e}")
    return redirect(url_for('news'))


@app.route('/news/preferences/remove/<symbol>', methods=['POST'])
@login_required
def news_preferences_remove(symbol):
    user_id = session.get('user_id')
    sym = (symbol or '').upper()
    try:
        db.remove_news_preference(user_id, sym)
    except Exception as e:
        print(f"Error removing news preference: {e}")
    return redirect(url_for('news'))


# NOTE: `/explore` route moved to `blueprints/explore_bp.py` and is
# registered as a blueprint during app initialization. Keeping the
# original implementation here would create duplicate route
# registrations, so the implementation now lives in the blueprint.



# NOTE: `/api/chart/<symbol>` moved to `blueprints/api_bp.py` and is
# registered during app initialization. The blueprint provides the
# `/api/chart/<symbol>` endpoint and uses `helpers.get_chart_data`
# (which will read/write Redis cache if configured).


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
    """Show options trading interface (coming soon)"""
    # --- Feature coming soon ---
    # user_id = session["user_id"]
    # positions = db.get_user_options_positions(user_id, status='open')
    # ...
    return render_template("coming_soon.html")


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

def emit_league_activity(league_id, activity):
    """Emit a new league activity to all members in the league"""
    try:
        socketio.emit('league_activity_new', {
            'league_id': league_id,
            'activity': activity
        }, room=f'league_{league_id}')
        
        # Also emit to chat_activity for chat integration
        socketio.emit('chat_activity', activity, room=f'league_{league_id}')
    except Exception as e:
        logging.error(f"Error emitting league activity: {e}")

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logging.info(f"Client connected: {request.sid}")
    
    # Join user-specific room for personalized updates
    user_id = session.get('user_id')
    if user_id:
        join_room(f'user_{user_id}')
        
        # Join league-specific rooms for activity feeds
        user_leagues = db.get_user_leagues(user_id)
        for league in user_leagues:
            join_room(f'league_{league["id"]}')
        
        # Send initial portfolio state based on active context
        try:
            context = get_active_portfolio_context()
            
            # Get cash and stocks based on context
            cash = get_portfolio_cash(user_id, context)
            stocks = get_portfolio_stocks(user_id, context)
            
            # Calculate portfolio value
            portfolio_value = cash
            for stock in stocks:
                q = lookup(stock["symbol"])
                if q:
                    portfolio_value += stock["shares"] * q["price"]
            
            logging.debug(f"DEBUG handle_connect: Sending portfolio_update for context={context}, cash=${cash}, total=${portfolio_value}")
            
            emit('portfolio_update', {
                'cash': cash,
                'total_value': portfolio_value,
                'stocks': [{'symbol': s["symbol"], 'shares': s["shares"]} for s in stocks]
            })
        except Exception as e:
            logging.error(f"Error sending initial portfolio state: {e}")
    emit('connection_response', {'status': 'connected'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection and cleanup subscriptions"""
    logging.info(f"Client disconnected: {request.sid}")
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
    
    logging.info(f"Client {request.sid} subscribed to {symbol}")


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
    logging.info(f"Client {request.sid} unsubscribed from {symbol}")


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
            
            # Get follower's user data
            try:
                follower = db.get_user(follower_id)
                if not follower:
                    logging.warning(f"Follower {follower_id} not found during copy trade execution")
                    continue
                follower_cash = follower['cash']
            except Exception as e:
                logging.error(f"Error fetching follower {follower_id} data: {e}")
                continue
            
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
                # Get follower's holding and execute sell
                follower_holding = db.get_user_stock(follower_id, symbol)
                follower_shares = follower_holding['shares'] if follower_holding else 0
                
                if follower_shares > 0 and copy_shares <= follower_shares:
                    # Record transaction
                    copied_txn_id = db.record_transaction(
                        follower_id, symbol, -copy_shares, price, 'sell',
                        strategy='copy_trade', notes=f'Copied from {db.get_user(trader_id)["username"]}'
                    )
                    
                    # Calculate proceeds
                    trade_value = copy_shares * price
                    proceeds = trade_value  # Simplified - no fees for copy trades
                    
                    # Update cash
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
            logging.error(f"Error executing copy trade for follower {copier['follower_id']}: {e}")
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
                f'You completed "{challenge["name"]}"! Reward: ${reward.get("cash", 0):.2f}',
                f'/challenges/{challenge["id"]}'
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
            
            logging.info(f"Updating prices for {len(symbols)} symbols...")
            
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
            logging.error(f"Error in background price updater: {e}")


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
                logging.info(f"Checking for options expiring on {current_date}...")
                
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
                    logging.info(f"Processing expirations for {len(symbols)} symbols...")
                    
                    # Get current prices
                    current_prices = {}
                    for symbol in symbols:
                        quote = lookup(symbol, force_refresh=True)
                        if quote:
                            current_prices[symbol] = quote['price']
                    
                    # Process expirations
                    processed = db.expire_options(current_date, current_prices)
                    logging.info(f"Processed {processed} options positions")
        
        except Exception as e:
            logging.error(f"Error in options expiration checker: {e}")


# Start background thread for options expiration
expiration_thread = threading.Thread(target=background_options_expiration_checker, daemon=True)
expiration_thread.start()


# Privacy Settings Route
@app.route("/settings/privacy", methods=["POST"])
@login_required
def update_privacy_settings():
    user_id = session.get("user_id")
    
    # Get form values
    profile_visibility = request.form.get("profile_visibility", "public")
    email_visibility = "private" if request.form.get("email_visibility") else "public"
    notifications_enabled = request.form.get("notifications_enabled") is not None
    display_portfolio_publicly = request.form.get("display_portfolio_publicly") is not None
    
    # Build privacy settings dict
    privacy_settings = {
        "profile_visibility": profile_visibility,
        "email_visibility": email_visibility,
        "notifications_enabled": notifications_enabled,
        "display_portfolio_publicly": display_portfolio_publicly
    }
    
    # Update privacy settings in the database
    success = db.update_user_privacy(user_id, privacy_settings)
    
    if success:
        flash("Privacy settings updated successfully!", "success")
    else:
        flash("Error updating privacy settings. Please try again.", "danger")
    
    return redirect("/settings")


@app.route("/settings/preferences", methods=["POST"])
@login_required
def update_preferences():
    """Update user preferences (timezone, etc.)"""
    user_id = session.get("user_id")
    timezone_offset = request.form.get("timezone_offset", "-5")
    
    try:
        timezone_offset = int(timezone_offset)
        # Validate timezone is in reasonable range
        if not -12 <= timezone_offset <= 14:
            timezone_offset = -5  # Default to EST
    except (ValueError, TypeError):
        timezone_offset = -5
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET timezone_offset = ? 
            WHERE id = ?
        """, (timezone_offset, user_id))
        conn.commit()
        conn.close()
        
        flash("Preferences updated successfully!", "success")
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        flash("Error updating preferences. Please try again.", "danger")
    
    return redirect("/settings")


# ===== ADVANCED LEAGUE FEATURES ROUTES =====

@app.route("/api/league/<int:league_id>/h2h/create", methods=["POST"])
@login_required
def api_create_h2h_matchup(league_id):
    """Create a new H2H matchup."""
    try:
        user_id = session.get("user_id")
        data = request.get_json()
        
        opponent_id = data.get("opponent_id")
        duration_days = data.get("duration_days", 7)
        starting_capital = data.get("starting_capital", 10000)
        
        if not opponent_id:
            return jsonify({"error": "Opponent ID required"}), 400
        
        # Verify league membership
        league = db.get_league(league_id)
        if not league:
            return jsonify({"error": "League not found"}), 404
        
        # Create matchup
        matchup_id = advanced_league_db.create_h2h_matchup(
            league_id, user_id, opponent_id, duration_days, starting_capital
        )
        
        # Log activity
        db.add_league_activity(
            league_id=league_id,
            activity_type='h2h_challenge',
            title=f"H2H Challenge Started",
            description=f"Challenge against opponent for {duration_days} days",
            user_id=user_id,
            metadata={"matchup_id": matchup_id, "opponent_id": opponent_id}
        )
        
        return jsonify({"matchup_id": matchup_id, "status": "created"}), 201
    
    except Exception as e:
        logging.error(f"Error creating H2H matchup: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/league/<int:league_id>/h2h/matchups", methods=["GET"])
@login_required
def api_get_user_h2h_matchups(league_id):
    """Get H2H matchups for current user."""
    try:
        user_id = session.get("user_id")
        status = request.args.get("status", "active")
        
        matchups = advanced_league_db.get_user_h2h_matchups(
            user_id, league_id, status=status
        )
        
        # Enrich with user info
        for matchup in matchups:
            if matchup['challenger_id'] == user_id:
                opponent = db.get_user(matchup['opponent_id'])
                matchup['opponent_name'] = opponent.get('username') if opponent else 'Unknown'
                matchup['is_challenger'] = True
            else:
                opponent = db.get_user(matchup['challenger_id'])
                matchup['opponent_name'] = opponent.get('username') if opponent else 'Unknown'
                matchup['is_challenger'] = False
        
        return jsonify({"matchups": matchups}), 200
    
    except Exception as e:
        logging.error(f"Error getting H2H matchups: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/league/<int:league_id>/h2h/leaderboard", methods=["GET"])
@login_required
def api_get_h2h_leaderboard(league_id):
    """Get H2H leaderboard for a league."""
    try:
        leaderboard = advanced_league_db.get_h2h_leaderboard(league_id, limit=50)
        
        return jsonify({
            "leaderboard": leaderboard,
            "league_id": league_id
        }), 200
    
    except Exception as e:
        logging.error(f"Error getting H2H leaderboard: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/league/<int:league_id>/activity-feed/filtered", methods=["GET"])
@login_required
def api_get_filtered_activity_feed(league_id):
    """Get activity feed filtered by category."""
    try:
        category = request.args.get("category", "general")
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
        
        activities = advanced_league_db.get_activity_feed_by_category(
            league_id, category, limit=limit, offset=offset
        )
        
        # Enrich with user info
        for activity in activities:
            if activity['user_id']:
                user = db.get_user(activity['user_id'])
                if user:
                    activity['username'] = user.get('username')
                    activity['user_avatar'] = user.get('avatar_url')
        
        return jsonify({
            "activities": activities,
            "category": category,
            "league_id": league_id
        }), 200
    
    except Exception as e:
        logging.error(f"Error getting filtered activity feed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/league/<int:league_id>/statistics", methods=["GET"])
@login_required
def api_get_league_statistics(league_id):
    """Get comprehensive league statistics."""
    try:
        stats = advanced_league_db.get_league_statistics(league_id)
        
        return jsonify({
            "statistics": stats,
            "league_id": league_id
        }), 200
    
    except Exception as e:
        logging.error(f"Error getting league statistics: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/leagues/<int:league_id>/h2h", methods=["GET"])
@login_required
def league_h2h_matchups(league_id):
    """View H2H matchups page."""
    try:
        user_id = session.get("user_id")
        league = db.get_league(league_id)
        
        if not league:
            return apology("League not found", 404)
        
        # Check membership
        is_member = db.is_league_member(league_id, user_id)
        if not is_member:
            return apology("You are not a member of this league", 403)
        
        # Get user's active matchups
        active_matchups = advanced_league_db.get_user_h2h_matchups(user_id, league_id, status='active')
        completed_matchups = advanced_league_db.get_user_h2h_matchups(user_id, league_id, status='completed', limit=20)
        h2h_leaderboard = advanced_league_db.get_h2h_leaderboard(league_id, limit=50)
        
        # Enrich matchups with opponent info
        for matchup in active_matchups + completed_matchups:
            if matchup['challenger_id'] == user_id:
                opponent = db.get_user(matchup['opponent_id'])
                matchup['opponent_name'] = opponent.get('username') if opponent else 'Unknown'
                matchup['is_challenger'] = True
            else:
                opponent = db.get_user(matchup['challenger_id'])
                matchup['opponent_name'] = opponent.get('username') if opponent else 'Unknown'
                matchup['is_challenger'] = False
        
        league_members = db.get_league_members(league_id)
        
        return render_template(
            "league_h2h.html",
            league=league,
            active_matchups=active_matchups,
            completed_matchups=completed_matchups,
            h2h_leaderboard=h2h_leaderboard,
            league_members=league_members
        )
    
    except Exception as e:
        logging.error(f"Error displaying H2H matchups: {str(e)}")
        return apology(f"Error: {str(e)}", 500)


if __name__ == "__main__":
    # Start APScheduler jobs for leaderboards (manageable, configurable)
    try:
        scheduler = BackgroundScheduler()
        # Global leaderboard every 5 minutes
        scheduler.add_job(compute_and_cache_global_leaderboard, 'interval', minutes=5, id='global_leaderboard')
        # Per-league snapshots every 5 minutes (stagger if desired)
        scheduler.add_job(compute_and_cache_league_leaderboards, 'interval', minutes=5, id='league_leaderboards')
        scheduler.start()
        print("Leaderboard scheduler started (global & leagues every 5 minutes)")
    except Exception as e:
        print("Failed to start leaderboard scheduler:", e)

    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    finally:
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            pass