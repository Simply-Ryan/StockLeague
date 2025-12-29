"""
Real-Time Updates Service for StockLeague

Manages WebSocket connections and broadcasting of real-time data including:
- Live stock price updates
- Portfolio value changes
- League leaderboard updates
- Trade notifications
- Activity feed updates
- Achievement unlocks

Uses Flask-SocketIO with Redis pub/sub for distributed message delivery.
"""

import json
import logging
from datetime import datetime
from functools import wraps
from typing import Dict, List, Optional, Tuple
from flask import session, request
from flask_socketio import emit, join_room, leave_room, rooms

logger = logging.getLogger(__name__)


class RealtimeUpdatesManager:
    """Manages real-time data broadcasts to connected clients."""

    # Room naming conventions
    ROOM_USER_PREFIX = "user_"
    ROOM_LEAGUE_PREFIX = "league_"
    ROOM_PORTFOLIO_PREFIX = "portfolio_"
    ROOM_LEADERBOARD_PREFIX = "leaderboard_"
    ROOM_ACTIVITY_FEED_PREFIX = "activity_"
    BROADCAST_STOCK_PRICES = "stock_prices"
    BROADCAST_MARKET_STATUS = "market_status"

    def __init__(self):
        """Initialize the realtime updates manager."""
        self.active_users: Dict[str, Dict] = {}
        self.watched_stocks: Dict[str, set] = {}  # user_id -> set of symbols

    def get_user_room(self, user_id: int) -> str:
        """Get the room name for a specific user."""
        return f"{self.ROOM_USER_PREFIX}{user_id}"

    def get_league_room(self, league_id: int) -> str:
        """Get the room name for a specific league."""
        return f"{self.ROOM_LEAGUE_PREFIX}{league_id}"

    def get_portfolio_room(self, user_id: int, context: str = "personal") -> str:
        """Get the room name for a specific portfolio."""
        return f"{self.ROOM_PORTFOLIO_PREFIX}{user_id}_{context}"

    def get_leaderboard_room(self, league_id: int) -> str:
        """Get the room name for a league leaderboard."""
        return f"{self.ROOM_LEADERBOARD_PREFIX}{league_id}"

    def get_activity_feed_room(self, league_id: int) -> str:
        """Get the room name for a league activity feed."""
        return f"{self.ROOM_ACTIVITY_FEED_PREFIX}{league_id}"

    @staticmethod
    def emit_to_user(user_id: int, event: str, data: dict):
        """Emit an event to a specific user."""
        room = RealtimeUpdatesManager().get_user_room(user_id)
        emit(event, data, room=room)

    @staticmethod
    def emit_to_league(league_id: int, event: str, data: dict, exclude_user: Optional[int] = None):
        """Emit an event to all members of a league."""
        room = RealtimeUpdatesManager().get_league_room(league_id)
        emit(event, data, room=room, skip_sid=_get_sid_for_user(exclude_user) if exclude_user else None)

    @staticmethod
    def emit_to_portfolio(user_id: int, event: str, data: dict, context: str = "personal"):
        """Emit an event to portfolio watchers."""
        room = RealtimeUpdatesManager().get_portfolio_room(user_id, context)
        emit(event, data, room=room)

    @staticmethod
    def emit_to_leaderboard(league_id: int, event: str, data: dict):
        """Emit an event to leaderboard watchers."""
        room = RealtimeUpdatesManager().get_leaderboard_room(league_id)
        emit(event, data, room=room)

    @staticmethod
    def emit_to_activity_feed(league_id: int, event: str, data: dict):
        """Emit an event to activity feed watchers."""
        room = RealtimeUpdatesManager().get_activity_feed_room(league_id)
        emit(event, data, room=room)

    @staticmethod
    def broadcast_stock_prices(prices: Dict[str, float]):
        """Broadcast stock prices to all connected clients."""
        emit(
            'stock_price_update',
            {
                'prices': prices,
                'timestamp': datetime.utcnow().isoformat()
            },
            room=RealtimeUpdatesManager.BROADCAST_STOCK_PRICES,
            broadcast=True
        )

    @staticmethod
    def broadcast_market_status(status: str, market_open: bool):
        """Broadcast market status to all connected clients."""
        emit(
            'market_status_update',
            {
                'status': status,
                'market_open': market_open,
                'timestamp': datetime.utcnow().isoformat()
            },
            room=RealtimeUpdatesManager.BROADCAST_MARKET_STATUS,
            broadcast=True
        )


