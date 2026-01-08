"""
Chat Blueprint - handles real-time messaging and chat functionality.
Extracted from main app.py for modularity.
"""

from flask import Blueprint, request, session, jsonify, render_template, redirect
from flask_socketio import SocketIO, emit, join_room, leave_room
from functools import wraps
from datetime import datetime
import logging

from helpers import apology
from database.db_manager import DatabaseManager

chat_bp = Blueprint("chat", __name__)
logger = logging.getLogger(__name__)

# Will be injected by app
socketio = None


def set_socketio(sio):
    """Inject SocketIO instance."""
    global socketio
    socketio = sio


def login_required(f):
    """Decorator that redirects to login if user is not authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@chat_bp.route("/chat")
@login_required
def chat():
    """Main chat interface."""
    user_id = session["user_id"]
    db = DatabaseManager()
    
    try:
        user = db.get_user(user_id)
        if not user:
            return apology("User not found", 404)
        
        # Get recent conversations
        conversations = db.get_user_conversations(user_id)
        
        return render_template("chat.html", user=user, conversations=conversations)
    except Exception as e:
        logger.error(f"Error loading chat: {e}")
        return apology("Error loading chat", 500)


@chat_bp.route("/chat/settings")
@login_required
def chat_settings():
    """Chat settings page."""
    return render_template("chat_settings.html")


@chat_bp.route("/api/conversations")
@login_required
def api_conversations():
    """Get list of conversations as JSON."""
    user_id = session["user_id"]
    db = DatabaseManager()
    
    try:
        conversations = db.get_user_conversations(user_id)
        return jsonify({
            "success": True,
            "conversations": conversations
        })
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        return jsonify({"error": "Error fetching conversations"}), 500


# WebSocket event handlers (requires socketio to be injected)

def register_chat_events(sio):
    """Register all chat-related WebSocket events."""
    
    @sio.on('join_room')
    def handle_join_room(data):
        """Join a chat room."""
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Not authenticated'})
            return
        
        room_id = data.get('room_id')
        username = data.get('username')
        
        if not room_id:
            emit('error', {'message': 'Room ID required'})
            return
        
        try:
            # Verify user has access to room
            db = DatabaseManager()
            room = db.get_chat_room(room_id)
            if not room:
                emit('error', {'message': 'Room not found'})
                return
            
            # Check membership if private
            if room.get('is_private'):
                member = db.get_room_member(room_id, user_id)
                if not member:
                    emit('error', {'message': 'Access denied'})
                    return
            
            # Join the room
            join_room(f'chat_{room_id}')
            
            # Get chat history
            messages = db.get_chat_history(room_id, limit=100)
            
            # Notify other users
            emit('user_joined', {
                'username': username,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }, room=f'chat_{room_id}', skip_sid=True)
            
            # Send history to joining user
            emit('chat_history', {
                'room_id': room_id,
                'messages': messages
            })
            
            logger.info(f"User {user_id} joined room {room_id}")
        except Exception as e:
            logger.error(f"Error joining room: {e}")
            emit('error', {'message': 'Error joining room'})
    
    
    @sio.on('leave_room')
    def handle_leave_room(data):
        """Leave a chat room."""
        user_id = session.get('user_id')
        room_id = data.get('room_id')
        username = data.get('username')
        
        if not user_id or not room_id:
            return
        
        try:
            leave_room(f'chat_{room_id}')
            emit('user_left', {
                'username': username,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }, room=f'chat_{room_id}')
            
            logger.info(f"User {user_id} left room {room_id}")
        except Exception as e:
            logger.error(f"Error leaving room: {e}")
    
    
    @sio.on('chat_message')
    def handle_chat_message(data):
        """Handle incoming chat message."""
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Not authenticated'})
            return
        
        room_id = data.get('room_id')
        message_text = data.get('message', '').strip()
        
        if not room_id or not message_text:
            emit('error', {'message': 'Invalid message'})
            return
        
        try:
            db = DatabaseManager()
            
            # Verify access
            room = db.get_chat_room(room_id)
            if not room:
                emit('error', {'message': 'Room not found'})
                return
            
            # Store message
            message_id = db.store_chat_message(room_id, user_id, message_text)
            
            user = db.get_user(user_id)
            
            # Broadcast to room
            emit('new_message', {
                'message_id': message_id,
                'room_id': room_id,
                'user_id': user_id,
                'username': user['username'] if user else 'Unknown',
                'message': message_text,
                'timestamp': datetime.now().isoformat()
            }, room=f'chat_{room_id}')
            
            logger.debug(f"Message {message_id} sent to room {room_id}")
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
            emit('error', {'message': 'Error sending message'})
    
    
    @sio.on('typing')
    def handle_typing(data):
        """Notify others that user is typing."""
        user_id = session.get('user_id')
        room_id = data.get('room_id')
        username = data.get('username')
        
        if user_id and room_id:
            emit('user_typing', {
                'username': username,
                'user_id': user_id
            }, room=f'chat_{room_id}', skip_sid=True)
    
    
    @sio.on('disconnect')
    def handle_disconnect():
        """Handle user disconnect."""
        user_id = session.get('user_id')
        logger.info(f"User {user_id} disconnected")
