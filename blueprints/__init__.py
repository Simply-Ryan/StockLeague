"""
Blueprint package for modular route groups.

This package contains all Flask blueprints for StockLeague, organized by domain:
- auth_bp: User authentication (login, register, logout)
- portfolio_bp: Personal portfolio management
- trades_bp: Buy/sell/trade operations
- leagues_bp: League management and operations
- chat_bp: Real-time chat messaging
- explore_bp: Stock exploration and discovery
- api_bp: RESTful API endpoints
"""

# Re-export all blueprints for easy access
try:
    from blueprints.auth_bp import auth_bp
except ImportError:
    auth_bp = None

try:
    from blueprints.portfolio_bp import portfolio_bp
except ImportError:
    portfolio_bp = None

try:
    from blueprints.trades_bp import trades_bp
except ImportError:
    trades_bp = None

try:
    from blueprints.leagues_bp import leagues_bp
except ImportError:
    leagues_bp = None

try:
    from blueprints.chat_bp import chat_bp, register_chat_events
except ImportError:
    chat_bp = None
    register_chat_events = None

try:
    from blueprints.explore_bp import explore_bp
except ImportError:
    explore_bp = None

try:
    from blueprints.api_bp import api_bp
except ImportError:
    api_bp = None


__all__ = [
    'auth_bp',
    'portfolio_bp',
    'trades_bp',
    'leagues_bp',
    'chat_bp',
    'register_chat_events',
    'explore_bp',
    'api_bp',
]
