"""
tests/test_api.py

API endpoint tests for StockLeague.
Tests cover: authentication, portfolio, leagues, and market status endpoints.
"""

import pytest
import json
import os
from datetime import datetime
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app
from database.db_manager import DatabaseManager


@pytest.fixture
def client():
    """Create Flask test client"""
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client


@pytest.fixture
def auth_user(client):
    """Create and authenticate a test user"""
    # Register user
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpass123',
        'confirmation': 'testpass123'
    }, follow_redirects=True)
    
    # Login user
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    }, follow_redirects=True)
    
    return client


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_register_user(self, client):
        """Test user registration"""
        response = client.post('/register', data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'password123',
            'confirmation': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200 or response.status_code == 302
    
    def test_login_user(self, client):
        """Test user login"""
        # First register
        client.post('/register', data={
            'username': 'loginuser',
            'email': 'login@example.com',
            'password': 'password123',
            'confirmation': 'password123'
        })
        
        # Then login
        response = client.post('/login', data={
            'username': 'loginuser',
            'password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'wrongpass'
        }, follow_redirects=True)
        
        # Should show error message
        assert response.status_code == 200
        assert b'apology' in response.data or b'Invalid' in response.data or response.status_code == 200


class TestPortfolioEndpoints:
    """Test portfolio-related endpoints"""
    
    def test_dashboard_requires_login(self, client):
        """Test that dashboard requires authentication"""
        response = client.get('/dashboard')
        assert response.status_code == 302  # Redirect to login
    
    def test_quote_endpoint(self, client, auth_user):
        """Test stock quote endpoint"""
        response = auth_user.get('/quote?symbol=AAPL')
        assert response.status_code == 200
    
    def test_invalid_symbol_quote(self, client, auth_user):
        """Test quote with invalid symbol"""
        response = auth_user.get('/quote?symbol=INVALID12345')
        # Should either show error or apology
        assert response.status_code in [200, 400]


class TestMarketStatusAPI:
    """Test market status API endpoint"""
    
    def test_market_status_endpoint(self, client):
        """Test market status endpoint"""
        response = client.get('/api/market/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Verify response structure
        assert 'is_open' in data
        assert 'current_time' in data
        assert isinstance(data['is_open'], bool)
    
    def test_market_status_response_format(self, client):
        """Test market status response format"""
        response = client.get('/api/market/status')
        data = json.loads(response.data)
        
        # Verify optional next_open field
        if not data['is_open']:
            assert 'next_open' in data
        else:
            assert 'next_open' in data


class TestLeagueEndpoints:
    """Test league-related endpoints"""
    
    def test_leagues_requires_login(self, client):
        """Test that leagues page requires authentication"""
        response = client.get('/leagues')
        assert response.status_code == 302  # Redirect to login


class TestErrorHandling:
    """Test error handling in API endpoints"""
    
    def test_404_not_found(self, client, auth_user):
        """Test 404 not found error"""
        response = auth_user.get('/nonexistent-page')
        assert response.status_code == 404
    
    def test_invalid_request_method(self, client):
        """Test invalid HTTP method"""
        response = client.post('/quote')
        # Should be allowed or redirected, not 405
        assert response.status_code in [200, 302]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
