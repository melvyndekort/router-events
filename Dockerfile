FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

FROM base AS build

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY router_events/ ./router_events/
RUN uv build --wheel && pip install dist/*.whl

FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.source=https://github.com/melvyndekort/router-events

RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping && rm -rf /var/lib/apt/lists/*

COPY --from=build /venv /venv
COPY static /static

ENV PATH="/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

EXPOSE 13959

CMD ["uvicorn", "router_events.main:app", "--host", "0.0.0.0", "--port", "13959"]
