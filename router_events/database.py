"""Database operations for device tracking."""

import os
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
                        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)

    async def get_device(self, mac: str) -> Optional[Dict[str, Any]]:
        """Get device by MAC address."""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("SELECT * FROM devices WHERE mac = %s", (mac,))
                return await cursor.fetchone()

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

db = Database()
