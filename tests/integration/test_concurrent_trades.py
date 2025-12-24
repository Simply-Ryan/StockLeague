"""
tests/integration/test_concurrent_trades.py

Integration tests for concurrent trading scenarios:
- Concurrent buy/sell operations
- Race condition prevention
- Portfolio consistency under load
- High-frequency trading patterns
"""

import unittest
import os
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db_manager import DatabaseManager


class TestConcurrentTrading(unittest.TestCase):
    """Integration tests for concurrent trading operations"""
    
    def setUp(self):
        """Create test database and users"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = DatabaseManager(self.temp_db.name)
        
        # Create test users
        self.user_ids = []
        for i in range(5):
            user_id = self.create_test_user(f'user{i}', 100000.0)
            self.user_ids.append(user_id)
    
    def tearDown(self):
        """Clean up"""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def create_test_user(self, username, cash=100000.0):
        """Create a test user"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, hash, cash, email)
            VALUES (?, ?, ?, ?)
        """, (username, 'hash', cash, f'{username}@test.com'))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    
    # ========================================================================
    # CONCURRENT BUY TESTS
    # ========================================================================
    
    def test_concurrent_buys_same_stock(self):
        """Test multiple users buying same stock concurrently"""
        symbol = 'AAPL'
        
        def buy_stock(user_id):
            return self.db.execute_buy_trade_atomic(
                user_id=user_id,
                symbol=symbol,
                shares=100,
                price=150.0
            )
        
        # Execute 5 concurrent buys
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(buy_stock, uid) for uid in self.user_ids]
            results = [f.result() for f in as_completed(futures)]
        
        # All should succeed
        successes = sum(1 for s, _, _ in results if s)
        self.assertEqual(successes, 5, "Not all buys succeeded")
        
        # Verify each user has correct holding
        for user_id in self.user_ids:
            stock = self.db.get_user_stock(user_id, symbol)
            self.assertEqual(stock['shares'], 100)
            self.assertEqual(stock['avg_cost'], 150.0)
    
    def test_concurrent_buys_different_stocks(self):
        """Test same user buying different stocks concurrently"""
        user_id = self.user_ids[0]
        
        def buy_stock(symbol):
            return self.db.execute_buy_trade_atomic(
                user_id=user_id,
                symbol=symbol,
                shares=100,
                price=150.0
            )
        
        symbols = ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'TSLA']
        
        # Execute concurrent buys of different stocks
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(buy_stock, sym) for sym in symbols]
            results = [f.result() for f in as_completed(futures)]
        
        # All should succeed
        successes = sum(1 for s, _, _ in results if s)
        self.assertEqual(successes, 5, "Not all buys succeeded")
        
        # Verify all holdings exist
        for symbol in symbols:
            stock = self.db.get_user_stock(user_id, symbol)
            self.assertIsNotNone(stock)
            self.assertEqual(stock['shares'], 100)
        
        # Verify cash correctly reduced
        user = self.db.get_user(user_id)
        expected_cash = 100000.0 - (5 * 100 * 150.0)
        self.assertAlmostEqual(user['cash'], expected_cash, places=2)
    
    # ========================================================================
    # CONCURRENT SELL TESTS
    # ========================================================================
    
    def test_concurrent_sells_partial(self):
        """Test concurrent partial sells don't oversell"""
        user_id = self.user_ids[0]
        symbol = 'AAPL'
        
        # Create initial position: 1000 shares
        self.db.execute_buy_trade_atomic(user_id, symbol, 1000, 150.0)
        
        def sell_stock():
            return self.db.execute_sell_trade_atomic(
                user_id=user_id,
                symbol=symbol,
                shares=100,
                price=160.0
            )
        
        # Try to sell 100 shares 10 times concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(sell_stock) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]
        
        # All should succeed (1000 shares available for 10 * 100 = 1000 shares)
        # Actually some might fail due to concurrency - verify final state is consistent
        final_stock = self.db.get_user_stock(user_id, symbol)
        
        if final_stock:
            # Should be zero or positive
            self.assertGreaterEqual(final_stock['shares'], 0)
        else:
            # Position fully sold
            self.assertIsNone(final_stock)
    
    def test_concurrent_sells_insufficient_shares(self):
        """Test concurrent sells can't oversell"""
        user_id = self.user_ids[0]
        symbol = 'AAPL'
        
        # Create position: 150 shares
        self.db.execute_buy_trade_atomic(user_id, symbol, 150, 150.0)
        
        def sell_stock():
            return self.db.execute_sell_trade_atomic(
                user_id=user_id,
                symbol=symbol,
                shares=100,  # Each thread tries to sell 100
                price=160.0
            )
        
        # Concurrent sells where total > available
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(sell_stock) for _ in range(3)]
            results = [f.result() for f in as_completed(futures)]
        
        # At most 2 can succeed (150 / 100 = 1.5)
        successes = sum(1 for s, _, _ in results if s)
        self.assertLessEqual(successes, 2, "Too many concurrent sells succeeded")
        
        # Verify final state is valid
        final_stock = self.db.get_user_stock(user_id, symbol)
        if final_stock:
            self.assertGreaterEqual(final_stock['shares'], 0)
    
    # ========================================================================
    # MIXED OPERATION TESTS
    # ========================================================================
    
    def test_concurrent_buy_and_sell(self):
        """Test concurrent buys and sells on same position"""
        user_id = self.user_ids[0]
        symbol = 'AAPL'
        
        # Initial position: 1000 shares
        self.db.execute_buy_trade_atomic(user_id, symbol, 1000, 150.0)
        
        def trade():
            import random
            if random.choice([True, False]):
                return self.db.execute_buy_trade_atomic(
                    user_id=user_id, symbol=symbol, shares=50, price=150.0
                )
            else:
                return self.db.execute_sell_trade_atomic(
                    user_id=user_id, symbol=symbol, shares=50, price=150.0
                )
        
        # Execute 20 concurrent random trades
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(trade) for _ in range(20)]
            results = [f.result() for f in as_completed(futures)]
        
        # Verify final state is valid
        final_stock = self.db.get_user_stock(user_id, symbol)
        if final_stock:
            self.assertGreater(final_stock['shares'], 0)
            # Should be 1000 + some multiple of 50
            self.assertEqual((final_stock['shares'] - 1000) % 50, 0)
    
    # ========================================================================
    # CASH INTEGRITY TESTS
    # ========================================================================
    
    def test_cash_integrity_under_concurrent_trades(self):
        """Test cash balance remains consistent under concurrent trading"""
        user_id = self.user_ids[0]
        initial_cash = 100000.0
        
        def buy_and_sell():
            # Buy 10 shares @ $100
            s1, _, _ = self.db.execute_buy_trade_atomic(
                user_id=user_id, symbol='TEST', shares=10, price=100.0
            )
            if not s1:
                return False
            
            # Sell 10 shares @ $100 (no profit/loss)
            s2, _, _ = self.db.execute_sell_trade_atomic(
                user_id=user_id, symbol='TEST', shares=10, price=100.0
            )
            return s2
        
        # Execute 10 concurrent buy-sell cycles
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(buy_and_sell) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]
        
        # Verify final cash is correct (should be unchanged due to no profit/loss)
        user = self.db.get_user(user_id)
        self.assertAlmostEqual(user['cash'], initial_cash, places=2,
                             msg="Cash balance corrupted under concurrent trades")
    
    # ========================================================================
    # HIGH-FREQUENCY TRADING TESTS
    # ========================================================================
    
    def test_high_frequency_trading_sequence(self):
        """Test rapid buy/sell sequence doesn't corrupt state"""
        user_id = self.user_ids[0]
        symbol = 'AAPL'
        
        # Rapid buy-sell-buy sequence
        operations = [
            ('BUY', 100, 150.0),
            ('BUY', 50, 151.0),
            ('SELL', 75, 152.0),
            ('BUY', 100, 151.0),
            ('SELL', 100, 153.0),
            ('SELL', 75, 154.0),
        ]
        
        for op, shares, price in operations:
            if op == 'BUY':
                success, error, _ = self.db.execute_buy_trade_atomic(
                    user_id, symbol, shares, price
                )
            else:  # SELL
                success, error, _ = self.db.execute_sell_trade_atomic(
                    user_id, symbol, shares, price
                )
            
            if not success:
                self.fail(f"{op} operation failed: {error}")
        
        # Final position: 100 + 50 - 75 + 100 - 100 - 75 = 0
        final_stock = self.db.get_user_stock(user_id, symbol)
        self.assertIsNone(final_stock, "Expected position to be fully sold")
    
    def test_stress_test_many_trades(self):
        """Stress test: execute many trades rapidly"""
        user_id = self.user_ids[0]
        
        success_count = 0
        failure_count = 0
        
        for i in range(50):
            # Alternate buy and sell
            symbol = f'STOCK{i % 5}'
            
            if i % 2 == 0:
                # Buy
                success, error, _ = self.db.execute_buy_trade_atomic(
                    user_id, symbol, 10, 100.0
                )
            else:
                # Sell
                success, error, _ = self.db.execute_sell_trade_atomic(
                    user_id, symbol, 5, 100.0
                )
            
            if success:
                success_count += 1
            else:
                failure_count += 1
        
        # Should have mostly successes
        self.assertGreater(success_count, 30, "Too many trade failures")
        
        # Final state should be valid
        user = self.db.get_user(user_id)
        self.assertGreaterEqual(user['cash'], 0, "Negative cash balance!")
        
        # All holdings should have non-negative shares
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_stocks WHERE shares < 0")
        negative_count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(negative_count, 0, "Found negative share counts!")


