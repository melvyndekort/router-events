"""Tests for Pydantic models."""

from router_events.main import DeviceUpdate

def test_device_update_model():
    """Test DeviceUpdate model validation."""
    # Test with all fields
    update = DeviceUpdate(name="Test Device", notify=True)
    assert update.name == "Test Device"
    assert update.notify is True
    
    # Test with no fields (all optional)
    update = DeviceUpdate()
    assert update.name is None
    assert update.notify is None

def test_device_update_model_from_dict():
    """Test DeviceUpdate model from dictionary."""
    data = {"name": "My Device", "notify": False}
    update = DeviceUpdate(**data)
    assert update.name == "My Device"
    assert update.notify is False
