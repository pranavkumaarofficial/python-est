#!/bin/bash
set -e

# Python-EST Docker Entrypoint Script

echo "🔐 Starting Python-EST Server..."

# Configuration file path
CONFIG_FILE="${EST_CONFIG:-/app/config.yaml}"

# Check if configuration exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "📝 Configuration file not found at $CONFIG_FILE"
    echo "🔧 Initializing EST server..."

    # Initialize server with default configuration
    python-est init --host 0.0.0.0 --port 8443

    echo "✅ EST server initialized"
fi

# Check if SRP users exist
if [ ! -f "/app/data/srp_users.db" ] || [ ! -s "/app/data/srp_users.db" ]; then
    echo "👥 Creating default SRP users..."

    # Add default users if none exist
    python-est user add admin --password "${EST_ADMIN_PASSWORD:-admin123}" || true
    python-est user add testuser --password "${EST_TEST_PASSWORD:-testpass123}" || true

    echo "✅ Default SRP users created"
fi

# Execute the command
case "$1" in
    start)
        echo "🚀 Starting EST server..."
        exec python-est start --config "$CONFIG_FILE"
        ;;
    init)
        echo "🔧 Initializing EST server..."
        exec python-est init "${@:2}"
        ;;
    user)
        echo "👥 Managing SRP users..."
        exec python-est user "${@:2}"
        ;;
    status)
        echo "📊 Checking server status..."
        exec python-est status --config "$CONFIG_FILE"
        ;;
    shell)
        echo "🐚 Starting interactive shell..."
        exec /bin/bash
        ;;
    *)
        echo "🔐 Python-EST Server Docker Container"
        echo "Available commands:"
        echo "  start   - Start the EST server (default)"
        echo "  init    - Initialize server configuration"
        echo "  user    - Manage SRP users"
        echo "  status  - Check server status"
        echo "  shell   - Interactive shell"
        echo ""
        echo "Environment variables:"
        echo "  EST_CONFIG        - Configuration file path (default: /app/config.yaml)"
        echo "  EST_ADMIN_PASSWORD - Admin user password (default: admin123)"
        echo "  EST_TEST_PASSWORD  - Test user password (default: testpass123)"
        exec "$@"
        ;;
esac