def _get_sid_for_user(user_id: int) -> Optional[str]:
    """Get the session ID for a specific user (for excluding from broadcasts)."""
    # This would need to be implemented based on your session tracking
    return None


class SocketIOEventHandlers:
    """WebSocket event handlers for real-time updates."""

    def __init__(self, socketio):
        """Initialize event handlers."""
        self.socketio = socketio
        self.manager = RealtimeUpdatesManager()
        self.register_handlers()

    def register_handlers(self):
        """Register all Socket.IO event handlers."""
        self.socketio.on_event('connect', self.handle_connect)
        self.socketio.on_event('disconnect', self.handle_disconnect)
        self.socketio.on_event('watch_portfolio', self.handle_watch_portfolio)
        self.socketio.on_event('watch_league', self.handle_watch_league)
        self.socketio.on_event('watch_stock_prices', self.handle_watch_stock_prices)
        self.socketio.on_event('watch_leaderboard', self.handle_watch_leaderboard)
        self.socketio.on_event('watch_activity_feed', self.handle_watch_activity_feed)
        self.socketio.on_event('unwatch_portfolio', self.handle_unwatch_portfolio)
        self.socketio.on_event('unwatch_league', self.handle_unwatch_league)
        self.socketio.on_event('unwatch_stock_prices', self.handle_unwatch_stock_prices)

    def handle_connect(self):
        """Handle client connection."""
        user_id = session.get('user_id')
        sid = request.sid

        if user_id:
            self.manager.active_users[sid] = {
                'user_id': user_id,
                'connected_at': datetime.utcnow(),
                'rooms': set()
            }
            logger.info(f"User {user_id} connected with SID {sid}")
            emit('connection_confirmed', {'user_id': user_id, 'sid': sid})
        else:
            logger.debug(f"Guest connected with SID {sid}")

    def handle_disconnect(self):
        """Handle client disconnection."""
        sid = request.sid
        if sid in self.manager.active_users:
            user_id = self.manager.active_users[sid]['user_id']
            logger.info(f"User {user_id} disconnected")
            del self.manager.active_users[sid]

    def handle_watch_portfolio(self, data):
        """Handle portfolio watch request."""
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Not authenticated'})
            return

        target_user_id = data.get('user_id', user_id)
        context = data.get('context', 'personal')

        # Verify access (user can only watch their own portfolio or if league member)
        if target_user_id != user_id:
            # Check if they're in the same league as target user
            # This would require database access - implement based on your schema
            pass

        room = self.manager.get_portfolio_room(target_user_id, context)
        join_room(room)
        self.manager.active_users[request.sid]['rooms'].add(room)

        emit('portfolio_watch_confirmed', {
            'user_id': target_user_id,
            'context': context,
            'room': room
        })
        logger.info(f"User {user_id} watching portfolio {target_user_id} ({context})")

    def handle_watch_league(self, data):
        """Handle league watch request."""
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Not authenticated'})
            return

        league_id = data.get('league_id')
        if not league_id:
            emit('error', {'message': 'league_id required'})
            return

        room = self.manager.get_league_room(league_id)
        join_room(room)
        self.manager.active_users[request.sid]['rooms'].add(room)

        emit('league_watch_confirmed', {
            'league_id': league_id,
            'room': room
        })
        logger.info(f"User {user_id} watching league {league_id}")

    def handle_watch_stock_prices(self, data):
        """Handle stock price watching request."""
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Not authenticated'})
            return

        symbols = data.get('symbols', [])
        if not symbols:
            emit('error', {'message': 'symbols required'})
            return

        join_room(self.manager.BROADCAST_STOCK_PRICES)
        self.manager.watched_stocks.setdefault(user_id, set()).update(symbols)

        emit('stock_watch_confirmed', {
            'symbols': symbols,
            'room': self.manager.BROADCAST_STOCK_PRICES
        })
        logger.info(f"User {user_id} watching stocks: {symbols}")

    def handle_watch_leaderboard(self, data):
        """Handle leaderboard watch request."""
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Not authenticated'})
            return

        league_id = data.get('league_id')
        if not league_id:
            emit('error', {'message': 'league_id required'})
            return

        room = self.manager.get_leaderboard_room(league_id)
        join_room(room)
        self.manager.active_users[request.sid]['rooms'].add(room)

        emit('leaderboard_watch_confirmed', {
            'league_id': league_id,
            'room': room
        })
        logger.info(f"User {user_id} watching leaderboard {league_id}")

    def handle_watch_activity_feed(self, data):
        """Handle activity feed watch request."""
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Not authenticated'})
            return

        league_id = data.get('league_id')
        if not league_id:
            emit('error', {'message': 'league_id required'})
            return

        room = self.manager.get_activity_feed_room(league_id)
        join_room(room)
        self.manager.active_users[request.sid]['rooms'].add(room)

        emit('activity_feed_watch_confirmed', {
            'league_id': league_id,
            'room': room
        })
        logger.info(f"User {user_id} watching activity feed {league_id}")

    def handle_unwatch_portfolio(self, data):
        """Handle portfolio unwatch request."""
        user_id = session.get('user_id')
        target_user_id = data.get('user_id', user_id)
        context = data.get('context', 'personal')

        room = self.manager.get_portfolio_room(target_user_id, context)
        leave_room(room)
        if request.sid in self.manager.active_users:
            self.manager.active_users[request.sid]['rooms'].discard(room)

        emit('portfolio_unwatch_confirmed', {
            'user_id': target_user_id,
            'context': context
        })
        logger.info(f"User {user_id} unwatching portfolio {target_user_id}")

    def handle_unwatch_league(self, data):
        """Handle league unwatch request."""
        user_id = session.get('user_id')
        league_id = data.get('league_id')

        room = self.manager.get_league_room(league_id)
        leave_room(room)
        if request.sid in self.manager.active_users:
            self.manager.active_users[request.sid]['rooms'].discard(room)

        emit('league_unwatch_confirmed', {'league_id': league_id})
        logger.info(f"User {user_id} unwatching league {league_id}")

    def handle_unwatch_stock_prices(self, data):
        """Handle stock price unwatch request."""
        user_id = session.get('user_id')
        symbols = data.get('symbols', [])

        if user_id in self.manager.watched_stocks:
            self.manager.watched_stocks[user_id].difference_update(symbols)

        emit('stock_unwatch_confirmed', {'symbols': symbols})
        logger.info(f"User {user_id} unwatching stocks: {symbols}")


