"""
Test Suite for Member Limits Enforcement (Item #10)
Tests member limits, waitlist, and capacity management
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from members_limit_manager import MembersLimitManager


class TestMemberLimitInitialization(unittest.TestCase):
    """Test initializing member limits"""
    
    def setUp(self):
        """Set up test database"""
        self.db = DatabaseManager(':memory:')
        self.manager = MembersLimitManager(self.db)
    
    def test_initialize_league_limit(self):
        """Test initializing member limit for league"""
        league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        success, msg = self.manager.initialize_league_limit(league_id, 'public')
        
        self.assertTrue(success)
    
    def test_initialize_limit_different_types(self):
        """Test different league types have different defaults"""
        public_league = self.db.create_league(
            name="Public",
            creator_id=1,
            league_type="public"
        )
        private_league = self.db.create_league(
            name="Private",
            creator_id=1,
            league_type="private"
        )
        
        self.manager.initialize_league_limit(public_league, 'public')
        self.manager.initialize_league_limit(private_league, 'private')
        
        pub_limit = self.manager.get_league_limit(public_league)
        priv_limit = self.manager.get_league_limit(private_league)
        
        # Public should have higher default than private
        self.assertGreater(pub_limit['max_members'], priv_limit['max_members'])
    
    def test_get_uninitialized_limit(self):
        """Test getting limit for uninitialized league"""
        league_id = self.db.create_league(
            name="Test",
            creator_id=1,
            league_type="public"
        )
        
        limit = self.manager.get_league_limit(league_id)
        
        self.assertIsNone(limit)


class TestMemberLimitManagement(unittest.TestCase):
    """Test managing member limits"""
    
    def setUp(self):
        """Set up test data"""
        self.db = DatabaseManager(':memory:')
        self.manager = MembersLimitManager(self.db)
        
        self.league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        self.manager.initialize_league_limit(self.league_id, 'public')
    
    def test_get_league_limit(self):
        """Test getting league limit"""
        limit = self.manager.get_league_limit(self.league_id)
        
        self.assertIsNotNone(limit)
        self.assertIn('max_members', limit)
        self.assertIn('current_members', limit)
        self.assertIn('is_full', limit)
    
    def test_set_member_limit(self):
        """Test setting member limit"""
        success, msg = self.manager.set_member_limit(
            league_id=self.league_id,
            max_members=25,
            admin_id=1
        )
        
        self.assertTrue(success)
        
        limit = self.manager.get_league_limit(self.league_id)
        self.assertEqual(limit['max_members'], 25)
    
    def test_set_invalid_limit(self):
        """Test setting invalid limit"""
        success, msg = self.manager.set_member_limit(
            league_id=self.league_id,
            max_members=0,  # Below minimum
            admin_id=1
        )
        
        self.assertFalse(success)


class TestAddMembers(unittest.TestCase):
    """Test adding members with limit enforcement"""
    
    def setUp(self):
        """Set up test data"""
        self.db = DatabaseManager(':memory:')
        self.manager = MembersLimitManager(self.db)
        
        self.league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        self.manager.initialize_league_limit(self.league_id, 'public')
        self.manager.set_member_limit(self.league_id, 3, 1)  # Small limit for testing
    
    def test_add_member_below_limit(self):
        """Test adding member when below limit"""
        success, msg = self.manager.add_member(self.league_id, 2)
        
        self.assertTrue(success)
        
        limit = self.manager.get_league_limit(self.league_id)
        self.assertEqual(limit['current_members'], 1)
    
    def test_add_multiple_members(self):
        """Test adding multiple members"""
        for i in range(2, 4):
            self.manager.add_member(self.league_id, i)
        
        limit = self.manager.get_league_limit(self.league_id)
        self.assertEqual(limit['current_members'], 2)
    
    def test_add_member_exceeds_limit(self):
        """Test that adding member over limit puts them on waitlist"""
        # Fill league
        self.manager.add_member(self.league_id, 2)
        self.manager.add_member(self.league_id, 3)
        self.manager.add_member(self.league_id, 4)
        
        # Try to add when full
        success, msg = self.manager.add_member(self.league_id, 5)
        
        self.assertFalse(success)
        self.assertIn('waitlist', msg.lower())


class TestWaitlist(unittest.TestCase):
    """Test member waitlist functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.db = DatabaseManager(':memory:')
        self.manager = MembersLimitManager(self.db)
        
        self.league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        self.manager.initialize_league_limit(self.league_id, 'public')
        self.manager.set_member_limit(self.league_id, 2, 1)  # Very small limit
    
    def test_add_to_waitlist(self):
        """Test adding user to waitlist"""
        # Fill league
        self.manager.add_member(self.league_id, 2)
        self.manager.add_member(self.league_id, 3)
        
        # Add when full
        success, msg = self.manager.add_member(self.league_id, 4)
        
        self.assertFalse(success)
        
        # Check waitlist
        waitlist = self.manager.get_waitlist(self.league_id)
        self.assertEqual(len(waitlist), 1)
    
    def test_waitlist_order(self):
        """Test that waitlist respects order"""
        # Fill league
        self.manager.add_member(self.league_id, 2)
        self.manager.add_member(self.league_id, 3)
        
        # Add multiple to waitlist
        self.manager.add_member(self.league_id, 4)
        self.manager.add_member(self.league_id, 5)
        self.manager.add_member(self.league_id, 6)
        
        waitlist = self.manager.get_waitlist(self.league_id)
        
        # Should have 3 in order
        self.assertEqual(len(waitlist), 3)
        self.assertEqual(waitlist[0]['user_id'], 4)  # First added
        self.assertEqual(waitlist[1]['user_id'], 5)  # Second
        self.assertEqual(waitlist[2]['user_id'], 6)  # Third
    
    def test_remove_from_waitlist(self):
        """Test removing user from waitlist"""
        self.manager.add_member(self.league_id, 2)
        self.manager.add_member(self.league_id, 3)
        self.manager.add_member(self.league_id, 4)  # Goes to waitlist
        
        success, msg = self.manager.remove_from_waitlist(self.league_id, 4)
        
        self.assertTrue(success)
        
        waitlist = self.manager.get_waitlist(self.league_id)
        self.assertEqual(len(waitlist), 0)


