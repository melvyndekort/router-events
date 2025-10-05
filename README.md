# RouterOS Event Receiver

A FastAPI-based service for receiving and processing events from RouterOS devices.

## Features

- FastAPI web framework for high performance
- Event receiving endpoint for RouterOS webhooks
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
  "event": "dhcp-lease",
  "data": {
    "mac": "00:11:22:33:44:55",
    "ip": "192.168.1.100",
    "hostname": "test-device"
  }
}
```

**Response:**
```json
{
  "status": "ok"
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

## Development

### Project Structure

```
router-events/
├── router_events/          # Main package
│   ├── __init__.py
│   └── main.py            # FastAPI application
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   └── test_main.py
├── examples/              # Example scripts
│   └── routeros/          # RouterOS example scripts
├── .github/               # GitHub workflows and config
├── pyproject.toml         # Poetry configuration
├── Dockerfile             # Docker configuration
├── Makefile              # Build automation
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

- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 13959)
- `LOG_LEVEL` - Logging level (default: INFO)

## RouterOS Configuration

To send events from RouterOS to this service, configure a webhook in your RouterOS device:

```
/system script
add name=dhcp-notify source={
    :local url "http://your-server:13959/api/events"
    :local data "{\"event\":\"dhcp-lease\",\"data\":{\"mac\":\"$leaseActMAC\",\"ip\":\"$leaseActIP\",\"hostname\":\"$leaseActHostName\"}}"
    /tool fetch url=$url http-method=post http-header-field="Content-Type: application/json" http-data=$data
}
```

## License

MIT License - see LICENSE file for details.
