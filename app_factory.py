"""
Application Factory for StockLeague.

This module implements the Flask Application Factory pattern, allowing for
better testing, configuration management, and multi-environment support.

Usage:
    # In app.py or wsgi.py
    from app_factory import create_app
    
    app = create_app(config_name='production')
    socketio.run(app, debug=False)

Benefits:
    - Multiple app instances for testing
    - Environment-specific configuration
    - Extension initialization deferred
    - Easier to test with different configs
    - Following Flask best practices
"""

import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask
from flask_session import Session
from flask_socketio import SocketIO

# Redis imports
try:
    import redis
    from redis import ConnectionPool, Redis
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Local imports
from helpers import usd
from database.db_manager import DatabaseManager
from error_handlers import (
    DatabaseError, ValidationError, NotFoundError, PermissionError, RateLimitError
)
from performance_monitoring import PerformanceMonitor
from admin_monitoring import SystemMetrics, UserActivityMonitor, AlertManager, HealthChecker
from portfolio_analytics import ComprehensiveAnalytics
from audit_logger import AuditLogger
from query_performance_tracker import QueryPerformanceTracker


def get_config(config_name='development'):
    """Get configuration dictionary for the specified environment."""
    base_config = {
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
        'SESSION_PERMANENT': False,
        'SESSION_TYPE': 'filesystem',
        'SESSION_SQLALCHEMY_TABLE': 'sessions',
        'TEMPLATES_AUTO_RELOAD': True,
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB max upload
    }
    
    if config_name == 'production':
        base_config.update({
            'DEBUG': False,
            'TESTING': False,
            'PROPAGATE_EXCEPTIONS': False,
            'SECRET_KEY': os.environ.get('SECRET_KEY', os.urandom(32).hex()),
        })
    elif config_name == 'testing':
        base_config.update({
            'DEBUG': True,
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SESSION_TYPE': 'memory',
        })
    else:  # development
        base_config.update({
            'DEBUG': True,
            'TESTING': False,
            'TEMPLATES_AUTO_RELOAD': True,
        })
    
    return base_config


def setup_logging():
    """Configure logging for the application."""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def register_error_handlers(app):
    """Register error handlers with the Flask app."""
    
    @app.errorhandler(DatabaseError)
    def handle_database_error(error):
        from helpers import apology
        return apology(f"Database error: {error}", 500)
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        from helpers import apology
        return apology(f"Validation error: {error}", 400)
    
    @app.errorhandler(NotFoundError)
    def handle_not_found_error(error):
        from helpers import apology
        return apology(f"Not found: {error}", 404)
    
    @app.errorhandler(PermissionError)
    def handle_permission_error(error):
        from helpers import apology
        return apology(f"Permission denied: {error}", 403)
    
    @app.errorhandler(RateLimitError)
    def handle_rate_limit_error(error):
        from helpers import apology
        return apology(f"Rate limit exceeded: {error}", 429)
    
    @app.errorhandler(400)
    def bad_request(error):
        from helpers import apology
        return apology("Bad request", 400)
    
    @app.errorhandler(404)
    def not_found(error):
        from helpers import apology
        return apology("Page not found", 404)
    
    @app.errorhandler(500)
    def internal_error(error):
        from helpers import apology
        return apology("Internal server error", 500)


def register_jinja_filters(app):
    """Register Jinja2 filters and globals."""
    # Filters
    app.jinja_env.filters["usd"] = usd
    app.jinja_env.filters["abs"] = abs
    app.jinja_env.filters["min"] = min
    app.jinja_env.filters["max"] = max
    
    # Timestamp filter
    def jinja_format_timestamp(dt, include_time=False):
        """Jinja2 filter for formatting timestamps."""
        if not dt:
            return ""
        from utils import format_timestamp, get_user_timezone_offset
        from flask import session
        
        tz_offset = None
        if "user_id" in session:
            tz_offset = get_user_timezone_offset(session["user_id"])
        
        return format_timestamp(dt, include_time=include_time, timezone_offset=tz_offset or -5)
    
    app.jinja_env.filters["format_timestamp"] = jinja_format_timestamp
    
    # Lazy load image filter
    def lazy_load_image(src, alt="Image", width=None, height=None, css_class=""):
        """Jinja2 filter for creating lazy-loaded image tags."""
        if not src:
            return ""
        
        width_attr = f' width="{width}"' if width else ''
        height_attr = f' height="{height}"' if height else ''
        class_attr = f' class="{css_class}"' if css_class else ''
        
        return f'<img src="{src}" alt="{alt}"{width_attr}{height_attr}{class_attr} loading="lazy">'
    
    app.jinja_env.filters["lazy_image"] = lazy_load_image
    
    # Globals
    app.jinja_env.globals.update(abs=abs, min=min, max=max)


