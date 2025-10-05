# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Configure poetry: don't create virtual env, install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY router_events/ ./router_events/

# Expose the port the app will run on
EXPOSE 13959

# Run the app
CMD ["uvicorn", "router_events.main:app", "--host", "0.0.0.0", "--port", "13959"]
