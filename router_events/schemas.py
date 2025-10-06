"""API request/response models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


class EventRequest(BaseModel):
    """RouterOS event request."""
    action: str
    mac: str = Field(min_length=17, max_length=17)
    ip: str
    host: Optional[str] = None

    @field_validator('mac')
    @classmethod
    def validate_mac(cls, v):
        """Validate MAC address format."""
        if len(v) != 17 or (v.count(':') != 5 and v.count('-') != 5):
            raise ValueError('Invalid MAC address format')
        return v.lower()


class DeviceResponse(BaseModel):
    """Device response."""
    model_config = ConfigDict(from_attributes=True)

    mac: str
    name: Optional[str] = None
    notify: bool = False
    first_seen: datetime
    last_seen: datetime


class DevicesResponse(BaseModel):
    """Devices list response."""
    devices: List[DeviceResponse]


class DeviceUpdateRequest(BaseModel):
    """Device update request."""
    name: Optional[str] = Field(None, max_length=255)
    notify: Optional[bool] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Clean empty names."""
        return None if v is not None and not v.strip() else v


class UpdateResponse(BaseModel):
    """Update response."""
    status: str


class ManufacturerResponse(BaseModel):
    """Manufacturer response."""
    manufacturer: str


class HealthResponse(BaseModel):
    """Health response."""
    status: str
