"""Notification handling via ntfy."""

import os
from typing import Optional
import httpx

class NotificationService:
    """Service for sending notifications via ntfy."""

    def __init__(self):
        self.ntfy_url = os.getenv('NTFY_URL', 'https://ntfy.sh')
        self.topic = os.getenv('NTFY_TOPIC', 'router-events')
        self.token = os.getenv('NTFY_TOKEN')
        self.enabled = bool(os.getenv('NTFY_ENABLED', 'true').lower() == 'true')

    async def send_notification(self, title: str, message: str, priority: str = "default"):
        """Send notification via ntfy."""
        if not self.enabled:
            return

        try:
            headers = {
                "Title": title,
                "Priority": priority
            }

            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.ntfy_url}/{self.topic}",
                    data=message,
                    headers=headers
                )
        except httpx.RequestError as e:
            print(f"Failed to send notification: {e}")

    async def notify_unknown_device(self, mac: str, ip: str, hostname: Optional[str] = None):
        """Notify about unknown device connection."""
        device_name = hostname or "Unknown device"
        title = "Unknown Device Connected"
        message = f"{device_name} ({mac}) connected with IP {ip}"
        await self.send_notification(title, message, "high")

    async def notify_tracked_device(self, name: str, mac: str, ip: str):
        """Notify about tracked device connection."""
        title = "Tracked Device Connected"
        message = f"{name} ({mac}) connected with IP {ip}"
        await self.send_notification(title, message, "default")

notifier = NotificationService()
