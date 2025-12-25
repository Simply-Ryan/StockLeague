"""
Redis Caching Layer for StockLeague
Provides cache-aside pattern for performance optimization
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Callable
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)


class CacheKey:
    """Cache key builder with namespacing"""
    
    # Cache key prefixes for different data types
    LEADERBOARD = "leaderboard"
    USER_PORTFOLIO = "portfolio"
    LEAGUE = "league"
    LEAGUE_MEMBERS = "league_members"
    STOCK_QUOTE = "quote"
    OPTIONS_CHAIN = "options_chain"
    USER_STATS = "user_stats"
    LEAGUE_STATS = "league_stats"
    ACTIVITY_FEED = "activity"
    SEARCH = "search"
    SESSION = "session"
    
    @staticmethod
    def leaderboard(league_id: int, page: int = 1) -> str:
        """Leaderboard cache key"""
        return f"{CacheKey.LEADERBOARD}:league:{league_id}:page:{page}"
    
    @staticmethod
    def portfolio(user_id: int, league_id: int) -> str:
        """Portfolio cache key"""
        return f"{CacheKey.USER_PORTFOLIO}:user:{user_id}:league:{league_id}"
    
    @staticmethod
    def league(league_id: int) -> str:
        """League data cache key"""
        return f"{CacheKey.LEAGUE}:{league_id}"
    
    @staticmethod
    def league_members(league_id: int) -> str:
        """League members cache key"""
        return f"{CacheKey.LEAGUE_MEMBERS}:{league_id}"
    
    @staticmethod
    def stock_quote(symbol: str) -> str:
        """Stock quote cache key"""
        return f"{CacheKey.STOCK_QUOTE}:{symbol.upper()}"
    
    @staticmethod
    def options_chain(symbol: str, expiration: str) -> str:
        """Options chain cache key"""
        return f"{CacheKey.OPTIONS_CHAIN}:{symbol.upper()}:{expiration}"
    
    @staticmethod
    def user_stats(user_id: int) -> str:
        """User statistics cache key"""
        return f"{CacheKey.USER_STATS}:user:{user_id}"
    
    @staticmethod
    def league_stats(league_id: int) -> str:
        """League statistics cache key"""
        return f"{CacheKey.LEAGUE_STATS}:league:{league_id}"
    
    @staticmethod
    def activity_feed(league_id: int, page: int = 1) -> str:
        """Activity feed cache key"""
        return f"{CacheKey.ACTIVITY_FEED}:league:{league_id}:page:{page}"
    
    @staticmethod
    def search(query: str, category: str = "") -> str:
        """Search results cache key"""
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        if category:
            return f"{CacheKey.SEARCH}:{category}:{query_hash}"
        return f"{CacheKey.SEARCH}:general:{query_hash}"
    
    @staticmethod
    def session(session_id: str) -> str:
        """Session data cache key"""
        return f"{CacheKey.SESSION}:{session_id}"


class CacheConfig:
    """Cache configuration with TTL settings"""
    
    # Default TTL values (in seconds)
    LEADERBOARD_TTL = 300  # 5 minutes
    PORTFOLIO_TTL = 120  # 2 minutes
    LEAGUE_TTL = 600  # 10 minutes
    LEAGUE_MEMBERS_TTL = 300  # 5 minutes
    STOCK_QUOTE_TTL = 60  # 1 minute (market data updates frequently)
    OPTIONS_CHAIN_TTL = 300  # 5 minutes
    USER_STATS_TTL = 600  # 10 minutes
    LEAGUE_STATS_TTL = 600  # 10 minutes
    ACTIVITY_FEED_TTL = 300  # 5 minutes
    SEARCH_TTL = 3600  # 1 hour
    SESSION_TTL = 86400  # 24 hours
    
    @staticmethod
    def get_ttl(cache_type: str) -> int:
        """Get TTL for cache type"""
        ttl_map = {
            CacheKey.LEADERBOARD: CacheConfig.LEADERBOARD_TTL,
            CacheKey.USER_PORTFOLIO: CacheConfig.PORTFOLIO_TTL,
            CacheKey.LEAGUE: CacheConfig.LEAGUE_TTL,
            CacheKey.LEAGUE_MEMBERS: CacheConfig.LEAGUE_MEMBERS_TTL,
            CacheKey.STOCK_QUOTE: CacheConfig.STOCK_QUOTE_TTL,
            CacheKey.OPTIONS_CHAIN: CacheConfig.OPTIONS_CHAIN_TTL,
            CacheKey.USER_STATS: CacheConfig.USER_STATS_TTL,
            CacheKey.LEAGUE_STATS: CacheConfig.LEAGUE_STATS_TTL,
            CacheKey.ACTIVITY_FEED: CacheConfig.ACTIVITY_FEED_TTL,
            CacheKey.SEARCH: CacheConfig.SEARCH_TTL,
            CacheKey.SESSION: CacheConfig.SESSION_TTL,
        }
        return ttl_map.get(cache_type, 300)


class CacheManager:
    """
    Redis cache manager with cache-aside pattern.
    
    Usage:
        cache = CacheManager(redis_client)
        
        # Get with fallback
        data = cache.get_or_fetch(
            key=CacheKey.leaderboard(league_id),
            fetch_fn=lambda: db.get_leaderboard(league_id),
            ttl=300
        )
        
        # Direct operations
        cache.set(key, value, ttl=300)
        data = cache.get(key)
        cache.delete(key)
        cache.clear_pattern("leaderboard:*")
    """
    
    def __init__(self, redis_client):
        """
        Initialize cache manager.
        
        Args:
            redis_client: Redis connection instance
        """
        self.redis = redis_client
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        try:
            if not self.redis:
                return None
            
            value = self.redis.get(key)
            if value:
                self.stats['hits'] += 1
                try:
                    return json.loads(value)
                except:
                    return value
            else:
                self.stats['misses'] += 1
                return None
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            Success status
        """
        try:
            if not self.redis:
                return False
            
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            else:
                serialized = str(value)
            
            self.redis.setex(key, ttl, serialized)
            self.stats['sets'] += 1
            return True
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False
    
    def get_or_fetch(self, key: str, fetch_fn: Callable, ttl: int = 300) -> Optional[Any]:
        """
        Get from cache or fetch using callback.
        Cache-aside pattern.
        
        Args:
            key: Cache key
            fetch_fn: Function to call if cache miss
            ttl: Time to live in seconds
            
        Returns:
            Cached or fetched value
        """
        # Try cache first
        cached = self.get(key)
        if cached is not None:
            return cached
        
        # Cache miss - fetch data
        try:
            data = fetch_fn()
            if data is not None:
                self.set(key, data, ttl)
            return data
        except Exception as e:
            logger.error(f"Error fetching data for cache key {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Success status
        """
        try:
            if not self.redis:
                return False
            
            self.redis.delete(key)
            self.stats['deletes'] += 1
            return True
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "leaderboard:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            if not self.redis:
                return 0
            
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
                self.stats['deletes'] += len(keys)
                return len(keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    def clear(self) -> bool:
        """Clear entire cache"""
        try:
            if not self.redis:
                return False
            
            self.redis.flushdb()
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
        
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'sets': self.stats['sets'],
            'deletes': self.stats['deletes'],
            'total_requests': total,
            'hit_rate_percent': round(hit_rate, 2)
        }
    
    def reset_stats(self):
        """Reset cache statistics"""
        self.stats = {'hits': 0, 'misses': 0, 'sets': 0, 'deletes': 0}


class CacheInvalidator:
    """Manages cache invalidation for related data"""
    
    def __init__(self, cache_manager: CacheManager):
        """
        Initialize cache invalidator.
        
        Args:
            cache_manager: CacheManager instance
        """
        self.cache = cache_manager
    
    def invalidate_league(self, league_id: int):
        """Invalidate all league-related caches"""
        self.cache.delete_pattern(f"*league:{league_id}*")
        logger.info(f"Invalidated league {league_id} caches")
    
    def invalidate_user(self, user_id: int):
        """Invalidate all user-related caches"""
        self.cache.delete_pattern(f"*user:{user_id}*")
        logger.info(f"Invalidated user {user_id} caches")
    
    def invalidate_leaderboards(self):
        """Invalidate all leaderboard caches"""
        self.cache.delete_pattern(f"{CacheKey.LEADERBOARD}:*")
        logger.info("Invalidated all leaderboard caches")
    
    def invalidate_stock(self, symbol: str):
        """Invalidate stock quote cache"""
        self.cache.delete(CacheKey.stock_quote(symbol))
        logger.info(f"Invalidated quote cache for {symbol}")
    
    def invalidate_options_chain(self, symbol: str):
        """Invalidate options chain caches for symbol"""
        self.cache.delete_pattern(f"{CacheKey.OPTIONS_CHAIN}:{symbol.upper()}:*")
        logger.info(f"Invalidated options chain cache for {symbol}")
    
    def invalidate_trade_impact(self, user_id: int, league_id: int, symbol: str):
        """Invalidate caches affected by a trade"""
        # Portfolio changed
        self.cache.delete(CacheKey.portfolio(user_id, league_id))
        # Leaderboard affected
        self.cache.delete_pattern(f"{CacheKey.LEADERBOARD}:league:{league_id}:*")
        # User stats changed
        self.cache.delete(CacheKey.user_stats(user_id))
        # League stats might be affected
        self.cache.delete(CacheKey.league_stats(league_id))
        # Activity feed
        self.cache.delete_pattern(f"{CacheKey.ACTIVITY_FEED}:league:{league_id}:*")
        logger.info(f"Invalidated caches for trade by user {user_id} in league {league_id}")


def cache_result(ttl: int = 300, key_builder: Optional[Callable] = None):
    """
    Decorator to cache function results.
    
    Usage:
        @cache_result(ttl=300, key_builder=lambda league_id: CacheKey.leaderboard(league_id))
        def get_leaderboard(league_id):
            return db.get_leaderboard(league_id)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key building
                arg_str = "_".join(str(arg) for arg in args + tuple(kwargs.values()))
                cache_key = f"{func.__name__}:{arg_str}"
            
            # Try cache first
            from flask import g
            if hasattr(g, 'cache_manager'):
                cached = g.cache_manager.get(cache_key)
                if cached is not None:
                    return cached
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            if hasattr(g, 'cache_manager'):
                g.cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


class WarmCacheScheduler:
    """Pre-warm cache with frequently accessed data"""
    
    def __init__(self, db, cache_manager: CacheManager):
        """
        Initialize cache warmer.
        
        Args:
            db: DatabaseManager instance
            cache_manager: CacheManager instance
        """
        self.db = db
        self.cache = cache_manager
    
    def warm_leaderboards(self):
        """Pre-warm all league leaderboards"""
        try:
            leagues = self.db.get_all_leagues()
            for league in leagues:
                league_id = league.get('id')
                leaderboard = self.db.get_league_leaderboard(league_id)
                self.cache.set(
                    CacheKey.leaderboard(league_id),
                    leaderboard,
                    CacheConfig.LEADERBOARD_TTL
                )
            logger.info(f"Warmed {len(leagues)} leaderboard caches")
        except Exception as e:
            logger.error(f"Error warming leaderboards: {e}")
    
    def warm_popular_stocks(self):
        """Pre-warm quotes for popular stocks"""
        try:
            from helpers import lookup
            popular_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'SPY']
            
            for symbol in popular_symbols:
                quote = lookup(symbol)
                if quote:
                    self.cache.set(
                        CacheKey.stock_quote(symbol),
                        quote,
                        CacheConfig.STOCK_QUOTE_TTL
                    )
            logger.info(f"Warmed {len(popular_symbols)} stock quote caches")
        except Exception as e:
            logger.error(f"Error warming stock quotes: {e}")
    
    def warm_user_stats(self, user_ids: Optional[List[int]] = None):
        """Pre-warm user statistics"""
        try:
            if not user_ids:
                # Warm top users
                users = self.db.get_users_limit(limit=100)
                user_ids = [u.get('id') for u in users]
            
            for user_id in user_ids:
                stats = self.db.get_user_statistics(user_id)
                self.cache.set(
                    CacheKey.user_stats(user_id),
                    stats,
                    CacheConfig.USER_STATS_TTL
                )
            logger.info(f"Warmed {len(user_ids)} user stats caches")
        except Exception as e:
            logger.error(f"Error warming user stats: {e}")
    
    def warm_all(self):
        """Warm all major caches"""
        logger.info("Starting cache warming...")
        self.warm_leaderboards()
        self.warm_popular_stocks()
        self.warm_user_stats()
        logger.info("Cache warming complete")
