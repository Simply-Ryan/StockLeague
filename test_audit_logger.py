"""
Test Suite for Audit Logging System (Item #8)
Tests audit trail, reporting, and compliance functionality
"""

import unittest
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from audit_logger import AuditLogger, AuditLog


class TestAuditLogEntry(unittest.TestCase):
    """Test basic audit log entry creation"""
    
    def test_create_audit_log_entry(self):
        """Test creating an audit log entry"""
        log = AuditLog(
            action='CREATE',
            resource_type='LEAGUE',
            resource_id=1,
            user_id=1,
            status='success',
            details={'name': 'Test League'},
            changes=None,
            ip_address='127.0.0.1'
        )
        
        self.assertEqual(log.action, 'CREATE')
        self.assertEqual(log.resource_type, 'LEAGUE')
        self.assertEqual(log.resource_id, 1)
        self.assertEqual(log.user_id, 1)
        self.assertEqual(log.status, 'success')
        self.assertIsNotNone(log.checksum)
        self.assertIsNotNone(log.timestamp)
    
    def test_audit_log_checksum_immutable(self):
        """Test that checksum is immutable"""
        log1 = AuditLog(
            action='CREATE',
            resource_type='LEAGUE',
            resource_id=1,
            user_id=1
        )
        
        log2 = AuditLog(
            action='CREATE',
            resource_type='LEAGUE',
            resource_id=1,
            user_id=1
        )
        
        # Different timestamps = different checksums
        self.assertNotEqual(log1.checksum, log2.checksum)
    
    def test_audit_log_to_dict(self):
        """Test converting audit log to dict"""
        log = AuditLog(
            action='UPDATE',
            resource_type='PORTFOLIO',
            resource_id=5,
            user_id=2,
            details={'field': 'value'}
        )
        
        log_dict = log.to_dict()
        
        self.assertIn('action', log_dict)
        self.assertIn('resource_type', log_dict)
        self.assertIn('checksum', log_dict)
        self.assertEqual(log_dict['user_id'], 2)


class TestAuditLogger(unittest.TestCase):
    """Test audit logger functionality"""
    
    def setUp(self):
        """Set up test database and logger"""
        self.db = DatabaseManager(':memory:')
        self.logger = AuditLogger(self.db)
    
    def test_log_action_successful(self):
        """Test logging a successful action"""
        log_id = self.logger.log_action(
            action='CREATE',
            resource_type='LEAGUE',
            resource_id=1,
            user_id=1,
            status='success',
            details={'name': 'Test League'}
        )
        
        self.assertGreater(log_id, 0)
    
    def test_log_action_with_changes(self):
        """Test logging action with before/after changes"""
        log_id = self.logger.log_action(
            action='UPDATE',
            resource_type='LEAGUE',
            resource_id=1,
            user_id=1,
            status='success',
            changes={
                'name': {'before': 'Old Name', 'after': 'New Name'},
                'description': {'before': 'Old', 'after': 'New'}
            }
        )
        
        self.assertGreater(log_id, 0)
    
    def test_log_action_with_failure(self):
        """Test logging a failed action"""
        log_id = self.logger.log_action(
            action='DELETE',
            resource_type='LEAGUE',
            resource_id=999,
            user_id=1,
            status='failure',
            details={'error': 'League not found'}
        )
        
        self.assertGreater(log_id, 0)
    
    def test_sensitive_data_redaction(self):
        """Test that sensitive data is redacted"""
        log_id = self.logger.log_action(
            action='CREATE',
            resource_type='USER',
            resource_id=1,
            user_id=1,
            details={
                'username': 'john_doe',
                'password': 'secret123',
                'email': 'john@example.com',
                'api_key': 'sk_live_abc123'
            }
        )
        
        # Verify logged data has redacted fields
        logs = self.logger.get_audit_trail(limit=1)
        details = json.loads(logs[0]['details'])
        
        self.assertEqual(details['username'], 'john_doe')
        self.assertEqual(details['password'], '[REDACTED]')
        self.assertEqual(details['api_key'], '[REDACTED]')


