FROM python:3.11-slim

LABEL maintainer="Dias Costa <contato@diascosta.com.br>"
LABEL description="Worker para integração DW LAW e-Protocol - Consulta Processual"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker code
COPY . /app/

# Copy common modules from parent directory
COPY ../common /app/common/

# Create logs directory
RUN mkdir -p /var/log

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${METRICS_PORT:-8000}/health || exit 1

# Expose metrics port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the DW LAW worker
CMD ["python", "dw_law_worker/main.py"]
