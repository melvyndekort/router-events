"""Tests for the main FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from router_events.main import app

client = TestClient(app)

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_receive_event():
    """Test the event receiving endpoint."""
    test_event = {
        "event": "dhcp-lease",
        "data": {
            "mac": "00:11:22:33:44:55",
            "ip": "192.168.1.100",
            "hostname": "test-device"
        }
    }
    
    response = client.post("/api/events", json=test_event)
    assert response.status_code == 204

def test_receive_invalid_event():
    """Test handling of invalid event data."""
    response = client.post("/api/events", content="invalid json")
    assert response.status_code == 422  # FastAPI returns 422 for invalid JSON
