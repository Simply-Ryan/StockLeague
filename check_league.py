from database.db_manager import DatabaseManager

db = DatabaseManager()
league = db.get_league(1)

if league:
    print(f"League ID: {league['id']}")
    print(f"Name: {league['name']}")
    print(f"Starting Cash: ${league.get('starting_cash', 'NOT SET - DEFAULT 10000')}")
    print(f"Is Active: {league.get('is_active', False)}")
    print(f"Lifecycle State: {league.get('lifecycle_state', 'NOT SET')}")
    print(f"Created At: {league.get('created_at', 'UNKNOWN')}")
else:
    print("League 1 not found")
