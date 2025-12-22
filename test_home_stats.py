#!/usr/bin/env python3
"""
Test script to verify home page stats queries and database data.
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_stats():
    """Test the home page stats queries."""
    print("=" * 60)
    print("Testing Home Page Stats Queries")
    print("=" * 60)
    
    db = DatabaseManager()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Test 1: List all tables
    print("\n1. TABLES IN DATABASE:")
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        for table in tables:
            print(f"   - {table['name']}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Test 2: Count traders
    print("\n2. COUNT USERS (TRADERS):")
    try:
        cursor.execute("SELECT COUNT(*) as count FROM users")
        result = cursor.fetchone()
        if result:
            count_val = result['count'] if isinstance(result, dict) else result[0]
            print(f"   Count: {count_val}")
            print(f"   Type: {type(count_val)}")
            print(f"   Result dict: {dict(result) if hasattr(result, 'keys') else 'N/A'}")
    except Exception as e:
        print(f"   ERROR: {e}", exc_info=True)
    
    # Test 3: Count leagues
    print("\n3. COUNT LEAGUES:")
    try:
        cursor.execute("SELECT COUNT(*) as count FROM leagues")
        result = cursor.fetchone()
        if result:
            count_val = result['count'] if isinstance(result, dict) else result[0]
            print(f"   Count: {count_val}")
            print(f"   Type: {type(count_val)}")
    except Exception as e:
        print(f"   ERROR: {e}", exc_info=True)
    
    # Test 4: Count league transactions
    print("\n4. COUNT LEAGUE_TRANSACTIONS:")
    try:
        cursor.execute("SELECT COUNT(*) as count FROM league_transactions")
        result = cursor.fetchone()
        if result:
            count_val = result['count'] if isinstance(result, dict) else result[0]
            print(f"   Count: {count_val}")
            print(f"   Type: {type(count_val)}")
    except Exception as e:
        print(f"   ERROR: {e}", exc_info=True)
    
    # Test 5: Count personal transactions
    print("\n5. COUNT TRANSACTIONS:")
    try:
        cursor.execute("SELECT COUNT(*) as count FROM transactions")
        result = cursor.fetchone()
        if result:
            count_val = result['count'] if isinstance(result, dict) else result[0]
            print(f"   Count: {count_val}")
            print(f"   Type: {type(count_val)}")
    except Exception as e:
        print(f"   ERROR: {e}", exc_info=True)
    
    # Test 6: Sum portfolio cash
    print("\n6. SUM LEAGUE_PORTFOLIOS CASH:")
    try:
        cursor.execute("SELECT SUM(cash) as total_cash FROM league_portfolios")
        result = cursor.fetchone()
        if result:
            cash_val = result['total_cash'] if isinstance(result, dict) else result[0]
            print(f"   Total: {cash_val}")
            print(f"   Type: {type(cash_val)}")
    except Exception as e:
        print(f"   ERROR: {e}", exc_info=True)
    
    # Test 7: Detailed user data
    print("\n7. SAMPLE USERS:")
    try:
        cursor.execute("SELECT id, username, cash FROM users LIMIT 5")
        users = cursor.fetchall()
        for user in users:
            print(f"   - ID: {user['id']}, Username: {user['username']}, Cash: {user['cash']}")
    except Exception as e:
        print(f"   ERROR: {e}", exc_info=True)
    
    # Test 8: Detailed league data
    print("\n8. SAMPLE LEAGUES:")
    try:
        cursor.execute("SELECT id, name, creator_id FROM leagues LIMIT 5")
        leagues = cursor.fetchall()
        for league in leagues:
            print(f"   - ID: {league['id']}, Name: {league['name']}, Creator: {league['creator_id']}")
    except Exception as e:
        print(f"   ERROR: {e}", exc_info=True)
    
    # Test 9: Detailed league portfolio data
    print("\n9. SAMPLE LEAGUE_PORTFOLIOS:")
    try:
        cursor.execute("SELECT id, league_id, user_id, cash FROM league_portfolios LIMIT 5")
        portfolios = cursor.fetchall()
        for portfolio in portfolios:
            print(f"   - ID: {portfolio['id']}, League: {portfolio['league_id']}, User: {portfolio['user_id']}, Cash: {portfolio['cash']}")
    except Exception as e:
        print(f"   ERROR: {e}", exc_info=True)
    
    conn.close()
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == '__main__':
    test_stats()
