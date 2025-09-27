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

# Create directories with proper permissions
RUN mkdir -p /app/data /app/certs /app/logs && \
    chown -R est:est /app

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER est

# Expose EST port
EXPOSE 8443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -k -f https://localhost:8443/.well-known/est/cacerts || exit 1

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]
CMD ["start"]