#!/usr/bin/env python3
"""Quick test to verify app imports without syntax errors"""

import sys


def main():
    """Verify that the application module imports successfully."""
    try:
        print("Attempting to import app module...")
        import app
        print("SUCCESS: App module imported successfully!")
        print(f"Flask app created: {app.app}")
        print(f"Achievement filter registered: {'achievement_name' in app.app.jinja_env.filters}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
