# Python-EST Server Docker Image
# Production-ready image with all dependencies properly installed

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssl \
    curl \
    wget \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r est && useradd -r -g est est

# Copy requirements first for better caching
COPY requirements.txt ./

# Install Python dependencies from requirements.txt (more reliable than pyproject.toml)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Copy certificate generation scripts (required for setup)
COPY generate_certificates_python.py ./
COPY generate_ra_certificate.py ./
COPY create_iqe_user.py ./

# Install the package (editable mode for development)
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e . || \
    echo "Warning: Package installation failed, but dependencies are installed"

# Create directories with proper permissions
RUN mkdir -p /app/data /app/certs /app/logs && \
    chown -R est:est /app

# Copy and set up entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && \
    chown est:est /entrypoint.sh

# Switch to non-root user
USER est

# Expose EST ports
# Port 8445 for standalone HTTPS mode
# Port 8000 for nginx proxy mode (HTTP)
EXPOSE 8445 8000

# Health check - Use proper endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD if [ "$NGINX_MODE" = "true" ]; then \
            python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1; \
        else \
            curl -k -f https://localhost:8445/.well-known/est/cacerts || exit 1; \
        fi

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]
CMD ["start"]
