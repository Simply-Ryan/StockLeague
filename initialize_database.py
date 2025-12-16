import sqlite3

def initialize_database():
    db_path = "database/stockleague.db"

    schema = """
    CREATE TABLE IF NOT EXISTS league_portfolios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        league_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        cash NUMERIC NOT NULL DEFAULT 10000.00,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        locked_at TIMESTAMP,
        FOREIGN KEY (league_id) REFERENCES leagues(id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(league_id, user_id)
    );
    """

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create the league_portfolios table
        cursor.execute(schema)
        conn.commit()

        print("Database initialized successfully.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    initialize_database()