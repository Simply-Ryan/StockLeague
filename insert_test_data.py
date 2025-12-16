import sqlite3

def insert_test_data():
    db_path = "database/stockleague.db"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Insert test data
        league_id = 1
        user_id = 1
        cash = 5000.00

        cursor.execute(
            """
            INSERT INTO league_portfolios (league_id, user_id, cash)
            VALUES (?, ?, ?)
            """,
            (league_id, user_id, cash),
        )
        conn.commit()

        print("Test data inserted successfully.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    insert_test_data()