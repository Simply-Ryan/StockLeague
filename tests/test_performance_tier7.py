# Performance Testing Suite for TIER 7 Component 2
# Task 2.5: Performance testing and verification

import time
import pytest
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PerformanceBenchmark:
    """Benchmark test results."""
    
    def __init__(self, name, target_ms, actual_ms):
        self.name = name
        self.target_ms = target_ms
        self.actual_ms = actual_ms
        self.passed = actual_ms <= target_ms
        self.improvement = ((target_ms - actual_ms) / target_ms * 100) if target_ms > 0 else 0
    
    def __str__(self):
        status = "✓ PASS" if self.passed else "✗ FAIL"
        return f"{status} | {self.name:40} | Target: {self.target_ms:6}ms | Actual: {self.actual_ms:6.1f}ms | Improvement: {self.improvement:+6.1f}%"


@pytest.mark.performance
class TestDatabasePerformance:
    """Test database query performance after optimization."""
    
    @pytest.fixture
    def app(self):
        """Create test app."""
        from app_factory import create_app
        app = create_app('testing')
        return app
    
    @pytest.fixture
    def db(self, app):
        """Get database manager."""
        with app.app_context():
            from database.db_manager import DatabaseManager
            return DatabaseManager()
    
    def measure_time(self, func, *args, **kwargs):
        """Measure execution time of a function."""
        start = time.time()
        result = func(*args, **kwargs)
        elapsed_ms = (time.time() - start) * 1000
        return result, elapsed_ms
    
    def test_quote_lookup_performance(self, app):
        """Test quote lookup performance - should be < 50ms with cache."""
        with app.app_context():
            from helpers import lookup
            
            # First call (cache miss)
            quote1, time1 = self.measure_time(lookup, 'AAPL')
            assert quote1 is not None, "Quote lookup returned None"
            
            # Second call (cache hit)
            quote2, time2 = self.measure_time(lookup, 'AAPL')
            assert quote2 is not None, "Cached quote lookup returned None"
            
            # Cached call should be much faster
            benchmark = PerformanceBenchmark("Quote Lookup (Cached)", 50, time2)
            logger.info(benchmark)
            
            # Allow some tolerance for first call
            assert time1 < 2000, f"Fresh quote lookup took {time1:.1f}ms (too slow)"
            assert time2 < 50, f"Cached quote lookup took {time2:.1f}ms (target: < 50ms)"
    
    def test_leaderboard_performance(self, app, db):
        """Test leaderboard loading performance."""
        with app.app_context():
            from helpers import lookup
            
            # Create test league if needed
            league_id = 1
            league = db.get_league(league_id)
            if not league:
                logger.warning("No test league found - skipping leaderboard performance test")
                return
            
            # First call (cache miss)
            lb1, time1 = self.measure_time(
                db.get_league_leaderboard_with_values,
                league_id,
                lookup
            )
            assert lb1 is not None, "Leaderboard returned None"
            
            # Second call (cache hit)
            lb2, time2 = self.measure_time(
                db.get_league_leaderboard_with_values,
                league_id,
                lookup
            )
            assert lb2 is not None, "Cached leaderboard returned None"
            
            # Leaderboard should be cached
            benchmark = PerformanceBenchmark("Leaderboard Load (Cached)", 100, time2)
            logger.info(benchmark)
            
            # Allow tolerance for first calculation
            assert time1 < 5000, f"Fresh leaderboard took {time1:.1f}ms (too slow)"
            assert time2 < 100, f"Cached leaderboard took {time2:.1f}ms (target: < 100ms)"
    
    def test_user_stocks_query_performance(self, app, db):
        """Test user stocks query performance."""
        with app.app_context():
            user_id = 1
            
            # Measure query time
            stocks, elapsed_ms = self.measure_time(db.get_user_stocks, user_id)
            
            benchmark = PerformanceBenchmark("Get User Stocks", 50, elapsed_ms)
            logger.info(benchmark)
            
            assert elapsed_ms < 50, f"Get user stocks took {elapsed_ms:.1f}ms (target: < 50ms)"
    
    def test_league_members_query_performance(self, app, db):
        """Test league members query performance."""
        with app.app_context():
            league_id = 1
            
            # Measure query time
            members, elapsed_ms = self.measure_time(db.get_league_members, league_id)
            
            benchmark = PerformanceBenchmark("Get League Members", 50, elapsed_ms)
            logger.info(benchmark)
            
            assert elapsed_ms < 50, f"Get league members took {elapsed_ms:.1f}ms (target: < 50ms)"
    
    def test_database_stats(self, app, db):
        """Get and verify database statistics."""
        with app.app_context():
            stats = db.get_database_stats()
            
            logger.info(f"Database Statistics:")
            logger.info(f"  Size: {stats.get('size_mb', 0):.2f} MB")
            logger.info(f"  Users: {stats.get('users', 0)}")
            logger.info(f"  Transactions: {stats.get('transactions', 0)}")
            logger.info(f"  League Transactions: {stats.get('league_transactions', 0)}")
            logger.info(f"  Indexes: {stats.get('indexes', 0)}")
            
            assert stats.get('indexes', 0) >= 15, "Not enough indexes created"
    
    def test_slow_query_detection(self, app, db):
        """Test slow query detection."""
        with app.app_context():
            slow_queries = db.get_slow_query_info()
            
            if slow_queries:
                logger.warning("Potentially slow queries detected:")
                for query_info in slow_queries:
                    logger.warning(f"  Table: {query_info['table']}, Rows: {query_info['rows']}, Indexes: {query_info['indexes']}")
            else:
                logger.info("✓ No slow queries detected")


