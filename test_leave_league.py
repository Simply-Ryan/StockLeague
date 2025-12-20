#!/usr/bin/env python3
"""
Test script for leave_league functionality.
Tests both ownership transfer and league deletion.
"""

import os
import sys
import tempfile

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database.db_manager import DatabaseManager


def test_leave_league():
    """Test leave_league with ownership transfer and deletion"""
    
    # Create temp database
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, 'test_leave_league.db')
    db = DatabaseManager(db_path=db_path)
    
    print("=" * 60)
    print("Testing leave_league functionality")
    print("=" * 60)
    
    # 1. Create test users
    print("\n1. Creating test users...")
    from werkzeug.security import generate_password_hash
    
    user1_id = db.create_user("owner", generate_password_hash("password123"))
    user2_id = db.create_user("member1", generate_password_hash("password123"))
    user3_id = db.create_user("member2", generate_password_hash("password123"))
    
    print(f"   Owner ID: {user1_id}")
    print(f"   Member 1 ID: {user2_id}")
    print(f"   Member 2 ID: {user3_id}")
    
    # 2. Create a league
    print("\n2. Creating league...")
    league_id, invite_code = db.create_league(
        name="Test League",
        description="League to test leave functionality",
        creator_id=user1_id,
        league_type="private",
        starting_cash=10000.0
    )
    print(f"   League ID: {league_id}")
    print(f"   Invite Code: {invite_code}")
    
    # 3. Owner creates portfolio
    print("\n3. Creating league portfolios...")
    db.create_league_portfolio(league_id, user1_id, 10000.0)
    print(f"   Owner portfolio created")
    
    # 4. Members join
    print("\n4. Members joining league...")
    db.join_league(league_id, user2_id)
    db.create_league_portfolio(league_id, user2_id, 10000.0)
    print(f"   Member 1 joined")
    
    db.join_league(league_id, user3_id)
    db.create_league_portfolio(league_id, user3_id, 10000.0)
    print(f"   Member 2 joined")
    
    # 5. Verify initial state
    print("\n5. Verifying initial state...")
    league = db.get_league(league_id)
    members = db.get_league_members(league_id)
    print(f"   League creator: {league['creator_id']}")
    print(f"   Total members: {len(members)}")
    for m in members:
        print(f"     - User {m['id']}, Admin: {m['is_admin']}")
    
    # 6. Test ownership transfer - owner leaves with other members present
    print("\n6. Testing ownership transfer...")
    print(f"   Owner (user {user1_id}) leaving league...")
    db.leave_league(league_id, user1_id)
    
    league_after = db.get_league(league_id)
    if league_after:
        print(f"   ✓ League still exists")
        print(f"   New creator: {league_after['creator_id']}")
        print(f"   Expected new owner: {user2_id} (first to join after owner)")
        
        if league_after['creator_id'] == user2_id:
            print(f"   ✓ Ownership transferred correctly!")
        else:
            print(f"   ✗ ERROR: Ownership not transferred to correct member!")
            return False
        
        members_after = db.get_league_members(league_id)
        print(f"   Remaining members: {len(members_after)}")
        for m in members_after:
            is_admin_str = "Admin" if m['is_admin'] else "Regular"
            print(f"     - User {m['id']} ({is_admin_str})")
    else:
        print(f"   ✗ ERROR: League was deleted when it shouldn't have been!")
        return False
    
    # 7. Test league deletion - last member leaves
    print("\n7. Testing league deletion...")
    print(f"   Member 1 (user {user2_id}) leaving...")
    db.leave_league(league_id, user2_id)
    
    print(f"   Member 2 (user {user3_id}) leaving...")
    db.leave_league(league_id, user3_id)
    
    league_deleted = db.get_league(league_id)
    if league_deleted is None:
        print(f"   ✓ League deleted when last member left!")
    else:
        print(f"   ✗ ERROR: League still exists when it should be deleted!")
        return False
    
    # 8. Test single-member league deletion
    print("\n8. Testing single-member league deletion...")
    
    # Create another league with just owner
    league2_id, _ = db.create_league(
        name="Test League 2",
        description="Single member league",
        creator_id=user1_id,
        league_type="private",
        starting_cash=10000.0
    )
    db.create_league_portfolio(league2_id, user1_id, 10000.0)
    print(f"   Single-member league created: {league2_id}")
    
    # Owner leaves - league should be deleted
    db.leave_league(league2_id, user1_id)
    league2_deleted = db.get_league(league2_id)
    
    if league2_deleted is None:
        print(f"   ✓ Single-member league deleted when owner left!")
    else:
        print(f"   ✗ ERROR: Single-member league still exists!")
        return False
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_leave_league()
    sys.exit(0 if success else 1)
