"""Main FastAPI application for RouterOS event processing."""

import json
import uvicorn
from fastapi import FastAPI, Request, Response

app = FastAPI(
    title="RouterOS Event Receiver",
    description="Receives and processes events from RouterOS devices",
    version="0.1.0"
)

@app.post("/api/events")
async def receive_event(request: Request):
    """Receive and process RouterOS events."""
    try:
        content_type = request.headers.get("content-type", "")

        if content_type.startswith("application/json"):
            data = await request.json()
            host = data.get('host', '').strip()
            mac = data.get('mac', '')
            ip = data.get('ip', '')
            interface = data.get('interface', '')
            action = data.get('action', '')

            if host:
                print(f"DHCP {action}: {mac} ({host}) -> {ip} on {interface}")
            else:
                print(f"DHCP {action}: {mac} -> {ip} on {interface}")
        else:
            body = await request.body()
            print(f"Non-JSON event: {body.decode('utf-8')[:100]}")

        return Response(status_code=204)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        print(f"Error processing request: {exc}")
        return Response(status_code=204)  # Still return success to RouterOS

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    # Run the server on all interfaces (0.0.0.0) port 13959
    uvicorn.run(app, host="0.0.0.0", port=13959)
