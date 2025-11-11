#!/usr/bin/env python3
"""
Quick script to create IQE gateway user without interactive prompts.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from python_est.auth import SRPAuthenticator
from python_est.config import SRPConfig

async def main():
    """Create IQE gateway user."""
    print("=" * 60)
    print("Creating IQE Gateway Bootstrap User")
    print("=" * 60)

    # Configuration
    username = "iqe-gateway"
    password = "iqe-secure-password-2024"  # Change this if you want

    # Create SRP config
    config = SRPConfig(
        enabled=True,
        user_db=Path("certs/srp_users.db")
    )

    # Initialize authenticator
    auth = SRPAuthenticator(config)

    try:
        # Add user (async)
        await auth.add_user(username, password)

        print()
        print(f"[SUCCESS] User created successfully!")
        print()
        print("Bootstrap Credentials for IQE Team:")
        print("=" * 60)
        print(f"Username: {username}")
        print(f"Password: {password}")
        print("=" * 60)
        print()
        print("IMPORTANT: Save these credentials securely!")
        print("You will need to provide these to the IQE team.")
        print()
        print("User database: certs/srp_users.db.*")
        print()
        print("To change the password later, run:")
        print("  python create_iqe_user.py")
        print("and edit the 'password' variable in the script.")
        print()

    except Exception as e:
        print(f"[ERROR] Failed to create user: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
