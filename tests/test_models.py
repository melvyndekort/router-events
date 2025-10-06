"""Tests for Pydantic schemas."""

from router_events.schemas import EventRequest, DeviceUpdateRequest

def test_event_request_model():
    """Test EventRequest model validation."""
    event = EventRequest(
        action="assigned",
        mac="00:11:22:33:44:55",
        ip="192.168.1.100",
        host="test-device"
    )
    assert event.action == "assigned"
    assert event.mac == "00:11:22:33:44:55"
    assert event.ip == "192.168.1.100"
    assert event.host == "test-device"

def test_device_update_request_model():
    """Test DeviceUpdateRequest model validation."""
    # Test with all fields
    update = DeviceUpdateRequest(name="Test Device", notify=True)
    assert update.name == "Test Device"
    assert update.notify is True
    
    # Test with no fields (all optional)
    update = DeviceUpdateRequest()
    assert update.name is None
    assert update.notify is None

def test_device_update_request_from_dict():
    """Test DeviceUpdateRequest model from dictionary."""
    data = {"name": "My Device", "notify": False}
    update = DeviceUpdateRequest(**data)
    assert update.name == "My Device"
    assert update.notify is False
