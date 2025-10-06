"""Main FastAPI application for RouterOS event processing."""

import json
from contextlib import asynccontextmanager
from typing import Optional
import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel
from .database import db
from .notifications import notifier

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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=13959)
