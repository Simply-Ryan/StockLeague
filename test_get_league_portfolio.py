import sqlite3

def test_get_league_portfolio():
    db_path = "database/stockleague.db"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Test data
        league_id = 1
        user_id = 1

        # Query the league_portfolios table
        cursor.execute(
            "SELECT * FROM league_portfolios WHERE league_id = ? AND user_id = ?",
            (league_id, user_id),
        )
        portfolio = cursor.fetchone()

        if portfolio:
            print("Portfolio found:", dict(zip([col[0] for col in cursor.description], portfolio)))
        else:
            print("No portfolio found for league_id=1 and user_id=1.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    test_get_league_portfolio()