"""Database models for device tracking."""

from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ManufacturerStatus(str, Enum):
    """Manufacturer lookup status."""
    PENDING = "pending"
    FOUND = "found"
    UNKNOWN = "unknown"
    ERROR = "error"

    def is_final(self) -> bool:
        """Check if status is final."""
        return self in (self.FOUND, self.UNKNOWN)


class Device(Base):
    """Device tracking model."""
    __tablename__ = "devices"

    mac = Column(String(17), primary_key=True)
    name = Column(String(255), nullable=True)
    notify = Column(Boolean, default=False)
    manufacturer = Column(String(255), nullable=True)
    manufacturer_status = Column(
        SQLEnum(ManufacturerStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ManufacturerStatus.PENDING
    )
    manufacturer_last_attempt = Column(DateTime, nullable=True)
    first_seen = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    last_seen = Column(
        DateTime,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')
    )

    def __repr__(self):
        return f"<Device(mac='{self.mac}', name='{self.name}')>"

    @property
    def display_name(self) -> str:
        """Get display name."""
        return self.name or f"Device {self.mac}"
