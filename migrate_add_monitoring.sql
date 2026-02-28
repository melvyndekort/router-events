-- Migration to add device monitoring fields
-- Run this on your MariaDB/MySQL database

USE router_events;

-- Add online status column (default FALSE)
ALTER TABLE devices 
ADD COLUMN online BOOLEAN DEFAULT FALSE AFTER manufacturer_last_attempt;

-- Add last_ping timestamp column
ALTER TABLE devices 
ADD COLUMN last_ping DATETIME NULL AFTER online;

-- Verify the changes
DESCRIBE devices;
