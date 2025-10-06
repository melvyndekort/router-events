"""Database operations for device tracking."""

import os
import datetime
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, text

from .models import Device, ManufacturerStatus, Base

logger = logging.getLogger(__name__)


class Database:
    """Async database operations for device tracking."""

    def __init__(self):
        self.engine = None
        self.session_factory = None

    async def connect(self):
        """Connect to database and ensure schema exists."""
        db_url = (
            f"mysql+aiomysql://{os.getenv('DB_USER', 'router_events')}:"
            f"{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST', 'localhost')}:"
            f"{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'router_events')}"
        )

        self.engine = create_async_engine(db_url, echo=False)
        self.session_factory = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        # Create tables if they don't exist
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Test connection
        async with self.session_factory() as session:
            await session.execute(text("SELECT 1"))

        logger.info("Database connected")

    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()

    async def add_device(self, mac: str, name: Optional[str] = None) -> Device:
        """Add or update device."""
        async with self.session_factory() as session:
            device = await session.get(Device, mac)

            if device:
                device.last_seen = datetime.datetime.now()
                if name and not device.name:
                    device.name = name
            else:
                device = Device(
                    mac=mac,
                    name=name,
                    notify=False,
                    first_seen=datetime.datetime.now(),
                    last_seen=datetime.datetime.now()
                )
                session.add(device)

            await session.commit()
            return device

    async def get_devices(self) -> List[Device]:
        """Get all devices."""
        async with self.session_factory() as session:
            result = await session.execute(select(Device))
            return list(result.scalars().all())

    async def get_device(self, mac: str) -> Optional[Device]:
        """Get device by MAC."""
        async with self.session_factory() as session:
            return await session.get(Device, mac)

    async def set_device_name(self, mac: str, name: Optional[str]):
        """Update device name."""
        async with self.session_factory() as session:
            await session.execute(update(Device).where(Device.mac == mac).values(name=name))
            await session.commit()

    async def set_device_notify(self, mac: str, notify: bool):
        """Update device notification setting."""
        async with self.session_factory() as session:
            await session.execute(update(Device).where(Device.mac == mac).values(notify=notify))
            await session.commit()

    async def delete_device(self, mac: str):
        """Delete device by MAC address."""
        async with self.session_factory() as session:
            device = await session.get(Device, mac)
            if device:
                await session.delete(device)
                await session.commit()

    async def get_manufacturer(self, mac: str) -> Optional[str]:
        """Get cached manufacturer."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Device.manufacturer, Device.manufacturer_status).where(Device.mac == mac)
            )
            row = result.first()

            if not row:
                return None

            manufacturer, status = row
            if status == ManufacturerStatus.FOUND and manufacturer:
                return manufacturer
            if status in (ManufacturerStatus.UNKNOWN, ManufacturerStatus.ERROR):
                return 'Unknown'
            return None  # Pending status

    async def needs_manufacturer_lookup(self, mac: str) -> bool:
        """Check if manufacturer lookup is needed."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Device.manufacturer_status, Device.manufacturer_last_attempt,
                       Device.manufacturer)
                .where(Device.mac == mac)
            )
            row = result.first()

            if not row:
                return True

            status, last_attempt, manufacturer = row

            # If we have a successful lookup with actual data, no need to retry
            if status == ManufacturerStatus.FOUND and manufacturer:
                return False

            # If marked as unknown, no need to retry
            if status == ManufacturerStatus.UNKNOWN:
                return False

            # Retry errors after 5 minutes
            if status == ManufacturerStatus.ERROR and last_attempt:
                return (datetime.datetime.now() - last_attempt).total_seconds() > 300

            # Need lookup for pending, error, or found-but-empty
            return True

    async def set_manufacturer(self, mac: str, manufacturer: Optional[str], status: str = 'found'):
        """Set manufacturer info."""
        try:
            status_enum = ManufacturerStatus(status)
        except ValueError:
            logger.error("Invalid status: %s", status)
            return

        async with self.session_factory() as session:
            # Get or create device
            device = await session.get(Device, mac)
            if not device:
                device = Device(mac=mac)
                session.add(device)

            # Update manufacturer info
            device.manufacturer = manufacturer
            device.manufacturer_status = status_enum
            device.manufacturer_last_attempt = datetime.datetime.now()

            await session.commit()

    async def retry_failed_manufacturer_lookups(self) -> int:
        """Reset all failed and unknown manufacturer lookups for retry."""
        async with self.session_factory() as session:
            result = await session.execute(
                update(Device)
                .where(Device.manufacturer_status.in_([
                    ManufacturerStatus.ERROR, ManufacturerStatus.UNKNOWN
                ]))
                .values(
                    manufacturer_status=ManufacturerStatus.PENDING,
                    manufacturer_last_attempt=None
                )
            )
            await session.commit()
            return result.rowcount

    async def reset_manufacturer_lookup(self, mac: str):
        """Reset manufacturer lookup for specific device."""
        async with self.session_factory() as session:
            await session.execute(
                update(Device)
                .where(Device.mac == mac)
                .values(
                    manufacturer_status=ManufacturerStatus.PENDING,
                    manufacturer_last_attempt=None
                )
            )
            await session.commit()


db = Database()
