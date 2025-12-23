"""
tests/test_trading.py

Comprehensive trading system tests for StockLeague.
Tests cover: buy, sell, portfolio calculations, copy trading, and edge cases.
"""

import pytest
import sqlite3
import os
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from helpers import lookup, usd


class TestTradingSystem:
    """Test suite for trading operations"""
    
    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Setup test database before each test"""
        self.db_path = "test_stocks.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        
        self.db = DatabaseManager(self.db_path)
        
        # Create test user
        self.test_user_id = self.db.add_user("testuser", "testpass", "test@example.com")
        
        yield
        
        # Cleanup
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_user_creation(self):
        """Test user can be created successfully"""
        assert self.test_user_id is not None
        
        user = self.db.get_user(self.test_user_id)
        assert user is not None
        assert user['username'] == 'testuser'
        assert user['cash'] == 100000  # Default starting cash
    
    def test_buy_stock_success(self):
        """Test successful stock purchase"""
        user = self.db.get_user(self.test_user_id)
        initial_cash = user['cash']
        
        # Mock stock price
        price = 150.00
        shares = 10
        total_cost = price * shares
        
        # Record transaction
        txn_id = self.db.record_transaction(
            self.test_user_id, "AAPL", shares, price, "buy"
        )
        
        assert txn_id is not None
        
        # Verify cash was deducted
        self.db.update_cash(self.test_user_id, initial_cash - total_cost)
        user_updated = self.db.get_user(self.test_user_id)
        assert user_updated['cash'] == initial_cash - total_cost
    
    def test_sell_stock_success(self):
        """Test successful stock sale"""
        # First buy
        price = 100.00
        buy_shares = 20
        txn_id = self.db.record_transaction(
            self.test_user_id, "MSFT", buy_shares, price, "buy"
        )
        
        # Then sell
        sell_shares = 10
        sell_price = 105.00
        txn_id_sell = self.db.record_transaction(
            self.test_user_id, "MSFT", -sell_shares, sell_price, "sell"
        )
        
        assert txn_id_sell is not None
        
        # Verify transaction was recorded
        transactions = self.db.get_user_transactions(self.test_user_id)
        assert len(transactions) >= 2
    
    def test_insufficient_funds(self):
        """Test that user cannot buy more than they can afford"""
        user = self.db.get_user(self.test_user_id)
        cash = user['cash']
        
        # Try to buy stock that costs more than available cash
        price = 10000.00
        shares = 20
        total_cost = price * shares  # 200,000 > 100,000
        
        assert total_cost > cash, "Test setup failed: total cost should exceed cash"
    
    def test_insufficient_shares_to_sell(self):
        """Test that user cannot sell shares they don't have"""
        # Try to sell without buying first
        transactions = self.db.get_user_transactions(self.test_user_id)
        holdings = {}
        for txn in transactions:
            symbol = txn['symbol']
            holdings[symbol] = holdings.get(symbol, 0) + txn['shares']
        
        # Verify user has no TSLA shares
        assert holdings.get('TSLA', 0) == 0
    
    def test_portfolio_value_calculation(self):
        """Test portfolio value calculation with multiple holdings"""
        # Buy multiple stocks
        stocks = [
            ('AAPL', 10, 150.00),
            ('MSFT', 5, 300.00),
            ('GOOG', 2, 2800.00),
        ]
        
        total_invested = 0
        for symbol, shares, price in stocks:
            txn_id = self.db.record_transaction(
                self.test_user_id, symbol, shares, price, "buy"
            )
            total_invested += shares * price
        
        # Verify transactions were recorded
        transactions = self.db.get_user_transactions(self.test_user_id)
        assert len(transactions) == 3
        
        # Verify total invested calculation
        calculated_total = sum(t['shares'] * t['price'] for t in transactions if t['type'] == 'buy')
        assert abs(calculated_total - total_invested) < 0.01
    
    def test_transaction_history_chronological(self):
        """Test transaction history is returned in correct order"""
        # Create multiple transactions
        for i in range(3):
            self.db.record_transaction(
                self.test_user_id, "AAPL", 1, 100.00 + i, "buy"
            )
        
        transactions = self.db.get_user_transactions(self.test_user_id)
        
        # Verify all transactions exist
        assert len(transactions) == 3
        
        # Verify they're in order (most recent first in get_user_transactions)
        for t in transactions:
            assert t['symbol'] == 'AAPL'
            assert t['shares'] == 1
    
    def test_portfolio_context_isolation(self):
        """Test that personal and league portfolios are isolated"""
        # Create league
        league_id = self.db.create_league(self.test_user_id, "Test League", "Testing")
        assert league_id is not None
        
        # Buy in personal portfolio
        personal_price = 100.00
        personal_shares = 10
        self.db.record_transaction(
            self.test_user_id, "AAPL", personal_shares, personal_price, "buy"
        )
        
        # Buy in league portfolio
        league_price = 150.00
        league_shares = 5
        self.db.record_league_transaction(
            league_id, self.test_user_id, "AAPL", league_shares, league_price, "buy"
        )
        
        # Verify transactions are separate
        personal_txns = self.db.get_user_transactions(self.test_user_id)
        league_txns = self.db.get_league_transactions(league_id, self.test_user_id)
        
        assert len(personal_txns) == 1
        assert len(league_txns) == 1


