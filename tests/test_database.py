"""Tests for database operations."""

from router_events.database import Database

def test_database_init():
    """Test database initialization."""
    database = Database()
    assert database.engine is None
    assert database.session_factory is None

def test_database_global_instance():
    """Test the global database instance exists."""
    from router_events.database import db
    assert isinstance(db, Database)
