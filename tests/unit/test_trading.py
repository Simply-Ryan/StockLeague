"""
tests/unit/test_trading.py

Unit tests for trading functionality including:
- Atomic transaction execution
- Error handling and validation
- Rate limiting and throttling
- Buy/sell operations
"""

import unittest
import os
import tempfile
import sqlite3
from datetime import datetime, timedelta
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db_manager import DatabaseManager
from trade_throttle import (
    validate_trade_throttle, record_trade, check_trade_cooldown,
    check_trade_frequency, check_position_size_limit,
    check_daily_loss_limit, get_user_trade_history, clear_user_throttle_data
)


class TestDatabase(unittest.TestCase):
    """Tests for database operations"""
    
    def setUp(self):
        """Create temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = DatabaseManager(self.temp_db.name)
        
        # Create test user
        self.user_id = self.create_test_user(username='testuser', cash=100000.0)
        
    def tearDown(self):
        """Clean up temporary database"""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
            
    def create_test_user(self, username='testuser', cash=100000.0):
        """Helper to create a test user"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, hash, cash, email)
            VALUES (?, ?, ?, ?)
        """, (username, 'test_hash', cash, f'{username}@test.com'))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    
    # ========================================================================
    # ATOMIC BUY TRANSACTION TESTS
    # ========================================================================
    
    def test_buy_trade_atomic_success(self):
        """Test successful atomic buy transaction"""
        success, error_msg, txn_id = self.db.execute_buy_trade_atomic(
            user_id=self.user_id,
            symbol='AAPL',
            shares=100,
            price=150.0
        )
        
        self.assertTrue(success, f"Buy failed: {error_msg}")
        self.assertIsNotNone(txn_id)
        self.assertIsNone(error_msg)
        
        # Verify user cash was deducted
        user = self.db.get_user(self.user_id)
        expected_cash = 100000.0 - (100 * 150.0)
        self.assertAlmostEqual(user['cash'], expected_cash, places=2)
        
        # Verify stock holding was created
        stock = self.db.get_user_stock(self.user_id, 'AAPL')
        self.assertEqual(stock['shares'], 100)
        self.assertEqual(stock['avg_cost'], 150.0)
    
    def test_buy_trade_insufficient_funds(self):
        """Test buy fails when insufficient funds"""
        # Create user with only $5000
        user_id = self.create_test_user(username='pooruser', cash=5000.0)
        
        success, error_msg, txn_id = self.db.execute_buy_trade_atomic(
            user_id=user_id,
            symbol='AAPL',
            shares=100,
            price=150.0  # Need $15,000
        )
        
        self.assertFalse(success)
        self.assertIn("Insufficient funds", error_msg)
        self.assertIsNone(txn_id)
        
        # Verify cash wasn't modified
        user = self.db.get_user(user_id)
        self.assertEqual(user['cash'], 5000.0)
    
    def test_buy_trade_avg_cost_calculation(self):
        """Test average cost is recalculated correctly"""
        user_id = self.user_id
        
        # First buy: 100 shares @ $100
        s1, e1, _ = self.db.execute_buy_trade_atomic(user_id, 'AAPL', 100, 100.0)
        self.assertTrue(s1)
        
        # Second buy: 100 shares @ $200
        s2, e2, _ = self.db.execute_buy_trade_atomic(user_id, 'AAPL', 100, 200.0)
        self.assertTrue(s2)
        
        # Verify average cost: (100*100 + 100*200) / 200 = 150
        stock = self.db.get_user_stock(user_id, 'AAPL')
        self.assertEqual(stock['shares'], 200)
        self.assertEqual(stock['avg_cost'], 150.0)
    
    def test_buy_trade_user_not_found(self):
        """Test buy fails for non-existent user"""
        success, error_msg, txn_id = self.db.execute_buy_trade_atomic(
            user_id=99999,
            symbol='AAPL',
            shares=100,
            price=150.0
        )
        
        self.assertFalse(success)
        self.assertIn("User not found", error_msg)
        self.assertIsNone(txn_id)
    
    # ========================================================================
    # ATOMIC SELL TRANSACTION TESTS
    # ========================================================================
    
    def test_sell_trade_atomic_success(self):
        """Test successful atomic sell transaction"""
        # First create a position
        self.db.execute_buy_trade_atomic(self.user_id, 'AAPL', 100, 150.0)
        
        # Then sell half
        success, error_msg, txn_id = self.db.execute_sell_trade_atomic(
            user_id=self.user_id,
            symbol='AAPL',
            shares=50,
            price=160.0
        )
        
        self.assertTrue(success, f"Sell failed: {error_msg}")
        self.assertIsNotNone(txn_id)
        
        # Verify shares reduced
        stock = self.db.get_user_stock(self.user_id, 'AAPL')
        self.assertEqual(stock['shares'], 50)
        
        # Verify cash increased
        user = self.db.get_user(self.user_id)
        expected_cash = 100000.0 - (100 * 150.0) + (50 * 160.0)
        self.assertAlmostEqual(user['cash'], expected_cash, places=2)
    
    def test_sell_trade_insufficient_shares(self):
        """Test sell fails when insufficient shares"""
        # Create position with 50 shares
        self.db.execute_buy_trade_atomic(self.user_id, 'AAPL', 50, 150.0)
        
        # Try to sell more than available
        success, error_msg, txn_id = self.db.execute_sell_trade_atomic(
            user_id=self.user_id,
            symbol='AAPL',
            shares=100,
            price=160.0
        )
        
        self.assertFalse(success)
        self.assertIn("Insufficient shares", error_msg)
        self.assertIsNone(txn_id)
        
        # Verify holdings unchanged
        stock = self.db.get_user_stock(self.user_id, 'AAPL')
        self.assertEqual(stock['shares'], 50)
    
    def test_sell_trade_sell_all_deletes_position(self):
        """Test selling all shares deletes the position"""
        # Create position
        self.db.execute_buy_trade_atomic(self.user_id, 'AAPL', 100, 150.0)
        
        # Sell all
        success, error_msg, _ = self.db.execute_sell_trade_atomic(
            user_id=self.user_id,
            symbol='AAPL',
            shares=100,
            price=160.0
        )
        
        self.assertTrue(success)
        
        # Verify position deleted (returns None)
        stock = self.db.get_user_stock(self.user_id, 'AAPL')
        self.assertIsNone(stock)
    
    def test_sell_nonexistent_position(self):
        """Test sell fails for position that doesn't exist"""
        success, error_msg, txn_id = self.db.execute_sell_trade_atomic(
            user_id=self.user_id,
            symbol='AAPL',
            shares=100,
            price=160.0
        )
        
        self.assertFalse(success)
        self.assertIn("Insufficient shares", error_msg)
        self.assertIsNone(txn_id)
    
    # ========================================================================
    # TRANSACTION ISOLATION TESTS
    # ========================================================================
    
    def test_transaction_is_atomic(self):
        """Test that transaction is atomic (all-or-nothing)"""
        # This would require multi-threaded test to truly verify
        # For now, verify successful transaction is complete
        
        success, error_msg, txn_id = self.db.execute_buy_trade_atomic(
            self.user_id, 'AAPL', 100, 150.0
        )
        
        self.assertTrue(success)
        
        # All of these should exist:
        user = self.db.get_user(self.user_id)
        self.assertLess(user['cash'], 100000.0)  # Cash deducted
        
        stock = self.db.get_user_stock(self.user_id, 'AAPL')
        self.assertEqual(stock['shares'], 100)  # Stock created
        
        transactions = self.db.get_transactions(self.user_id)
        self.assertEqual(len(transactions), 1)  # Transaction recorded


