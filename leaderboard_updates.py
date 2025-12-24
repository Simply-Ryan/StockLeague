"""
leaderboard_updates.py

Real-time leaderboard update system using WebSocket.

This module provides functionality to:
- Calculate league leaderboard snapshots
- Broadcast leaderboard updates to league members
- Track leaderboard changes/rank movements
- Cache leaderboard data for performance
"""

import logging
import json
from datetime import datetime
from functools import lru_cache

logger = logging.getLogger(__name__)

# In-memory cache: league_id -> leaderboard_snapshot
_leaderboard_cache = {}

# Track previous state for change detection
_previous_leaderboard_state = {}


def calculate_leaderboard_snapshot(db, league_id, price_lookup_func):
    """
    Calculate current leaderboard snapshot for a league.
    
    Args:
        db: DatabaseManager instance
        league_id: League ID
        price_lookup_func: Function to lookup current stock price
    
    Returns:
        dict with leaderboard data and metadata
    """
    try:
        league = db.get_league(league_id)
        if not league:
            return None
        
        members = db.get_league_members(league_id)
        leaderboard_entries = []
        
        for member in members:
            user_id = member['id']
            
            # Get portfolio for this user in this league
            portfolio = db.get_league_portfolio(league_id, user_id)
            if not portfolio:
                continue
            
            cash = portfolio.get('cash', 0)
            
            # Get all holdings
            holdings = db.get_league_holdings(league_id, user_id)
            
            # Calculate total portfolio value
            stock_value = 0
            holding_details = []
            
            for holding in holdings:
                symbol = holding['symbol']
                shares = holding['shares']
                price = price_lookup_func(symbol) if price_lookup_func else 0
                
                if price:
                    position_value = shares * price
                    stock_value += position_value
                    
                    holding_details.append({
                        'symbol': symbol,
                        'shares': shares,
                        'price': price,
                        'value': position_value
                    })
            
            total_value = cash + stock_value
            
            # Calculate performance metrics
            starting_cash = league.get('starting_cash', 10000.0)
            profit_loss = total_value - starting_cash
            return_pct = (profit_loss / starting_cash * 100) if starting_cash > 0 else 0
            
            leaderboard_entries.append({
                'user_id': user_id,
                'username': member.get('username', 'Unknown'),
                'rank': 0,  # Will be set after sorting
                'total_value': round(total_value, 2),
                'cash': round(cash, 2),
                'stock_value': round(stock_value, 2),
                'profit_loss': round(profit_loss, 2),
                'return_pct': round(return_pct, 2),
                'holdings': holding_details,
                'avatar_url': member.get('avatar_url'),
                'is_admin': member.get('is_admin', False)
            })
        
        # Sort by total value (descending)
        leaderboard_entries.sort(key=lambda x: x['total_value'], reverse=True)
        
        # Assign ranks
        for i, entry in enumerate(leaderboard_entries, 1):
            entry['rank'] = i
        
        snapshot = {
            'league_id': league_id,
            'league_name': league.get('name', 'Unknown League'),
            'timestamp': datetime.now().isoformat(),
            'starting_cash': league.get('starting_cash', 10000.0),
            'leaderboard': leaderboard_entries,
            'member_count': len(leaderboard_entries)
        }
        
        return snapshot
        
    except Exception as e:
        logger.error(f"Error calculating leaderboard snapshot for league {league_id}: {e}", exc_info=True)
        return None


def detect_leaderboard_changes(old_snapshot, new_snapshot):
    """
    Detect changes in leaderboard between two snapshots.
    
    Returns:
        dict with detected changes (rank changes, new entries, etc.)
    """
    if not old_snapshot or not new_snapshot:
        return {'type': 'full_update', 'changes': []}
    
    changes = []
    
    old_by_user = {e['user_id']: e for e in old_snapshot.get('leaderboard', [])}
    new_by_user = {e['user_id']: e for e in new_snapshot.get('leaderboard', [])}
    
    # Detect rank changes
    for user_id, new_entry in new_by_user.items():
        old_entry = old_by_user.get(user_id)
        
        if old_entry is None:
            # New member
            changes.append({
                'type': 'new_member',
                'user_id': user_id,
                'username': new_entry['username'],
                'rank': new_entry['rank']
            })
        elif old_entry['rank'] != new_entry['rank']:
            # Rank changed
            rank_change = old_entry['rank'] - new_entry['rank']  # Positive = improvement
            changes.append({
                'type': 'rank_change',
                'user_id': user_id,
                'username': new_entry['username'],
                'old_rank': old_entry['rank'],
                'new_rank': new_entry['rank'],
                'rank_change': rank_change,
                'movement': 'up' if rank_change > 0 else 'down' if rank_change < 0 else 'same',
                'value_change': new_entry['total_value'] - old_entry['total_value']
            })
        elif old_entry['total_value'] != new_entry['total_value']:
            # Value changed but rank same
            changes.append({
                'type': 'value_change',
                'user_id': user_id,
                'username': new_entry['username'],
                'rank': new_entry['rank'],
                'value_change': new_entry['total_value'] - old_entry['total_value'],
                'old_value': old_entry['total_value'],
                'new_value': new_entry['total_value']
            })
    
    # Detect removed members
    for user_id in old_by_user:
        if user_id not in new_by_user:
            old_entry = old_by_user[user_id]
            changes.append({
                'type': 'member_removed',
                'user_id': user_id,
                'username': old_entry['username']
            })
    
    return {
        'type': 'incremental_update' if changes else 'no_change',
        'changes': changes
    }


