"""Database models for device tracking."""

from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class ManufacturerStatus(str, Enum):
    """Manufacturer lookup status."""
    PENDING = "pending"
    FOUND = "found"
    UNKNOWN = "unknown"
    ERROR = "error"

    def __str__(self):
        return self.value

class Device(Base):
    """Device model."""
    __tablename__ = "devices"

    mac = Column(String(17), primary_key=True)
    name = Column(String(255), nullable=True)
    notify = Column(Boolean, default=False)
    manufacturer = Column(String(255), nullable=True)
    manufacturer_status = Column(SQLEnum(ManufacturerStatus), default=ManufacturerStatus.PENDING)
    manufacturer_last_attempt = Column(DateTime, nullable=True)
    first_seen = Column(DateTime, server_default=func.now())
    last_seen = Column(DateTime, server_default=func.now(), onupdate=func.now())
