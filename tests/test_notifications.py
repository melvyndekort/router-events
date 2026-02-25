"""Tests for notification service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from router_events.notifications import NotificationService


class TestNotificationService:
    """Test notification service."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        with patch.dict('os.environ', {}, clear=True):
            service = NotificationService()
            assert service.url == 'http://apprise:8000'
            assert service.tag == 'homelab'
            assert service.key == 'apprise'
            assert service.enabled is True

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        env_vars = {
            'APPRISE_URL': 'https://apprise.example.com',
            'APPRISE_TAG': 'custom-tag',
            'APPRISE_KEY': 'custom-key',
            'APPRISE_ENABLED': 'false'
        }
        with patch.dict('os.environ', env_vars):
            service = NotificationService()
            assert service.url == 'https://apprise.example.com'
            assert service.tag == 'custom-tag'
            assert service.key == 'custom-key'
            assert service.enabled is False

    @pytest.mark.asyncio
    async def test_send_disabled(self):
        """Test sending notification when disabled."""
        service = NotificationService()
        service.enabled = False
        
        with patch('httpx.AsyncClient') as mock_client:
            await service.send("Test", "Message")
            mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_success(self):
        """Test successful notification."""
        service = NotificationService()
        service.enabled = True
        
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            await service.send("Test Title", "Test Message", "high")
            
            mock_client.post.assert_called_once_with(
                f"{service.url}/notify/{service.key}",
                json={"title": "Test Title", "body": "Test Message", "tag": service.tag}
            )

    @pytest.mark.asyncio
    async def test_send_request_error(self):
        """Test notification with request error."""
        service = NotificationService()
        service.enabled = True
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.RequestError("Network error"))
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Should not raise exception
            await service.send("Test", "Message")

    @pytest.mark.asyncio
    async def test_send_http_error(self):
        """Test notification with HTTP error."""
        service = NotificationService()
        service.enabled = True
        
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
            "Bad request", request=None, response=None
        ))
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Should not raise exception
            await service.send("Test", "Message")

    @pytest.mark.asyncio
    async def test_notify_unknown_device_with_hostname(self):
        """Test unknown device notification with hostname."""
        service = NotificationService()
        
        with patch.object(service, 'send', new_callable=AsyncMock) as mock_send:
            await service.notify_unknown_device("00:11:22:33:44:55", "192.168.1.100", "test-device")
            
            mock_send.assert_called_once_with(
                "Unknown Device Connected",
                "test-device (00:11:22:33:44:55) connected with IP 192.168.1.100",
                "high"
            )

    @pytest.mark.asyncio
    async def test_notify_unknown_device_without_hostname(self):
        """Test unknown device notification without hostname."""
        service = NotificationService()
        
        with patch.object(service, 'send', new_callable=AsyncMock) as mock_send:
            await service.notify_unknown_device("00:11:22:33:44:55", "192.168.1.100")
            
            mock_send.assert_called_once_with(
                "Unknown Device Connected",
                "Unknown device (00:11:22:33:44:55) connected with IP 192.168.1.100",
                "high"
            )

    @pytest.mark.asyncio
    async def test_notify_tracked_device(self):
        """Test tracked device notification."""
        service = NotificationService()
        
        with patch.object(service, 'send', new_callable=AsyncMock) as mock_send:
            await service.notify_tracked_device("My Device", "00:11:22:33:44:55", "192.168.1.100")
            
            mock_send.assert_called_once_with(
                "Tracked Device Connected",
                "My Device (00:11:22:33:44:55) connected with IP 192.168.1.100"
            )

    @pytest.mark.asyncio
    async def test_notify_unknown_device_released(self):
        """Test unknown device disconnection notification."""
        service = NotificationService()

        with patch.object(service, 'send', new_callable=AsyncMock) as mock_send:
            await service.notify_unknown_device("00:11:22:33:44:55", "192.168.1.100", "test-device", "released")

            mock_send.assert_called_once_with(
                "Unknown Device Disconnected",
                "test-device (00:11:22:33:44:55) disconnected",
                "high"
            )

    @pytest.mark.asyncio
    async def test_notify_tracked_device_released(self):
        """Test tracked device disconnection notification."""
        service = NotificationService()

        with patch.object(service, 'send', new_callable=AsyncMock) as mock_send:
            await service.notify_tracked_device("My Device", "00:11:22:33:44:55", "192.168.1.100", "released")

            mock_send.assert_called_once_with(
                "Tracked Device Disconnected",
                "My Device (00:11:22:33:44:55) disconnected"
            )

    @pytest.mark.asyncio
    async def test_notify_unknown_device_custom_action(self):
        """Test unknown device with custom action."""
        service = NotificationService()

        with patch.object(service, 'send', new_callable=AsyncMock) as mock_send:
            await service.notify_unknown_device("00:11:22:33:44:55", "192.168.1.100", "test-device", "renewed")

            mock_send.assert_called_once_with(
                "Unknown Device (Renewed)",
                "test-device (00:11:22:33:44:55) - renewed with IP 192.168.1.100",
                "high"
            )

    @pytest.mark.asyncio
    async def test_notify_tracked_device_custom_action(self):
        """Test tracked device with custom action."""
        service = NotificationService()

        with patch.object(service, 'send', new_callable=AsyncMock) as mock_send:
            await service.notify_tracked_device("My Device", "00:11:22:33:44:55", "192.168.1.100", "renewed")

            mock_send.assert_called_once_with(
                "Tracked Device (Renewed)",
                "My Device (00:11:22:33:44:55) - renewed with IP 192.168.1.100"
            )
