from database.db_manager import DatabaseManager

db = DatabaseManager()

print("=== Checking Portfolio Separation ===\n")

# Get user 1's personal portfolio
user = db.get_user(1)
if user:
    print(f"User 1 Personal Portfolio:")
    print(f"  Cash: ${user['cash']}")
    
    stocks = db.get_user_stocks(1)
    print(f"  Stocks: {len(stocks)} holdings")
    for stock in stocks:
        print(f"    - {stock['symbol']}: {stock['shares']} shares")
    
    transactions = db.get_transactions(1)
    print(f"  Transactions: {len(transactions)} total")

print("\n" + "="*50 + "\n")

# Get user 1's league portfolios
conn = db.get_connection()
cursor = conn.cursor()
cursor.execute("SELECT * FROM league_portfolios WHERE user_id = 1")
league_portfolios = cursor.fetchall()

if league_portfolios:
    print(f"User 1 League Portfolios: {len(league_portfolios)} total")
    for lp in league_portfolios:
        league_id = lp[0]
        league = db.get_league(league_id)
        print(f"\n  League {league_id} ({league['name'] if league else 'Unknown'}):")
        print(f"    Cash: ${lp[2]}")
        
        holdings = db.get_league_holdings(league_id, 1)
        print(f"    Holdings: {len(holdings)} stocks")
        for holding in holdings:
            print(f"      - {holding['symbol']}: {holding['shares']} shares")
        
        transactions = db.get_league_transactions(league_id, 1)
        print(f"    Transactions: {len(transactions)} total")
else:
    print("User 1 has no league portfolios")

conn.close()

print("\n" + "="*50)
print("\nCONCLUSION:")
print("If personal and league portfolios show the same stocks/cash,")
print("there is a bug. They should be completely independent.")
