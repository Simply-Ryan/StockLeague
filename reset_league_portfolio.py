from database.db_manager import DatabaseManager
import sqlite3

db = DatabaseManager()
conn = db.get_connection()
cursor = conn.cursor()

print("=== Recreating League Portfolio for User 1 in League 1 ===\n")

# Get league starting cash
league = db.get_league(1)
starting_cash = league.get('starting_cash', 10000.0)

print(f"League '{league['name']}' starting cash: ${starting_cash}")

# Delete existing portfolio and holdings
print("\nDeleting existing league portfolio and holdings...")
cursor.execute("DELETE FROM league_portfolios WHERE league_id = 1 AND user_id = 1")
cursor.execute("DELETE FROM league_holdings WHERE league_id = 1 AND user_id = 1")
cursor.execute("DELETE FROM league_transactions WHERE league_id = 1 AND user_id = 1")
conn.commit()

# Recreate portfolio with correct starting cash
print(f"Creating new league portfolio with ${starting_cash}...")
db.create_league_portfolio(1, 1, starting_cash)

# Verify
cursor.execute("SELECT * FROM league_portfolios WHERE league_id = 1 AND user_id = 1")
portfolio = cursor.fetchone()

if portfolio:
    print(f"\n✓ League portfolio created successfully!")
    print(f"  Cash: ${portfolio[2]}")
else:
    print("\n✗ Failed to create league portfolio")

conn.close()

print("\nDone! The league portfolio has been reset to starting cash.")
print("The personal portfolio remains unchanged.")