class TestWaitlistPromotion(unittest.TestCase):
    """Test automatic waitlist promotion"""
    
    def setUp(self):
        """Set up test data"""
        self.db = DatabaseManager(':memory:')
        self.manager = MembersLimitManager(self.db)
        
        self.league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        self.manager.initialize_league_limit(self.league_id, 'public')
        self.manager.set_member_limit(self.league_id, 2, 1)
    
    def test_promote_on_member_removal(self):
        """Test that member is promoted from waitlist when space opens"""
        # Fill league
        self.manager.add_member(self.league_id, 2)
        self.manager.add_member(self.league_id, 3)
        
        # Add to waitlist
        self.manager.add_member(self.league_id, 4)
        
        # Remove a member
        self.manager.remove_member(self.league_id, 2)
        
        # Check that user 4 is now member
        cursor = self.db.get_connection().cursor()
        cursor.execute('''
            SELECT id FROM league_members
            WHERE league_id = ? AND user_id = 4
        ''', (self.league_id,))
        
        member = cursor.fetchone()
        self.assertIsNotNone(member, "User should be promoted from waitlist")


class TestMemberCapacity(unittest.TestCase):
    """Test capacity checks"""
    
    def setUp(self):
        """Set up test data"""
        self.db = DatabaseManager(':memory:')
        self.manager = MembersLimitManager(self.db)
        
        self.league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        self.manager.initialize_league_limit(self.league_id, 'public')
    
    def test_can_add_member(self):
        """Test checking if member can be added"""
        can_add, msg = self.manager.can_add_member(self.league_id)
        
        self.assertTrue(can_add)
    
    def test_cannot_add_when_full(self):
        """Test that can_add returns False when league is full"""
        self.manager.set_member_limit(self.league_id, 1, 1)
        self.manager.add_member(self.league_id, 2)
        
        can_add, msg = self.manager.can_add_member(self.league_id)
        
        self.assertFalse(can_add)
    
    def test_member_count(self):
        """Test getting member count"""
        self.manager.add_member(self.league_id, 2)
        self.manager.add_member(self.league_id, 3)
        
        count = self.manager.get_member_count(self.league_id)
        
        self.assertEqual(count, 2)


class TestEnforcement(unittest.TestCase):
    """Test enabling/disabling enforcement"""
    
    def setUp(self):
        """Set up test data"""
        self.db = DatabaseManager(':memory:')
        self.manager = MembersLimitManager(self.db)
        
        self.league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        self.manager.initialize_league_limit(self.league_id, 'public')
    
    def test_toggle_enforcement(self):
        """Test toggling enforcement"""
        success, msg = self.manager.enforce_limit(self.league_id, False)
        
        self.assertTrue(success)
        
        limit = self.manager.get_league_limit(self.league_id)
        self.assertEqual(limit['is_enforced'], 0)


class TestLimitHistory(unittest.TestCase):
    """Test tracking limit changes"""
    
    def setUp(self):
        """Set up test data"""
        self.db = DatabaseManager(':memory:')
        self.manager = MembersLimitManager(self.db)
        
        self.league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        self.manager.initialize_league_limit(self.league_id, 'public')
    
    def test_get_limit_history(self):
        """Test getting limit change history"""
        self.manager.set_member_limit(self.league_id, 25, 1, reason="Test")
        self.manager.set_member_limit(self.league_id, 30, 1, reason="Growth")
        
        history = self.manager.get_limit_history(self.league_id)
        
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['new_limit'], 30)


if __name__ == '__main__':
    unittest.main()
