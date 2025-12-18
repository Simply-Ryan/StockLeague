from flask import Blueprint, jsonify, request
from helpers import get_chart_data, cache_chart_data

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/chart/<path:symbol>')
def api_chart(symbol):
    """Return JSON chart data (prices) for given symbol.

    This blueprint endpoint mirrors the old `/api/chart/<symbol>` route
    and uses `helpers.get_chart_data` which will read from Redis when
    available. After fetching, we attempt to cache the result if Redis
    is configured.
    """
    days = int(request.args.get('days', 30))
    try:
        chart = get_chart_data(symbol, days=days)
        if not chart:
            return jsonify({'prices': []})

        try:
            cache_chart_data(symbol, days=days, chart_data=chart)
        except Exception:
            pass

        return jsonify({'prices': chart.get('prices', [])})
    except Exception as e:
        print(f"Error in api/chart for {symbol}: {e}")
        return jsonify({'prices': []})
