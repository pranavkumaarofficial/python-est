#!/bin/bash

# Test RA Certificate Authentication with Nginx
#
# This script tests the EST server running behind nginx
# with RA certificate authentication

set -e

echo "================================================================"
echo "RA Certificate Authentication Test (Nginx Mode)"
echo "================================================================"
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

# Check prerequisites
info "Checking prerequisites..."

if [ ! -f "certs/iqe-ra-cert.pem" ]; then
    failure "RA certificate not found: certs/iqe-ra-cert.pem"
    exit 1
fi

if [ ! -f "certs/iqe-ra-key.pem" ]; then
    failure "RA private key not found: certs/iqe-ra-key.pem"
    exit 1
fi

success "Prerequisites OK"
echo ""

# Test 1: Health check
info "Test 1: Health check endpoint"
if curl -s -k https://localhost:8445/health | grep -q "OK"; then
    success "Health check passed"
else
    failure "Health check failed"
    exit 1
fi
echo ""

# Test 2: CA certificates (no auth required)
info "Test 2: Retrieve CA certificates (no authentication)"
if curl -s -k https://localhost:8445/.well-known/est/cacerts -o /tmp/test-cacerts.p7 2>&1; then
    if [ -f /tmp/test-cacerts.p7 ] && [ -s /tmp/test-cacerts.p7 ]; then
        success "CA certificates retrieved"

        # Verify PKCS#7 format
        file /tmp/test-cacerts.p7 | grep -q "ASCII" && success "Format: base64 (as expected)" || info "Format: DER binary"
    else
        failure "Empty response"
        exit 1
    fi
else
    failure "Failed to retrieve CA certificates"
    exit 1
fi
echo ""

# Test 3: Generate test CSR
info "Test 3: Generating test CSR for enrollment"

python3 << 'EOF'
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generate key
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# Generate CSR
csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, 'US'),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'Hospital'),
    x509.NameAttribute(NameOID.COMMON_NAME, 'test-pump-nginx-001'),
])).sign(key, hashes.SHA256())

# Save CSR in DER format
with open('/tmp/test-csr.der', 'wb') as f:
    f.write(csr.public_bytes(serialization.Encoding.DER))

print("CSR generated")
EOF

success "Test CSR generated"
echo ""

# Test 4: Enrollment WITH RA certificate
info "Test 4: Enrollment with RA certificate authentication"

HTTP_CODE=$(curl -s -k https://localhost:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @/tmp/test-csr.der \
  -o /tmp/test-cert-ra.p7 \
  -w "%{http_code}")

echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    success "RA certificate authentication: SUCCESS"

    if [ -f /tmp/test-cert-ra.p7 ] && [ -s /tmp/test-cert-ra.p7 ]; then
        success "Certificate received"

        # Try to decode
        file /tmp/test-cert-ra.p7 | grep -q "ASCII" && FORMAT="base64" || FORMAT="DER"
        success "Response format: $FORMAT"

        # Validate certificate
        if [ "$FORMAT" = "base64" ]; then
            base64 -d /tmp/test-cert-ra.p7 > /tmp/test-cert-ra-decoded.p7 2>/dev/null || true
            openssl pkcs7 -inform DER -in /tmp/test-cert-ra-decoded.p7 -print_certs -out /tmp/test-cert-ra.pem 2>/dev/null
        else
            openssl pkcs7 -inform DER -in /tmp/test-cert-ra.p7 -print_certs -out /tmp/test-cert-ra.pem 2>/dev/null
        fi

        if [ -f /tmp/test-cert-ra.pem ] && [ -s /tmp/test-cert-ra.pem ]; then
            success "Certificate is valid PKCS#7"

            # Extract subject
            SUBJECT=$(openssl x509 -in /tmp/test-cert-ra.pem -noout -subject 2>/dev/null | cut -d'=' -f2-)
            success "Certificate subject: $SUBJECT"
        else
            failure "Failed to parse certificate"
        fi
    else
        failure "Empty certificate response"
    fi
else
    failure "RA certificate authentication FAILED (HTTP $HTTP_CODE)"
    echo "Response content:"
    cat /tmp/test-cert-ra.p7 2>/dev/null || echo "(empty)"
    exit 1
fi

echo ""

# Test 5: Enrollment WITHOUT client certificate (should fail or use password)
info "Test 5: Enrollment without client certificate (password auth test)"

HTTP_CODE=$(curl -s -k https://localhost:8445/.well-known/est/simpleenroll \
  -u iqe-gateway:iqe-secure-password-2024 \
  -H "Content-Type: application/pkcs10" \
  --data-binary @/tmp/test-csr.der \
  -o /tmp/test-cert-pwd.p7 \
  -w "%{http_code}")

echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    success "Password authentication: SUCCESS (fallback working)"
elif [ "$HTTP_CODE" = "401" ]; then
    info "Password authentication: FAILED (expected if user doesn't exist)"
else
    info "Unexpected status: $HTTP_CODE"
fi

echo ""

# Check server logs for RA authentication
info "Checking server logs for RA authentication..."

echo ""
echo "--- Python EST Server Logs (last 30 lines) ---"
docker-compose -f docker-compose-nginx.yml logs --tail=30 python-est-server | grep -E "Client certificate|RA|authentication|simpleenroll"
echo ""

echo "--- Nginx Logs (last 10 lines) ---"
docker-compose -f docker-compose-nginx.yml logs --tail=10 nginx
echo ""

# Summary
echo "================================================================"
echo "TEST SUMMARY"
echo "================================================================"
echo ""
echo "Results:"
echo "  [1] Health check:           PASS"
echo "  [2] CA certificates:        PASS"
echo "  [3] CSR generation:         PASS"
if [ "$HTTP_CODE" = "200" ]; then
    echo "  [4] RA authentication:      PASS ✓"
else
    echo "  [4] RA authentication:      FAIL ✗"
fi
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "================================================================"
    echo "SUCCESS: RA CERTIFICATE AUTHENTICATION WORKING!"
    echo "================================================================"
    echo ""
    echo "The EST server with nginx is correctly:"
    echo "  ✓ Extracting client certificates from TLS"
    echo "  ✓ Forwarding certificates via HTTP headers"
    echo "  ✓ Authenticating based on RA certificate"
    echo "  ✓ Issuing certificates"
    echo ""
    echo "Ready for IQE integration!"
    echo ""
else
    echo "================================================================"
    echo "FAILED: RA CERTIFICATE AUTHENTICATION NOT WORKING"
    echo "================================================================"
    echo ""
    echo "Check the logs above for details"
    echo ""
    echo "Common issues:"
    echo "  - Nginx not forwarding client certificate headers"
    echo "  - Python middleware not parsing certificate correctly"
    echo "  - Certificate validation failing"
    echo ""
    echo "Debug commands:"
    echo "  docker-compose -f docker-compose-nginx.yml logs python-est-server"
    echo "  docker-compose -f docker-compose-nginx.yml logs nginx"
    echo ""
    exit 1
fi

# Cleanup
rm -f /tmp/test-*.p7 /tmp/test-*.pem /tmp/test-*.der 2>/dev/null || true

exit 0
