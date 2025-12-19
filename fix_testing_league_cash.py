#!/usr/bin/env python3
"""
Fix portfolio starting cash for Testing League

This script corrects the portfolio cash for users in the Testing League
to match the league's configured starting_cash of 20000.
"""

import sqlite3
import sys

def fix_testing_league_portfolios():
    """Fix portfolios in Testing League to use correct starting cash"""
    
    db_path = "database/stocks.db"
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Find Testing League
        cursor.execute("SELECT id, starting_cash FROM leagues WHERE name = 'Testing League'")
        league = cursor.fetchone()
        
        if not league:
            print("❌ Testing League not found in database")
            return False
        
        league_id = league['id']
        correct_cash = league['starting_cash']
        
        print(f"✓ Found Testing League (ID: {league_id})")
        print(f"  League starting_cash: ${correct_cash}")
        
        # Get current portfolios
        cursor.execute(
            "SELECT id, user_id, cash FROM league_portfolios WHERE league_id = ?",
            (league_id,)
        )
        portfolios = cursor.fetchall()
        
        if not portfolios:
            print("✓ No portfolios found for Testing League")
            return True
        
        print(f"\n✓ Found {len(portfolios)} portfolios:")
        for portfolio in portfolios:
            print(f"  - User {portfolio['user_id']}: ${portfolio['cash']}")
        
        # Update portfolios to correct cash amount
        cursor.execute(
            "UPDATE league_portfolios SET cash = ? WHERE league_id = ?",
            (correct_cash, league_id)
        )
        
        conn.commit()
        
        print(f"\n✅ Updated {cursor.rowcount} portfolios to ${correct_cash}")
        
        # Verify update
        cursor.execute(
            "SELECT id, user_id, cash FROM league_portfolios WHERE league_id = ?",
            (league_id,)
        )
        updated = cursor.fetchall()
        
        print(f"\n✓ Verification:")
        for portfolio in updated:
            print(f"  - User {portfolio['user_id']}: ${portfolio['cash']}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = fix_testing_league_portfolios()
    sys.exit(0 if success else 1)
