# Python-EST Server Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssl \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r est && useradd -r -g est est

# Copy requirements and install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Copy source code
COPY src/ ./src/
COPY examples/ ./examples/
COPY est_server.py ./
COPY est_client.py ./
COPY generate_certificates.py ./
COPY validate_setup.py ./
COPY config.example.yaml ./

# Create directories with proper permissions
RUN mkdir -p /app/data /app/certs /app/logs && \
    chown -R est:est /app

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER est

# Expose EST ports
# Port 8445 for standalone HTTPS mode
# Port 8000 for nginx proxy mode (HTTP)
EXPOSE 8445 8000

# Health check
# Check port 8000 (nginx mode) if NGINX_MODE is set, otherwise 8445 (standalone)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD if [ "$NGINX_MODE" = "true" ]; then \
            curl -f http://localhost:8000/ || exit 1; \
        else \
            curl -k -f https://localhost:8445/.well-known/est/cacerts || exit 1; \
        fi

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]
CMD ["start"]