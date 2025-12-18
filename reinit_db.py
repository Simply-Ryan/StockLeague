#!/usr/bin/env python3
"""
Reinitialize the database with the new schema
"""
import os
import sys

# Add the database module to path
sys.path.insert(0, '/workspaces/codespaces-blank/StockLeague')

from database.db_manager import DatabaseManager

# Delete old database files
db_path = "database/stocks.db"
for suffix in ["", "-shm", "-wal"]:
    try:
        os.remove(db_path + suffix)
        print(f"Deleted {db_path + suffix}")
    except FileNotFoundError:
        pass

# Reinitialize the database
print("Reinitializing database...")
db = DatabaseManager(db_path="database/stocks.db")

# Verify tables were created
import sqlite3
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
conn.close()

print(f"\nDatabase reinitialized successfully!")
print(f"Total tables created: {len(tables)}")
print("\nTables:")
for table in sorted(tables):
    print(f"  - {table[0]}")
