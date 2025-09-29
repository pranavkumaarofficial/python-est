#!/usr/bin/env python3
"""
Python EST Server - RFC 7030 Compliant Implementation

EST (Enrollment over Secure Transport) server providing certificate
enrollment services for IoT devices and enterprise environments.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from python_est.server import ESTServer
from python_est.config import ESTConfig

async def main():
    """Start the EST server."""
    try:
        # Load configuration
        config = ESTConfig.from_file("config.yaml")

        # Create and start server
        server = ESTServer(config)

        print("Starting Python EST Server (RFC 7030 Compliant)")
        print("=" * 50)
        print("Dashboard:        https://localhost:8445/")
        print("EST Bootstrap:    https://localhost:8445/.well-known/est/bootstrap")
        print("EST CA Certs:     https://localhost:8445/.well-known/est/cacerts")
        print("EST Enrollment:   https://localhost:8445/.well-known/est/simpleenroll")
        print("")
        print("Default credentials: estuser / estpass123")
        print("=" * 50)
        print("Press Ctrl+C to stop...")

        await server.start()

    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())