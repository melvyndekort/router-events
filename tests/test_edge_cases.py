"""Edge case tests that actually validate important behavior."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from router_events.main import app

@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    with patch('router_events.main.db') as mock_db:
        mock_db.connect = AsyncMock()
        mock_db.get_device = AsyncMock(return_value=None)
        mock_db.add_device = AsyncMock()
        mock_db.update_device_name = AsyncMock()
        mock_db.set_device_notify = AsyncMock()
        
        with patch('router_events.main.notifier') as mock_notifier:
            mock_notifier.notify_unknown_device = AsyncMock()
            mock_notifier.notify_tracked_device = AsyncMock()
            
            yield TestClient(app)

def test_event_with_empty_host(client):
    """Test event processing with empty host."""
    test_event = {
        "action": "assigned",
        "mac": "00:11:22:33:44:55",
        "ip": "192.168.1.100",
        "host": ""
    }
    
    response = client.post("/api/events", json=test_event)
    assert response.status_code == 204

def test_event_with_whitespace_host(client):
    """Test event processing with whitespace-only host."""
    test_event = {
        "action": "assigned",
        "mac": "00:11:22:33:44:55",
        "ip": "192.168.1.100",
        "host": "   "
    }
    
    response = client.post("/api/events", json=test_event)
    assert response.status_code == 204

@patch('router_events.main.db')
@patch('router_events.main.notifier')
def test_known_device_name_fallback_logic(mock_notifier, mock_db, client):
    """Test device name fallback logic."""
    mock_db.get_device = AsyncMock(return_value={"name": "Device Name", "notify": True})
    mock_db.add_device = AsyncMock()
    mock_notifier.notify_tracked_device = AsyncMock()
    
    test_event = {
        "action": "assigned",
        "mac": "00:11:22:33:44:55",
        "ip": "192.168.1.100",
        "host": "hostname"
    }
    
    response = client.post("/api/events", json=test_event)
    assert response.status_code == 204
    
    # Verify the tracked device notification was called with the right name
    mock_notifier.notify_tracked_device.assert_called_once_with("Device Name", "00:11:22:33:44:55", "192.168.1.100")

def test_update_device_notify_only(client):
    """Test updating only notify flag."""
    mac = "00:11:22:33:44:55"
    update_data = {"notify": False}
    
    response = client.put(f"/api/devices/{mac}", json=update_data)
    assert response.status_code == 200
    assert response.json() == {"status": "updated"}

def test_update_device_empty_payload(client):
    """Test updating device with empty payload."""
    mac = "00:11:22:33:44:55"
    update_data = {}
    
    response = client.put(f"/api/devices/{mac}", json=update_data)
    assert response.status_code == 200
    assert response.json() == {"status": "updated"}
