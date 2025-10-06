"""Tests for the main FastAPI application."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import httpx

from router_events.main import app, lifespan, process_device_event, lookup_manufacturer, get_device_attr, _parse_manufacturer_response, RateLimiter
from router_events.models import Device, ManufacturerStatus
from datetime import datetime


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_device():
    """Mock device object."""
    device = MagicMock()
    device.mac = "00:11:22:33:44:55"
    device.name = "Test Device"
    device.notify = True
    device.first_seen = datetime(2024, 1, 1, 10, 0, 0)
    device.last_seen = datetime(2024, 1, 1, 12, 0, 0)
    return device


class TestRateLimiter:
    """Test RateLimiter class."""

    @pytest.mark.asyncio
    async def test_rate_limiter_no_wait(self):
        """Test rate limiter when no wait is needed."""
        limiter = RateLimiter(interval=0.1)
        await limiter.wait_if_needed()
        # Should complete quickly
        assert limiter.last_request > 0

    @pytest.mark.asyncio
    async def test_rate_limiter_with_wait(self):
        """Test rate limiter enforces wait."""
        limiter = RateLimiter(interval=0.1)
        limiter.last_request = 999999999  # Force wait
        start_time = limiter.last_request
        await limiter.wait_if_needed()
        assert limiter.last_request > start_time


class TestUtilityFunctions:
    """Test utility functions."""

    def test_get_device_attr_object(self):
        """Test getting attribute from object."""
        # Create a simple object without get method
        class SimpleDevice:
            def __init__(self):
                self.name = "Test"
        
        device = SimpleDevice()
        assert get_device_attr(device, 'name') == "Test"
        assert get_device_attr(device, 'missing', 'default') == 'default'

    def test_get_device_attr_dict(self):
        """Test getting attribute from dict."""
        device = {'name': 'Test'}
        assert get_device_attr(device, 'name') == "Test"
        assert get_device_attr(device, 'missing', 'default') == 'default'

    def test_get_device_attr_neither(self):
        """Test getting attribute from neither object nor dict."""
        device = "not_dict_or_object"
        assert get_device_attr(device, 'name', 'default') == 'default'

    @pytest.mark.asyncio
    async def test_parse_manufacturer_response_maclookup(self):
        """Test parsing maclookup.app response."""
        response = MagicMock()
        response.json.return_value = {'company': 'Apple, Inc.'}
        result = await _parse_manufacturer_response(response, "https://maclookup.app/api")
        assert result == 'Apple, Inc.'

    @pytest.mark.asyncio
    async def test_parse_manufacturer_response_maclookup_alt(self):
        """Test parsing maclookup.app response with companyName."""
        response = MagicMock()
        response.json.return_value = {'companyName': 'Apple, Inc.'}
        result = await _parse_manufacturer_response(response, "https://maclookup.app/api")
        assert result == 'Apple, Inc.'

    @pytest.mark.asyncio
    async def test_parse_manufacturer_response_text(self):
        """Test parsing plain text response."""
        response = MagicMock()
        response.text = "Apple, Inc."
        result = await _parse_manufacturer_response(response, "https://api.macvendors.com")
        assert result == "Apple, Inc."

    @pytest.mark.asyncio
    async def test_parse_manufacturer_response_json_error(self):
        """Test parsing response with JSON error."""
        response = MagicMock()
        response.json.side_effect = ValueError("Invalid JSON")
        response.text = "Apple, Inc."
        result = await _parse_manufacturer_response(response, "https://maclookup.app/api")
        assert result == "Apple, Inc."


class TestLifespan:
    """Test application lifespan."""

    @pytest.mark.asyncio
    async def test_lifespan(self):
        """Test application lifespan handler."""
        with patch('router_events.main.db') as mock_db:
            mock_db.connect = AsyncMock()
            mock_db.close = AsyncMock()
            
            async with lifespan(app):
                pass
            
            mock_db.connect.assert_called_once()
            mock_db.close.assert_called_once()


class TestEndpoints:
    """Test API endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_root_redirect(self, client):
        """Test root endpoint redirects."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/devices.html"

    @patch('router_events.main.FileResponse')
    def test_devices_page(self, mock_file_response, client):
        """Test devices HTML page."""
        mock_file_response.return_value = MagicMock()
        response = client.get("/devices.html")
        mock_file_response.assert_called_once_with("static/devices.html")

    @patch('router_events.main.process_device_event')
    def test_receive_event_valid(self, mock_process, client):
        """Test receiving valid event."""
        mock_process.return_value = AsyncMock()
        
        event = {
            "action": "assigned",
            "mac": "00:11:22:33:44:55",
            "ip": "192.168.1.100",
            "host": "test-device"
        }
        
        response = client.post("/api/events", json=event)
        assert response.status_code == 204

    def test_receive_event_non_json(self, client):
        """Test receiving non-JSON event."""
        response = client.post("/api/events", content="not json", headers={"content-type": "text/plain"})
        assert response.status_code == 204

    def test_receive_event_invalid_json(self, client):
        """Test receiving invalid JSON."""
        response = client.post("/api/events", content="invalid json", headers={"content-type": "application/json"})
        assert response.status_code == 204

    def test_receive_event_non_assigned(self, client):
        """Test receiving non-assigned event."""
        event = {"action": "released", "mac": "00:11:22:33:44:55"}
        response = client.post("/api/events", json=event)
        assert response.status_code == 204

    def test_receive_event_no_mac(self, client):
        """Test receiving event without MAC."""
        event = {"action": "assigned", "ip": "192.168.1.100"}
        response = client.post("/api/events", json=event)
        assert response.status_code == 204

    @patch('router_events.main.db')
    def test_get_devices(self, mock_db, client, mock_device):
        """Test getting all devices."""
        mock_db.get_devices = AsyncMock(return_value=[mock_device])
        
        response = client.get("/api/devices")
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert len(data["devices"]) == 1
        assert data["devices"][0]["mac"] == "00:11:22:33:44:55"

    @patch('router_events.main.db')
    def test_get_device_found(self, mock_db, client, mock_device):
        """Test getting existing device."""
        mock_db.get_device = AsyncMock(return_value=mock_device)
        
        response = client.get("/api/devices/00:11:22:33:44:55")
        assert response.status_code == 200
        data = response.json()
        assert data["mac"] == "00:11:22:33:44:55"
        assert data["name"] == "Test Device"

    @patch('router_events.main.db')
    def test_get_device_not_found(self, mock_db, client):
        """Test getting non-existent device."""
        mock_db.get_device = AsyncMock(return_value=None)
        
        response = client.get("/api/devices/00:11:22:33:44:55")
        assert response.status_code == 404
        assert response.json() == {"detail": "Device not found"}

    @patch('router_events.main.db')
    def test_update_device_existing(self, mock_db, client, mock_device):
        """Test updating existing device."""
        mock_db.get_device = AsyncMock(return_value=mock_device)
        mock_db.set_device_name = AsyncMock()
        mock_db.set_device_notify = AsyncMock()
        
        update_data = {"name": "New Name", "notify": False}
        response = client.put("/api/devices/00:11:22:33:44:55", json=update_data)
        
        assert response.status_code == 200
        assert response.json() == {"status": "updated"}
        mock_db.set_device_name.assert_called_once_with("00:11:22:33:44:55", "New Name")
        mock_db.set_device_notify.assert_called_once_with("00:11:22:33:44:55", False)

    @patch('router_events.main.db')
    def test_update_device_new(self, mock_db, client):
        """Test updating non-existent device."""
        mock_db.get_device = AsyncMock(return_value=None)
        mock_db.add_device = AsyncMock()
        mock_db.set_device_name = AsyncMock()
        
        update_data = {"name": "New Device"}
        response = client.put("/api/devices/00:11:22:33:44:55", json=update_data)
        
        assert response.status_code == 200
        mock_db.add_device.assert_called_once_with("00:11:22:33:44:55", "New Device")

    @patch('router_events.main.db')
    def test_get_manufacturer_cached(self, mock_db, client):
        """Test getting cached manufacturer."""
        mock_db.get_manufacturer = AsyncMock(return_value="Apple, Inc.")
        
        response = client.get("/api/manufacturer/00:11:22:33:44:55")
        assert response.status_code == 200
        assert response.json() == {"manufacturer": "Apple, Inc."}

    @patch('router_events.main.db')
    def test_get_manufacturer_no_background_task(self, mock_db, client):
        """Test manufacturer lookup when background task not needed."""
        mock_db.get_manufacturer = AsyncMock(return_value=None)
        mock_db.needs_manufacturer_lookup = AsyncMock(return_value=False)
        
        response = client.get("/api/manufacturer/00:11:22:33:44:55")
        assert response.status_code == 200
        assert response.json() == {"manufacturer": "Loading..."}

    @patch('router_events.main.db')
    def test_retry_failed_lookups(self, mock_db, client):
        """Test retrying failed manufacturer lookups."""
        mock_db.retry_failed_manufacturer_lookups = AsyncMock(return_value=5)
        
        response = client.post("/api/manufacturer/retry")
        assert response.status_code == 200
        assert response.json() == {"message": "Reset 5 failed lookups for retry"}

    @patch('router_events.main.db')
    def test_retry_manufacturer_lookup_endpoint(self, mock_db, client):
        """Test retry manufacturer lookup endpoint without background task."""
        mock_db.reset_manufacturer_lookup = AsyncMock()
        
        # Mock the background task to avoid execution
        with patch('router_events.main.lookup_manufacturer') as mock_lookup:
            response = client.post("/api/manufacturer/00:11:22:33:44:55/retry")
            assert response.status_code == 200
            assert response.json() == {"message": "Manufacturer lookup reset for 00:11:22:33:44:55"}


class TestProcessDeviceEvent:
    """Test device event processing."""

    @patch('router_events.main.db')
    @patch('router_events.main.notifier')
    @pytest.mark.asyncio
    async def test_process_new_device(self, mock_notifier, mock_db):
        """Test processing event for new device."""
        mock_db.get_device = AsyncMock(return_value=None)
        mock_db.add_device = AsyncMock()
        mock_notifier.notify_unknown_device = AsyncMock()
        
        await process_device_event("00:11:22:33:44:55", "192.168.1.100", "test-host")
        
        mock_db.add_device.assert_called_once_with("00:11:22:33:44:55", "test-host")
        mock_notifier.notify_unknown_device.assert_called_once_with(
            "00:11:22:33:44:55", "192.168.1.100", "test-host"
        )

    @patch('router_events.main.db')
    @patch('router_events.main.notifier')
    @pytest.mark.asyncio
    async def test_process_existing_device_notify(self, mock_notifier, mock_db, mock_device):
        """Test processing event for existing device with notifications."""
        mock_db.get_device = AsyncMock(return_value=mock_device)
        mock_db.add_device = AsyncMock()
        mock_notifier.notify_tracked_device = AsyncMock()
        
        await process_device_event("00:11:22:33:44:55", "192.168.1.100", "test-host")
        
        mock_db.add_device.assert_called_once_with("00:11:22:33:44:55", "test-host")
        mock_notifier.notify_tracked_device.assert_called_once_with(
            "Test Device", "00:11:22:33:44:55", "192.168.1.100"
        )

    @patch('router_events.main.db')
    @patch('router_events.main.notifier')
    @pytest.mark.asyncio
    async def test_process_existing_device_no_notify(self, mock_notifier, mock_db):
        """Test processing event for existing device without notifications."""
        device = MagicMock()
        device.name = "Test Device"
        device.notify = False
        
        mock_db.get_device = AsyncMock(return_value=device)
        mock_db.add_device = AsyncMock()
        mock_notifier.notify_tracked_device = AsyncMock()
        
        await process_device_event("00:11:22:33:44:55", "192.168.1.100", "test-host")
        
        mock_notifier.notify_tracked_device.assert_not_called()


class TestManufacturerLookup:
    """Test manufacturer lookup functionality."""

    @patch('router_events.main.db')
    @patch('router_events.main.pending_lookups', set())
    @patch('router_events.main.rate_limiter')
    @pytest.mark.asyncio
    async def test_lookup_manufacturer_already_pending(self, mock_limiter, mock_db):
        """Test lookup when already pending."""
        from router_events.main import pending_lookups
        pending_lookups.add("00:11:22:33:44:55")
        
        await lookup_manufacturer("00:11:22:33:44:55")
        
        mock_db.needs_manufacturer_lookup.assert_not_called()

    @patch('router_events.main.db')
    @patch('router_events.main.pending_lookups', set())
    @patch('router_events.main.rate_limiter')
    @pytest.mark.asyncio
    async def test_lookup_manufacturer_not_needed(self, mock_limiter, mock_db):
        """Test lookup when not needed."""
        mock_db.needs_manufacturer_lookup = AsyncMock(return_value=False)
        
        await lookup_manufacturer("00:11:22:33:44:55")
        
        mock_db.set_manufacturer.assert_not_called()

    @patch('router_events.main.db')
    @patch('router_events.main.pending_lookups', set())
    @patch('router_events.main.rate_limiter')
    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_lookup_manufacturer_success(self, mock_client_class, mock_limiter, mock_db):
        """Test successful manufacturer lookup."""
        mock_db.needs_manufacturer_lookup = AsyncMock(return_value=True)
        mock_db.set_manufacturer = AsyncMock()
        mock_limiter.wait_if_needed = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Apple, Inc."
        
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        await lookup_manufacturer("00:11:22:33:44:55")
        
        mock_db.set_manufacturer.assert_any_call("00:11:22:33:44:55", None, 'pending')
        mock_db.set_manufacturer.assert_any_call("00:11:22:33:44:55", "Apple, Inc.", 'found')

    @patch('router_events.main.db')
    @patch('router_events.main.pending_lookups', set())
    @patch('router_events.main.rate_limiter')
    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_lookup_manufacturer_all_fail(self, mock_client_class, mock_limiter, mock_db):
        """Test manufacturer lookup when all APIs fail."""
        mock_db.needs_manufacturer_lookup = AsyncMock(return_value=True)
        mock_db.set_manufacturer = AsyncMock()
        mock_limiter.wait_if_needed = AsyncMock()
        
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.RequestError("Network error"))
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        await lookup_manufacturer("00:11:22:33:44:55")
        
        mock_db.set_manufacturer.assert_any_call("00:11:22:33:44:55", 'Unknown', 'unknown')


