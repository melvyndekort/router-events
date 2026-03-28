# router-events

> For global standards, way-of-workings, and pre-commit checklist, see `~/.kiro/steering/behavior.md`

## Role

Python developer and DevOps engineer.

## What This Does

FastAPI service that receives and processes DHCP events from RouterOS devices via syslog and Vector. Stores events in MySQL (via aiomysql + SQLAlchemy). Includes a static HTML page (`static/devices.html`) for viewing connected devices.

## Repository Structure

- `router_events/` — FastAPI application source
- `tests/` — Test suite (uses pytest-asyncio)
- `static/` — Static HTML/assets (devices page, favicon)
- `examples/` — Example data/configs
- `Dockerfile` — Slim-based build (needs iputils-ping)
- `Makefile` — `install`, `test`, `lint` (pylint), `build`, `full-build`, `dev`, `run`

## Deployment

- Container image: `ghcr.io/melvyndekort/router-events:latest`
- Runs on homelab Docker via Portainer, exposed on port 13959

## Related Repositories

- `~/src/melvyndekort/homelab` — Docker Compose stack that runs this container
- `~/src/melvyndekort/network-monitor` — Consumes device data from this service
