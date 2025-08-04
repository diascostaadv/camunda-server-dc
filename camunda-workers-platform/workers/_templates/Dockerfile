# Dockerfile for {{WORKER_NAME}} worker
# This is optional - if not present, the default workers/Dockerfile will be used

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for this specific worker)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash worker
RUN chown -R worker:worker /app

# Create log directory
RUN mkdir -p /var/log && chown -R worker:worker /var/log

# Copy common requirements and install Python dependencies
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy additional requirements for this worker (if exists)
COPY requirements.txt ./worker-requirements.txt 2>/dev/null || echo "No additional requirements"
RUN [ -f worker-requirements.txt ] && pip install --no-cache-dir -r worker-requirements.txt || echo "No additional requirements to install"

# Copy common modules
COPY ../common ./common

# Copy worker code
COPY . ./{{WORKER_NAME}}

# Change to non-root user
USER worker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${METRICS_PORT:-{{WORKER_PORT}}}/metrics || exit 1

# Run the worker
CMD ["python", "{{WORKER_NAME}}/main.py"]