def init_realtime_updates(socketio, app):
    """Initialize real-time updates system."""
    handlers = SocketIOEventHandlers(socketio)
    manager = RealtimeUpdatesManager()
    
    # Attach manager to app for easy access
    app.realtime_manager = manager
    
    return manager, handlers


# Client-side helper function template
REALTIME_CLIENT_CODE = """
// StockLeague Real-Time Updates - Client-side helper

const RealtimeClient = {
    socket: null,
    
    init: function() {
        this.socket = io();
        this.setupEventHandlers();
    },
    
    setupEventHandlers: function() {
        this.socket.on('connect', () => {
            console.log('Connected to real-time updates');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from real-time updates');
        });
        
        this.socket.on('error', (data) => {
            console.error('Real-time error:', data.message);
        });
        
        // Portfolio updates
        this.socket.on('portfolio_update', (data) => {
            console.log('Portfolio updated:', data);
            // Update portfolio display
            updatePortfolioDisplay(data);
        });
        
        // Stock price updates
        this.socket.on('stock_price_update', (data) => {
            console.log('Stock prices updated:', data.prices);
            // Update price display
            updateStockPrices(data.prices);
        });
        
        // Leaderboard updates
        this.socket.on('leaderboard_update', (data) => {
            console.log('Leaderboard updated:', data);
            // Update leaderboard display
            updateLeaderboard(data);
        });
        
        // Activity feed updates
        this.socket.on('activity_feed_update', (data) => {
            console.log('Activity feed updated:', data);
            // Update activity feed
            updateActivityFeed(data);
        });
        
        // Trade notifications
        this.socket.on('trade_executed', (data) => {
            console.log('Trade executed:', data);
            // Show notification
            showTradeNotification(data);
        });
    },
    
    watchPortfolio: function(userId = null, context = 'personal') {
        this.socket.emit('watch_portfolio', {
            user_id: userId,
            context: context
        });
    },
    
    watchLeague: function(leagueId) {
        this.socket.emit('watch_league', {
            league_id: leagueId
        });
    },
    
    watchStockPrices: function(symbols) {
        this.socket.emit('watch_stock_prices', {
            symbols: symbols
        });
    },
    
    watchLeaderboard: function(leagueId) {
        this.socket.emit('watch_leaderboard', {
            league_id: leagueId
        });
    },
    
    watchActivityFeed: function(leagueId) {
        this.socket.emit('watch_activity_feed', {
            league_id: leagueId
        });
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    RealtimeClient.init();
});
"""
