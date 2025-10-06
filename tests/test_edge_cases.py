"""Edge case tests for the application."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import httpx

from router_events.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestEventProcessingEdgeCases:
    """Test edge cases in event processing."""

    @patch('router_events.main.process_device_event')
    def test_event_with_empty_host(self, mock_process, client):
        """Test event with empty host string."""
        mock_process.return_value = AsyncMock()
        
        event = {
            "action": "assigned",
            "mac": "00:11:22:33:44:55",
            "ip": "192.168.1.100",
            "host": ""
        }
        
        response = client.post("/api/events", json=event)
        assert response.status_code == 204

    @patch('router_events.main.process_device_event')
    def test_event_with_whitespace_host(self, mock_process, client):
        """Test event with whitespace-only host."""
        mock_process.return_value = AsyncMock()
        
        event = {
            "action": "assigned",
            "mac": "00:11:22:33:44:55",
            "ip": "192.168.1.100",
            "host": "   "
        }
        
        response = client.post("/api/events", json=event)
        assert response.status_code == 204

    def test_event_with_malformed_json(self, client):
        """Test event with malformed JSON."""
        response = client.post(
            "/api/events",
            content='{"action": "assigned", "mac":}',
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 204

    def test_event_with_missing_content_type(self, client):
        """Test event without content-type header."""
        response = client.post("/api/events", json={"action": "assigned"})
        # FastAPI automatically sets content-type for json parameter
        assert response.status_code == 204

    def test_event_processing_exception(self, client):
        """Test event processing with exception."""
        with patch('router_events.main.process_device_event', side_effect=Exception("Test error")):
            event = {
                "action": "assigned",
                "mac": "00:11:22:33:44:55",
                "ip": "192.168.1.100"
            }
            
            response = client.post("/api/events", json=event)
            assert response.status_code == 204  # Should still return 204


class TestManufacturerLookupEdgeCases:
    """Test edge cases in manufacturer lookup."""

    @patch('router_events.main.db')
    @patch('router_events.main.pending_lookups', set())
    def test_manufacturer_lookup_no_background_task(self, mock_db, client):
        """Test manufacturer lookup when background task not needed."""
        mock_db.get_manufacturer = AsyncMock(return_value=None)
        mock_db.needs_manufacturer_lookup = AsyncMock(return_value=False)
        
        response = client.get("/api/manufacturer/00:11:22:33:44:55")
        assert response.status_code == 200
        assert response.json() == {"manufacturer": "Loading..."}

    @patch('router_events.main.db')
    @patch('router_events.main.pending_lookups')
    def test_manufacturer_lookup_already_pending(self, mock_pending, mock_db, client):
        """Test manufacturer lookup when already pending."""
        mock_pending.__contains__ = MagicMock(return_value=True)
        mock_db.get_manufacturer = AsyncMock(return_value=None)
        mock_db.needs_manufacturer_lookup = AsyncMock(return_value=True)
        
        response = client.get("/api/manufacturer/00:11:22:33:44:55")
        assert response.status_code == 200
        assert response.json() == {"manufacturer": "Loading..."}

    @patch('router_events.main.db')
    @patch('router_events.main.pending_lookups', set())
    @patch('router_events.main.rate_limiter')
    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_lookup_manufacturer_not_found_response(self, mock_client_class, mock_limiter, mock_db):
        """Test manufacturer lookup with 'Not Found' response."""
        from router_events.main import lookup_manufacturer
        
        mock_db.needs_manufacturer_lookup = AsyncMock(return_value=True)
        mock_db.set_manufacturer = AsyncMock()
        mock_limiter.wait_if_needed = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Not Found"
        
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        await lookup_manufacturer("00:11:22:33:44:55")
        
        # Should mark as unknown when "Not Found" is returned
        mock_db.set_manufacturer.assert_any_call("00:11:22:33:44:55", 'Unknown', 'unknown')

    @patch('router_events.main.db')
    @patch('router_events.main.pending_lookups', set())
    @patch('router_events.main.rate_limiter')
    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_lookup_manufacturer_error_response(self, mock_client_class, mock_limiter, mock_db):
        """Test manufacturer lookup with error response."""
        from router_events.main import lookup_manufacturer
        
        mock_db.needs_manufacturer_lookup = AsyncMock(return_value=True)
        mock_db.set_manufacturer = AsyncMock()
        mock_limiter.wait_if_needed = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Error: Invalid MAC"
        
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        await lookup_manufacturer("00:11:22:33:44:55")
        
        # Should mark as unknown when error is returned
        mock_db.set_manufacturer.assert_any_call("00:11:22:33:44:55", 'Unknown', 'unknown')

    @patch('router_events.main.db')
    @patch('router_events.main.pending_lookups', set())
    @patch('router_events.main.rate_limiter')
    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_lookup_manufacturer_empty_response(self, mock_client_class, mock_limiter, mock_db):
        """Test manufacturer lookup with empty response."""
        from router_events.main import lookup_manufacturer
        
        mock_db.needs_manufacturer_lookup = AsyncMock(return_value=True)
        mock_db.set_manufacturer = AsyncMock()
        mock_limiter.wait_if_needed = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        await lookup_manufacturer("00:11:22:33:44:55")
        
        # Should mark as unknown when empty response
        mock_db.set_manufacturer.assert_any_call("00:11:22:33:44:55", 'Unknown', 'unknown')

    @patch('router_events.main.db')
    @patch('router_events.main.pending_lookups', set())
    @patch('router_events.main.rate_limiter')
    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_lookup_manufacturer_404_response(self, mock_client_class, mock_limiter, mock_db):
        """Test manufacturer lookup with 404 response."""
        from router_events.main import lookup_manufacturer
        
        mock_db.needs_manufacturer_lookup = AsyncMock(return_value=True)
        mock_db.set_manufacturer = AsyncMock()
        mock_limiter.wait_if_needed = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        await lookup_manufacturer("00:11:22:33:44:55")
        
        # Should mark as unknown when all APIs fail
        mock_db.set_manufacturer.assert_any_call("00:11:22:33:44:55", 'Unknown', 'unknown')

    @patch('router_events.main.db')
    @patch('router_events.main.pending_lookups', set())
    @patch('router_events.main.rate_limiter')
    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_lookup_manufacturer_maclookup_json_response(self, mock_client_class, mock_limiter, mock_db):
        """Test manufacturer lookup with maclookup.app JSON response."""
        from router_events.main import lookup_manufacturer
        
        mock_db.needs_manufacturer_lookup = AsyncMock(return_value=True)
        mock_db.set_manufacturer = AsyncMock()
        mock_limiter.wait_if_needed = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"company": "Apple, Inc."}
        mock_response.text.strip.return_value = "Apple, Inc."
        
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        await lookup_manufacturer("00:11:22:33:44:55")
        
        # Should call set_manufacturer with the parsed response
        mock_db.set_manufacturer.assert_any_call("00:11:22:33:44:55", "Apple, Inc.", 'found')


class TestDeviceUpdateEdgeCases:
    """Test edge cases in device updates."""

    @patch('router_events.main.db')
    def test_update_device_name_only(self, mock_db, client):
        """Test updating device with name only."""
        mock_db.get_device = AsyncMock(return_value=MagicMock())
        mock_db.set_device_name = AsyncMock()
        mock_db.set_device_notify = AsyncMock()
        
        update_data = {"name": "New Name"}
        response = client.put("/api/devices/00:11:22:33:44:55", json=update_data)
        
        assert response.status_code == 200
        mock_db.set_device_name.assert_called_once()
        mock_db.set_device_notify.assert_not_called()

    @patch('router_events.main.db')
    def test_update_device_notify_only(self, mock_db, client):
        """Test updating device with notify only."""
        mock_db.get_device = AsyncMock(return_value=MagicMock())
        mock_db.set_device_name = AsyncMock()
        mock_db.set_device_notify = AsyncMock()
        
        update_data = {"notify": True}
        response = client.put("/api/devices/00:11:22:33:44:55", json=update_data)
        
        assert response.status_code == 200
        mock_db.set_device_name.assert_not_called()
        mock_db.set_device_notify.assert_called_once()

    @patch('router_events.main.db')
    def test_update_device_empty_request(self, mock_db, client):
        """Test updating device with empty request."""
        mock_db.get_device = AsyncMock(return_value=MagicMock())
        mock_db.set_device_name = AsyncMock()
        mock_db.set_device_notify = AsyncMock()
        
        update_data = {}
        response = client.put("/api/devices/00:11:22:33:44:55", json=update_data)
        
        assert response.status_code == 200
        mock_db.set_device_name.assert_not_called()
        mock_db.set_device_notify.assert_not_called()


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_large_request_body(self, client):
        """Test handling of large request body."""
        large_host = "x" * 10000
        event = {
            "action": "assigned",
            "mac": "00:11:22:33:44:55",
            "ip": "192.168.1.100",
            "host": large_host
        }
        
        response = client.post("/api/events", json=event)
        assert response.status_code == 204  # Should handle gracefully
