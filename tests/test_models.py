"""Tests for database models."""

import pytest
from datetime import datetime

from router_events.models import Device, ManufacturerStatus


class TestManufacturerStatus:
    """Test ManufacturerStatus enum."""

    def test_enum_values(self):
        """Test enum values."""
        assert ManufacturerStatus.PENDING == "pending"
        assert ManufacturerStatus.FOUND == "found"
        assert ManufacturerStatus.UNKNOWN == "unknown"
        assert ManufacturerStatus.ERROR == "error"

    def test_is_final_true(self):
        """Test is_final returns True for final statuses."""
        assert ManufacturerStatus.FOUND.is_final() is True
        assert ManufacturerStatus.UNKNOWN.is_final() is True

    def test_is_final_false(self):
        """Test is_final returns False for non-final statuses."""
        assert ManufacturerStatus.PENDING.is_final() is False
        assert ManufacturerStatus.ERROR.is_final() is False


class TestDevice:
    """Test Device model."""

    def test_device_creation(self):
        """Test device creation."""
        device = Device(
            mac="00:11:22:33:44:55",
            name="Test Device",
            notify=True
        )
        
        assert device.mac == "00:11:22:33:44:55"
        assert device.name == "Test Device"
        assert device.notify is True
        # Note: manufacturer_status default is set by SQLAlchemy, not in constructor

    def test_device_repr(self):
        """Test device string representation."""
        device = Device(mac="00:11:22:33:44:55", name="Test Device")
        expected = "<Device(mac='00:11:22:33:44:55', name='Test Device')>"
        assert repr(device) == expected

    def test_display_name_with_name(self):
        """Test display name when name is set."""
        device = Device(mac="00:11:22:33:44:55", name="My Device")
        assert device.display_name == "My Device"

    def test_display_name_without_name(self):
        """Test display name when name is not set."""
        device = Device(mac="00:11:22:33:44:55")
        assert device.display_name == "Device 00:11:22:33:44:55"

    def test_device_defaults(self):
        """Test device default values."""
        device = Device(mac="00:11:22:33:44:55")
        
        assert device.name is None
        # Note: notify default is set by SQLAlchemy column definition
        assert device.manufacturer is None
        assert device.manufacturer_last_attempt is None
