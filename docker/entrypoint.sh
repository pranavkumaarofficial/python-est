#!/bin/bash
set -e

echo "🔐 Starting Python-EST Server..."

# Configuration file path
CONFIG_FILE="${EST_CONFIG:-/app/config.yaml}"

# Check if configuration exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ ERROR: Configuration file not found at $CONFIG_FILE"
    echo "Please mount a config file to /app/config.yaml"
    exit 1
fi

# Start the server using CLI module
echo "🚀 Starting EST server with config: $CONFIG_FILE"
exec python -m python_est.cli start --config "$CONFIG_FILE"
