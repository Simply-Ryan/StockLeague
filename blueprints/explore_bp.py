from flask import Blueprint, render_template, session, request, jsonify
from helpers import get_popular_stocks, get_market_movers, get_market_indices, get_volume_leaders
from database.db_manager import DatabaseManager

explore_bp = Blueprint('explore', __name__)

db = DatabaseManager()


@explore_bp.route('/explore')
def explore():
    """Explore page: market movers, popular stocks, and indices.

    This blueprint keeps the same behavior as the original `/explore`
    route but is split out to improve maintainability.
    
    Optimization: Initial load is lightweight, with lazy-loading via API for additional data.
    """
    user_id = session.get('user_id')

    # Market data - optimized initial load
    try:
        popular = get_popular_stocks(limit=5)  # Reduce from 8 to 5 for faster initial load
    except Exception:
        popular = []

    try:
        movers = get_market_movers(limit=3)  # Reduce from 5 to 3 per side for faster load
    except Exception:
        movers = {'gainers': [], 'losers': []}

    # Market indices summary
    try:
        market_indices = get_market_indices()
    except Exception:
        market_indices = []

    # Build a short market summary (simple heuristic)
    try:
        up = 0
        down = 0
        for idx in market_indices:
            if idx.get('change', 0) > 0:
                up += 1
            elif idx.get('change', 0) < 0:
                down += 1
        if up > down:
            market_trend = 'up'
        elif down > up:
            market_trend = 'down'
        else:
            market_trend = 'mixed'
    except Exception:
        market_trend = 'mixed'

    popular_symbols = [p.get('symbol') for p in popular if p.get('symbol')]
    index_symbols = [idx.get('symbol') for idx in market_indices if idx.get('symbol')]

    # Volume leaders - reduce to 5 for initial load
    try:
        volume_leaders = get_volume_leaders(limit=5)
    except Exception:
        volume_leaders = []

    return render_template('explore.html',
                           popular_stocks=popular,
                           market_movers=movers,
                           market_indices=market_indices,
                           market_trend=market_trend,
                           popular_symbols=popular_symbols,
                           index_symbols=index_symbols,
                           volume_leaders=volume_leaders)


# Pagination API endpoints for lazy-loading
@explore_bp.route('/api/explore/popular')
def api_explore_popular():
    """Get popular stocks with pagination"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    try:
        # Get all popular stocks (cached)
        all_stocks = get_popular_stocks(limit=20)  # Get up to 20 total
        
        # Simple pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        paginated = all_stocks[start_idx:end_idx]
        has_more = end_idx < len(all_stocks)
        
        return jsonify({
            'stocks': paginated,
            'page': page,
            'has_more': has_more,
            'total': len(all_stocks)
        })
    except Exception as e:
        print(f"Error in api_explore_popular: {e}")
        return jsonify({'stocks': [], 'error': str(e)}), 500


@explore_bp.route('/api/explore/movers')
def api_explore_movers():
    """Get market movers with pagination"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    mover_type = request.args.get('type', 'gainers')  # 'gainers' or 'losers'
    
    try:
        # Get all movers (cached)
        all_movers = get_market_movers(limit=10)  # Get up to 10 per side
        movers_list = all_movers.get(mover_type, [])
        
        # Simple pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        paginated = movers_list[start_idx:end_idx]
        has_more = end_idx < len(movers_list)
        
        return jsonify({
            'movers': paginated,
            'type': mover_type,
            'page': page,
            'has_more': has_more,
            'total': len(movers_list)
        })
    except Exception as e:
        print(f"Error in api_explore_movers: {e}")
        return jsonify({'movers': [], 'error': str(e)}), 500


@explore_bp.route('/api/explore/volume')
def api_explore_volume():
    """Get volume leaders with pagination"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    try:
        # Get all volume leaders (cached)
        all_leaders = get_volume_leaders(limit=20)  # Get up to 20 total
        
        # Simple pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        paginated = all_leaders[start_idx:end_idx]
        has_more = end_idx < len(all_leaders)
        
        return jsonify({
            'leaders': paginated,
            'page': page,
            'has_more': has_more,
            'total': len(all_leaders)
        })
    except Exception as e:
        print(f"Error in api_explore_volume: {e}")
        return jsonify({'leaders': [], 'error': str(e)}), 500