def emit_leaderboard_update(socketio, league_id, leaderboard_snapshot, change_summary=None):
    """
    Broadcast leaderboard update to all members in a league.
    
    Args:
        socketio: SocketIO instance
        league_id: League ID
        leaderboard_snapshot: Current leaderboard snapshot
        change_summary: Optional change summary for optimization
    """
    if not leaderboard_snapshot:
        return
    
    try:
        update_data = {
            'league_id': league_id,
            'leaderboard': leaderboard_snapshot['leaderboard'],
            'timestamp': leaderboard_snapshot['timestamp'],
            'member_count': leaderboard_snapshot['member_count']
        }
        
        if change_summary:
            update_data['changes'] = change_summary.get('changes', [])
            update_data['change_type'] = change_summary.get('type', 'full_update')
        
        socketio.emit('leaderboard_update', update_data, room=f'league_{league_id}')
        logger.debug(f"Leaderboard update emitted for league {league_id}")
        
    except Exception as e:
        logger.error(f"Error emitting leaderboard update for league {league_id}: {e}")


def update_and_broadcast_leaderboard(socketio, db, league_id, price_lookup_func):
    """
    Calculate leaderboard, detect changes, and broadcast update to members.
    
    This is the main entry point called after trades execute.
    
    Args:
        socketio: SocketIO instance
        db: DatabaseManager instance
        league_id: League ID
        price_lookup_func: Function to lookup stock prices
    """
    try:
        # Calculate new snapshot
        new_snapshot = calculate_leaderboard_snapshot(db, league_id, price_lookup_func)
        if not new_snapshot:
            logger.warning(f"Could not calculate leaderboard for league {league_id}")
            return
        
        # Get old snapshot for change detection
        old_snapshot = _leaderboard_cache.get(league_id)
        
        # Detect changes
        change_summary = detect_leaderboard_changes(old_snapshot, new_snapshot)
        
        # Cache new snapshot
        _leaderboard_cache[league_id] = new_snapshot
        
        # Emit to clients
        emit_leaderboard_update(socketio, league_id, new_snapshot, change_summary)
        
        logger.info(f"Leaderboard updated for league {league_id} with {len(change_summary.get('changes', []))} changes")
        
    except Exception as e:
        logger.error(f"Error updating and broadcasting leaderboard for league {league_id}: {e}", exc_info=True)


def get_cached_leaderboard(league_id):
    """
    Get cached leaderboard snapshot.
    
    Args:
        league_id: League ID
    
    Returns:
        Leaderboard snapshot dict or None if not cached
    """
    return _leaderboard_cache.get(league_id)


def invalidate_leaderboard_cache(league_id=None):
    """
    Invalidate leaderboard cache.
    
    Args:
        league_id: Specific league to invalidate, or None for all
    """
    if league_id:
        if league_id in _leaderboard_cache:
            del _leaderboard_cache[league_id]
        logger.debug(f"Invalidated leaderboard cache for league {league_id}")
    else:
        _leaderboard_cache.clear()
        logger.debug("Invalidated all leaderboard caches")


def emit_rank_alert(socketio, league_id, user_id, alert_data):
    """
    Emit special alert for significant rank changes.
    
    Args:
        socketio: SocketIO instance
        league_id: League ID
        user_id: User ID affected
        alert_data: Alert information (rank change, new position, etc.)
    """
    try:
        alert_message = {
            'league_id': league_id,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            **alert_data
        }
        
        socketio.emit('rank_alert', alert_message, room=f'league_{league_id}')
        
    except Exception as e:
        logger.error(f"Error emitting rank alert: {e}")


def emit_milestone_alert(socketio, league_id, user_id, milestone_type, milestone_data):
    """
    Emit alert for achievement milestones (e.g., first place, double portfolio value).
    
    Args:
        socketio: SocketIO instance
        league_id: League ID
        user_id: User ID
        milestone_type: Type of milestone ('first_place', 'doubled_value', etc.)
        milestone_data: Additional milestone information
    """
    try:
        message = {
            'league_id': league_id,
            'user_id': user_id,
            'milestone_type': milestone_type,
            'timestamp': datetime.now().isoformat(),
            **milestone_data
        }
        
        socketio.emit('milestone_alert', message, room=f'league_{league_id}')
        
    except Exception as e:
        logger.error(f"Error emitting milestone alert: {e}")


def get_leaderboard_summary(league_id, db, limit=10):
    """
    Get simplified leaderboard summary (top N members).
    
    Args:
        league_id: League ID
        db: DatabaseManager instance
        limit: Number of top members to return
    
    Returns:
        List of top leaderboard entries
    """
    snapshot = _leaderboard_cache.get(league_id)
    if not snapshot:
        return []
    
    leaderboard = snapshot.get('leaderboard', [])
    return [
        {
            'rank': entry['rank'],
            'username': entry['username'],
            'total_value': entry['total_value'],
            'return_pct': entry['return_pct']
        }
        for entry in leaderboard[:limit]
    ]
