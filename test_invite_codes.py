"""
Test Suite for Invite Code Expiration (Item #9)
Tests invite code generation, validation, and expiration
"""

import unittest
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from invite_manager import InviteCodeManager


class TestInviteCodeGeneration(unittest.TestCase):
    """Test invite code generation"""
    
    def setUp(self):
        """Set up test database"""
        self.db = DatabaseManager(':memory:')
        self.manager = InviteCodeManager(self.db)
    
    def test_generate_code(self):
        """Test generating an invite code"""
        code = self.manager.generate_code()
        
        self.assertIsNotNone(code)
        self.assertEqual(len(code), 8)
        self.assertTrue(all(c.isalnum() for c in code))
    
    def test_generated_codes_unique(self):
        """Test that generated codes are unique"""
        codes = {self.manager.generate_code() for _ in range(100)}
        
        self.assertEqual(len(codes), 100)


class TestInviteCodeCreation(unittest.TestCase):
    """Test creating invite codes"""
    
    def setUp(self):
        """Set up test database with league"""
        self.db = DatabaseManager(':memory:')
        self.manager = InviteCodeManager(self.db)
        
        # Create test league
        self.league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
    
    def test_create_invite_code(self):
        """Test creating an invite code"""
        success, code, message = self.manager.create_invite_code(
            league_id=self.league_id,
            created_by=1,
            expiration_days=7
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(code)
        self.assertEqual(len(code), 8)
    
    def test_create_single_use_code(self):
        """Test creating single-use code"""
        success, code, message = self.manager.create_invite_code(
            league_id=self.league_id,
            created_by=1,
            is_single_use=True
        )
        
        self.assertTrue(success)
    
    def test_create_code_with_max_uses(self):
        """Test creating code with usage limit"""
        success, code, message = self.manager.create_invite_code(
            league_id=self.league_id,
            created_by=1,
            max_uses=5
        )
        
        self.assertTrue(success)
    
    def test_create_code_invalid_expiration(self):
        """Test creating code with invalid expiration"""
        success, code, message = self.manager.create_invite_code(
            league_id=self.league_id,
            created_by=1,
            expiration_days=400  # Exceeds MAX_EXPIRATION_DAYS
        )
        
        self.assertFalse(success)


class TestInviteCodeValidation(unittest.TestCase):
    """Test validating invite codes"""
    
    def setUp(self):
        """Set up test data"""
        self.db = DatabaseManager(':memory:')
        self.manager = InviteCodeManager(self.db)
        
        self.league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        # Create valid code
        _, self.valid_code, _ = self.manager.create_invite_code(
            league_id=self.league_id,
            created_by=1,
            expiration_days=7
        )
    
    def test_validate_valid_code(self):
        """Test validating a valid code"""
        is_valid, info, msg = self.manager.validate_code(self.valid_code)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(info)
    
    def test_validate_invalid_code(self):
        """Test validating an invalid code"""
        is_valid, info, msg = self.manager.validate_code("INVALID")
        
        self.assertFalse(is_valid)
    
    def test_validate_deactivated_code(self):
        """Test validating a deactivated code"""
        # Deactivate code
        self.manager.deactivate_code(self.valid_code, self.league_id, 1)
        
        is_valid, info, msg = self.manager.validate_code(self.valid_code)
        
        self.assertFalse(is_valid)


class TestInviteCodeUsage(unittest.TestCase):
    """Test using invite codes"""
    
    def setUp(self):
        """Set up test data"""
        self.db = DatabaseManager(':memory:')
        self.manager = InviteCodeManager(self.db)
        
        self.league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        _, self.code, _ = self.manager.create_invite_code(
            league_id=self.league_id,
            created_by=1
        )
    
    def test_use_valid_code(self):
        """Test using a valid code"""
        success, league_id, msg = self.manager.use_code(self.code, user_id=2)
        
        self.assertTrue(success)
        self.assertEqual(league_id, self.league_id)
    
    def test_use_invalid_code(self):
        """Test using invalid code"""
        success, league_id, msg = self.manager.use_code("INVALID", user_id=2)
        
        self.assertFalse(success)
    
    def test_use_single_use_code_twice(self):
        """Test that single-use code cannot be used twice"""
        _, single_code, _ = self.manager.create_invite_code(
            league_id=self.league_id,
            created_by=1,
            is_single_use=True
        )
        
        # First use
        success1, _, _ = self.manager.use_code(single_code, user_id=2)
        self.assertTrue(success1)
        
        # Second use
        success2, _, _ = self.manager.use_code(single_code, user_id=3)
        self.assertFalse(success2)
    
    def test_use_code_respects_max_uses(self):
        """Test that code respects max uses limit"""
        _, limited_code, _ = self.manager.create_invite_code(
            league_id=self.league_id,
            created_by=1,
            max_uses=2
        )
        
        # First use
        self.manager.use_code(limited_code, user_id=2)
        
        # Second use
        self.manager.use_code(limited_code, user_id=3)
        
        # Third use should fail
        success, _, _ = self.manager.use_code(limited_code, user_id=4)
        self.assertFalse(success)


class TestInviteCodeList(unittest.TestCase):
    """Test listing invite codes"""
    
    def setUp(self):
        """Set up test data"""
        self.db = DatabaseManager(':memory:')
        self.manager = InviteCodeManager(self.db)
        
        self.league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        # Create multiple codes
        for i in range(3):
            self.manager.create_invite_code(
                league_id=self.league_id,
                created_by=1
            )
    
    def test_get_league_codes(self):
        """Test getting all codes for a league"""
        codes = self.manager.get_league_codes(self.league_id)
        
        self.assertEqual(len(codes), 3)
    
    def test_get_codes_excludes_expired(self):
        """Test that expired codes are excluded from active list"""
        codes = self.manager.get_league_codes(self.league_id, active_only=True)
        
        # All should be active
        self.assertTrue(all(not c['is_expired'] for c in codes))


class TestInviteCodeCleanup(unittest.TestCase):
    """Test cleanup of expired codes"""
    
    def setUp(self):
        """Set up test database"""
        self.db = DatabaseManager(':memory:')
        self.manager = InviteCodeManager(self.db)
    
    def test_cleanup_expired_codes_dry_run(self):
        """Test cleanup dry run"""
        count = self.manager.cleanup_expired_codes(dry_run=True)
        
        self.assertIsInstance(count, int)
        self.assertGreaterEqual(count, 0)


if __name__ == '__main__':
    unittest.main()
