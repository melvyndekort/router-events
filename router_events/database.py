"""Database operations for device tracking using SQLAlchemy."""

import os
import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, insert
from alembic.config import Config
from alembic import command
from .models import Device, ManufacturerStatus

class Database:
    """Database connection and operations for device tracking."""

    def __init__(self):
        self.engine = None
        self.async_session = None

    async def connect(self):
        """Connect to the database."""
        db_url = (f"mysql+aiomysql://{os.getenv('DB_USER', 'router_events')}:"
                 f"{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST', 'localhost')}:"
                 f"{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'router_events')}")

        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        # Run migrations
        await self._run_migrations()

    async def _run_migrations(self):
        """Run Alembic migrations."""
        try:
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")
        except (FileNotFoundError, ImportError) as e:
            print(f"Migration warning: {e}")

    async def add_device(self, mac: str, host: Optional[str] = None):
        """Add or update a device."""
        async with self.async_session() as session:
            # Check if device exists
            result = await session.execute(select(Device).where(Device.mac == mac))
            device = result.scalar_one_or_none()

            if device:
                # Update last_seen
                device.last_seen = datetime.datetime.now()
                if host:
                    device.name = host
            else:
                # Create new device
                device = Device(
                    mac=mac,
                    name=host,
                    notify=False,
                    first_seen=datetime.datetime.now(),
                    last_seen=datetime.datetime.now()
                )
                session.add(device)

            await session.commit()
            return device

    async def get_devices(self) -> List[Device]:
        """Get all devices."""
        async with self.async_session() as session:
            result = await session.execute(select(Device))
            return result.scalars().all()

    async def get_device(self, mac: str) -> Optional[Device]:
        """Get a specific device."""
        async with self.async_session() as session:
            result = await session.execute(select(Device).where(Device.mac == mac))
            return result.scalar_one_or_none()

    async def set_device_name(self, mac: str, name: Optional[str]):
        """Set device name."""
        async with self.async_session() as session:
            await session.execute(
                update(Device).where(Device.mac == mac).values(name=name)
            )
            await session.commit()

    async def set_device_notify(self, mac: str, notify: bool):
        """Set device notification flag."""
        async with self.async_session() as session:
            await session.execute(
                update(Device).where(Device.mac == mac).values(notify=notify)
            )
            await session.commit()

    async def get_manufacturer(self, mac: str) -> Optional[str]:
        """Get manufacturer for a device."""
        async with self.async_session() as session:
            result = await session.execute(
                select(Device.manufacturer, Device.manufacturer_status)
                .where(Device.mac == mac)
            )
            row = result.first()
            if not row:
                return None

            manufacturer, status = row
            if status == ManufacturerStatus.FOUND:
                return manufacturer
            if status == ManufacturerStatus.UNKNOWN:
                return 'Unknown'

            return None

    async def needs_manufacturer_lookup(self, mac: str) -> bool:
        """Check if MAC needs manufacturer lookup (new or retry needed)."""
        async with self.async_session() as session:
            result = await session.execute(
                select(Device.manufacturer_status, Device.manufacturer_last_attempt)
                .where(Device.mac == mac)
            )
            row = result.first()

            if not row:
                return True  # New device

            status, last_attempt = row

            # Retry if error status and more than 5 minutes since last attempt
            if status == ManufacturerStatus.ERROR and last_attempt:
                now = datetime.datetime.now()
                if (now - last_attempt).total_seconds() > 300:  # 5 minutes
                    return True

            # Needs lookup if pending or error
            return status in (ManufacturerStatus.PENDING, ManufacturerStatus.ERROR)

    async def set_manufacturer(self, mac: str, manufacturer: Optional[str], status: str = 'found'):
        """Set manufacturer for a device."""
        status_enum = ManufacturerStatus(status)
        async with self.async_session() as session:
            # Upsert device with manufacturer info
            stmt = insert(Device).values(
                mac=mac,
                manufacturer=manufacturer,
                manufacturer_status=status_enum,
                manufacturer_last_attempt=datetime.datetime.now()
            )
            stmt = stmt.on_duplicate_key_update(
                manufacturer=stmt.inserted.manufacturer,
                manufacturer_status=stmt.inserted.manufacturer_status,
                manufacturer_last_attempt=stmt.inserted.manufacturer_last_attempt
            )
            await session.execute(stmt)
            await session.commit()

    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()

# Global database instance
db = Database()
