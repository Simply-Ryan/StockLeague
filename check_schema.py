import sqlite3

conn = sqlite3.connect('database/stockleague.db')
cursor = conn.cursor()

print("=== league_portfolios Table Schema ===\n")
cursor.execute("PRAGMA table_info(league_portfolios)")
columns = cursor.fetchall()
for col in columns:
    print(f"Column: {col[1]}, Type: {col[2]}, NotNull: {col[3]}, Default: {col[4]}")

print("\n=== Current Data in league_portfolios ===\n")
cursor.execute("SELECT * FROM league_portfolios")
rows = cursor.fetchall()
for row in rows:
    print(f"League: {row[0]}, User: {row[1]}, Cash: {row[2]}")

conn.close()
