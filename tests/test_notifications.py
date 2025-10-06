"""Tests for notification service."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx
from router_events.notifications import NotificationService

@pytest.fixture
def notification_service():
    """Create notification service for testing."""
    return NotificationService()

@pytest.mark.asyncio
async def test_send_notification_enabled(notification_service):
    """Test sending notification when enabled."""
    notification_service.enabled = True
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = Mock()
        mock_response.raise_for_status = Mock(return_value=None)
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        await notification_service.send("Test", "Message", "high")
        
        mock_client.return_value.__aenter__.return_value.post.assert_called_once_with(
            f"{notification_service.url}/{notification_service.topic}",
            data="Message",
            headers={"Title": "Test", "Priority": "high"}
        )
        mock_response.raise_for_status.assert_called_once()

@pytest.mark.asyncio
async def test_send_notification_with_token(notification_service):
    """Test sending notification with token authentication."""
    notification_service.enabled = True
    notification_service.token = "test-token"
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = Mock()
        mock_response.raise_for_status = Mock(return_value=None)
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        await notification_service.send("Test", "Message", "high")
        
        mock_client.return_value.__aenter__.return_value.post.assert_called_once_with(
            f"{notification_service.url}/{notification_service.topic}",
            data="Message",
            headers={"Title": "Test", "Priority": "high", "Authorization": "Bearer test-token"}
        )
        mock_response.raise_for_status.assert_called_once()

@pytest.mark.asyncio
async def test_send_notification_disabled(notification_service):
    """Test sending notification when disabled."""
    notification_service.enabled = False
    
    with patch('httpx.AsyncClient') as mock_client:
        await notification_service.send("Test", "Message")
        
        mock_client.assert_not_called()

@pytest.mark.asyncio
async def test_send_notification_error(notification_service):
    """Test notification error handling."""
    notification_service.enabled = True
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.RequestError("Network error")
        
        # Should not raise exception
        await notification_service.send("Test", "Message")

@pytest.mark.asyncio
async def test_notify_unknown_device(notification_service):
    """Test unknown device notification."""
    notification_service.send = AsyncMock()
    
    await notification_service.notify_unknown_device("00:11:22:33:44:55", "192.168.1.100", "test")
    
    notification_service.send.assert_called_once_with(
        "Unknown Device Connected",
        "test (00:11:22:33:44:55) connected with IP 192.168.1.100",
        "high"
    )

@pytest.mark.asyncio
async def test_notify_unknown_device_no_hostname(notification_service):
    """Test unknown device notification without hostname."""
    notification_service.send = AsyncMock()
    
    await notification_service.notify_unknown_device("00:11:22:33:44:55", "192.168.1.100")
    
    notification_service.send.assert_called_once_with(
        "Unknown Device Connected",
        "Unknown device (00:11:22:33:44:55) connected with IP 192.168.1.100",
        "high"
    )

@pytest.mark.asyncio
async def test_notify_tracked_device(notification_service):
    """Test tracked device notification."""
    notification_service.send = AsyncMock()
    
    await notification_service.notify_tracked_device("My Device", "00:11:22:33:44:55", "192.168.1.100")
    
    notification_service.send.assert_called_once_with(
        "Tracked Device Connected",
        "My Device (00:11:22:33:44:55) connected with IP 192.168.1.100"
    )