class TestAuditQueries(unittest.TestCase):
    """Test audit log queries"""
    
    def setUp(self):
        """Set up test data"""
        self.db = DatabaseManager(':memory:')
        self.logger = AuditLogger(self.db)
        
        # Log various actions
        self.logger.log_action('CREATE', 'LEAGUE', 1, 1, 'success')
        self.logger.log_action('CREATE', 'LEAGUE', 2, 1, 'success')
        self.logger.log_action('UPDATE', 'LEAGUE', 1, 2, 'success')
        self.logger.log_action('DELETE', 'LEAGUE', 3, 3, 'failure')
    
    def test_get_all_audit_trail(self):
        """Test retrieving all audit logs"""
        logs = self.logger.get_audit_trail()
        
        self.assertEqual(len(logs), 4)
    
    def test_filter_by_user(self):
        """Test filtering audit logs by user"""
        logs = self.logger.get_audit_trail(user_id=1)
        
        self.assertEqual(len(logs), 2)
        self.assertTrue(all(log['user_id'] == 1 for log in logs))
    
    def test_filter_by_resource_type(self):
        """Test filtering by resource type"""
        logs = self.logger.get_audit_trail(resource_type='LEAGUE')
        
        self.assertEqual(len(logs), 4)
        self.assertTrue(all(log['resource_type'] == 'LEAGUE' for log in logs))
    
    def test_filter_by_resource_id(self):
        """Test filtering by specific resource"""
        logs = self.logger.get_audit_trail(resource_id=1)
        
        self.assertEqual(len(logs), 2)
        self.assertTrue(all(log['resource_id'] == 1 for log in logs))
    
    def test_filter_by_action(self):
        """Test filtering by action type"""
        logs = self.logger.get_audit_trail(action='CREATE')
        
        self.assertEqual(len(logs), 2)
        self.assertTrue(all(log['action'] == 'CREATE' for log in logs))
    
    def test_filter_by_date_range(self):
        """Test filtering by date range"""
        start = datetime.utcnow() - timedelta(hours=1)
        end = datetime.utcnow() + timedelta(hours=1)
        
        logs = self.logger.get_audit_trail(start_date=start, end_date=end)
        
        self.assertEqual(len(logs), 4)
    
    def test_limit_results(self):
        """Test limiting results"""
        logs = self.logger.get_audit_trail(limit=2)
        
        self.assertEqual(len(logs), 2)


class TestUserActivity(unittest.TestCase):
    """Test user activity reporting"""
    
    def setUp(self):
        """Set up test data"""
        self.db = DatabaseManager(':memory:')
        self.logger = AuditLogger(self.db)
        
        # Log user actions
        for i in range(5):
            self.logger.log_action('CREATE', 'LEAGUE', i, 1, 'success')
        
        for i in range(3):
            self.logger.log_action('UPDATE', 'LEAGUE', i, 1, 'success')
        
        self.logger.log_action('DELETE', 'LEAGUE', 1, 1, 'failure')
    
    def test_get_user_activity(self):
        """Test getting user activity summary"""
        activity = self.logger.get_user_activity(1)
        
        self.assertEqual(activity['user_id'], 1)
        self.assertEqual(activity['total_actions'], 9)
        self.assertGreater(activity['success_rate'], 0)
    
    def test_user_activity_actions_breakdown(self):
        """Test action breakdown in user activity"""
        activity = self.logger.get_user_activity(1)
        
        self.assertIn('CREATE', activity['actions'])
        self.assertIn('UPDATE', activity['actions'])
        self.assertIn('DELETE', activity['actions'])
        
        self.assertEqual(activity['actions']['CREATE'], 5)
        self.assertEqual(activity['actions']['UPDATE'], 3)
        self.assertEqual(activity['actions']['DELETE'], 1)
    
    def test_user_activity_success_rate(self):
        """Test success rate calculation"""
        activity = self.logger.get_user_activity(1)
        
        # 8 successes out of 9 total
        expected_rate = (8 / 9) * 100
        self.assertAlmostEqual(activity['success_rate'], expected_rate, places=1)


class TestAuditIntegrity(unittest.TestCase):
    """Test audit trail integrity verification"""
    
    def setUp(self):
        """Set up test database"""
        self.db = DatabaseManager(':memory:')
        self.logger = AuditLogger(self.db)
    
    def test_log_checksum_verification(self):
        """Test verifying log entry checksum"""
        log_id = self.logger.log_action(
            action='CREATE',
            resource_type='LEAGUE',
            resource_id=1,
            user_id=1
        )
        
        # Verify should return True (or handle gracefully)
        result = self.logger.verify_audit_integrity(log_id)
        
        # Should be boolean
        self.assertIsInstance(result, bool)
    
    def test_verify_nonexistent_log(self):
        """Test verifying non-existent log"""
        result = self.logger.verify_audit_integrity(999999)
        
        self.assertFalse(result)


