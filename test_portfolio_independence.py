from database.db_manager import DatabaseManager

db = DatabaseManager()

print("=== Testing Portfolio Independence ===\n")

from database.db_manager import DatabaseManager


def main():
    db = DatabaseManager()

    print("=== Testing Portfolio Independence ===\n")

    # Get initial state
    user = db.get_user(1)
    league_portfolio = db.get_league_portfolio(1, 1)

    if not user:
        print("No user with id=1 found. Skipping standalone portfolio independence check.")
        return

    print(f"BEFORE:")
    print(f"  Personal Cash: ${user['cash']}")
    print(f"  League Cash: ${league_portfolio['cash'] if league_portfolio else 0}")

    # Modify personal cash to $50,000
    print(f"\n>>> Changing PERSONAL cash to $50,000...")
    db.update_cash(1, 50000.00)

    # Check both again
    user = db.get_user(1)
    league_portfolio = db.get_league_portfolio(1, 1)

    print(f"\nAFTER changing personal:")
    print(f"  Personal Cash: ${user['cash']}")
    print(f"  League Cash: ${league_portfolio['cash'] if league_portfolio else 0}")

    if league_portfolio and league_portfolio['cash'] == 100000.00:
        print(f"\n✓ SUCCESS: League cash unchanged!")
    else:
        print(f"\n✗ BUG: League cash was affected!")

    # Now modify league cash to $75,000
    print(f"\n>>> Changing LEAGUE cash to $75,000...")
    db.update_league_cash(1, 1, 75000.00)

    # Check both again
    user = db.get_user(1)
    league_portfolio = db.get_league_portfolio(1, 1)

    print(f"\nAFTER changing league:")
    print(f"  Personal Cash: ${user['cash']}")
    print(f"  League Cash: ${league_portfolio['cash'] if league_portfolio else 0}")

    if user and user['cash'] == 50000.00:
        print(f"\n✓ SUCCESS: Personal cash unchanged!")
    else:
        print(f"\n✗ BUG: Personal cash was affected!")

    print(f"\n=== CONCLUSION ===")
    print("If both tests passed, portfolios are independent!")
    print("The code is working correctly.")


if __name__ == '__main__':
    main()
