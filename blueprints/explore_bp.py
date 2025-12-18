from flask import Blueprint, render_template, session
from helpers import get_popular_stocks, get_market_movers, get_market_indices, get_volume_leaders
from database.db_manager import DatabaseManager

explore_bp = Blueprint('explore', __name__)

db = DatabaseManager()


@explore_bp.route('/explore')
def explore():
    """Explore page: market movers, popular stocks, and indices.

    This blueprint keeps the same behavior as the original `/explore`
    route but is split out to improve maintainability.
    """
    user_id = session.get('user_id')

    # Market data
    try:
        popular = get_popular_stocks()
    except Exception:
        popular = []

    try:
        movers = get_market_movers()
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

    # Volume leaders (show on explore page)
    try:
        volume_leaders = get_volume_leaders()
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
