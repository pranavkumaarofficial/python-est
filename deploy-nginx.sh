#!/bin/bash

# EST Server with Nginx - Deployment Script
#
# This script deploys the EST server with nginx reverse proxy
# for production-ready RA certificate authentication

set -e

echo "================================================================"
echo "EST Server with Nginx - Deployment Script"
echo "================================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check prerequisites
info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    error "Docker is not installed"
fi

if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose is not installed"
fi

info "Prerequisites OK"
echo ""

# Check certificate files
info "Checking certificate files..."

REQUIRED_CERTS=(
    "certs/ca-cert.pem"
    "certs/ca-key.pem"
    "certs/server.crt"
    "certs/server.key"
    "certs/iqe-ra-cert.pem"
    "certs/iqe-ra-key.pem"
)

for cert in "${REQUIRED_CERTS[@]}"; do
    if [ ! -f "$cert" ]; then
        error "Missing certificate: $cert"
    fi
done

info "All certificates present"
echo ""

# Verify certificate chain
info "Verifying certificate chain..."

if openssl verify -CAfile certs/ca-cert.pem certs/server.crt > /dev/null 2>&1; then
    info "Server certificate: OK"
else
    error "Server certificate validation failed"
fi

if openssl verify -CAfile certs/ca-cert.pem certs/iqe-ra-cert.pem > /dev/null 2>&1; then
    info "RA certificate: OK"
else
    error "RA certificate validation failed"
fi

echo ""

# Check nginx configuration
info "Checking nginx configuration..."

if [ ! -f "nginx/nginx.conf" ]; then
    error "Nginx configuration not found: nginx/nginx.conf"
fi

info "Nginx configuration: OK"
echo ""

# Stop any running containers
info "Stopping existing containers..."
docker-compose -f docker-compose-nginx.yml down 2>/dev/null || true
echo ""

# Build images
info "Building Docker images..."
docker-compose -f docker-compose-nginx.yml build --no-cache
echo ""

# Start services
info "Starting services..."
docker-compose -f docker-compose-nginx.yml up -d
echo ""

# Wait for services to be healthy
info "Waiting for services to be healthy..."
sleep 10

MAX_WAIT=60
WAITED=0

while [ $WAITED -lt $MAX_WAIT ]; do
    if docker-compose -f docker-compose-nginx.yml ps | grep -q "healthy"; then
        break
    fi
    echo -n "."
    sleep 2
    WAITED=$((WAITED + 2))
done

echo ""

if [ $WAITED -ge $MAX_WAIT ]; then
    error "Services failed to become healthy"
fi

info "Services are healthy"
echo ""

# Display running services
info "Running services:"
docker-compose -f docker-compose-nginx.yml ps
echo ""

# Test endpoints
info "Testing endpoints..."

# Test health endpoint
if curl -s -k https://localhost:8445/health | grep -q "OK"; then
    info "Health check: OK"
else
    warn "Health check failed (may be normal if nginx is still starting)"
fi

# Test cacerts endpoint
if curl -s -k https://localhost:8445/.well-known/est/cacerts > /tmp/test-cacerts.p7 2>&1; then
    if [ -f /tmp/test-cacerts.p7 ] && [ -s /tmp/test-cacerts.p7 ]; then
        info "CA certs endpoint: OK"
        rm -f /tmp/test-cacerts.p7
    else
        warn "CA certs endpoint returned empty response"
    fi
else
    warn "CA certs endpoint failed"
fi

echo ""

# Display logs
info "Recent logs from Python EST server:"
docker-compose -f docker-compose-nginx.yml logs --tail=20 python-est-server
echo ""

info "Recent logs from Nginx:"
docker-compose -f docker-compose-nginx.yml logs --tail=20 nginx
echo ""

# Summary
echo "================================================================"
echo "DEPLOYMENT COMPLETE"
echo "================================================================"
echo ""
echo "EST Server Details:"
echo "  URL:        https://localhost:8445"
echo "  Dashboard:  https://localhost:8445/"
echo "  Mode:       Nginx proxy with RA authentication"
echo ""
echo "Nginx Details:"
echo "  TLS Port:   8445 (public)"
echo "  Backend:    python-est-server:8000 (internal HTTP)"
echo "  Logs:       docker-compose -f docker-compose-nginx.yml logs -f nginx"
echo ""
echo "Python EST Server Details:"
echo "  HTTP Port:  8000 (internal only)"
echo "  Mode:       NGINX_MODE=true (HTTP, no TLS)"
echo "  Logs:       docker-compose -f docker-compose-nginx.yml logs -f python-est-server"
echo ""
echo "RA Certificate Files for IQE Team:"
echo "  CA Cert:    certs/ca-cert.pem"
echo "  RA Cert:    certs/iqe-ra-cert.pem"
echo "  RA Key:     certs/iqe-ra-key.pem"
echo ""
echo "Commands:"
echo "  View logs:      docker-compose -f docker-compose-nginx.yml logs -f"
echo "  Stop services:  docker-compose -f docker-compose-nginx.yml down"
echo "  Restart:        docker-compose -f docker-compose-nginx.yml restart"
echo "  Status:         docker-compose -f docker-compose-nginx.yml ps"
echo ""
echo "Next Steps:"
echo "  1. Test RA authentication: ./test-ra-nginx.sh"
echo "  2. Transfer certificates to IQE team (see iqe_deployment_package/)"
echo "  3. IQE team configures gateway with RA certificate"
echo "  4. Monitor logs during IQE testing"
echo ""
echo "================================================================"