def register_blueprints(app, logger):
    """Register all Flask blueprints."""
    try:
        from blueprints.explore_bp import explore_bp
        from blueprints.api_bp import api_bp
        from blueprints.auth_bp import auth_bp
        from blueprints.portfolio_bp import portfolio_bp
        from blueprints.trades_bp import trades_bp
        from blueprints.leagues_bp import leagues_bp
        from blueprints.chat_bp import chat_bp, register_chat_events
        
        # Register core blueprints
        app.register_blueprint(explore_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(portfolio_bp)
        app.register_blueprint(trades_bp)
        app.register_blueprint(leagues_bp)
        app.register_blueprint(chat_bp)
        
        logger.info("✓ Core blueprints registered")
        
        return register_chat_events
    except ImportError as e:
        logger.warning(f"Could not import core blueprints: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error registering blueprints: {e}")
        return None


def register_specialized_blueprints(app, logger, db, audit_logger, 
                                   system_metrics, user_activity_monitor, 
                                   alert_manager, health_checker):
    """Register specialized blueprints (audit, monitoring, engagement)."""
    try:
        from audit_routes import create_audit_blueprint
        from admin_monitoring_routes import create_admin_monitoring_blueprint
        from engagement_routes import register_engagement_routes
        
        # Audit blueprint
        audit_bp = create_audit_blueprint(db, audit_logger)
        app.register_blueprint(audit_bp)
        
        # Admin monitoring blueprint
        monitoring_bp = create_admin_monitoring_blueprint(
            db, system_metrics, user_activity_monitor, alert_manager, health_checker
        )
        app.register_blueprint(monitoring_bp)
        
        # Engagement routes
        register_engagement_routes(app)
        
        logger.info("✓ Specialized blueprints registered")
    except ImportError as e:
        logger.warning(f"Could not import specialized blueprints: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error with specialized blueprints: {e}")


def setup_redis_cache(logger):
    """
    Setup Redis cache with connection pooling and error handling.
    
    Returns:
        tuple: (redis_client, cache_manager, cache_invalidator)
               All will be None if Redis unavailable
    """
    if not REDIS_AVAILABLE:
        logger.warning("⚠ redis-py not installed. Run: pip install redis")
        return None, None, None
    
    try:
        # Create connection pool
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_pool = ConnectionPool.from_url(
            redis_url,
            decode_responses=True,
            max_connections=10,
            socket_connect_timeout=5,
            socket_keepalive=True,
            socket_keepalive_options={
                1: 1,  # TCP_KEEPIDLE
                2: 3,  # TCP_KEEPINTVL
                3: 5,  # TCP_KEEPCNT
            } if hasattr(redis_pool, 'socket_keepalive_options') else None
        )
        
        # Create Redis client
        redis_client = Redis(connection_pool=redis_pool)
        
        # Test connection
        redis_client.ping()
        logger.info(f"✓ Redis connected successfully ({redis_url})")
        
        # Initialize cache manager
        from redis_cache_manager import CacheManager, CacheInvalidator, WarmCacheScheduler
        cache_manager = CacheManager(redis_client)
        cache_invalidator = CacheInvalidator(cache_manager)
        
        logger.info("✓ Cache manager initialized")
        
        return redis_client, cache_manager, cache_invalidator
        
    except (RedisError, RedisConnectionError, ConnectionError) as e:
        logger.warning(f"⚠ Redis connection failed: {e}")
        logger.info("  - Falling back to no-cache mode")
        logger.info("  - To use Redis, ensure: redis-server is running, or REDIS_URL is correct")
        
        # Return None values - app will work without cache
        from redis_cache_manager import CacheManager, CacheInvalidator
        
        # Create dummy cache manager that doesn't cache
        cache_manager = CacheManager(None)
        cache_invalidator = CacheInvalidator(cache_manager)
        
        return None, cache_manager, cache_invalidator
        
    except Exception as e:
        logger.error(f"✗ Unexpected Redis setup error: {e}")
        from redis_cache_manager import CacheManager, CacheInvalidator
        cache_manager = CacheManager(None)
        cache_invalidator = CacheInvalidator(cache_manager)
        return None, cache_manager, cache_invalidator


def setup_websocket(app, logger):
    """Setup Flask-SocketIO."""
    try:
        socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
        
        # Register WebSocket events
        from realtime_updates import SocketIOEventHandlers
        socketio_handlers = SocketIOEventHandlers(socketio)
        
        logger.info("✓ WebSocket configured")
        return socketio, socketio_handlers
    except Exception as e:
        logger.error(f"Failed to configure WebSocket: {e}")
        return None, None


def setup_scheduler(app, logger, socketio):
    """Setup APScheduler background jobs."""
    try:
        from leaderboard_updates import (
            compute_and_cache_global_leaderboard,
            compute_and_cache_league_leaderboards,
            broadcast_stock_prices
        )
        
        scheduler = BackgroundScheduler()
        
        # Global leaderboard every 5 minutes
        scheduler.add_job(
            compute_and_cache_global_leaderboard,
            'interval',
            minutes=5,
            id='global_leaderboard'
        )
        
        # Per-league leaderboards every 5 minutes
        scheduler.add_job(
            compute_and_cache_league_leaderboards,
            'interval',
            minutes=5,
            id='league_leaderboards'
        )
        
        # Stock prices every 5 seconds
        scheduler.add_job(
            broadcast_stock_prices,
            'interval',
            seconds=5,
            id='broadcast_stock_prices'
        )
        
        scheduler.start()
        logger.info("✓ Background scheduler started")
        return scheduler
    except Exception as e:
        logger.warning(f"Failed to start scheduler: {e}")
        return None


def create_app(config_name='development'):
    """
    Application factory function.
    
    Creates and configures a Flask application instance with all extensions,
    blueprints, error handlers, and background tasks.
    
    Args:
        config_name (str): Configuration to use ('development', 'testing', 'production')
    
    Returns:
        Flask: Configured Flask application instance
    
    Example:
        app = create_app('production')
        socketio.run(app)
    """
    # Setup logging
    logger = setup_logging()
    logger.info(f"Creating StockLeague app with config: {config_name}")
    
    # Create Flask app
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Load configuration
    config = get_config(config_name)
    app.config.update(config)
    logger.info(f"✓ Configuration loaded: {len(config)} settings")
    
    # Initialize session
    Session(app)
    logger.info("✓ Session configured")
    
    # Register Jinja2 filters
    register_jinja_filters(app)
    logger.info("✓ Jinja2 filters registered")
    
    # Register error handlers
    register_error_handlers(app)
    logger.info("✓ Error handlers registered")
    
    # Initialize database
    try:
        db = DatabaseManager()
        logger.info("✓ Database initialized")
        app.db = db
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Setup Redis cache
    try:
        redis_client, cache_manager, cache_invalidator = setup_redis_cache(logger)
        app.redis_client = redis_client
        app.cache = cache_manager
        app.cache_invalidator = cache_invalidator
        logger.info("✓ Cache system initialized")
    except Exception as e:
        logger.warning(f"Cache setup error: {e}")
        # Initialize dummy cache manager for fallback
        from redis_cache_manager import CacheManager, CacheInvalidator
        app.cache = CacheManager(None)
        app.cache_invalidator = CacheInvalidator(app.cache)
    
    # Setup monitoring and auditing
    system_metrics = None
    user_activity_monitor = None
    alert_manager = None
    health_checker = None
    perf_monitor = None
    audit_logger = None
    query_tracker = None
    
    try:
        system_metrics = SystemMetrics(db)
        user_activity_monitor = UserActivityMonitor(db)
        alert_manager = AlertManager()
        health_checker = HealthChecker(db)
        perf_monitor = PerformanceMonitor()
        audit_logger = AuditLogger(db)
        query_tracker = QueryPerformanceTracker(slow_query_threshold_ms=100)  # TIER 7: Query monitoring
        
        logger.info("✓ Monitoring and auditing initialized")
        
        app.system_metrics = system_metrics
        app.user_activity_monitor = user_activity_monitor
        app.alert_manager = alert_manager
        app.health_checker = health_checker
        app.perf_monitor = perf_monitor
        app.audit_logger = audit_logger
        app.query_tracker = query_tracker  # TIER 7: Query performance tracking
    except Exception as e:
        logger.warning(f"Could not initialize monitoring: {e}")
    
    # Register blueprints
    register_chat_events = register_blueprints(app, logger)
    
    # Register specialized blueprints
    register_specialized_blueprints(app, logger, db, audit_logger,
                                   system_metrics, user_activity_monitor,
                                   alert_manager, health_checker)
    
    # Setup WebSocket
    socketio, socketio_handlers = setup_websocket(app, logger)
    if socketio and register_chat_events:
        try:
            register_chat_events(socketio)
            logger.info("✓ Chat WebSocket events registered")
        except Exception as e:
            logger.warning(f"Could not register chat events: {e}")
    
    app.socketio = socketio
    app.socketio_handlers = socketio_handlers
    
    # Setup scheduler (only in non-testing environments)
    if config_name != 'testing':
        scheduler = setup_scheduler(app, logger, socketio)
        app.scheduler = scheduler
    
    # Context processor for portfolio
    @app.context_processor
    def inject_portfolio_context():
        """Inject portfolio context into templates."""
        from flask import session
        context = session.get("portfolio_context")
        if not context:
            context = {"type": "personal", "league_id": None, "league_name": None}
        return {
            "portfolio_context": context,
            "context_type": context.get("type"),
            "context_league_id": context.get("league_id"),
            "context_league_name": context.get("league_name"),
        }
    
    # After request handler
    @app.after_request
    def after_request(response):
        """Add security headers after each request."""
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = "0"
        response.headers["Pragma"] = "no-cache"
        return response
    
    logger.info("=" * 60)
    logger.info(f"✓ StockLeague app created successfully ({config_name})")
    logger.info(f"✓ Total routes: {len([r for r in app.url_map.iter_rules()])}")
    logger.info("=" * 60)
    
    return app


if __name__ == '__main__':
    # For development/testing
    app = create_app('development')
    if hasattr(app, 'socketio'):
        app.socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    else:
        app.run(debug=True, host='0.0.0.0', port=5000)
