# Python-EST Server Docker Image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssl \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY pyproject.toml ./
COPY README.md ./
COPY generate_certificates_python.py ./
COPY generate_ra_certificate.py ./
COPY create_iqe_user.py ./

# Install build tools and package
RUN pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir -e .

# Create directories
RUN mkdir -p /app/data /app/certs /app/logs

# Copy entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create non-root user and set permissions
RUN groupadd -r est && useradd -r -g est est && \
    chown -R est:est /app /entrypoint.sh

# Switch to non-root user
USER est

# Expose ports
EXPOSE 8445 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/health')" || exit 1

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]
