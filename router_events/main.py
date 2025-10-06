"""Main FastAPI application for RouterOS event processing."""

import json
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Set
import uvicorn
import httpx
from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse, FileResponse
from .database import db
from .notifications import notifier
from .schemas import DeviceUpdateRequest, UpdateResponse

class RateLimiter:
    """Rate limiter for API requests."""
    def __init__(self):
        self.last_request_time = 0.0

    def should_wait(self, min_interval: float = 0.5) -> float:
        """Check if we should wait and return wait time."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < min_interval:
            return min_interval - elapsed
        return 0.0

    def mark_request(self):
        """Mark that a request was made."""
        self.last_request_time = time.time()

rate_limiter = RateLimiter()

# Track pending manufacturer lookups
pending_lookups: Set[str] = set()

async def lookup_manufacturer_background(mac: str):
    """Background task to lookup manufacturer with retry logic."""
    if mac in pending_lookups:
        return

    # Check if lookup is needed
    if not await db.needs_manufacturer_lookup(mac):
        return

    pending_lookups.add(mac)

    try:
        # Rate limiting: wait at least 0.5 seconds between requests
        wait_time = rate_limiter.should_wait()
        if wait_time > 0:
            await asyncio.sleep(wait_time)

        async with httpx.AsyncClient() as client:
            try:
                rate_limiter.mark_request()
                response = await client.get(f"https://api.macvendors.com/{mac}", timeout=5.0)

                if response.status_code == 200:
                    manufacturer = response.text.strip()
                    if manufacturer and "Not Found" not in manufacturer:
                        await db.set_manufacturer(mac, manufacturer, 'found')
                        print(f"Found manufacturer for {mac}: {manufacturer}")
                        return
                    await db.set_manufacturer(mac, 'Unknown', 'unknown')
                    print(f"No manufacturer found for {mac}")
                    return
                if response.status_code == 429:  # Rate limited
                    await db.set_manufacturer(mac, None, 'error')
                    print(f"Rate limited for {mac}, will retry later")
                    return
                await db.set_manufacturer(mac, None, 'error')
                print(f"API error for {mac}: status {response.status_code}")
                return

            except (httpx.RequestError, httpx.TimeoutException) as e:
                await db.set_manufacturer(mac, None, 'error')
                print(f"Network error looking up manufacturer for {mac}: {e}")

    finally:
        pending_lookups.discard(mac)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await db.connect()
    yield
    # Shutdown (if needed)

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
        content_type = request.headers.get("content-type", "")

        if content_type.startswith("application/json"):
            data = await request.json()
            host = (data.get('host') or '').strip()
            mac = data.get('mac', '')
            ip = data.get('ip', '')
            action = data.get('action', '')

            if action == 'assigned' and mac:
                device = await db.get_device(mac)

                if not device:
                    # Unknown device
                    await db.add_device(mac, host or None)
                    await notifier.notify_unknown_device(mac, ip, host)
                    print(f"Unknown device: {mac} ({host or 'no hostname'}) -> {ip}")
                else:
                    # Update last seen
                    await db.add_device(mac, host or device.get('name'))

                    if device.get('notify'):
                        device_name = device.get('name') or host or 'Unknown'
                        await notifier.notify_tracked_device(device_name, mac, ip)

                    device_display = device.get('name') or host or 'no name'
                    print(f"Known device: {mac} ({device_display}) -> {ip}")
        else:
            body = await request.body()
            print(f"Non-JSON event: {body.decode('utf-8')[:100]}")

        return Response(status_code=204)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        print(f"Error processing request: {exc}")
        return Response(status_code=204)

@app.get("/api/devices")
async def get_devices():
    """Get all devices."""
    devices = await db.get_devices()
    return {"devices": [
        {
            "mac": device.mac,
            "name": device.name,
            "notify": device.notify,
            "first_seen": device.first_seen,
            "last_seen": device.last_seen
        }
        for device in devices
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
    """Update device name or notification settings."""
    device = await db.get_device(mac)
    if not device:
        await db.add_device(mac, update.name)

    if update.name is not None:
        await db.set_device_name(mac, update.name)
    if update.notify is not None:
        await db.set_device_notify(mac, update.notify)

    return UpdateResponse(status="updated")

@app.get("/api/manufacturer/{mac}")
async def get_manufacturer(mac: str, background_tasks: BackgroundTasks):
    """Get manufacturer for MAC address."""
    # Check database first
    manufacturer = await db.get_manufacturer(mac)
    if manufacturer:
        return {"manufacturer": manufacturer}

    # If needs lookup and not already pending, start background lookup
    if await db.needs_manufacturer_lookup(mac) and mac not in pending_lookups:
        background_tasks.add_task(lookup_manufacturer_background, mac)

    # Return loading status for now
    return {"manufacturer": "Loading..."}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=13959)
