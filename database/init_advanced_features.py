#!/usr/bin/env python3
"""
Initialize Advanced League Features Database Tables

This script initializes all the new database tables for:
- H2H Matchups
- League Seasons
- Division/Tier System
- Enhanced Activity Feed

Run this once after updating your StockLeague installation:
    python database/init_advanced_features.py

"""

import sqlite3
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from database.advanced_league_features import AdvancedLeagueDB


def main():
    """Initialize advanced league features."""
    print("=" * 60)
    print("StockLeague Advanced Features Initialization")
    print("=" * 60)
    
    try:
        # Initialize database manager
        db = DatabaseManager()
        print("✓ Database manager initialized")
        
        # Initialize advanced league features
        advanced_league_db = AdvancedLeagueDB(db)
        print("✓ Advanced league DB initialized")
        
        # Create tables
        print("\nCreating database tables...")
        
        advanced_league_db.init_h2h_tables()
        print("✓ H2H matchup tables created")
        
        advanced_league_db.init_season_tables()
        print("✓ Season tables created")
        
        advanced_league_db.init_division_tables()
        print("✓ Division/tier tables created")
        
        advanced_league_db.init_enhanced_activity_feed()
        print("✓ Enhanced activity feed tables created")
        
        print("\n" + "=" * 60)
        print("SUCCESS! Advanced league features initialized")
        print("=" * 60)
        print("\nNew features available:")
        print("  • H2H Matchups - Challenge friends to 1v1 trading battles")
        print("  • League Seasons - Structured competition with seasons")
        print("  • Division System - Tiered competition levels")
        print("  • Enhanced Activity Feed - Categorized activities with filtering")
        print("\nNew API Endpoints:")
        print("  • POST /api/league/<id>/h2h/create - Create H2H matchup")
        print("  • GET /api/league/<id>/h2h/matchups - Get user's matchups")
        print("  • GET /api/league/<id>/h2h/leaderboard - Get H2H leaderboard")
        print("  • GET /api/league/<id>/activity-feed/filtered - Filtered activity feed")
        print("  • GET /api/league/<id>/statistics - League statistics")
        print("\nNew Pages:")
        print("  • GET /leagues/<id>/h2h - H2H matchups dashboard")
        print("\n" + "=" * 60)
        
        return 0
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
