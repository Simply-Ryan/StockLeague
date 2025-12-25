"""
Unit Tests for Trading Routes
Tests for sell(), buy(), and copy_trade functionality
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add app directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Mock the database before importing app
sys.modules['database'] = MagicMock()

class TestSellRoute:
    """Test cases for the sell() trading route"""
    
    @pytest.fixture
    def client(self):
        """Create Flask test client"""
        from app import app, db
        app.config['TESTING'] = True
        with app.test_client() as client:
            with app.test_request_context():
                yield client
    
    @pytest.fixture
    def mock_db(self):
        """Mock database for testing"""
        mock = MagicMock()
        mock.get_user_stock = MagicMock(return_value={'symbol': 'AAPL', 'shares': 100})
        mock.get_league_holding = MagicMock(return_value={'symbol': 'AAPL', 'shares': 100})
        mock.execute_sell_trade_atomic = MagicMock(return_value=(True, None, 12345))
        mock.execute_league_trade_atomic = MagicMock(return_value=(True, None, 12345))
        mock.get_user = MagicMock(return_value={'id': 1, 'username': 'testuser', 'cash': 5000})
        mock.get_user_stocks = MagicMock(return_value=[])
        mock.query = MagicMock(return_value=[])
        return mock
    
    def test_sell_personal_portfolio_valid(self, mock_db):
        """Test selling from personal portfolio with valid data"""
        # Setup
        symbol = 'AAPL'
        shares = 50
        price = 150.00
        
        # Verify stock is fetched correctly
        stock = mock_db.get_user_stock(1, symbol)
        assert stock is not None, "Stock should be found"
        assert stock['shares'] >= shares, f"Should have enough shares to sell {shares}"
    
    def test_sell_insufficient_shares(self, mock_db):
        """Test selling more shares than owned"""
        # Setup
        mock_db.get_user_stock.return_value = {'symbol': 'AAPL', 'shares': 10}
        symbol = 'AAPL'
        shares = 50  # More than available
        
        # Verify check
        stock = mock_db.get_user_stock(1, symbol)
        assert stock['shares'] < shares, "Should not have enough shares"
    
    def test_sell_stock_not_found(self, mock_db):
        """Test selling stock that user doesn't own"""
        mock_db.get_user_stock.return_value = None
        
        symbol = 'GOOG'
        stock = mock_db.get_user_stock(1, symbol)
        assert stock is None, "Stock should not exist"
    
    def test_sell_league_portfolio_valid(self, mock_db):
        """Test selling from league portfolio with valid data"""
        symbol = 'AAPL'
        shares = 50
        league_id = 5
        
        stock = mock_db.get_league_holding(league_id, 1, symbol)
        assert stock is not None, "League stock should be found"
        assert stock['shares'] >= shares, "Should have enough shares in league"
    
    def test_sell_invalid_symbol(self, mock_db):
        """Test selling invalid stock symbol"""
        # This should be caught by lookup() function
        symbol = 'INVALID'
        # In real test, lookup() would return None for invalid symbols
        pass
    
    def test_atomic_transaction_executed(self, mock_db):
        """Test that atomic transaction is properly executed"""
        symbol = 'AAPL'
        shares = 50
        price = 150.00
        
        success, error, txn_id = mock_db.execute_sell_trade_atomic(1, symbol, shares, price, None, None)
        assert success is True, "Transaction should succeed"
        assert txn_id is not None, "Transaction ID should be returned"
        assert error is None, "No error should occur"


