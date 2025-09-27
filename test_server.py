#!/usr/bin/env python3
"""
Test the updated EST server with new features
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from python_est.server import ESTServer
from python_est.config import ESTConfig

async def main():
    """Test the EST server."""
    try:
        # Load configuration
        config = ESTConfig.from_file("config.yaml")

        # Create and start server
        server = ESTServer(config)

        print("Starting EST Server with new features...")
        print("Server Stats: https://localhost:8445/")
        print("Bootstrap UI: https://localhost:8445/.well-known/est/bootstrap")
        print("Fixed credentials: estuser / estpass123")
        print("Features: Bootstrap -> Auto-Enrollment -> Complete!")
        print("")
        print("Press Ctrl+C to stop...")

        await server.start()

    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())