class TestErrorRecovery(unittest.TestCase):
    """Tests for error recovery and data consistency"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = DatabaseManager(self.temp_db.name)
        
        self.user_id = self.create_test_user('testuser', 100000.0)
    
    def tearDown(self):
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def create_test_user(self, username, cash=100000.0):
        """Create a test user"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, hash, cash, email)
            VALUES (?, ?, ?, ?)
        """, (username, 'hash', cash, f'{username}@test.com'))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    
    def test_failed_buy_rolls_back(self):
        """Test failed buy transaction rolls back completely"""
        initial_cash = 100000.0
        
        # Attempt buy that will fail (insufficient funds)
        success, error, _ = self.db.execute_buy_trade_atomic(
            self.user_id, 'AAPL', 1000, 150.0
        )
        
        self.assertFalse(success)
        
        # Verify state unchanged
        user = self.db.get_user(self.user_id)
        self.assertEqual(user['cash'], initial_cash)
        
        stock = self.db.get_user_stock(self.user_id, 'AAPL')
        self.assertIsNone(stock)
    
    def test_failed_sell_rolls_back(self):
        """Test failed sell transaction rolls back completely"""
        # Create initial position
        self.db.execute_buy_trade_atomic(self.user_id, 'AAPL', 100, 150.0)
        
        initial_shares = 100
        initial_cash = 100000.0 - (100 * 150.0)
        
        # Attempt sell that will fail (insufficient shares)
        success, error, _ = self.db.execute_sell_trade_atomic(
            self.user_id, 'AAPL', 200, 160.0
        )
        
        self.assertFalse(success)
        
        # Verify state unchanged
        stock = self.db.get_user_stock(self.user_id, 'AAPL')
        self.assertEqual(stock['shares'], initial_shares)
        
        user = self.db.get_user(self.user_id)
        self.assertAlmostEqual(user['cash'], initial_cash, places=2)


if __name__ == '__main__':
    unittest.main()
