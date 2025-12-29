"""
Database Optimization Module for StockLeague

Provides query optimization, strategic indexing, caching strategies, and
connection pooling for improved database performance.

Target: 40% improvement in query execution time
Focus: Most frequently queried tables (users, portfolios, trades, leagues, activity)
"""

import sqlite3
import logging
import time
from functools import wraps
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class DatabaseOptimizationManager:
    """
    Manages database optimization including:
    - Strategic index creation
    - Query analysis and optimization
    - Connection pooling
    - Caching of frequently accessed data
    """

    def __init__(self, db_manager):
        """
        Initialize optimization manager.
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager
        self.query_stats = {}
        self.slow_queries = []
        self.cache = {}
        self.cache_ttl = {}

    def add_strategic_indexes(self):
        """
        Add critical indexes for frequently queried tables.
        
        This focuses on:
        1. User authentication and lookup
        2. Portfolio and trading queries
        3. League operations
        4. Activity feed queries
        5. Foreign key relationships
        """
        indexes = [
            # Users table - critical for auth and lookups
            ("users", "idx_users_username", ["username"], True),
            ("users", "idx_users_email", ["email"], True),
            ("users", "idx_users_created_at", ["created_at"], False),
            ("users", "idx_users_is_admin", ["is_admin"], False),
            
            # Portfolios - frequently queried
            ("portfolios", "idx_portfolios_user_id", ["user_id"], False),
            ("portfolios", "idx_portfolios_is_primary", ["user_id", "is_primary"], False),
            
            # Stocks (holdings) - critical for trading
            ("stocks", "idx_stocks_user_symbol", ["user_id", "symbol"], False),
            ("stocks", "idx_stocks_user_id", ["user_id"], False),
            ("stocks", "idx_stocks_portfolio_id", ["portfolio_id"], False),
            
            # Transactions - heavily queried for history
            ("transactions", "idx_transactions_user_id", ["user_id"], False),
            ("transactions", "idx_transactions_user_type", ["user_id", "type"], False),
            ("transactions", "idx_transactions_timestamp", ["timestamp"], False),
            ("transactions", "idx_transactions_symbol", ["symbol"], False),
            
            # Leagues - critical for league operations
            ("leagues", "idx_leagues_owner_id", ["owner_id"], False),
            ("leagues", "idx_leagues_state", ["state"], False),
            ("leagues", "idx_leagues_created_at", ["created_at"], False),
            ("leagues", "idx_leagues_invite_code", ["invite_code"], True),
            
            # League members - frequent lookups
            ("league_members", "idx_league_members_league_id", ["league_id"], False),
            ("league_members", "idx_league_members_user_id", ["user_id"], False),
            ("league_members", "idx_league_members_league_user", ["league_id", "user_id"], True),
            
            # League stocks/holdings - critical for league trading
            ("league_stocks", "idx_league_stocks_league_user", ["league_id", "user_id"], False),
            ("league_stocks", "idx_league_stocks_symbol", ["league_id", "symbol"], False),
            
            # League transactions
            ("league_transactions", "idx_league_txn_league_id", ["league_id"], False),
            ("league_transactions", "idx_league_txn_user_id", ["user_id"], False),
            ("league_transactions", "idx_league_txn_timestamp", ["timestamp"], False),
            
            # Friends/following relationships
            ("friends", "idx_friends_user_id", ["user_id"], False),
            ("friends", "idx_friends_friend_id", ["friend_id"], False),
            ("friends", "idx_friends_user_friend", ["user_id", "friend_id"], True),
            
            # Activity feed - frequently queried
            ("activity_feed", "idx_activity_league_id", ["league_id"], False),
            ("activity_feed", "idx_activity_user_id", ["user_id"], False),
            ("activity_feed", "idx_activity_timestamp", ["timestamp"], False),
            
            # Notifications
            ("notifications", "idx_notifications_user_id", ["user_id"], False),
            ("notifications", "idx_notifications_read", ["read"], False),
            ("notifications", "idx_notifications_user_read", ["user_id", "read"], False),
            
            # Leaderboards - cached but need index
            ("leaderboards", "idx_leaderboards_league", ["league_id"], False),
            ("leaderboards", "idx_leaderboards_period", ["period"], False),
        ]

        conn = self.db.get_connection()
        cursor = conn.cursor()
        created_count = 0
        skipped_count = 0

        for table, index_name, columns, unique in indexes:
            try:
                # Check if table exists first
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,)
                )
                if not cursor.fetchone():
                    logger.debug(f"Table {table} does not exist, skipping index {index_name}")
                    skipped_count += 1
                    continue

                # Create unique or regular index
                unique_str = "UNIQUE " if unique else ""
                columns_str = ", ".join(columns)
                cursor.execute(
                    f"CREATE {unique_str}INDEX IF NOT EXISTS {index_name} ON {table}({columns_str})"
                )
                created_count += 1
                logger.info(f"Created {unique_str}index: {index_name} on {table}({columns_str})")
            except sqlite3.OperationalError as e:
                logger.warning(f"Could not create index {index_name}: {e}")
                skipped_count += 1

        conn.commit()
        conn.close()
        
        logger.info(f"Strategic indexes: {created_count} created, {skipped_count} skipped")
        return created_count

    def analyze_query_performance(self):
        """
        Analyze database schema and query performance.
        
        Returns:
            Dict with analysis results including table sizes and index coverage
        """
        analysis = {
            'tables': [],
            'missing_indexes': [],
            'recommendations': []
        }

        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Get all tables
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]

            # Get indexes for this table
            cursor.execute(f"PRAGMA index_list({table})")
            indexes = cursor.fetchall()
            index_count = len(indexes)

            # Get columns
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            column_count = len(columns)

            table_info = {
                'name': table,
                'rows': row_count,
                'columns': column_count,
                'indexes': index_count
            }
            analysis['tables'].append(table_info)

        conn.close()

        # Generate recommendations
        for table_info in analysis['tables']:
            if table_info['rows'] > 1000 and table_info['indexes'] == 0:
                analysis['missing_indexes'].append(f"{table_info['name']} ({table_info['rows']} rows)")
                analysis['recommendations'].append(
                    f"Table '{table_info['name']}' has {table_info['rows']} rows but no indexes. "
                    f"Consider adding indexes on frequently queried columns."
                )

        return analysis

    def enable_query_optimization_pragmas(self):
        """
        Enable SQLite pragmas for better query optimization.
        
        Includes:
        - WAL (Write-Ahead Logging) for concurrency
        - Synchronous mode for performance
        - Query planner options
        - Memory usage settings
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        pragmas = [
            # WAL mode - allows readers and writers to coexist
            ("PRAGMA journal_mode=WAL", "WAL mode"),
            
            # Synchronous mode - balance between safety and speed
            ("PRAGMA synchronous=NORMAL", "Synchronous mode"),
            
            # Temporary store - keep temp data in memory
            ("PRAGMA temp_store=MEMORY", "Temp store"),
            
            # Cache size - increase query cache
            ("PRAGMA cache_size=-64000", "Cache size (64MB)"),
            
            # Query timeout - prevent hanging queries
            ("PRAGMA busy_timeout=5000", "Busy timeout"),
            
            # Enable query optimizer
            ("PRAGMA optimize", "Query optimizer"),
            
            # Foreign keys (already needed for referential integrity)
            ("PRAGMA foreign_keys=ON", "Foreign keys"),
        ]

        for pragma, description in pragmas:
            try:
                cursor.execute(pragma)
                logger.info(f"Enabled: {description}")
            except sqlite3.OperationalError as e:
                logger.warning(f"Could not enable {description}: {e}")

        conn.commit()
        conn.close()

    def vacuum_and_analyze(self):
        """
        Run VACUUM and ANALYZE to optimize database structure.
        
        VACUUM: Defragments database file and improves performance
        ANALYZE: Analyzes query patterns to help query planner
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            logger.info("Running VACUUM...")
            cursor.execute("VACUUM")
            logger.info("VACUUM completed")

            logger.info("Running ANALYZE...")
            cursor.execute("ANALYZE")
            logger.info("ANALYZE completed")

            conn.commit()
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not run VACUUM/ANALYZE: {e}")
        finally:
            conn.close()

    def cache_frequently_accessed_data(self, key: str, value: Any, ttl_seconds: int = 300):
        """
        Cache frequently accessed data.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds (default: 5 minutes)
        """
        self.cache[key] = value
        self.cache_ttl[key] = datetime.now() + timedelta(seconds=ttl_seconds)

    def get_cached_data(self, key: str) -> Optional[Any]:
        """
        Get cached data if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if expired/not found
        """
        if key not in self.cache:
            return None

        if datetime.now() > self.cache_ttl.get(key, datetime.now()):
            del self.cache[key]
            if key in self.cache_ttl:
                del self.cache_ttl[key]
            return None

        return self.cache[key]

    def clear_cache(self, key: Optional[str] = None):
        """
        Clear cache data.
        
        Args:
            key: Specific key to clear, or None to clear all
        """
        if key:
            if key in self.cache:
                del self.cache[key]
            if key in self.cache_ttl:
                del self.cache_ttl[key]
        else:
            self.cache.clear()
            self.cache_ttl.clear()

    def profile_query(self, query: str, params: tuple = ()) -> Dict[str, Any]:
        """
        Profile a query for execution time and statistics.
        
        Args:
            query: SQL query to profile
            params: Query parameters
            
        Returns:
            Dict with execution stats (time, rows affected, etc.)
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        start_time = time.time()
        try:
            cursor.execute(query, params)
            result = cursor.fetchall()
            execution_time = time.time() - start_time

            stats = {
                'query': query[:100],  # First 100 chars of query
                'execution_time_ms': execution_time * 1000,
                'rows_returned': len(result),
                'timestamp': datetime.now()
            }

            # Track slow queries (> 100ms)
            if execution_time * 1000 > 100:
                self.slow_queries.append(stats)
                logger.warning(f"Slow query detected: {query[:100]} ({execution_time*1000:.2f}ms)")

            return stats
        except Exception as e:
            logger.error(f"Error profiling query: {e}")
            return {'error': str(e), 'query': query[:100]}
        finally:
            conn.close()

    def get_optimization_report(self) -> str:
        """
        Generate a comprehensive optimization report.
        
        Returns:
            Formatted report string
        """
        analysis = self.analyze_query_performance()
        
        report = "=" * 60 + "\n"
        report += "DATABASE OPTIMIZATION REPORT\n"
        report += "=" * 60 + "\n\n"

        report += "TABLE ANALYSIS:\n"
        report += "-" * 60 + "\n"
        report += f"{'Table':<30} {'Rows':<10} {'Indexes':<10}\n"
        report += "-" * 60 + "\n"
        
        for table_info in sorted(analysis['tables'], key=lambda x: x['rows'], reverse=True):
            report += f"{table_info['name']:<30} {table_info['rows']:<10} {table_info['indexes']:<10}\n"

        report += "\nRECOMMENDATIONS:\n"
        report += "-" * 60 + "\n"
        
        if analysis['recommendations']:
            for rec in analysis['recommendations']:
                report += f"• {rec}\n"
        else:
            report += "• Database is well-optimized for current schema\n"

        report += "\nSLOW QUERIES (> 100ms):\n"
        report += "-" * 60 + "\n"
        
        if self.slow_queries:
            for query_stat in self.slow_queries[-10:]:  # Last 10 slow queries
                report += f"• {query_stat['query']} ({query_stat['execution_time_ms']:.2f}ms)\n"
        else:
            report += "• No slow queries detected\n"

        report += "\nOPTIMIZATION STATUS:\n"
        report += "-" * 60 + "\n"
        report += f"• Cache entries: {len(self.cache)}\n"
        report += f"• Cache hit rate: {self._calculate_cache_hit_rate():.1%}\n"
        report += "=" * 60 + "\n"

        return report

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if not self.query_stats:
            return 0.0
        
        cache_hits = sum(1 for stat in self.query_stats.values() if stat.get('cached'))
        total_queries = len(self.query_stats)
        return cache_hits / total_queries if total_queries > 0 else 0.0

    def optimize_all(self):
        """
        Run all optimization procedures.
        
        This includes:
        1. Add strategic indexes
        2. Enable optimization pragmas
        3. Run VACUUM and ANALYZE
        4. Generate report
        """
        logger.info("Starting comprehensive database optimization...")

        # Step 1: Add indexes
        logger.info("Step 1: Adding strategic indexes...")
        index_count = self.add_strategic_indexes()

        # Step 2: Enable pragmas
        logger.info("Step 2: Enabling optimization pragmas...")
        self.enable_query_optimization_pragmas()

        # Step 3: VACUUM and ANALYZE
        logger.info("Step 3: Running VACUUM and ANALYZE...")
        self.vacuum_and_analyze()

        # Step 4: Report
        logger.info("Step 4: Generating optimization report...")
        report = self.get_optimization_report()
        logger.info(f"\n{report}")

        logger.info("Database optimization complete!")
        return {
            'indexes_created': index_count,
            'report': report
        }


def optimize_database_on_startup(db_manager):
    """
    Convenience function to optimize database on application startup.
    
    Args:
        db_manager: DatabaseManager instance
    """
    optimizer = DatabaseOptimizationManager(db_manager)
    result = optimizer.optimize_all()
    return optimizer, result
