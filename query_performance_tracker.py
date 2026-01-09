# Query Performance Monitoring for TIER 7 Component 2
# Task 2.4: Query monitoring and performance tracking

import time
import logging
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class QueryPerformanceTracker:
    """Track query performance metrics for monitoring."""
    
    def __init__(self, slow_query_threshold_ms=100):
        """
        Initialize query tracker.
        
        Args:
            slow_query_threshold_ms: Queries slower than this (in ms) are flagged as slow
        """
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.slow_queries = []
        self.query_times = defaultdict(list)
        self.total_queries = 0
        self.total_time = 0
        self.query_errors = []
        self.max_history = 1000  # Keep last 1000 slow queries
    
    def log_query(self, query, duration_ms, error=None):
        """
        Log a query execution.
        
        Args:
            query: SQL query string
            duration_ms: Execution time in milliseconds
            error: Exception if query failed (optional)
        """
        self.total_queries += 1
        self.total_time += duration_ms
        
        # Track query times by type
        query_type = query.split()[0].upper() if query else 'UNKNOWN'
        self.query_times[query_type].append(duration_ms)
        
        # Log slow queries
        if duration_ms >= self.slow_query_threshold_ms:
            self.slow_queries.append({
                'query': query[:200],  # First 200 chars
                'duration_ms': duration_ms,
                'timestamp': datetime.now().isoformat(),
                'error': str(error) if error else None
            })
            
            # Keep history bounded
            if len(self.slow_queries) > self.max_history:
                self.slow_queries = self.slow_queries[-self.max_history:]
            
            logger.warning(f"SLOW QUERY ({duration_ms:.1f}ms): {query[:80]}")
        
        # Track errors
        if error:
            self.query_errors.append({
                'query': query[:200],
                'error': str(error),
                'timestamp': datetime.now().isoformat()
            })
            
            if len(self.query_errors) > 100:
                self.query_errors = self.query_errors[-100:]
    
    def get_stats(self):
        """Get current performance statistics."""
        avg_time = (self.total_time / self.total_queries) if self.total_queries > 0 else 0
        
        stats_by_type = {}
        for query_type, times in self.query_times.items():
            stats_by_type[query_type] = {
                'count': len(times),
                'avg_ms': round(sum(times) / len(times), 2),
                'max_ms': round(max(times), 2),
                'min_ms': round(min(times), 2)
            }
        
        return {
            'total_queries': self.total_queries,
            'total_time_ms': round(self.total_time, 2),
            'avg_query_time_ms': round(avg_time, 2),
            'slow_queries_count': len(self.slow_queries),
            'error_count': len(self.query_errors),
            'stats_by_type': stats_by_type,
            'slow_query_threshold_ms': self.slow_query_threshold_ms
        }
    
    def get_slow_queries(self, limit=10):
        """Get slowest queries."""
        sorted_queries = sorted(self.slow_queries, key=lambda x: x['duration_ms'], reverse=True)
        return sorted_queries[:limit]
    
    def get_recent_errors(self, limit=10):
        """Get recent query errors."""
        return self.query_errors[-limit:]
    
    def reset_stats(self):
        """Reset all tracking data."""
        self.slow_queries = []
        self.query_times = defaultdict(list)
        self.total_queries = 0
        self.total_time = 0
        self.query_errors = []
        logger.info("Query performance stats reset")


class QueryTimer:
    """Context manager for timing queries."""
    
    def __init__(self, tracker, query_str):
        """
        Initialize timer.
        
        Args:
            tracker: QueryPerformanceTracker instance
            query_str: SQL query string
        """
        self.tracker = tracker
        self.query = query_str
        self.start_time = None
        self.error = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and log."""
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            self.error = exc_val if exc_type else None
            self.tracker.log_query(self.query, duration_ms, self.error)


def get_query_stats_html():
    """Generate HTML report of query stats (for admin dashboard)."""
    from flask import current_app
    
    if not hasattr(current_app, 'query_tracker'):
        return "<p>No query tracking data available.</p>"
    
    tracker = current_app.query_tracker
    stats = tracker.get_stats()
    slow_queries = tracker.get_slow_queries(20)
    
    html = f"""
    <div class="query-stats">
        <h3>Query Performance Statistics</h3>
        <ul>
            <li>Total Queries: <strong>{stats['total_queries']}</strong></li>
            <li>Total Time: <strong>{stats['total_time_ms']:.1f}ms</strong></li>
            <li>Average Time: <strong>{stats['avg_query_time_ms']:.2f}ms</strong></li>
            <li>Slow Queries: <strong>{stats['slow_queries_count']}</strong></li>
            <li>Errors: <strong>{stats['error_count']}</strong></li>
        </ul>
        
        <h4>Slowest Queries</h4>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <th>Duration (ms)</th>
                <th>Query</th>
                <th>Time</th>
            </tr>
    """
    
    for q in slow_queries:
        html += f"""
            <tr>
                <td>{q['duration_ms']:.1f}</td>
                <td style="word-break: break-all;">{q['query']}</td>
                <td>{q['timestamp']}</td>
            </tr>
        """
    
    html += """
        </table>
    </div>
    """
    
    return html
