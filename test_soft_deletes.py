"""
Test Suite for Soft Deletes / League Archives (Item #7)
Tests archiving, restoration, and archive management functionality
"""

import unittest
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from soft_deletes import LeagueArchiveManager


class TestLeagueArchiving(unittest.TestCase):
    """Test basic league archiving functionality"""
    
    def setUp(self):
        """Set up test database"""
        self.db = DatabaseManager(':memory:')
        self.archive_mgr = LeagueArchiveManager(self.db)
    
    def test_archive_active_league(self):
        """Test archiving an active league"""
        # Create test league
        league_id = self.db.create_league(
            name="Test League",
            description="Test Description",
            creator_id=1,
            league_type="public",
            starting_cash=10000
        )
        
        # Verify league not archived initially
        league = self.db.get_league(league_id)
        self.assertIsNone(league.get('soft_deleted_at'))
        
        # Archive the league
        success, message = self.archive_mgr.archive_league(league_id, admin_id=1)
        
        # Verify success
        self.assertTrue(success)
        self.assertIn("archived successfully", message)
        
        # Verify league is archived
        league = self.db.get_league(league_id, include_archived=True)
        self.assertIsNotNone(league.get('soft_deleted_at'))
    
    def test_archive_already_archived_league(self):
        """Test archiving an already archived league"""
        league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        # Archive once
        self.archive_mgr.archive_league(league_id, admin_id=1)
        
        # Try to archive again
        success, message = self.archive_mgr.archive_league(league_id, admin_id=1)
        
        # Should fail
        self.assertFalse(success)
        self.assertIn("already archived", message)
    
    def test_archive_nonexistent_league(self):
        """Test archiving a nonexistent league"""
        success, message = self.archive_mgr.archive_league(999999, admin_id=1)
        
        self.assertFalse(success)
        self.assertIn("not found", message)


class TestLeagueRestoration(unittest.TestCase):
    """Test league restoration functionality"""
    
    def setUp(self):
        """Set up test database"""
        self.db = DatabaseManager(':memory:')
        self.archive_mgr = LeagueArchiveManager(self.db)
    
    def test_restore_archived_league(self):
        """Test restoring an archived league"""
        # Create and archive league
        league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        self.archive_mgr.archive_league(league_id, admin_id=1)
        
        # Verify archived
        league = self.db.get_league(league_id, include_archived=True)
        self.assertIsNotNone(league.get('soft_deleted_at'))
        
        # Restore the league
        success, message = self.archive_mgr.restore_league(league_id, admin_id=1)
        
        # Verify success
        self.assertTrue(success)
        self.assertIn("restored successfully", message)
        
        # Verify no longer archived
        league = self.db.get_league(league_id)
        self.assertIsNone(league.get('soft_deleted_at'))
    
    def test_restore_active_league(self):
        """Test restoring an active (not archived) league"""
        league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        # Try to restore without archiving
        success, message = self.archive_mgr.restore_league(league_id, admin_id=1)
        
        # Should fail
        self.assertFalse(success)
        self.assertIn("not archived", message)
    
    def test_restore_nonexistent_league(self):
        """Test restoring a nonexistent league"""
        success, message = self.archive_mgr.restore_league(999999, admin_id=1)
        
        self.assertFalse(success)
        self.assertIn("not found", message)


