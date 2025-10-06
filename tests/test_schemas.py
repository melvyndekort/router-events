"""Tests for API schemas."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from router_events.schemas import (
    EventRequest, DeviceResponse, DevicesResponse, DeviceUpdateRequest,
    UpdateResponse, ManufacturerResponse, HealthResponse
)


class TestEventRequest:
    """Test EventRequest schema."""

    def test_valid_event_request(self):
        """Test valid event request."""
        data = {
            "action": "assigned",
            "mac": "00:11:22:33:44:55",
            "ip": "192.168.1.100",
            "host": "test-device"
        }
        event = EventRequest(**data)
        
        assert event.action == "assigned"
        assert event.mac == "00:11:22:33:44:55"
        assert event.ip == "192.168.1.100"
        assert event.host == "test-device"

    def test_event_request_no_host(self):
        """Test event request without host."""
        data = {
            "action": "assigned",
            "mac": "00:11:22:33:44:55",
            "ip": "192.168.1.100"
        }
        event = EventRequest(**data)
        assert event.host is None

    def test_mac_validation_valid_colon(self):
        """Test MAC validation with colons."""
        data = {
            "action": "assigned",
            "mac": "00:11:22:33:44:55",
            "ip": "192.168.1.100"
        }
        event = EventRequest(**data)
        assert event.mac == "00:11:22:33:44:55"

    def test_mac_validation_valid_dash(self):
        """Test MAC validation with dashes."""
        data = {
            "action": "assigned",
            "mac": "00-11-22-33-44-55",
            "ip": "192.168.1.100"
        }
        event = EventRequest(**data)
        assert event.mac == "00-11-22-33-44-55"

    def test_mac_validation_case_conversion(self):
        """Test MAC address case conversion."""
        data = {
            "action": "assigned",
            "mac": "AA:BB:CC:DD:EE:FF",
            "ip": "192.168.1.100"
        }
        event = EventRequest(**data)
        assert event.mac == "aa:bb:cc:dd:ee:ff"

    def test_mac_validation_invalid_length(self):
        """Test MAC validation with invalid length."""
        data = {
            "action": "assigned",
            "mac": "00:11:22:33:44",
            "ip": "192.168.1.100"
        }
        with pytest.raises(ValidationError):
            EventRequest(**data)

    def test_mac_validation_invalid_format(self):
        """Test MAC validation with invalid format."""
        data = {
            "action": "assigned",
            "mac": "00.11.22.33.44.55",
            "ip": "192.168.1.100"
        }
        with pytest.raises(ValidationError):
            EventRequest(**data)


class TestDeviceResponse:
    """Test DeviceResponse schema."""

    def test_device_response(self):
        """Test device response creation."""
        data = {
            "mac": "00:11:22:33:44:55",
            "name": "Test Device",
            "notify": True,
            "first_seen": datetime(2024, 1, 1, 10, 0, 0),
            "last_seen": datetime(2024, 1, 1, 12, 0, 0)
        }
        response = DeviceResponse(**data)
        
        assert response.mac == "00:11:22:33:44:55"
        assert response.name == "Test Device"
        assert response.notify is True
        assert response.first_seen == datetime(2024, 1, 1, 10, 0, 0)
        assert response.last_seen == datetime(2024, 1, 1, 12, 0, 0)

    def test_device_response_defaults(self):
        """Test device response with defaults."""
        data = {
            "mac": "00:11:22:33:44:55",
            "first_seen": datetime(2024, 1, 1, 10, 0, 0),
            "last_seen": datetime(2024, 1, 1, 12, 0, 0)
        }
        response = DeviceResponse(**data)
        
        assert response.name is None
        assert response.notify is False


class TestDevicesResponse:
    """Test DevicesResponse schema."""

    def test_devices_response(self):
        """Test devices response."""
        device_data = {
            "mac": "00:11:22:33:44:55",
            "first_seen": datetime(2024, 1, 1, 10, 0, 0),
            "last_seen": datetime(2024, 1, 1, 12, 0, 0)
        }
        device = DeviceResponse(**device_data)
        response = DevicesResponse(devices=[device])
        
        assert len(response.devices) == 1
        assert response.devices[0].mac == "00:11:22:33:44:55"


class TestDeviceUpdateRequest:
    """Test DeviceUpdateRequest schema."""

    def test_device_update_request(self):
        """Test device update request."""
        data = {"name": "New Name", "notify": True}
        request = DeviceUpdateRequest(**data)
        
        assert request.name == "New Name"
        assert request.notify is True

    def test_device_update_request_partial(self):
        """Test partial device update request."""
        data = {"name": "New Name"}
        request = DeviceUpdateRequest(**data)
        
        assert request.name == "New Name"
        assert request.notify is None

    def test_name_validation_empty_string(self):
        """Test name validation with empty string."""
        data = {"name": "   "}
        request = DeviceUpdateRequest(**data)
        assert request.name is None

    def test_name_validation_none(self):
        """Test name validation with None."""
        data = {"name": None}
        request = DeviceUpdateRequest(**data)
        assert request.name is None

    def test_name_validation_valid(self):
        """Test name validation with valid string."""
        data = {"name": "Valid Name"}
        request = DeviceUpdateRequest(**data)
        assert request.name == "Valid Name"

    def test_name_validation_max_length(self):
        """Test name validation with max length."""
        long_name = "a" * 256
        data = {"name": long_name}
        with pytest.raises(ValidationError):
            DeviceUpdateRequest(**data)


class TestOtherSchemas:
    """Test other response schemas."""

    def test_update_response(self):
        """Test update response."""
        response = UpdateResponse(status="updated")
        assert response.status == "updated"

    def test_manufacturer_response(self):
        """Test manufacturer response."""
        response = ManufacturerResponse(manufacturer="Apple, Inc.")
        assert response.manufacturer == "Apple, Inc."

    def test_health_response(self):
        """Test health response."""
        response = HealthResponse(status="healthy")
        assert response.status == "healthy"
