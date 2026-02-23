# RouterOS Event Receiver

A FastAPI-based service for receiving and processing DHCP events from RouterOS devices via syslog and Vector.

## Architecture

Events flow through the following pipeline:
1. **RouterOS** - Sends DHCP events to syslog
2. **Vector** - Receives syslog messages, filters DHCP events, and forwards to router-events
3. **router-events** - Processes events, tracks devices, and sends notifications

## Features

- FastAPI web framework for high performance
- Event receiving endpoint for Vector HTTP sink
- Syslog message parsing for DHCP events
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
Receives RouterOS events from Vector.

**Request Body (from Vector):**
```json
{
  "message": "dhcp-server assigned 192.168.1.100 for 00:11:22:33:44:55 test-device"
}
```

Or direct format (legacy):
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
      "last_ip": "192.168.1.100",
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
  "last_ip": "192.168.1.100",
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
- Last known IP address for each device
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

To send DHCP events from RouterOS to this service, configure syslog on your RouterOS device to send messages to your Vector instance.

### RouterOS 7.x Syslog Configuration

```
# Configure syslog action to send to Vector
/system logging action
add name=remote remote=<vector-server-ip> remote-port=514 target=remote

# Enable DHCP server logging
/system logging
add action=remote topics=dhcp
```

Replace `<vector-server-ip>` with the IP address of your Vector server.

### Vector Configuration

Vector receives syslog messages, filters DHCP events, and forwards them to router-events:

```toml
[sources.syslog]
type = "syslog"
address = "0.0.0.0:514"
mode = "udp"

[transforms.dhcp_filter]
type = "filter"
inputs = ["syslog"]
condition = 'contains!(.appname, "dhcp")'

[sinks.router_events]
type = "http"
inputs = ["dhcp_filter"]
uri = "http://<router-events-server>:13959/api/events"
encoding.codec = "json"
method = "post"
```

Replace `<router-events-server>` with your router-events server IP address.

### Message Format

RouterOS sends DHCP events in the following syslog format:
```
dhcp-server assigned 192.168.1.100 for 00:11:22:33:44:55 hostname
dhcp-server deassigned 192.168.1.100 from 00:11:22:33:44:55
```

Vector's syslog source parses these messages and extracts the appname (`dhcp-server`) into a separate field. The `message` field sent to router-events contains:
```
assigned 192.168.1.100 for 00:11:22:33:44:55 hostname
deassigned 192.168.1.100 from 00:11:22:33:44:55
```

The router-events service automatically parses these messages to extract:
- Action (assigned/deassigned)
- IP address
- MAC address
- Hostname (if present)

## License

MIT License - see LICENSE file for details.