class TestArchiveQueries(unittest.TestCase):
    """Test querying archived leagues"""
    
    def setUp(self):
        """Set up test database"""
        self.db = DatabaseManager(':memory:')
        self.archive_mgr = LeagueArchiveManager(self.db)
        
        # Create test user
        self.user_id = 1
        
        # Create multiple leagues
        self.active_league_id = self.db.create_league(
            name="Active League",
            description="Still active",
            creator_id=self.user_id,
            league_type="public"
        )
        
        self.archived_league_id = self.db.create_league(
            name="Archived League",
            description="Was archived",
            creator_id=self.user_id,
            league_type="public"
        )
        
        # Archive one league
        self.archive_mgr.archive_league(self.archived_league_id, admin_id=self.user_id)
    
    def test_get_league_filters_archived(self):
        """Test that get_league filters out archived by default"""
        # Active league should be found
        active = self.db.get_league(self.active_league_id)
        self.assertIsNotNone(active)
        
        # Archived league should not be found (default)
        archived = self.db.get_league(self.archived_league_id)
        self.assertIsNone(archived)
        
        # Archived league should be found with flag
        archived = self.db.get_league(self.archived_league_id, include_archived=True)
        self.assertIsNotNone(archived)
        self.assertIsNotNone(archived.get('soft_deleted_at'))
    
    def test_get_user_leagues_filters_archived(self):
        """Test that get_user_leagues filters out archived by default"""
        # Fetch user leagues (default)
        leagues = self.db.get_user_leagues(self.user_id)
        league_ids = [l['id'] for l in leagues]
        
        # Should only have active league
        self.assertIn(self.active_league_id, league_ids)
        self.assertNotIn(self.archived_league_id, league_ids)
        
        # With include_archived flag, should have both
        leagues = self.db.get_user_leagues(self.user_id, include_archived=True)
        league_ids = [l['id'] for l in leagues]
        
        self.assertIn(self.active_league_id, league_ids)
        self.assertIn(self.archived_league_id, league_ids)
    
    def test_get_archived_leagues(self):
        """Test getting archived leagues for a user"""
        archived = self.archive_mgr.get_user_archived_leagues(self.user_id)
        
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0]['id'], self.archived_league_id)
    
    def test_is_league_archived(self):
        """Test checking if league is archived"""
        # Active league
        is_archived = self.db.is_league_archived(self.active_league_id)
        self.assertFalse(is_archived)
        
        # Archived league
        is_archived = self.db.is_league_archived(self.archived_league_id)
        self.assertTrue(is_archived)


class TestArchiveInfo(unittest.TestCase):
    """Test archive information retrieval"""
    
    def setUp(self):
        """Set up test database"""
        self.db = DatabaseManager(':memory:')
        self.archive_mgr = LeagueArchiveManager(self.db)
    
    def test_get_archive_info_for_archived_league(self):
        """Test getting archive info"""
        # Create and archive league
        league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        self.archive_mgr.archive_league(league_id, admin_id=1)
        
        # Get archive info
        info = self.archive_mgr.get_archive_info(league_id)
        
        self.assertIsNotNone(info)
        self.assertEqual(info['league_id'], league_id)
        self.assertEqual(info['league_name'], 'Test League')
        self.assertIsNotNone(info['archived_at'])
        self.assertGreaterEqual(info['days_archived'], 0)
    
    def test_get_archive_info_for_active_league(self):
        """Test getting archive info for active league returns None"""
        league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        info = self.archive_mgr.get_archive_info(league_id)
        self.assertIsNone(info)


class TestArchiveStatistics(unittest.TestCase):
    """Test archive statistics"""
    
    def setUp(self):
        """Set up test database"""
        self.db = DatabaseManager(':memory:')
        self.archive_mgr = LeagueArchiveManager(self.db)
    
    def test_get_archive_statistics(self):
        """Test getting archive statistics"""
        # Create and archive multiple leagues
        for i in range(3):
            league_id = self.db.create_league(
                name=f"League {i}",
                description=f"Test {i}",
                creator_id=1,
                league_type="public"
            )
            self.archive_mgr.archive_league(league_id, admin_id=1)
        
        # Get statistics
        stats = self.archive_mgr.get_archive_statistics()
        
        self.assertEqual(stats['total_archived'], 3)
        self.assertEqual(stats['archived_this_week'], 3)


