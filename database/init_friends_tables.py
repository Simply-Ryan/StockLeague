import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'stocks.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'friends_schema.sql')

def apply_friends_schema():
    with sqlite3.connect(DB_PATH) as conn:
        with open(SCHEMA_PATH, 'r') as f:
            sql = f.read()
        conn.executescript(sql)
        print("[INFO] Friends, blocks, and follows tables created (if not exist).")

if __name__ == "__main__":
    apply_friends_schema()
