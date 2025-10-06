"""Notification service via ntfy."""

import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class NotificationService:
    """Simple notification service using ntfy."""

    def __init__(self):
        self.url = os.getenv('NTFY_URL', 'https://ntfy.sh')
        self.topic = os.getenv('NTFY_TOPIC', 'router-events')
        self.token = os.getenv('NTFY_TOKEN')
        self.enabled = os.getenv('NTFY_ENABLED', 'true').lower() == 'true'

    async def send(self, title: str, message: str, priority: str = "default"):
        """Send notification."""
        if not self.enabled:
            return

        headers = {"Title": title, "Priority": priority}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.url}/{self.topic}",
                    data=message,
                    headers=headers
                )
                response.raise_for_status()
                logger.info("Notification sent: %s", title)
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error("Notification failed '%s': %s", title, e)

    async def notify_unknown_device(self, mac: str, ip: str, hostname: Optional[str] = None):
        """Notify about unknown device."""
        device_name = hostname or "Unknown device"
        await self.send(
            "Unknown Device Connected",
            f"{device_name} ({mac}) connected with IP {ip}",
            "high"
        )

    async def notify_tracked_device(self, name: str, mac: str, ip: str):
        """Notify about tracked device."""
        await self.send(
            "Tracked Device Connected",
            f"{name} ({mac}) connected with IP {ip}"
        )


notifier = NotificationService()
