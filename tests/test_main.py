"""Tests for the main FastAPI application."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from router_events.main import app, lifespan

@pytest.fixture
def client():
    """Create test client with mocked database."""
    with patch('router_events.main.db') as mock_db:
        mock_db.connect = AsyncMock()
        mock_db.get_device = AsyncMock(return_value=None)
        mock_db.get_all_devices = AsyncMock(return_value=[])
        mock_db.add_device = AsyncMock()
        mock_db.update_device_name = AsyncMock()
        mock_db.set_device_notify = AsyncMock()
        
        with patch('router_events.main.notifier') as mock_notifier:
            mock_notifier.notify_unknown_device = AsyncMock()
            mock_notifier.notify_tracked_device = AsyncMock()
            
            yield TestClient(app)

@pytest.mark.asyncio
async def test_lifespan():
    """Test application lifespan handler."""
    with patch('router_events.main.db') as mock_db:
        mock_db.connect = AsyncMock()
        
        async with lifespan(app):
            pass
        
        mock_db.connect.assert_called_once()

def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_receive_dhcp_event_unknown_device(client):
    """Test receiving a DHCP assignment event for unknown device."""
    test_event = {
        "action": "assigned",
        "mac": "00:11:22:33:44:55",
        "ip": "192.168.1.100",
        "host": "test-device"
    }
    
    response = client.post("/api/events", json=test_event)
    assert response.status_code == 204

@patch('router_events.main.db')
@patch('router_events.main.notifier')
def test_receive_dhcp_event_known_device_with_notify(mock_notifier, mock_db, client):
    """Test receiving event for known device with notifications enabled."""
    mock_db.get_device = AsyncMock(return_value={"name": "Known Device", "notify": True})
    mock_db.add_device = AsyncMock()
    mock_notifier.notify_tracked_device = AsyncMock()
    
    test_event = {
        "action": "assigned",
        "mac": "00:11:22:33:44:55",
        "ip": "192.168.1.100"
    }
    
    response = client.post("/api/events", json=test_event)
    assert response.status_code == 204

def test_receive_non_assigned_event(client):
    """Test receiving non-assignment event."""
    test_event = {
        "action": "released",
        "mac": "00:11:22:33:44:55",
        "ip": "192.168.1.100"
    }
    
    response = client.post("/api/events", json=test_event)
    assert response.status_code == 204

def test_receive_event_no_mac(client):
    """Test receiving event without MAC address."""
    test_event = {
        "action": "assigned",
        "ip": "192.168.1.100"
    }
    
    response = client.post("/api/events", json=test_event)
    assert response.status_code == 204

def test_receive_invalid_json(client):
    """Test handling of invalid JSON."""
    response = client.post("/api/events", content="invalid json")
    assert response.status_code == 204

def test_receive_non_json_content(client):
    """Test handling of non-JSON content."""
    response = client.post("/api/events", content="plain text", headers={"content-type": "text/plain"})
    assert response.status_code == 204

def test_receive_event_with_none_host(client):
    """Test event processing with None host value."""
    test_event = {
        "action": "assigned",
        "mac": "00:11:22:33:44:55",
        "ip": "192.168.1.100",
        "host": None
    }
    
    response = client.post("/api/events", json=test_event)
    assert response.status_code == 204

@patch('router_events.main.db')
def test_update_existing_device(mock_db, client):
    """Test updating existing device."""
    mock_db.get_device = AsyncMock(return_value={"name": "Old Name"})
    mock_db.update_device_name = AsyncMock()
    mock_db.set_device_notify = AsyncMock()
    
    mac = "00:11:22:33:44:55"
    update_data = {"name": "New Name", "notify": True}
    
    response = client.put(f"/api/devices/{mac}", json=update_data)
    assert response.status_code == 200
    assert response.json() == {"status": "updated"}

@patch('router_events.main.db')
def test_get_all_devices(mock_db, client):
    """Test getting all devices."""
    mock_devices = [
        {"mac": "00:11:22:33:44:55", "name": "Device 1"},
        {"mac": "00:11:22:33:44:66", "name": "Device 2"}
    ]
    mock_db.get_all_devices = AsyncMock(return_value=mock_devices)
    
    response = client.get("/api/devices")
    assert response.status_code == 200
    assert response.json() == {"devices": mock_devices}

@patch('router_events.main.db')
def test_get_device_found(mock_db, client):
    """Test getting existing device."""
    mock_device = {"mac": "00:11:22:33:44:55", "name": "Test Device"}
    mock_db.get_device = AsyncMock(return_value=mock_device)
    
    response = client.get("/api/devices/00:11:22:33:44:55")
    assert response.status_code == 200
    assert response.json() == mock_device

@patch('router_events.main.db')
def test_get_device_not_found(mock_db, client):
    """Test getting non-existent device."""
    mock_db.get_device = AsyncMock(return_value=None)
    
    response = client.get("/api/devices/00:11:22:33:44:55")
    assert response.status_code == 404
    assert response.json() == {"detail": "Device not found"}

def test_root_redirect(client):
    """Test root endpoint redirects to devices page."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/devices.html"

def test_devices_html_page(client):
    """Test devices HTML page endpoint."""
    response = client.get("/devices.html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

@patch('router_events.main.httpx.AsyncClient')
def test_get_manufacturer_success(mock_client, client):
    """Test successful manufacturer lookup."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "Apple, Inc."
    
    mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    
    response = client.get("/api/manufacturer/00:11:22:33:44:55")
    assert response.status_code == 200
    assert response.json() == {"manufacturer": "Apple, Inc."}

@patch('router_events.main.httpx.AsyncClient')
def test_get_manufacturer_unknown(mock_client, client):
    """Test manufacturer lookup failure."""
    import httpx
    mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=httpx.RequestError("API error"))
    
    response = client.get("/api/manufacturer/00:11:22:33:44:55")
    assert response.status_code == 200
    assert response.json() == {"manufacturer": "Unknown"}

def test_update_new_device(client):
    """Test updating non-existent device."""
    mac = "00:11:22:33:44:55"
    update_data = {"name": "My Device", "notify": True}
    
    response = client.put(f"/api/devices/{mac}", json=update_data)
    assert response.status_code == 200
    assert response.json() == {"status": "updated"}
