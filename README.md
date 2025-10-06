# RouterOS Event Receiver

A FastAPI-based service for receiving and processing events from RouterOS devices.

## Features

- FastAPI web framework for high performance
- Event receiving endpoint for RouterOS webhooks
- MariaDB integration for device tracking
- ntfy notifications for unknown and tracked devices
- Device management API for manual naming
- Health check endpoint for monitoring
- Docker support for easy deployment
- Comprehensive test suite
- Code quality checks with pylint

## Installation

### Using Poetry (Recommended)

```bash
# Install dependencies
make install

# Run tests
make test

# Start development server
make dev

# Start production server
make run
```

### Using Docker

```bash
# Build Docker image
make full-build

# Run container
docker run -p 13959:13959 router-events
```

## API Endpoints

### POST /api/events
Receives RouterOS events via webhook.

**Request Body:**
```json
{
  "action": "assigned",
  "mac": "00:11:22:33:44:55",
  "ip": "192.168.1.100",
  "host": "test-device"
}
```

**Response:**
- Status Code: 204 (No Content)

### GET /api/devices
Get all tracked devices.

**Response:**
```json
{
  "devices": [
    {
      "mac": "00:11:22:33:44:55",
      "name": "My Device",
      "notify": true,
      "first_seen": "2024-01-01T10:00:00",
      "last_seen": "2024-01-01T12:00:00"
    }
  ]
}
```

### GET /api/devices/{mac}
Get specific device by MAC address.

**Response:**
```json
{
  "mac": "00:11:22:33:44:55",
  "name": "My Device",
  "notify": true,
  "first_seen": "2024-01-01T10:00:00",
  "last_seen": "2024-01-01T12:00:00"
}
```

**Error Response:**
- Status Code: 404 (Device not found)

### GET /api/manufacturer/{mac}
Get manufacturer information for a MAC address.

**Response:**
```json
{
  "manufacturer": "Apple, Inc."
}
```

### PUT /api/devices/{mac}
Update device name or notification settings.

**Request Body:**
```json
{
  "name": "My Device",
  "notify": true
}
```

**Response:**
```json
{
  "status": "updated"
}
```

### GET /health
Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy"
}
```

## Web Interface

The application includes a web interface for viewing tracked devices:

- **GET /** - Redirects to the devices page
- **GET /devices.html** - Web interface showing all tracked devices in a table format

The web interface displays:
- MAC addresses of all tracked devices
- Device manufacturers (looked up via MAC address)
- Device names (or "Unknown" if not set) - editable inline
- Notification status - toggle with checkbox
- First and last seen timestamps
- Auto-refreshes every 30 seconds

Access the web interface at `http://your-server:13959/` after starting the service.

## Development

### Project Structure

```
router-events/
├── router_events/          # Main package
│   ├── __init__.py
│   ├── main.py            # FastAPI application
│   ├── database.py        # Database operations
│   └── notifications.py   # Notification service
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_main.py
│   ├── test_database.py
│   ├── test_notifications.py
│   ├── test_models.py
│   └── test_edge_cases.py
├── examples/              # Example scripts
│   └── routeros/          # RouterOS example scripts
├── .github/               # GitHub workflows and config
├── pyproject.toml         # Poetry configuration
├── Dockerfile             # Docker configuration
├── Makefile              # Build automation
├── .env.example          # Environment configuration example
└── README.md
```

### Available Make Commands

- `make install` - Install dependencies
- `make test` - Run tests with coverage
- `make build` - Build Python package
- `make full-build` - Build Docker image
- `make pylint` - Run code quality checks
- `make dev` - Start development server
- `make run` - Start production server
- `make clean` - Clean build artifacts

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
poetry run pytest tests/test_main.py

# Run with coverage report
poetry run pytest --cov=router_events --cov-report=html
```

### Code Quality

```bash
# Run pylint
make pylint

# Fix common issues
poetry run black router_events tests
poetry run isort router_events tests
```

## Configuration

The application can be configured through environment variables:

### Server Configuration
- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 13959)
- `LOG_LEVEL` - Logging level (default: INFO)

### Database Configuration
- `DB_HOST` - MariaDB host (default: localhost)
- `DB_PORT` - MariaDB port (default: 3306)
- `DB_USER` - Database user (default: router_events)
- `DB_PASSWORD` - Database password (required)
- `DB_NAME` - Database name (default: router_events)

### Notification Configuration
- `NTFY_URL` - ntfy server URL (default: https://ntfy.sh)
- `NTFY_TOPIC` - ntfy topic name (default: router-events)
- `NTFY_ENABLED` - Enable notifications (default: true)

Copy `.env.example` to `.env` and configure your settings.

## RouterOS Configuration

To send events from RouterOS to this service, configure a webhook in your RouterOS device:

```
/system script add name=dhcp-notify source=":local mac \$leaseActMAC; :local ip \$leaseActIP; :local host \"\"; :local action \"assigned\"; :do {:local leaseId [/ip dhcp-server lease find mac-address=\$mac]; :if ([:len \$leaseId] > 0) do={:set host [/ip dhcp-server lease get \$leaseId host-name]}} on-error={:set host \"\"}; /tool fetch url=\"http://your-server:13959/api/events\" http-method=post http-data=\"{\\\"action\\\":\\\"\$action\\\",\\\"mac\\\":\\\"\$mac\\\",\\\"ip\\\":\\\"\$ip\\\",\\\"host\\\":\\\"\$host\\\"}\" http-header-field=\"Content-Type: application/json\" keep-result=no"
```

Replace `your-server` with your actual server IP address.

## License

MIT License - see LICENSE file for details.
