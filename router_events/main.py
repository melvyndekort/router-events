"""Main FastAPI application for RouterOS event processing."""

from fastapi import FastAPI, Request, HTTPException, Response
import uvicorn
import json

app = FastAPI(
    title="RouterOS Event Receiver",
    description="Receives and processes events from RouterOS devices",
    version="0.1.0"
)

@app.post("/api/events")
async def receive_event(request: Request):
    """Receive and process RouterOS events."""
    try:
        data = await request.json()
        print(json.dumps(data, indent=2))
        return Response(status_code=204)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid JSON")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    # Run the server on all interfaces (0.0.0.0) port 13959
    uvicorn.run(app, host="0.0.0.0", port=13959)
