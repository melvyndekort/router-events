FROM python:3-slim AS base

RUN pip install --upgrade pip
RUN pip install "poetry>=1.6,<1.7"

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

FROM base AS build

COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt | pip install -r /dev/stdin

COPY . .
RUN pip install .

FROM python:3-slim AS runtime

LABEL org.opencontainers.image.source=https://github.com/melvyndekort/router-events

COPY --from=build /venv /venv

ENV PATH="/venv/bin:$PATH"

EXPOSE 13959

CMD ["uvicorn", "router_events.main:app", "--host", "0.0.0.0", "--port", "13959"]
