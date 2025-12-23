"""
pytest configuration and fixtures
"""

import pytest
import os
from database.db_manager import DatabaseManager


@pytest.fixture(scope="session")
def test_db():
    """Create a test database for the entire test session"""
    db_path = "test_db.sqlite"
    
    # Remove existing test db
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db = DatabaseManager(db_path)
    
    yield db
    
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def clean_db(test_db):
    """Provide a clean database state for each test"""
    yield test_db
    
    # Reset data after each test (optional)
    # You can add cleanup logic here if needed


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
