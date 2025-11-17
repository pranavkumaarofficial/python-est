#!/bin/bash

echo "🔐 FreeRADIUS Starting..."

# Create required directories
echo "Creating required directories..."
mkdir -p /tmp/radiusd
chown freerad:freerad /tmp/radiusd
chmod 700 /tmp/radiusd

# Fix permissions for mounted certificates (Windows compatibility)
echo "Fixing certificate permissions..."
chmod 600 /etc/freeradius/certs/server/server.key 2>/dev/null || true
chmod 644 /etc/freeradius/certs/server/server.pem 2>/dev/null || true
chmod 644 /etc/freeradius/certs/ca/ca-cert.pem 2>/dev/null || true
chown -R freerad:freerad /etc/freeradius/certs 2>/dev/null || true

echo "✅ Starting FreeRADIUS..."

# Start FreeRADIUS
exec freeradius -f -X