class TestTradeThrottling(unittest.TestCase):
    """Tests for trade throttling functionality"""
    
    def setUp(self):
        """Clear throttle data before each test"""
        clear_user_throttle_data(1)
    
    def tearDown(self):
        """Clean up after each test"""
        clear_user_throttle_data(1)
    
    # ========================================================================
    # TRADE COOLDOWN TESTS
    # ========================================================================
    
    def test_trade_cooldown_allows_first_trade(self):
        """Test first trade is always allowed"""
        allowed, msg, remaining = check_trade_cooldown(1, 'AAPL', cooldown_seconds=2)
        self.assertTrue(allowed)
        self.assertIsNone(msg)
    
    def test_trade_cooldown_blocks_rapid_trade(self):
        """Test rapid trade of same symbol is blocked"""
        # Record first trade
        record_trade(1, 'AAPL', 'buy', 100, 150.0)
        
        # Immediately try second
        allowed, msg, remaining = check_trade_cooldown(1, 'AAPL', cooldown_seconds=2)
        self.assertFalse(allowed)
        self.assertIn("wait", msg.lower())
        self.assertGreater(remaining, 0)
    
    def test_trade_cooldown_different_symbols(self):
        """Test cooldown only applies to same symbol"""
        # Record trade of AAPL
        record_trade(1, 'AAPL', 'buy', 100, 150.0)
        
        # Different symbol should be allowed
        allowed, msg, _ = check_trade_cooldown(1, 'MSFT', cooldown_seconds=2)
        self.assertTrue(allowed)
    
    # ========================================================================
    # TRADE FREQUENCY TESTS
    # ========================================================================
    
    def test_trade_frequency_allows_within_limit(self):
        """Test trades within limit are allowed"""
        # Record 5 trades
        for i in range(5):
            record_trade(1, f'STOCK{i}', 'buy', 1, 100.0)
        
        # 6th should be allowed (limit is 10/min)
        allowed, msg, _ = check_trade_frequency(1, max_trades_per_minute=10)
        self.assertTrue(allowed)
    
    def test_trade_frequency_blocks_over_limit(self):
        """Test trades over limit are blocked"""
        # Record 10 trades
        for i in range(10):
            record_trade(1, f'STOCK{i}', 'buy', 1, 100.0)
        
        # 11th should be blocked
        allowed, msg, _ = check_trade_frequency(1, max_trades_per_minute=10)
        self.assertFalse(allowed)
        self.assertIn("frequency", msg.lower())
    
    # ========================================================================
    # POSITION SIZE TESTS
    # ========================================================================
    
    def test_position_size_allows_small_position(self):
        """Test small position is allowed"""
        allowed, msg = check_position_size_limit(
            user_id=1,
            symbol='AAPL',
            current_shares=0,
            new_shares=100,
            cash=100000.0,
            price=150.0,
            max_position_pct=25.0
        )
        # Position: 100 * $150 = $15,000 / $115,000 = 13% < 25%
        self.assertTrue(allowed)
    
    def test_position_size_blocks_large_position(self):
        """Test oversized position is blocked"""
        allowed, msg = check_position_size_limit(
            user_id=1,
            symbol='AAPL',
            current_shares=0,
            new_shares=500,  # $75,000
            cash=10000.0,
            price=150.0,
            max_position_pct=25.0
        )
        # Position: 500 * $150 = $75,000 / $85,000 = 88% > 25%
        self.assertFalse(allowed)
        self.assertIn("position", msg.lower())
    
    # ========================================================================
    # DAILY LOSS TESTS
    # ========================================================================
    
    def test_daily_loss_allows_before_limit(self):
        """Test trading allowed before loss limit"""
        allowed, msg = check_daily_loss_limit(
            user_id=1,
            current_daily_loss=-2000.0,
            max_daily_loss=-5000.0
        )
        # -$2000 > -$5000 limit
        self.assertTrue(allowed)
    
    def test_daily_loss_blocks_at_limit(self):
        """Test trading blocked when loss limit reached"""
        allowed, msg = check_daily_loss_limit(
            user_id=1,
            current_daily_loss=-5000.0,
            max_daily_loss=-5000.0
        )
        # -$5000 == -$5000 limit
        self.assertFalse(allowed)
        self.assertIn("loss limit", msg.lower())
    
    def test_daily_loss_blocks_over_limit(self):
        """Test trading blocked when over loss limit"""
        allowed, msg = check_daily_loss_limit(
            user_id=1,
            current_daily_loss=-6000.0,
            max_daily_loss=-5000.0
        )
        # -$6000 < -$5000 limit
        self.assertFalse(allowed)
    
    # ========================================================================
    # COMPOSITE VALIDATION TESTS
    # ========================================================================
    
    def test_comprehensive_validation_all_pass(self):
        """Test comprehensive validation passes when all checks pass"""
        allowed, msg = validate_trade_throttle(
            user_id=1,
            symbol='AAPL',
            action='buy',
            shares=100,
            price=150.0,
            current_shares=0,
            cash=100000.0,
            current_daily_loss=-2000.0
        )
        self.assertTrue(allowed)
        self.assertIsNone(msg)
    
    def test_comprehensive_validation_fails_on_cooldown(self):
        """Test comprehensive validation fails on cooldown"""
        record_trade(1, 'AAPL', 'buy', 100, 150.0)
        
        allowed, msg = validate_trade_throttle(
            user_id=1,
            symbol='AAPL',
            action='buy',
            shares=100,
            price=150.0,
            current_shares=0,
            cash=100000.0,
            current_daily_loss=0
        )
        self.assertFalse(allowed)
        self.assertIn("wait", msg.lower())
    
    def test_comprehensive_validation_fails_on_position(self):
        """Test comprehensive validation fails on position size"""
        allowed, msg = validate_trade_throttle(
            user_id=1,
            symbol='AAPL',
            action='buy',
            shares=500,
            price=150.0,
            current_shares=0,
            cash=10000.0,
            current_daily_loss=0,
            max_position_pct=25.0
        )
        self.assertFalse(allowed)
        self.assertIn("position", msg.lower())


class TestTradeHistory(unittest.TestCase):
    """Tests for trade history tracking"""
    
    def setUp(self):
        clear_user_throttle_data(1)
    
    def tearDown(self):
        clear_user_throttle_data(1)
    
    def test_record_and_retrieve_trades(self):
        """Test recording and retrieving trades"""
        record_trade(1, 'AAPL', 'buy', 100, 150.0)
        record_trade(1, 'MSFT', 'sell', 50, 300.0)
        
        history = get_user_trade_history(1, minutes=60)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0][1], 'AAPL')
        self.assertEqual(history[1][1], 'MSFT')
    
    def test_trade_history_time_filtering(self):
        """Test trade history respects time window"""
        record_trade(1, 'AAPL', 'buy', 100, 150.0)
        
        # Should be included in 60-minute window
        history = get_user_trade_history(1, minutes=60)
        self.assertEqual(len(history), 1)
        
        # Should be excluded from 0-minute window
        history = get_user_trade_history(1, minutes=0)
        self.assertEqual(len(history), 0)


if __name__ == '__main__':
    unittest.main()
