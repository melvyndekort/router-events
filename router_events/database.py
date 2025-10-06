"""Database operations for device tracking."""

import os
import datetime
from typing import Optional, Dict, Any
import aiomysql

class Database:
    """Database connection and operations for device tracking."""

    def __init__(self):
        self.pool = None

    async def connect(self):
        """Initialize database connection pool."""
        self.pool = await aiomysql.create_pool(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '3306')),
            user=os.getenv('DB_USER', 'router_events'),
            password=os.getenv('DB_PASSWORD', ''),
            db=os.getenv('DB_NAME', 'router_events'),
            autocommit=True
        )
        await self._create_tables()

    async def _create_tables(self):
        """Create required tables if they don't exist."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS devices (
                        mac VARCHAR(17) PRIMARY KEY,
                        name VARCHAR(255),
                        notify BOOLEAN DEFAULT FALSE,
                        manufacturer VARCHAR(255),
                        manufacturer_status ENUM('pending', 'found', 'unknown', 'error') DEFAULT 'pending',
                        manufacturer_last_attempt TIMESTAMP NULL,
                        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        mac VARCHAR(17),
                        ip VARCHAR(45),
                        host VARCHAR(255),
                        action VARCHAR(50),
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_mac (mac),
                        INDEX idx_timestamp (timestamp)
                    )
                """)

    async def get_device(self, mac: str) -> Optional[Dict[str, Any]]:
        """Get device by MAC address."""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("SELECT * FROM devices WHERE mac = %s", (mac,))
                return await cursor.fetchone()

    async def get_all_devices(self) -> list:
        """Get all devices."""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("SELECT * FROM devices ORDER BY last_seen DESC")
                return await cursor.fetchall()

    async def add_device(self, mac: str, name: str = None, notify: bool = False):
        """Add or update device."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO devices (mac, name, notify)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    name = COALESCE(VALUES(name), name),
                    notify = VALUES(notify),
                    last_seen = CURRENT_TIMESTAMP
                """, (mac, name, notify))

    async def update_device_name(self, mac: str, name: str):
        """Update device name."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE devices SET name = %s WHERE mac = %s",
                    (name, mac)
                )

    async def set_device_notify(self, mac: str, notify: bool):
        """Set device notification flag."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE devices SET notify = %s WHERE mac = %s",
                    (notify, mac)
                )

    async def get_manufacturer(self, mac: str) -> Optional[str]:
        """Get manufacturer for a device."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT manufacturer, manufacturer_status, manufacturer_last_attempt
                    FROM devices WHERE mac = %s
                """, (mac,))
                result = await cursor.fetchone()
                if not result:
                    return None

                # Return manufacturer if found
                if result['manufacturer_status'] == 'found':
                    return result['manufacturer']
                if result['manufacturer_status'] == 'unknown':
                    return 'Unknown'

                return None  # Still pending or needs retry

    async def needs_manufacturer_lookup(self, mac: str) -> bool:
        """Check if MAC needs manufacturer lookup (new or retry needed)."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT manufacturer_status, manufacturer_last_attempt
                    FROM devices WHERE mac = %s
                """, (mac,))
                result = await cursor.fetchone()

                if not result:
                    return True  # New device

                status = result['manufacturer_status']
                last_attempt = result['manufacturer_last_attempt']

                # Retry if error status and more than 5 minutes since last attempt
                if status == 'error' and last_attempt:
                    now = datetime.datetime.now()
                    if (now - last_attempt).total_seconds() > 300:  # 5 minutes
                        return True

                # Needs lookup if pending or error
                return status in ('pending', 'error')

    async def set_manufacturer(self, mac: str, manufacturer: str, status: str = 'found'):
        """Set manufacturer for a device."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO devices (mac, manufacturer, manufacturer_status, manufacturer_last_attempt)
                    VALUES (%s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE
                        manufacturer = VALUES(manufacturer),
                        manufacturer_status = VALUES(manufacturer_status),
                        manufacturer_last_attempt = VALUES(manufacturer_last_attempt)
                """, (mac, manufacturer, status))

db = Database()
