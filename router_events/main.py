"""Main FastAPI application for RouterOS event processing."""

import json
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional, Dict, Set
import uvicorn
import httpx
from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel
from .database import db
from .notifications import notifier

class ManufacturerCache:
    """Cache for manufacturer lookups with rate limiting."""

    def __init__(self):
        self.cache: Dict[str, str] = {}
        self.last_request_time = 0.0
        self.pending: Set[str] = set()

    def get(self, mac: str) -> Optional[str]:
        """Get cached manufacturer."""
        return self.cache.get(mac)

    def set(self, mac: str, manufacturer: str) -> None:
        """Set cached manufacturer."""
        self.cache[mac] = manufacturer
        self.pending.discard(mac)

    def is_pending(self, mac: str) -> bool:
        """Check if MAC is being processed."""
        return mac in self.pending

    def add_pending(self, mac: str) -> None:
        """Mark MAC as being processed."""
        self.pending.add(mac)

manufacturer_cache = ManufacturerCache()

async def lookup_manufacturer_background(mac: str):
    """Background task to lookup manufacturer."""
    if manufacturer_cache.get(mac) or manufacturer_cache.is_pending(mac):
        return

    manufacturer_cache.add_pending(mac)

    # Rate limiting: wait at least 0.5 seconds between requests
    current_time = time.time()
    if current_time - manufacturer_cache.last_request_time < 0.5:
        await asyncio.sleep(0.5 - (current_time - manufacturer_cache.last_request_time))

    async with httpx.AsyncClient() as client:
        try:
            manufacturer_cache.last_request_time = time.time()
            response = await client.get(f"https://api.macvendors.com/{mac}", timeout=5.0)
            if response.status_code == 200:
                manufacturer = response.text.strip()
                if manufacturer and "Not Found" not in manufacturer:
                    manufacturer_cache.set(mac, manufacturer)
                    print(f"Found manufacturer for {mac}: {manufacturer}")
                    return
            print(f"No manufacturer found for {mac}: status {response.status_code}")
        except (httpx.RequestError, httpx.TimeoutException) as e:
            print(f"Error looking up manufacturer for {mac}: {e}")

    # Cache unknown results too
    manufacturer_cache.set(mac, "Unknown")

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

class DeviceUpdate(BaseModel):
    """Device update model for API requests."""
    name: Optional[str] = None
    notify: Optional[bool] = None

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
    devices = await db.get_all_devices()
    return {"devices": devices}

@app.get("/api/devices/{mac}")
async def get_device(mac: str):
    """Get device by MAC address."""
    device = await db.get_device(mac)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@app.put("/api/devices/{mac}")
async def update_device(mac: str, update: DeviceUpdate):
    """Update device name or notification settings."""
    device = await db.get_device(mac)
    if not device:
        await db.add_device(mac, update.name, update.notify or False)
    else:
        if update.name is not None:
            await db.update_device_name(mac, update.name)
        if update.notify is not None:
            await db.set_device_notify(mac, update.notify)

    return {"status": "updated"}

@app.get("/api/manufacturer/{mac}")
async def get_manufacturer(mac: str, background_tasks: BackgroundTasks):
    """Get manufacturer for MAC address."""
    # Check cache first
    cached = manufacturer_cache.get(mac)
    if cached:
        return {"manufacturer": cached}

    # If not cached and not pending, start background lookup
    if not manufacturer_cache.is_pending(mac):
        background_tasks.add_task(lookup_manufacturer_background, mac)

    # Return loading status for now
    return {"manufacturer": "Loading..."}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=13959)
