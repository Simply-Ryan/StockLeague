#!/usr/bin/env python3
"""
Seed the database with test data if it's empty.
Run this once to add initial test data for the home page stats.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager

def seed_test_data():
    """Add test data if database is empty."""
    db = DatabaseManager()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Check if data exists
    cursor.execute("SELECT COUNT(*) as count FROM users")
    user_count = cursor.fetchone()['count']
    
    print(f"Current users: {user_count}")
    
    if user_count == 0:
        print("\n[+] Seeding database with test data...")
        
        # Add test users
        cursor.execute("""
            INSERT INTO users (username, hash, email, cash)
            VALUES 
                (?, ?, ?, ?),
                (?, ?, ?, ?)
        """, (
            "testuser1", "hashed_password_1", "test1@example.com", 15000.00,
            "testuser2", "hashed_password_2", "test2@example.com", 12000.00,
        ))
        conn.commit()
        print("    ✓ Added 2 test users")
        
        # Get user IDs for league creation
        cursor.execute("SELECT id FROM users ORDER BY id LIMIT 2")
        user_ids = [row['id'] for row in cursor.fetchall()]
        
        # Add test league
        cursor.execute("""
            INSERT INTO leagues (name, description, creator_id, starting_cash)
            VALUES (?, ?, ?, ?)
        """, ("Test League", "A test league for development", user_ids[0], 10000.00))
        conn.commit()
        print("    ✓ Added 1 test league")
        
        # Get league ID
        cursor.execute("SELECT id FROM leagues ORDER BY id DESC LIMIT 1")
        league_id = cursor.fetchone()['id']
        
        # Add league members
        cursor.execute("""
            INSERT INTO league_members (league_id, user_id, joined_at, score)
            VALUES (?, ?, datetime('now'), ?), (?, ?, datetime('now'), ?)
        """, (league_id, user_ids[0], 1000.00, league_id, user_ids[1], 950.00))
        conn.commit()
        print("    ✓ Added 2 league members")
        
        # Add league portfolios
        cursor.execute("""
            INSERT INTO league_portfolios (league_id, user_id, cash)
            VALUES (?, ?, ?), (?, ?, ?)
        """, (league_id, user_ids[0], 15000.00, league_id, user_ids[1], 12000.00))
        conn.commit()
        print("    ✓ Added league portfolios")
        
        # Add sample transactions
        cursor.execute("""
            INSERT INTO league_transactions (league_id, user_id, symbol, shares, price, type)
            VALUES 
                (?, ?, ?, ?, ?, ?),
                (?, ?, ?, ?, ?, ?),
                (?, ?, ?, ?, ?, ?)
        """, (
            league_id, user_ids[0], "AAPL", 10, 150.00, "BUY",
            league_id, user_ids[0], "GOOGL", 5, 2800.00, "BUY",
            league_id, user_ids[1], "MSFT", 8, 300.00, "BUY",
        ))
        conn.commit()
        print("    ✓ Added 3 league transactions")
        
        # Add personal transactions
        cursor.execute("""
            INSERT INTO transactions (user_id, symbol, shares, price, type)
            VALUES 
                (?, ?, ?, ?, ?),
                (?, ?, ?, ?, ?)
        """, (
            user_ids[0], "TSLA", 3, 250.00, "BUY",
            user_ids[1], "AMZN", 2, 3300.00, "BUY",
        ))
        conn.commit()
        print("    ✓ Added 2 personal transactions")
        
        print("\n✅ Database seeding complete!")
    else:
        print(f"\n[i] Database already has {user_count} users. Skipping seed.")
    
    conn.close()

if __name__ == '__main__':
    seed_test_data()
