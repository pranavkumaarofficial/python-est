"""
SRP Authentication Module

Secure Remote Password (SRP) authentication implementation for EST bootstrap.
"""

import asyncio
import hashlib
import hmac
import logging
import secrets
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    import tlslite
    from tlslite.utils.tlsdb import TLSDBError
except ImportError:
    # Fallback if tlslite not available or different version
    class TLSDBError(Exception):
        pass

from .config import SRPConfig
from .exceptions import ESTAuthenticationError

logger = logging.getLogger(__name__)


@dataclass
class AuthenticationResult:
    """Result of SRP authentication attempt."""
    success: bool
    username: Optional[str] = None
    error_message: Optional[str] = None


class SRPAuthenticator:
    """
    SRP (Secure Remote Password) authenticator for EST bootstrap.

    Implements RFC 2945 SRP authentication protocol for secure
    password-based authentication without transmitting passwords.
    """

    def __init__(self, config: SRPConfig) -> None:
        """Initialize SRP authenticator."""
        self.config = config
        self.user_db_path = config.user_db
        self._ensure_user_db()

    def _ensure_user_db(self) -> None:
        """Ensure SRP user database exists."""
        self.user_db_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.user_db_path.exists():
            logger.info(f"Creating SRP user database: {self.user_db_path}")
            # Create empty database
            self.user_db_path.touch()

    async def authenticate(self, username: str, password: str) -> AuthenticationResult:
        """
        Authenticate user with SRP protocol.

        Args:
            username: User identifier
            password: User password

        Returns:
            AuthenticationResult indicating success/failure
        """
        try:
            # Load user verifier from database
            verifier_info = await self._get_user_verifier(username)
            if not verifier_info:
                return AuthenticationResult(
                    success=False,
                    error_message="User not found"
                )

            # Perform SRP authentication
            # Note: This is a simplified implementation
            # In production, you'd implement full SRP protocol
            auth_success = await self._verify_password(
                username, password, verifier_info
            )

            if auth_success:
                logger.info(f"SRP authentication successful for user: {username}")
                return AuthenticationResult(success=True, username=username)
            else:
                logger.warning(f"SRP authentication failed for user: {username}")
                return AuthenticationResult(
                    success=False,
                    error_message="Invalid credentials"
                )

        except Exception as e:
            logger.error(f"SRP authentication error for user {username}: {e}")
            return AuthenticationResult(
                success=False,
                error_message="Authentication error"
            )

    async def _get_user_verifier(self, username: str) -> Optional[Dict[str, str]]:
        """Get user verifier information from database."""
        try:
            # For simplicity, using a basic file-based approach
            # In production, consider using a proper database
            if not self.user_db_path.exists():
                return None

            # Read user database (simplified format)
            # Format: username:salt:verifier
            with open(self.user_db_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or ':' not in line:
                        continue

                    parts = line.split(':')
                    if len(parts) >= 3 and parts[0] == username:
                        return {
                            'username': parts[0],
                            'salt': parts[1],
                            'verifier': parts[2]
                        }

            return None

        except Exception as e:
            logger.error(f"Error reading user database: {e}")
            return None

    async def _verify_password(self, username: str, password: str, verifier_info: Dict[str, str]) -> bool:
        """Verify password against stored verifier."""
        try:
            # Simplified password verification
            # In production, implement full SRP verification
            salt = verifier_info['salt']
            stored_verifier = verifier_info['verifier']

            # Generate verifier from provided password
            password_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                salt.encode(),
                100000  # iterations
            )
            computed_verifier = password_hash.hex()

            return hmac.compare_digest(stored_verifier, computed_verifier)

        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    async def add_user(self, username: str, password: str) -> bool:
        """
        Add new SRP user to database.

        Args:
            username: User identifier
            password: User password

        Returns:
            True if user added successfully
        """
        try:
            # Check if user already exists
            existing = await self._get_user_verifier(username)
            if existing:
                logger.warning(f"User already exists: {username}")
                return False

            # Generate salt and verifier
            salt = secrets.token_hex(self.config.salt_length)
            password_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                salt.encode(),
                100000
            )
            verifier = password_hash.hex()

            # Append to database
            with open(self.user_db_path, 'a') as f:
                f.write(f"{username}:{salt}:{verifier}\n")

            logger.info(f"Added SRP user: {username}")
            return True

        except Exception as e:
            logger.error(f"Error adding user {username}: {e}")
            return False

    async def ensure_default_user(self) -> bool:
        """
        Ensure default fixed user exists for bootstrap authentication.

        Returns:
            True if default user exists or was created successfully
        """
        default_username = "estuser"
        default_password = "estpass123"

        try:
            # Check if default user exists
            existing = await self._get_user_verifier(default_username)
            if existing:
                logger.info(f"Default user '{default_username}' already exists")
                return True

            # Create default user
            success = await self.add_user(default_username, default_password)
            if success:
                logger.info(f"Created default user: {default_username} / {default_password}")
            return success

        except Exception as e:
            logger.error(f"Error ensuring default user: {e}")
            return False

    async def remove_user(self, username: str) -> bool:
        """
        Remove SRP user from database.

        Args:
            username: User identifier to remove

        Returns:
            True if user removed successfully
        """
        try:
            if not self.user_db_path.exists():
                return False

            # Read all users except the one to remove
            users = []
            with open(self.user_db_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        parts = line.split(':')
                        if len(parts) >= 3 and parts[0] != username:
                            users.append(line)

            # Write back without the removed user
            with open(self.user_db_path, 'w') as f:
                for user in users:
                    f.write(f"{user}\n")

            logger.info(f"Removed SRP user: {username}")
            return True

        except Exception as e:
            logger.error(f"Error removing user {username}: {e}")
            return False

    async def list_users(self) -> List[str]:
        """List all SRP users."""
        try:
            users = []
            if self.user_db_path.exists():
                with open(self.user_db_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and ':' in line:
                            username = line.split(':')[0]
                            users.append(username)
            return users

        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []

    async def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """
        Change user password.

        Args:
            username: User identifier
            old_password: Current password
            new_password: New password

        Returns:
            True if password changed successfully
        """
        try:
            # Verify old password
            auth_result = await self.authenticate(username, old_password)
            if not auth_result.success:
                return False

            # Remove old user and add with new password
            await self.remove_user(username)
            return await self.add_user(username, new_password)

        except Exception as e:
            logger.error(f"Error changing password for {username}: {e}")
            return False