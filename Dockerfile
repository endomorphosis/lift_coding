# Dockerfile for HandsFree Dev Companion API
# Production-friendly configuration with uvicorn

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency files
COPY requirements-dev.txt .
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-dev.txt && \
    pip install --no-cache-dir -e .

# Copy application code
COPY src/ ./src/
COPY spec/ ./spec/
COPY scripts/ ./scripts/

# Create data directory for DuckDB (volume mount point)
RUN mkdir -p /app/data

# Environment variables with defaults
# Port binding
ENV PORT=8080
# Auth mode (dev/jwt/api_key)
ENV HANDSFREE_AUTH_MODE=dev
# Database path
ENV DUCKDB_PATH=/app/data/handsfree.db
# Redis configuration
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV REDIS_ENABLED=true
# Metrics
ENV HANDSFREE_ENABLE_METRICS=false

# Expose port
EXPOSE 8080

# Set Python path to include src directory
ENV PYTHONPATH=/app/src

# Run with uvicorn in production mode (no reload)
CMD ["sh", "-c", "uvicorn handsfree.api:app --host 0.0.0.0 --port ${PORT} --log-level info"]
