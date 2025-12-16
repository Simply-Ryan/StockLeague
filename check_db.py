from database.db_manager import DatabaseManager

db = DatabaseManager()
conn = db.get_connection()
cursor = conn.cursor()

# Check tables
print("=== Database Tables ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
for table in tables:
    print(f"  - {table}")

# Check if league_portfolios and league_holdings exist
if 'league_portfolios' in tables:
    print("\n=== League Portfolios ===")
    cursor.execute("SELECT * FROM league_portfolios LIMIT 5")
    portfolios = cursor.fetchall()
    print(f"Found {len(portfolios)} league portfolios")
    for p in portfolios:
        print(f"  League {p[0]}, User {p[1]}, Cash: ${p[2]}")

if 'league_holdings' in tables:
    print("\n=== League Holdings ===")
    cursor.execute("SELECT * FROM league_holdings LIMIT 5")
    holdings = cursor.fetchall()
    print(f"Found {len(holdings)} league holdings")
    for h in holdings:
        print(f"  League {h[0]}, User {h[1]}, Symbol: {h[2]}, Shares: {h[3]}")

# Check personal transactions
if 'transactions' in tables:
    print("\n=== Personal Transactions (sample) ===")
    cursor.execute("SELECT user_id, symbol, shares, type FROM transactions LIMIT 5")
    trans = cursor.fetchall()
    print(f"Found personal transactions")
    for t in trans:
        print(f"  User {t[0]}, {t[3]} {t[2]} shares of {t[1]}")

# Check league transactions
if 'league_transactions' in tables:
    print("\n=== League Transactions (sample) ===")
    cursor.execute("SELECT league_id, user_id, symbol, shares, type FROM league_transactions LIMIT 5")
    trans = cursor.fetchall()
    print(f"Found league transactions")
    for t in trans:
        print(f"  League {t[0]}, User {t[1]}, {t[4]} {t[3]} shares of {t[2]}")

conn.close()
print("\nDone!")
