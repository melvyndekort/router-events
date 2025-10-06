"""Unit tests for database operations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from router_events.database import Database
from router_events.models import Device, ManufacturerStatus


class TestDatabase:
    """Test Database class."""

    def test_init(self):
        """Test database initialization."""
        db = Database()
        assert db.engine is None
        assert db.session_factory is None

    @patch('router_events.database.create_async_engine')
    @patch('router_events.database.sessionmaker')
    @pytest.mark.asyncio
    async def test_connect(self, mock_sessionmaker, mock_create_engine):
        """Test database connection."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_session_factory = MagicMock()
        mock_sessionmaker.return_value = mock_session_factory
        
        # Mock the engine.begin context manager
        mock_conn = MagicMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_conn.run_sync = AsyncMock()
        
        # Mock session for connection test
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        db = Database()
        await db.connect()
        
        assert db.engine == mock_engine
        assert db.session_factory == mock_session_factory
        mock_create_engine.assert_called_once()
        mock_sessionmaker.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self):
        """Test database close."""
        db = Database()
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        db.engine = mock_engine
        
        await db.close()
        mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_engine(self):
        """Test database close with no engine."""
        db = Database()
        # Should not raise exception
        await db.close()

    @patch('router_events.database.datetime')
    @pytest.mark.asyncio
    async def test_add_device_new(self, mock_datetime):
        """Test adding new device."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.datetime.now.return_value = mock_now
        
        db = Database()
        mock_session = MagicMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await db.add_device("00:11:22:33:44:55", "Test Device")
        
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        assert isinstance(result, Device)

    @patch('router_events.database.datetime')
    @pytest.mark.asyncio
    async def test_add_device_existing(self, mock_datetime):
        """Test updating existing device."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.datetime.now.return_value = mock_now
        
        existing_device = Device(mac="00:11:22:33:44:55", name="Old Name")
        
        db = Database()
        mock_session = MagicMock()
        mock_session.get = AsyncMock(return_value=existing_device)
        mock_session.commit = AsyncMock()
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await db.add_device("00:11:22:33:44:55", "New Name")
        
        assert result.last_seen == mock_now
        assert result.name == "Old Name"  # Should not overwrite existing name
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_devices(self):
        """Test getting all devices."""
        mock_devices = [
            Device(mac="00:11:22:33:44:55", name="Device 1"),
            Device(mac="00:11:22:33:44:66", name="Device 2")
        ]
        
        db = Database()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_devices
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await db.get_devices()
        
        assert result == mock_devices
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_device(self):
        """Test getting device by MAC."""
        mock_device = Device(mac="00:11:22:33:44:55", name="Test Device")
        
        db = Database()
        mock_session = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_device)
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await db.get_device("00:11:22:33:44:55")
        
        assert result == mock_device
        mock_session.get.assert_called_once_with(Device, "00:11:22:33:44:55")

    @pytest.mark.asyncio
    async def test_set_device_name(self):
        """Test setting device name."""
        db = Database()
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        await db.set_device_name("00:11:22:33:44:55", "New Name")
        
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_device_notify(self):
        """Test setting device notification setting."""
        db = Database()
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        await db.set_device_notify("00:11:22:33:44:55", True)
        
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_manufacturer_found(self):
        """Test getting manufacturer with found status."""
        db = Database()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.first.return_value = ("Apple, Inc.", ManufacturerStatus.FOUND)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await db.get_manufacturer("00:11:22:33:44:55")
        
        assert result == "Apple, Inc."

    @pytest.mark.asyncio
    async def test_get_manufacturer_unknown(self):
        """Test getting manufacturer with unknown status."""
        db = Database()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.first.return_value = (None, ManufacturerStatus.UNKNOWN)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await db.get_manufacturer("00:11:22:33:44:55")
        
        assert result == "Unknown"

    @pytest.mark.asyncio
    async def test_get_manufacturer_pending(self):
        """Test getting manufacturer with pending status."""
        db = Database()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.first.return_value = (None, ManufacturerStatus.PENDING)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await db.get_manufacturer("00:11:22:33:44:55")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_needs_manufacturer_lookup_no_device(self):
        """Test needs lookup for non-existent device."""
        db = Database()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await db.needs_manufacturer_lookup("00:11:22:33:44:55")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_needs_manufacturer_lookup_found(self):
        """Test needs lookup for device with found manufacturer."""
        db = Database()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.first.return_value = (ManufacturerStatus.FOUND, None, "Apple, Inc.")
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await db.needs_manufacturer_lookup("00:11:22:33:44:55")
        
        assert result is False

    @patch('router_events.database.datetime')
    @pytest.mark.asyncio
    async def test_needs_manufacturer_lookup_error_retry(self, mock_datetime):
        """Test needs lookup for error status with old timestamp."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_old = datetime(2024, 1, 1, 11, 0, 0)  # 1 hour ago
        mock_datetime.datetime.now.return_value = mock_now
        
        db = Database()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.first.return_value = (ManufacturerStatus.ERROR, mock_old, None)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await db.needs_manufacturer_lookup("00:11:22:33:44:55")
        
        assert result is True

    @patch('router_events.database.datetime')
    @pytest.mark.asyncio
    async def test_set_manufacturer(self, mock_datetime):
        """Test setting manufacturer."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.datetime.now.return_value = mock_now
        
        db = Database()
        mock_session = MagicMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        await db.set_manufacturer("00:11:22:33:44:55", "Apple, Inc.", "found")
        
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_manufacturer_invalid_status(self):
        """Test setting manufacturer with invalid status."""
        db = Database()
        mock_session = MagicMock()
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Should handle invalid status gracefully
        await db.set_manufacturer("00:11:22:33:44:55", "Apple", "invalid")
        
        # Should not call session methods due to invalid status
        mock_session.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_retry_failed_manufacturer_lookups(self):
        """Test retrying failed manufacturer lookups."""
        db = Database()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await db.retry_failed_manufacturer_lookups()
        
        assert result == 5
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_manufacturer_lookup(self):
        """Test resetting manufacturer lookup."""
        db = Database()
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        
        db.session_factory = MagicMock()
        db.session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        db.session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        await db.reset_manufacturer_lookup("00:11:22:33:44:55")
        
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