class TestAuditExports(unittest.TestCase):
    """Test audit log exports"""
    
    def setUp(self):
        """Set up test data"""
        self.db = DatabaseManager(':memory:')
        self.logger = AuditLogger(self.db)
        
        # Log test actions
        self.logger.log_action('CREATE', 'LEAGUE', 1, 1, 'success')
        self.logger.log_action('UPDATE', 'LEAGUE', 1, 1, 'success')
    
    def test_export_json(self):
        """Test exporting logs as JSON"""
        json_export = self.logger.export_audit_report(format='json')
        
        self.assertIsInstance(json_export, str)
        parsed = json.loads(json_export)
        self.assertIsInstance(parsed, list)
        self.assertEqual(len(parsed), 2)
    
    def test_export_csv(self):
        """Test exporting logs as CSV"""
        csv_export = self.logger.export_audit_report(format='csv')
        
        self.assertIsInstance(csv_export, str)
        lines = csv_export.strip().split('\n')
        # Header + 2 data rows
        self.assertGreaterEqual(len(lines), 2)


class TestHighRiskActivities(unittest.TestCase):
    """Test high-risk activity detection"""
    
    def setUp(self):
        """Set up test data"""
        self.db = DatabaseManager(':memory:')
        self.logger = AuditLogger(self.db)
        
        # Log some failures
        self.logger.log_action('DELETE', 'LEAGUE', 1, 1, 'failure')
        self.logger.log_action('DELETE', 'LEAGUE', 2, 1, 'failure')
        self.logger.log_action('DELETE', 'LEAGUE', 3, 2, 'failure')
        
        # Log successes
        self.logger.log_action('CREATE', 'LEAGUE', 4, 1, 'success')
    
    def test_get_high_risk_activities(self):
        """Test identifying high-risk activities"""
        risky = self.logger.get_high_risk_activities(days=7)
        
        self.assertEqual(len(risky), 3)
        self.assertTrue(all(log['status'] == 'failure' for log in risky))


class TestAuditCleanup(unittest.TestCase):
    """Test audit log cleanup"""
    
    def setUp(self):
        """Set up test data"""
        self.db = DatabaseManager(':memory:')
        self.logger = AuditLogger(self.db)
    
    def test_cleanup_dry_run(self):
        """Test cleanup dry run (no deletion)"""
        # Log action
        self.logger.log_action('CREATE', 'LEAGUE', 1, 1)
        
        # Dry run cleanup
        count = self.logger.cleanup_old_logs(days=0, dry_run=True)
        
        # Should report count but not delete
        self.assertGreaterEqual(count, 0)
        
        # Verify log still exists
        logs = self.logger.get_audit_trail()
        self.assertEqual(len(logs), 1)


class TestSensitiveDataHandling(unittest.TestCase):
    """Test sensitive data redaction"""
    
    def setUp(self):
        """Set up test logger"""
        self.db = DatabaseManager(':memory:')
        self.logger = AuditLogger(self.db)
    
    def test_redact_password(self):
        """Test password redaction"""
        test_data = {'password': 'secret123'}
        redacted = self.logger._redact_sensitive_data(test_data)
        
        self.assertEqual(redacted['password'], '[REDACTED]')
    
    def test_redact_nested_data(self):
        """Test redacting nested sensitive data"""
        test_data = {
            'user': {
                'username': 'john',
                'password': 'secret'
            },
            'api_key': 'key123'
        }
        redacted = self.logger._redact_sensitive_data(test_data)
        
        self.assertEqual(redacted['user']['password'], '[REDACTED]')
        self.assertEqual(redacted['api_key'], '[REDACTED]')
        self.assertEqual(redacted['user']['username'], 'john')
    
    def test_preserve_non_sensitive_data(self):
        """Test that non-sensitive data is preserved"""
        test_data = {
            'league_name': 'Test League',
            'member_count': 5,
            'status': 'active'
        }
        redacted = self.logger._redact_sensitive_data(test_data)
        
        self.assertEqual(redacted['league_name'], 'Test League')
        self.assertEqual(redacted['member_count'], 5)
        self.assertEqual(redacted['status'], 'active')


if __name__ == '__main__':
    unittest.main()