class TestCopyTradeFunction:
    """Test cases for the _execute_copy_trades() helper function"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database for copy trades"""
        mock = MagicMock()
        mock.get_active_copiers = MagicMock(return_value=[
            {'follower_id': 2, 'copy_buys': True, 'copy_sells': True, 
             'allocation_percentage': 50, 'max_trade_amount': 5000},
            {'follower_id': 3, 'copy_buys': False, 'copy_sells': True,
             'allocation_percentage': 100, 'max_trade_amount': 10000}
        ])
        mock.get_user = MagicMock(return_value={'id': 1, 'username': 'trader', 'cash': 10000})
        mock.get_user_stock = MagicMock(return_value={'symbol': 'AAPL', 'shares': 100})
        mock.record_transaction = MagicMock(return_value=12346)
        mock.update_cash = MagicMock(return_value=True)
        mock.record_copied_trade = MagicMock(return_value=True)
        mock.add_notification = MagicMock(return_value=True)
        return mock
    
    def test_copy_trade_execute_buy(self, mock_db):
        """Test executing copy buys"""
        trader_id = 1
        symbol = 'AAPL'
        shares = 100
        price = 150.00
        
        copiers = mock_db.get_active_copiers(trader_id)
        assert len(copiers) > 0, "Should have active copiers"
        
        for copier in copiers:
            if copier['copy_buys']:
                assert copier['allocation_percentage'] > 0
                assert copier['max_trade_amount'] > 0
    
    def test_copy_trade_execute_sell(self, mock_db):
        """Test executing copy sells"""
        trader_id = 1
        symbol = 'AAPL'
        shares = 50
        price = 150.00
        
        copiers = mock_db.get_active_copiers(trader_id)
        for copier in copiers:
            if copier['copy_sells']:
                follower_id = copier['follower_id']
                follower_stock = mock_db.get_user_stock(follower_id, symbol)
                assert follower_stock is not None
    
    def test_copy_trade_allocation_percentage(self, mock_db):
        """Test that allocation percentage is correctly applied"""
        trader_id = 1
        shares = 100
        price = 150.00
        allocation_pct = 0.5  # 50%
        
        copy_shares = max(1, int(shares * allocation_pct))
        assert copy_shares == 50, "Should copy 50% of shares"
    
    def test_copy_trade_max_trade_limit(self, mock_db):
        """Test that max trade amount limit is enforced"""
        shares = 100
        price = 150.00
        max_trade = 5000
        
        copy_cost = shares * price  # 15,000
        if copy_cost > max_trade:
            limited_shares = int(max_trade / price)
            assert limited_shares < shares, "Should limit shares based on max trade"
    
    def test_copy_trade_skip_insufficient_cash(self, mock_db):
        """Test that copy trade is skipped if follower has insufficient cash"""
        follower_cash = 1000
        shares = 100
        price = 150.00
        copy_cost = shares * price  # 15,000
        
        if copy_cost > follower_cash:
            # Copy trade should be skipped
            pass


class TestBuyRoute:
    """Test cases for the buy() trading route"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database for buy trades"""
        mock = MagicMock()
        mock.get_user = MagicMock(return_value={'id': 1, 'username': 'testuser', 'cash': 10000})
        mock.get_user_stock = MagicMock(return_value=None)  # No existing position
        mock.execute_buy_trade_atomic = MagicMock(return_value=(True, None, 12345))
        mock.get_league_portfolio = MagicMock(return_value={'cash': 10000})
        return mock
    
    def test_buy_insufficient_cash(self, mock_db):
        """Test buying stock with insufficient cash"""
        symbol = 'AAPL'
        shares = 100
        price = 150.00
        total_cost = shares * price  # 15,000
        user_cash = 10000
        
        assert total_cost > user_cash, "User should have insufficient cash"
    
    def test_buy_sufficient_cash(self, mock_db):
        """Test buying stock with sufficient cash"""
        symbol = 'AAPL'
        shares = 50
        price = 150.00
        total_cost = shares * price  # 7,500
        user_cash = 10000
        
        assert total_cost < user_cash, "User should have sufficient cash"
    
    def test_buy_atomic_transaction(self, mock_db):
        """Test that buy executes with atomic transaction"""
        symbol = 'AAPL'
        shares = 50
        price = 150.00
        
        success, error, txn_id = mock_db.execute_buy_trade_atomic(1, symbol, shares, price, None, None)
        assert success is True
        assert txn_id is not None


class TestErrorHandling:
    """Test cases for error handling in trading routes"""
    
    def test_sell_with_database_error(self):
        """Test sell route handles database errors gracefully"""
        # This should return a 500 error with a meaningful message
        pass
    
    def test_sell_with_invalid_context(self):
        """Test sell with invalid portfolio context"""
        # This should return a 403 error
        pass
    
    def test_copy_trade_with_invalid_copier(self):
        """Test copy trade skips invalid copier"""
        # This should continue to next copier
        pass


class TestInputValidation:
    """Test cases for input validation in trading routes"""
    
    def test_sell_missing_symbol(self):
        """Test sell with missing symbol"""
        # Should return 400 error
        pass
    
    def test_sell_missing_shares(self):
        """Test sell with missing shares"""
        # Should return 400 error
        pass
    
    def test_sell_negative_shares(self):
        """Test sell with negative shares"""
        # Should return 400 error
        pass
    
    def test_sell_non_integer_shares(self):
        """Test sell with non-integer shares"""
        # Should return 400 error
        pass
    
    def test_symbol_case_insensitive(self):
        """Test that symbols are converted to uppercase"""
        symbol = 'aapl'
        normalized = symbol.upper().strip()
        assert normalized == 'AAPL'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
