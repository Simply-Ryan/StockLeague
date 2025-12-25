#!/usr/bin/env python3
"""
Phase 3 Complete Integration Script
Validates setup and orchestrates full integration
"""

import sys
import os
import json
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from league_activity_feed import LeagueActivityFeed
from league_performance_metrics import LeaguePerformanceMetrics
from league_announcements import LeagueAnnouncements

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def validate_database():
    """Validate database setup"""
    print_section("1. Database Validation")
    
    try:
        db = DatabaseManager()
        print("✓ Database connection successful")
        
        # Check for Phase 3 tables
        cursor = db.get_connection().cursor()
        tables = [
            'league_activity_log',
            'league_announcements',
            'league_system_events',
            'league_performance_snapshots',
            'league_analytics'
        ]
        
        all_exist = True
        for table in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            exists = cursor.fetchone() is not None
            status = "✓" if exists else "✗"
            print(f"{status} {table}")
            if not exists:
                all_exist = False
        
        return all_exist
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False

def validate_services():
    """Validate service classes"""
    print_section("2. Service Validation")
    
    try:
        db = DatabaseManager()
        
        # Test ActivityFeed
        feed = LeagueActivityFeed(db=db)
        print("✓ LeagueActivityFeed initialized")
        
        # Test PerformanceMetrics
        metrics = LeaguePerformanceMetrics(db=db)
        print("✓ LeaguePerformanceMetrics initialized")
        
        # Test Announcements
        announcements = LeagueAnnouncements(db=db)
        print("✓ LeagueAnnouncements initialized")
        
        return True
    except Exception as e:
        print(f"✗ Service error: {e}")
        return False

def validate_api_routes():
    """Validate API routes are registered"""
    print_section("3. API Routes Validation")
    
    try:
        # Import the app
        from app import app
        
        # Get all routes
        engagement_routes = []
        for rule in app.url_map.iter_rules():
            if 'engagement' in rule.rule:
                engagement_routes.append(rule.rule)
        
        if engagement_routes:
            print(f"✓ Found {len(engagement_routes)} engagement routes:")
            for route in sorted(engagement_routes):
                print(f"  - {route}")
            return True
        else:
            print("✗ No engagement routes found")
            return False
    except Exception as e:
        print(f"✗ Route error: {e}")
        return False

def test_basic_workflow():
    """Test basic engagement workflow"""
    print_section("4. Basic Workflow Test")
    
    try:
        db = DatabaseManager()
        feed = LeagueActivityFeed(db=db)
        
        # Test logging an activity (with mock data)
        print("Testing activity logging...")
        
        # Create a simple activity log entry
        cursor = db.get_connection().cursor()
        
        # Insert test activity
        cursor.execute("""
            INSERT INTO league_activity_log 
            (league_id, user_id, activity_type, description, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (1, 1, 'test_activity', 'Integration test activity'))
        
        db.get_connection().commit()
        print("✓ Activity logged successfully")
        
        # Query it back
        cursor.execute("""
            SELECT id, activity_type, description FROM league_activity_log 
            WHERE league_id = ? ORDER BY created_at DESC LIMIT 1
        """, (1,))
        
        result = cursor.fetchone()
        if result:
            print(f"✓ Activity retrieved: {result}")
            return True
        else:
            print("✗ Activity not found")
            return False
            
    except Exception as e:
        print(f"✗ Workflow test error: {e}")
        return False

def main():
    """Run all validations"""
    print("\n" + "=" * 70)
    print("  PHASE 3 INTEGRATION VALIDATION")
    print("=" * 70)
    
    results = {
        'database': validate_database(),
        'services': validate_services(),
        'routes': validate_api_routes(),
        'workflow': test_basic_workflow(),
    }
    
    print_section("Integration Status Summary")
    print(f"Database:  {'✓ PASS' if results['database'] else '✗ FAIL'}")
    print(f"Services:  {'✓ PASS' if results['services'] else '✗ FAIL'}")
    print(f"Routes:    {'✓ PASS' if results['routes'] else '✗ FAIL'}")
    print(f"Workflow:  {'✓ PASS' if results['workflow'] else '✗ FAIL'}")
    
    all_pass = all(results.values())
    print("\n" + "=" * 70)
    if all_pass:
        print("✓ ALL VALIDATIONS PASSED - Ready for Phase 3 Integration")
    else:
        print("✗ SOME VALIDATIONS FAILED - See errors above")
    print("=" * 70 + "\n")
    
    return 0 if all_pass else 1

if __name__ == '__main__':
    sys.exit(main())
