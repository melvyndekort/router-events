"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class EventRequest(BaseModel):
    """RouterOS event request model."""
    action: str
    mac: str
    ip: str
    host: Optional[str] = None


class DeviceResponse(BaseModel):
    """Device response model."""
    mac: str
    name: Optional[str] = None
    notify: bool = False
    first_seen: datetime
    last_seen: datetime


class DevicesResponse(BaseModel):
    """Devices list response model."""
    devices: list[DeviceResponse]


class DeviceUpdateRequest(BaseModel):
    """Device update request model."""
    name: Optional[str] = None
    notify: Optional[bool] = None


class UpdateResponse(BaseModel):
    """Update response model."""
    status: str