class TestPermanentDeletion(unittest.TestCase):
    """Test permanent deletion of archived leagues"""
    
    def setUp(self):
        """Set up test database"""
        self.db = DatabaseManager(':memory:')
        self.archive_mgr = LeagueArchiveManager(self.db)
    
    def test_permanent_delete_requires_confirmation(self):
        """Test permanent delete requires confirm=True"""
        league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        self.archive_mgr.archive_league(league_id, admin_id=1)
        
        # Try to delete without confirmation
        success, message = self.archive_mgr.permanently_delete_league(league_id, admin_id=1, confirm=False)
        
        self.assertFalse(success)
        self.assertIn("Confirmation required", message)
        
        # League should still exist
        league = self.db.get_league(league_id, include_archived=True)
        self.assertIsNotNone(league)
    
    def test_permanent_delete_active_league_fails(self):
        """Test permanent delete of active league fails"""
        league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        # Try to delete without archiving
        success, message = self.archive_mgr.permanently_delete_league(league_id, admin_id=1, confirm=True)
        
        self.assertFalse(success)
        self.assertIn("must be archived", message)
    
    def test_permanent_delete_archived_league(self):
        """Test permanent delete of archived league"""
        league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        self.archive_mgr.archive_league(league_id, admin_id=1)
        
        # Delete permanently
        success, message = self.archive_mgr.permanently_delete_league(league_id, admin_id=1, confirm=True)
        
        self.assertTrue(success)
        
        # League should not exist
        league = self.db.get_league(league_id, include_archived=True)
        self.assertIsNone(league)


class TestArchiveWorkflow(unittest.TestCase):
    """Test complete archive workflow"""
    
    def setUp(self):
        """Set up test database"""
        self.db = DatabaseManager(':memory:')
        self.archive_mgr = LeagueArchiveManager(self.db)
    
    def test_complete_archive_restore_workflow(self):
        """Test archiving, viewing, and restoring a league"""
        # Create league
        league_id = self.db.create_league(
            name="Test League",
            description="Test",
            creator_id=1,
            league_type="public"
        )
        
        # Verify in active leagues
        user_leagues = self.db.get_user_leagues(1)
        self.assertTrue(any(l['id'] == league_id for l in user_leagues))
        
        # Archive it
        success, _ = self.archive_mgr.archive_league(league_id, admin_id=1)
        self.assertTrue(success)
        
        # Verify not in active leagues
        user_leagues = self.db.get_user_leagues(1)
        self.assertFalse(any(l['id'] == league_id for l in user_leagues))
        
        # Verify in archived leagues
        archived = self.archive_mgr.get_user_archived_leagues(1)
        self.assertTrue(any(l['id'] == league_id for l in archived))
        
        # Restore it
        success, _ = self.archive_mgr.restore_league(league_id, admin_id=1)
        self.assertTrue(success)
        
        # Verify back in active leagues
        user_leagues = self.db.get_user_leagues(1)
        self.assertTrue(any(l['id'] == league_id for l in user_leagues))
        
        # Verify not in archived leagues
        archived = self.archive_mgr.get_user_archived_leagues(1)
        self.assertFalse(any(l['id'] == league_id for l in archived))


class TestErrorHandling(unittest.TestCase):
    """Test error handling in archive operations"""
    
    def setUp(self):
        """Set up test database"""
        self.db = DatabaseManager(':memory:')
        self.archive_mgr = LeagueArchiveManager(self.db)
    
    def test_archive_handles_missing_league(self):
        """Test archive handles missing league gracefully"""
        success, message = self.archive_mgr.archive_league(999999, admin_id=1)
        
        self.assertFalse(success)
        self.assertIsInstance(message, str)
        self.assertGreater(len(message), 0)
    
    def test_get_archived_leagues_empty(self):
        """Test get_archived_leagues returns empty list when none exist"""
        archived = self.archive_mgr.get_user_archived_leagues(1)
        
        self.assertIsInstance(archived, list)
        self.assertEqual(len(archived), 0)
    
    def test_statistics_with_no_archives(self):
        """Test statistics when no archives exist"""
        stats = self.archive_mgr.get_archive_statistics()
        
        self.assertEqual(stats['total_archived'], 0)


if __name__ == '__main__':
    unittest.main()
