import sqlite3

def validate_league_portfolios():
    db_path = "database/stockleague.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
        SELECT league_id, user_id, COUNT(*) 
        FROM league_portfolios 
        GROUP BY league_id, user_id 
        HAVING COUNT(*) > 1;
        """

        cursor.execute(query)
        duplicates = cursor.fetchall()

        if duplicates:
            print("Duplicate entries found in league_portfolios:")
            for row in duplicates:
                print(f"League ID: {row[0]}, User ID: {row[1]}, Count: {row[2]}")
        else:
            print("No duplicate entries found in league_portfolios.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    validate_league_portfolios()