# RouterOS Event Receiver

A FastAPI-based service for receiving and processing events from RouterOS devices.

## Features

- FastAPI web framework for high performance
- Event receiving endpoint for RouterOS webhooks
- MariaDB/MySQL integration for device tracking with SQLAlchemy ORM
- Automatic database schema creation
- ntfy notifications for unknown and tracked devices
- Device management API for manual naming
- Manufacturer lookup via MAC address with rate limiting
- Web interface for device management
- Health check endpoint for monitoring
- Docker support for easy deployment
- Comprehensive test suite with 97% coverage (107 tests)
- Code quality checks with pylint (10/10 score)

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

**Note:** Results are cached and processed asynchronously in the background to respect API rate limits. May return "Loading..." initially. Failed lookups are automatically retried every 5 minutes.

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

### DELETE /api/devices/{mac}
Delete device by MAC address.

**Response:**
```json
{
  "status": "deleted"
}
```

**Error Response:**
- Status Code: 404 (Device not found)

### POST /api/manufacturer/retry
Force retry of all failed manufacturer lookups.

**Response:**
```json
{
  "message": "Reset 5 failed lookups for retry"
}
```

### POST /api/manufacturer/{mac}/retry
Force retry of manufacturer lookup for specific device.

**Response:**
```json
{
  "message": "Manufacturer lookup reset for 00:11:22:33:44:55"
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
- Delete buttons for removing devices (with confirmation)
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
│   ├── notifications.py   # Notification service
│   ├── models.py          # SQLAlchemy models
│   └── schemas.py         # Pydantic schemas
├── static/                # Static web files
│   └── devices.html       # Web interface for device management
├── tests/                 # Test suite (97% coverage)
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_main.py       # FastAPI endpoint tests
│   ├── test_database.py   # Database operation tests
│   ├── test_notifications.py # Notification service tests
│   ├── test_models.py     # Model tests
│   ├── test_schemas.py    # Schema validation tests
│   └── test_edge_cases.py # Edge case and error handling tests
├── examples/              # Example scripts
│   └── routeros/          # RouterOS example scripts
├── .github/               # GitHub workflows and config
├── pyproject.toml         # Poetry configuration
├── poetry.lock            # Poetry lock file
├── Dockerfile             # Docker configuration
├── Makefile              # Build automation
├── .env.example          # Environment configuration example
├── .gitignore            # Git ignore rules
├── LICENSE               # MIT License
├── SECURITY.md           # Security policy
└── README.md
```

### Available Make Commands

- `make install` - Install dependencies
- `make update-deps` - Update dependencies
- `make test` - Run tests with coverage (97% coverage)
- `make build` - Build Python package
- `make full-build` - Build Docker image
- `make pylint` - Run code quality checks (10/10 score)
- `make dev` - Start development server
- `make run` - Start production server
- `make clean` - Clean build artifacts

### Running Tests

```bash
# Run all tests with coverage
make test

# Run specific test file
poetry run pytest tests/test_main.py

# Run with detailed coverage report
poetry run pytest --cov=router_events --cov-report=html
```

### Code Quality

The project maintains high code quality standards:

```bash
# Run pylint (currently 10/10 score)
make pylint

# Fix common formatting issues
poetry run black router_events tests
poetry run isort router_events tests
```

### Test Coverage

The project has comprehensive test coverage:
- **Total Coverage: 97%**
- **107 tests** covering all major functionality
- Unit tests for all components
- Edge case and error handling tests
- No skipped tests or warnings

## Configuration

The application can be configured through environment variables:

### Server Configuration
- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 13959)
- `LOG_LEVEL` - Logging level (default: INFO)

### Database Configuration
- `DB_HOST` - MariaDB/MySQL host (default: localhost)
- `DB_PORT` - MariaDB/MySQL port (default: 3306)
- `DB_USER` - Database user (default: router_events)
- `DB_PASSWORD` - Database password (required)
- `DB_NAME` - Database name (default: router_events)

### Notification Configuration
- `NTFY_URL` - ntfy server URL (default: https://ntfy.sh)
- `NTFY_TOPIC` - ntfy topic name (default: router-events)
- `NTFY_TOKEN` - ntfy authentication token (optional)
- `NTFY_ENABLED` - Enable notifications (default: true)

Copy `.env.example` to `.env` and configure your settings.

## RouterOS Configuration

To send events from RouterOS to this service, configure a webhook in your RouterOS device:

```
/system script add name=dhcp-notify source=":local mac \$leaseActMAC; :local ip \$leaseActIP; :local dhcpServer \$leaseServerName; :local interface \"\"; :local eventType \"dhcp\"; :local host \"\"; :local action \"unknown\"; :do {:set interface [/ip dhcp-server get [find name=\$dhcpServer] interface]} on-error={:set interface \"\"}; :do {:local leaseId [/ip dhcp-server lease find mac-address=\$mac]; :if ([:len \$leaseId] > 0) do={:set host [/ip dhcp-server lease get \$leaseId host-name]; :set action \"assigned\"} else={:set action \"released\"}} on-error={:set host \"\"; :set action \"error\"}; /tool fetch url=\"http://your-server:13959/api/events\" http-method=post http-data=\"{\\\"action\\\":\\\"\$action\\\",\\\"mac\\\":\\\"\$mac\\\",\\\"ip\\\":\\\"\$ip\\\",\\\"host\\\":\\\"\$host\\\"}\" http-header-field=\"Content-Type: application/json\" keep-result=no"

# To trigger this script on DHCP lease events:
/ip dhcp-server set [find name="your-dhcp-server"] lease-script=dhcp-notify
```

Replace `your-server` with your actual server IP address and `your-dhcp-server` with your DHCP server name.

## License

MIT License - see LICENSE file for details.
