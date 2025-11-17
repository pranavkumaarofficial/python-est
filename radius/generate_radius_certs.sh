#!/bin/bash
# Generate FreeRADIUS Server Certificates
# This script generates RADIUS server's own certificates (not EST certificates)
# Run this on the RADIUS VM during initial setup

set -e

CERT_DIR="radius-server-certs"
DAYS=3650  # 10 years

echo "🔐 Generating FreeRADIUS Server Certificates..."

# Create directory
mkdir -p "$CERT_DIR"

# Generate RADIUS server private key
echo "📝 Generating RADIUS server private key..."
openssl genrsa -out "$CERT_DIR/server.key" 2048

# Generate RADIUS server certificate (self-signed)
echo "📝 Generating RADIUS server certificate..."
openssl req -new -x509 \
    -key "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.pem" \
    -days $DAYS \
    -subj "/C=US/ST=CA/L=Test/O=Ferrari Medical Inc/CN=RADIUS Server"

# Set permissions
chmod 600 "$CERT_DIR/server.key"
chmod 644 "$CERT_DIR/server.pem"

echo "✅ RADIUS server certificates generated in $CERT_DIR/"
echo ""
echo "Files created:"
echo "  - $CERT_DIR/server.key (private key)"
echo "  - $CERT_DIR/server.pem (certificate)"
echo ""
echo "⚠️  IMPORTANT: You still need to copy the EST CA certificate from EST VM:"
echo "   mkdir -p radius-certs"
echo "   scp user@EST_VM_IP:/path/to/python-est/certs/ca-cert.pem radius-certs/"
