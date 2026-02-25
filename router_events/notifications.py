"""Notification service via Apprise API."""

import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class NotificationService:
    """Simple notification service using Apprise API."""

    def __init__(self):
        self.url = os.getenv('APPRISE_URL', 'http://apprise:8000')
        self.tag = os.getenv('APPRISE_TAG', 'homelab')
        self.key = os.getenv('APPRISE_KEY', 'apprise')
        self.enabled = os.getenv('APPRISE_ENABLED', 'true').lower() == 'true'

    async def send(self, title: str, message: str, priority: str = "default"):  # pylint: disable=unused-argument
        """Send notification via Apprise API.
        
        Note: priority parameter kept for API compatibility but not used by Apprise.
        """
        if not self.enabled:
            return

        payload = {
            'title': title,
            'body': message,
            'tag': self.tag
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.url.rstrip('/')}/notify/{self.key}",
                    json=payload
                )
                response.raise_for_status()
                logger.info("Notification sent: %s", title)
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error("Notification failed '%s': %s", title, e)

    async def notify_unknown_device(
        self, mac: str, ip: str, hostname: Optional[str] = None, action: str = "assigned"
    ):
        """Notify about unknown device."""
        device_name = hostname or "Unknown device"
        if action == "assigned":
            await self.send(
                "Unknown Device Connected",
                f"{device_name} ({mac}) connected with IP {ip}",
                "high"
            )
        elif action == "released":
            await self.send(
                "Unknown Device Disconnected",
                f"{device_name} ({mac}) disconnected",
                "high"
            )
        else:
            await self.send(
                f"Unknown Device ({action.title()})",
                f"{device_name} ({mac}) - {action}" + (f" with IP {ip}" if ip else ""),
                "high"
            )

    async def notify_tracked_device(
        self, name: str, mac: str, ip: str, action: str = "assigned"
    ):
        """Notify about tracked device."""
        if action == "assigned":
            await self.send(
                "Tracked Device Connected",
                f"{name} ({mac}) connected with IP {ip}"
            )
        elif action == "released":
            await self.send(
                "Tracked Device Disconnected",
                f"{name} ({mac}) disconnected"
            )
        else:
            await self.send(
                f"Tracked Device ({action.title()})",
                f"{name} ({mac}) - {action}" + (f" with IP {ip}" if ip else "")
            )


notifier = NotificationService()
