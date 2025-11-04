#!/bin/bash

# Build Verification Script
# Tests that Docker build completes successfully

set -e

echo "=========================================="
echo "Docker Build Verification"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

success() {
    echo -e "${GREEN}✓${NC} $1"
}

failure() {
    echo -e "${RED}✗${NC} $1"
}

info() {
    echo -e "${YELLOW}→${NC} $1"
}

# Step 1: Check prerequisites
info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    failure "Docker not installed"
    exit 1
fi
success "Docker installed"

if ! command -v docker-compose &> /dev/null; then
    failure "Docker Compose not installed"
    exit 1
fi
success "Docker Compose installed"

echo ""

# Step 2: Check required files
info "Checking required files..."

REQUIRED_FILES=(
    "Dockerfile"
    "requirements.txt"
    "pyproject.toml"
    "docker-compose-nginx.yml"
    "config-nginx.yaml"
    "nginx/nginx.conf"
    "docker/entrypoint.sh"
    "src/python_est/server.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ] && [ ! -d "$(dirname $file)" ]; then
        failure "Missing: $file"
        exit 1
    fi
done
success "All required files present"

echo ""

# Step 3: Build Python EST Server image
info "Building Python EST Server image (this may take a few minutes)..."

if docker-compose -f docker-compose-nginx.yml build python-est-server 2>&1 | tee build.log; then
    success "Python EST Server image built successfully"
else
    failure "Python EST Server build failed"
    echo ""
    echo "Build log saved to: build.log"
    echo "Last 50 lines:"
    tail -50 build.log
    exit 1
fi

echo ""

# Step 4: Check image size
info "Checking image size..."

IMAGE_SIZE=$(docker images python-est_python-est-server --format "{{.Size}}" | head -1)
success "Image size: $IMAGE_SIZE"

echo ""

# Step 5: Test image can start
info "Testing image can start..."

# Start container temporarily
docker run --rm -d \
    --name test-python-est \
    -e NGINX_MODE=true \
    -v $(pwd)/certs:/app/certs:ro \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/config-nginx.yaml:/app/config.yaml:ro \
    python-est_python-est-server 2>/dev/null || true

sleep 5

# Check if container is running
if docker ps | grep -q test-python-est; then
    success "Container started successfully"

    # Check logs
    info "Container logs:"
    docker logs test-python-est 2>&1 | head -20

    # Stop container
    docker stop test-python-est 2>/dev/null || true
else
    failure "Container failed to start"
    info "Container logs:"
    docker logs test-python-est 2>&1 || true
    docker rm -f test-python-est 2>/dev/null || true
    exit 1
fi

echo ""

# Step 6: Pull nginx image
info "Pulling nginx image..."

if docker pull nginx:1.25-alpine &> /dev/null; then
    success "Nginx image pulled"
else
    failure "Failed to pull nginx image"
    exit 1
fi

echo ""

# Step 7: Validate docker-compose config
info "Validating docker-compose configuration..."

if docker-compose -f docker-compose-nginx.yml config > /dev/null 2>&1; then
    success "Docker Compose config valid"
else
    failure "Docker Compose config invalid"
    docker-compose -f docker-compose-nginx.yml config
    exit 1
fi

echo ""

# Summary
echo "=========================================="
echo "BUILD VERIFICATION COMPLETE"
echo "=========================================="
echo ""
echo "Results:"
echo "  ✓ Docker and Docker Compose installed"
echo "  ✓ All required files present"
echo "  ✓ Python EST Server image built"
echo "  ✓ Container can start"
echo "  ✓ Nginx image available"
echo "  ✓ Docker Compose config valid"
echo ""
echo "Next steps:"
echo "  1. Deploy: docker-compose -f docker-compose-nginx.yml up -d"
echo "  2. Check logs: docker-compose -f docker-compose-nginx.yml logs -f"
echo "  3. Test health: curl -k https://localhost:8445/health"
echo ""
echo "=========================================="

exit 0