class LoadTester:
    """Simulate load testing."""
    
    @staticmethod
    def run_load_test(app, num_requests=100, concurrent_users=10):
        """
        Simulate load on the app.
        
        Args:
            app: Flask app
            num_requests: Total requests to make
            concurrent_users: Simulated concurrent users
            
        Returns:
            Load test results dictionary
        """
        import concurrent.futures
        from helpers import lookup
        
        results = {
            'total_requests': num_requests,
            'successful': 0,
            'failed': 0,
            'times': [],
            'start_time': datetime.now().isoformat(),
            'errors': []
        }
        
        def make_request(request_id):
            """Make a single request."""
            try:
                with app.app_context():
                    start = time.time()
                    quote = lookup('AAPL')
                    elapsed_ms = (time.time() - start) * 1000
                    
                    if quote:
                        return ('success', elapsed_ms)
                    else:
                        return ('failed', elapsed_ms)
            except Exception as e:
                return ('error', str(e))
        
        # Execute requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    status, data = future.result()
                    
                    if status == 'success':
                        results['successful'] += 1
                        results['times'].append(data)
                    elif status == 'failed':
                        results['failed'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append(data)
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(str(e))
        
        # Calculate statistics
        if results['times']:
            results['avg_response_ms'] = sum(results['times']) / len(results['times'])
            results['min_response_ms'] = min(results['times'])
            results['max_response_ms'] = max(results['times'])
            results['throughput_rps'] = num_requests / (sum(results['times']) / 1000 / num_requests)
        
        results['end_time'] = datetime.now().isoformat()
        
        return results


def generate_performance_report(results):
    """Generate a performance report from load test results."""
    report = f"""
    ╔════════════════════════════════════════════════════════╗
    ║        TIER 7 COMPONENT 2 PERFORMANCE REPORT           ║
    ╠════════════════════════════════════════════════════════╣
    
    Load Test Results:
    ─────────────────
    Total Requests:     {results.get('total_requests', 0)}
    Successful:         {results.get('successful', 0)} ({results.get('successful', 0)*100/results.get('total_requests', 1):.1f}%)
    Failed:             {results.get('failed', 0)}
    
    Response Times:
    ───────────────
    Average:            {results.get('avg_response_ms', 0):.2f} ms
    Min:                {results.get('min_response_ms', 0):.2f} ms
    Max:                {results.get('max_response_ms', 0):.2f} ms
    
    Throughput:
    ───────────
    Requests/sec:       {results.get('throughput_rps', 0):.2f}
    
    Errors:             {len(results.get('errors', []))}
    
    Test Duration:      {results.get('start_time')} to {results.get('end_time')}
    
    ╚════════════════════════════════════════════════════════╝
    """
    return report


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])
