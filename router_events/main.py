"""Main FastAPI application for RouterOS event processing."""

import asyncio
import time
import logging
from contextlib import asynccontextmanager
from typing import Set

import uvicorn
import httpx
from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse, FileResponse

from .database import db
from .notifications import notifier
from .schemas import DeviceUpdateRequest, UpdateResponse

logger = logging.getLogger(__name__)


class RateLimiter:  # pylint: disable=too-few-public-methods
    """Simple rate limiter for API requests."""

    def __init__(self, interval: float = 0.5):
        self.interval = interval
        self.last_request = 0.0

    async def wait_if_needed(self):
        """Wait if rate limit requires it."""
        elapsed = time.time() - self.last_request
        if elapsed < self.interval:
            await asyncio.sleep(self.interval - elapsed)
        self.last_request = time.time()


# Global state
rate_limiter = RateLimiter()
pending_lookups: Set[str] = set()


async def lookup_manufacturer(mac: str):
    """Background manufacturer lookup with rate limiting and multiple APIs."""
    if mac in pending_lookups:
        return

    if not await db.needs_manufacturer_lookup(mac):
        return

    pending_lookups.add(mac)
    try:
        # Set status to pending to prevent duplicate lookups
        await db.set_manufacturer(mac, None, 'pending')
        await rate_limiter.wait_if_needed()

        # Try multiple APIs in order
        apis = [
            f"https://api.macvendors.com/{mac}",
            f"https://maclookup.app/api/v2/macs/{mac}",
            f"https://api.maclookup.app/v2/macs/{mac}/company/name"
        ]

        async with httpx.AsyncClient(timeout=5.0) as client:
            for api_url in apis:
                try:
                    response = await client.get(api_url)

                    if response.status_code == 200:
                        manufacturer = await _parse_manufacturer_response(response, api_url)

                        if (manufacturer and "Not Found" not in manufacturer
                            and "error" not in manufacturer.lower()):
                            await db.set_manufacturer(mac, manufacturer, 'found')
                            logger.info("Found manufacturer for %s: %s (via %s)",
                                      mac, manufacturer, api_url)
                            return

                except (httpx.RequestError, httpx.TimeoutException):
                    continue  # Try next API

            # All APIs failed or returned no data
            await db.set_manufacturer(mac, 'Unknown', 'unknown')

    except (httpx.RequestError, httpx.TimeoutException) as e:
        await db.set_manufacturer(mac, None, 'error')
        logger.error("Manufacturer lookup failed for %s: %s", mac, e)
    finally:
        pending_lookups.discard(mac)


async def _parse_manufacturer_response(response, api_url: str) -> str:
    """Parse manufacturer response based on API type."""
    if "maclookup.app" in api_url:
        # Handle JSON response from maclookup.app
        try:
            data = response.json()
            if isinstance(data, dict):
                return data.get('company') or data.get('companyName') or ""
            return response.text.strip()
        except (ValueError, TypeError):
            return response.text.strip()
    else:
        # Handle plain text response
        return response.text.strip()


def get_device_attr(device, attr: str, default=None):
    """Get attribute from device (handles both dict and object)."""
    if hasattr(device, attr):
        return getattr(device, attr, default)
    return device.get(attr, default) if hasattr(device, 'get') else default


async def process_device_event(mac: str, ip: str, host: str):
    """Process device assignment event."""
    device = await db.get_device(mac)

    if not device:
        await db.add_device(mac, host or None)
        await notifier.notify_unknown_device(mac, ip, host)
        logger.info("New device: %s (%s) -> %s", mac, host or 'unknown', ip)
    else:
        device_name = get_device_attr(device, 'name')
        await db.add_device(mac, host or device_name)

        if get_device_attr(device, 'notify', False):
            name = device_name or host or 'Unknown'
            await notifier.notify_tracked_device(name, mac, ip)
            logger.info("Tracked device: %s -> %s", name, ip)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifecycle management."""
    logger.info("Starting RouterOS Event Receiver")
    await db.connect()
    yield
    await db.close()
    logger.info("Application stopped")


app = FastAPI(
    title="RouterOS Event Receiver",
    description="Receives and processes events from RouterOS devices",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Redirect to devices page."""
    return RedirectResponse(url="/devices.html")


@app.get("/devices.html")
async def devices_page():
    """Serve devices HTML page."""
    return FileResponse("static/devices.html")


@app.post("/api/events")
async def receive_event(request: Request):
    """Receive and process RouterOS events."""
    try:
        if not request.headers.get("content-type", "").startswith("application/json"):
            return Response(status_code=204)

        data = await request.json()
        if data.get('action') == 'assigned' and data.get('mac'):
            await process_device_event(
                data['mac'],
                data.get('ip', ''),
                (data.get('host') or '').strip()
            )

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Event processing error: %s", e)

    return Response(status_code=204)


@app.get("/api/devices")
async def get_devices():
    """Get all devices."""
    devices = await db.get_devices()
    return {"devices": [
        {
            "mac": d.mac,
            "name": d.name,
            "notify": d.notify,
            "first_seen": d.first_seen,
            "last_seen": d.last_seen
        }
        for d in devices
    ]}


@app.get("/api/devices/{mac}")
async def get_device(mac: str):
    """Get device by MAC address."""
    device = await db.get_device(mac)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return {
        "mac": device.mac,
        "name": device.name,
        "notify": device.notify,
        "first_seen": device.first_seen,
        "last_seen": device.last_seen
    }


@app.put("/api/devices/{mac}")
async def update_device(mac: str, update: DeviceUpdateRequest):
    """Update device settings."""
    if not await db.get_device(mac):
        await db.add_device(mac, update.name)

    if update.name is not None:
        await db.set_device_name(mac, update.name)
    if update.notify is not None:
        await db.set_device_notify(mac, update.notify)

    return UpdateResponse(status="updated")


@app.get("/api/manufacturer/{mac}")
async def get_manufacturer(mac: str, background_tasks: BackgroundTasks):
    """Get manufacturer for MAC address."""
    manufacturer = await db.get_manufacturer(mac)
    if manufacturer:
        return {"manufacturer": manufacturer}

    if await db.needs_manufacturer_lookup(mac) and mac not in pending_lookups:
        background_tasks.add_task(lookup_manufacturer, mac)

    return {"manufacturer": "Loading..."}


@app.post("/api/manufacturer/retry")
async def retry_failed_lookups():
    """Force retry of all failed manufacturer lookups."""
    count = await db.retry_failed_manufacturer_lookups()
    return {"message": f"Reset {count} failed lookups for retry"}


@app.post("/api/manufacturer/{mac}/retry")
async def retry_manufacturer_lookup(mac: str, background_tasks: BackgroundTasks):
    """Force retry of manufacturer lookup for specific device."""
    await db.reset_manufacturer_lookup(mac)
    background_tasks.add_task(lookup_manufacturer, mac)
    return {"message": f"Manufacturer lookup reset for {mac}"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=13959)
