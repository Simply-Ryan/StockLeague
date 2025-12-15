import sqlite3

conn = sqlite3.connect('database/stocks.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== USERS ===")
users = c.execute('SELECT id, username, cash FROM users').fetchall()
for u in users:
    print(f"  User {u['id']} ({u['username']}): ${u['cash']:.2f}")

print("\n=== LEAGUE PORTFOLIOS ===")
lp = c.execute('SELECT * FROM league_portfolios').fetchall()
for p in lp:
    print(f"  User {p['user_id']} in League {p['league_id']}: ${p['cash']:.2f}")

print("\n=== TABLES ===")
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    print(f"  {t['name']}")
    
print("\n=== PERSONAL TRANSACTIONS ===")
txns = c.execute('SELECT user_id, symbol, shares, type FROM transactions ORDER BY id DESC LIMIT 10').fetchall()
for t in txns:
    print(f"  User {t['user_id']}: {t['type']} {t['shares']} shares of {t['symbol']}")

print("\n=== LEAGUE HOLDINGS ===")
holdings = c.execute('SELECT user_id, league_id, symbol, shares FROM league_holdings WHERE shares > 0').fetchall()
for h in holdings:
    print(f"  User {h['user_id']} in League {h['league_id']}: {h['shares']} shares of {h['symbol']}")

conn.close()
