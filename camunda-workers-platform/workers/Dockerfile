FROM python:3.11-slim

# Build argument for worker directory
ARG WORKER_DIR=hello-world

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash worker
RUN chown -R worker:worker /app

# Create log directory
RUN mkdir -p /var/log && chown -R worker:worker /var/log

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy common modules
COPY common ./common

# Copy specific worker code
COPY ${WORKER_DIR} ./current_worker

# Change to non-root user
USER worker

# Health check (usando variável de ambiente para porta)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${METRICS_PORT:-8001}/metrics || exit 1

# Default command for current worker
CMD ["python", "current_worker/main.py"]