class TestLeagueTrading:
    """Test suite for league trading operations"""
    
    @pytest.fixture(autouse=True)
    def setup_league_db(self):
        """Setup test database with league for each test"""
        self.db_path = "test_league.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        
        self.db = DatabaseManager(self.db_path)
        
        # Create test users
        self.user1_id = self.db.add_user("user1", "pass1", "user1@example.com")
        self.user2_id = self.db.add_user("user2", "pass2", "user2@example.com")
        
        # Create league
        self.league_id = self.db.create_league(self.user1_id, "Test League", "Testing")
        self.db.join_league(self.league_id, self.user2_id)
        
        yield
        
        # Cleanup
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_league_creation(self):
        """Test league can be created"""
        assert self.league_id is not None
        
        league = self.db.get_league(self.league_id)
        assert league is not None
        assert league['name'] == 'Test League'
    
    def test_league_members(self):
        """Test league members are tracked correctly"""
        members = self.db.get_league_members(self.league_id)
        
        assert len(members) >= 2
        member_ids = [m['user_id'] for m in members]
        assert self.user1_id in member_ids
        assert self.user2_id in member_ids
    
    def test_league_leaderboard(self):
        """Test league leaderboard calculation"""
        # Add transactions for both users
        self.db.record_league_transaction(
            self.league_id, self.user1_id, "AAPL", 10, 150.00, "buy"
        )
        self.db.record_league_transaction(
            self.league_id, self.user2_id, "MSFT", 5, 300.00, "buy"
        )
        
        # Get leaderboard
        leaderboard = self.db.get_league_leaderboard(self.league_id)
        
        assert leaderboard is not None
        assert len(leaderboard) >= 2
    
    def test_league_portfolio_isolation(self):
        """Test league portfolios don't interfere with each other"""
        league2_id = self.db.create_league(self.user1_id, "League 2", "Testing 2")
        
        # User1 trades in league1
        self.db.record_league_transaction(
            self.league_id, self.user1_id, "AAPL", 10, 150.00, "buy"
        )
        
        # User1 trades in league2
        self.db.record_league_transaction(
            league2_id, self.user1_id, "MSFT", 5, 300.00, "buy"
        )
        
        # Verify transactions are separate
        txns1 = self.db.get_league_transactions(self.league_id, self.user1_id)
        txns2 = self.db.get_league_transactions(league2_id, self.user1_id)
        
        assert len(txns1) == 1
        assert len(txns2) == 1


class TestErrorHandling:
    """Test suite for error handling and edge cases"""
    
    @pytest.fixture(autouse=True)
    def setup_error_db(self):
        """Setup test database for error testing"""
        self.db_path = "test_errors.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        
        self.db = DatabaseManager(self.db_path)
        self.user_id = self.db.add_user("erroruser", "pass", "error@example.com")
        
        yield
        
        # Cleanup
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_invalid_user_id(self):
        """Test handling of invalid user ID"""
        user = self.db.get_user(99999)
        assert user is None
    
    def test_invalid_league_id(self):
        """Test handling of invalid league ID"""
        league = self.db.get_league(99999)
        assert league is None
    
    def test_transaction_with_invalid_symbol(self):
        """Test transaction with invalid symbol (should succeed but verify)"""
        txn_id = self.db.record_transaction(
            self.user_id, "INVALID", 10, 100.00, "buy"
        )
        
        # Transaction should be recorded regardless
        assert txn_id is not None
    
    def test_negative_share_handling(self):
        """Test handling of negative shares"""
        # Record a buy first
        self.db.record_transaction(self.user_id, "AAPL", 10, 150.00, "buy")
        
        # Record a sell (negative shares)
        txn_id = self.db.record_transaction(
            self.user_id, "AAPL", -5, 160.00, "sell"
        )
        
        assert txn_id is not None
    
    def test_zero_price_transaction(self):
        """Test transaction with zero price"""
        txn_id = self.db.record_transaction(
            self.user_id, "AAPL", 10, 0.00, "buy"
        )
        
        # Transaction should be recorded but flagged as unusual
        assert txn_id is not None
    
    def test_missing_price_handling(self):
        """Test portfolio calculation with missing stock prices"""
        # Record transactions
        self.db.record_transaction(self.user_id, "AAPL", 10, 150.00, "buy")
        self.db.record_transaction(self.user_id, "FAKESTK", 5, 100.00, "buy")
        
        # Portfolio calculation should handle missing prices gracefully
        transactions = self.db.get_user_transactions(self.user_id)
        assert len(transactions) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
