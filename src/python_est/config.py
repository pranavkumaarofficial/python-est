"""
EST Server Configuration

Pydantic models for type-safe configuration management.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
import yaml


class TLSConfig(BaseModel):
    """TLS/SSL configuration."""

    cert_file: Path = Field(..., description="Path to server certificate file")
    key_file: Path = Field(..., description="Path to server private key file")
    ca_file: Optional[Path] = Field(None, description="Path to CA certificate file")
    min_version: str = Field("TLSv1.2", description="Minimum TLS version")
    max_version: str = Field("TLSv1.3", description="Maximum TLS version")
    ciphers: Optional[List[str]] = Field(None, description="Allowed cipher suites")

    @validator('cert_file', 'key_file', 'ca_file')
    def validate_file_exists(cls, v: Optional[Path]) -> Optional[Path]:
        if v and not v.exists():
            raise ValueError(f"File does not exist: {v}")
        return v


class SRPConfig(BaseModel):
    """SRP (Secure Remote Password) configuration."""

    enabled: bool = Field(True, description="Enable SRP authentication")
    user_db: Path = Field(Path("data/srp_users.db"), description="SRP user database path")
    salt_length: int = Field(32, description="Salt length in bytes")
    verifier_length: int = Field(256, description="Verifier length in bits")

    @validator('user_db')
    def validate_user_db_dir(cls, v: Path) -> Path:
        v.parent.mkdir(parents=True, exist_ok=True)
        return v


class CAConfig(BaseModel):
    """Certificate Authority configuration."""

    ca_cert: Path = Field(..., description="CA certificate file")
    ca_key: Path = Field(..., description="CA private key file")
    ca_key_password: Optional[str] = Field(None, description="CA key password")
    cert_validity_days: int = Field(365, description="Certificate validity in days")
    key_size: int = Field(2048, description="RSA key size for issued certificates")
    digest_algorithm: str = Field("sha256", description="Digest algorithm for signing")

    @validator('ca_cert', 'ca_key')
    def validate_ca_files(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"CA file does not exist: {v}")
        return v


class ServerConfig(BaseModel):
    """HTTP server configuration."""

    host: str = Field("0.0.0.0", description="Server bind address")
    port: int = Field(8443, description="Server port")
    workers: int = Field(1, description="Number of worker processes")
    reload: bool = Field(False, description="Auto-reload on code changes")
    access_log: bool = Field(True, description="Enable access logging")
    debug: bool = Field(False, description="Enable debug mode")


class ESTConfig(BaseModel):
    """Complete EST server configuration."""

    server: ServerConfig = Field(default_factory=ServerConfig)
    tls: TLSConfig
    srp: SRPConfig = Field(default_factory=SRPConfig)
    ca: CAConfig

    # EST-specific settings
    bootstrap_enabled: bool = Field(True, description="Enable bootstrap endpoint")
    bootstrap_path: str = Field("/.well-known/est/bootstrap", description="Bootstrap endpoint path")
    cacerts_path: str = Field("/.well-known/est/cacerts", description="CA certificates endpoint path")
    simpleenroll_path: str = Field("/.well-known/est/simpleenroll", description="Simple enrollment endpoint path")
    simplereenroll_path: str = Field("/.well-known/est/simplereenroll", description="Simple re-enrollment endpoint path")

    # Response format configuration (for gateway compatibility)
    response_format: str = Field(
        "base64",
        description="Response format: 'base64' (RFC 7030 compliant) or 'der' (raw binary for IQE gateway)"
    )

    # Security settings
    max_cert_lifetime_days: int = Field(365, description="Maximum certificate lifetime")
    require_client_cert: bool = Field(False, description="Require client certificates for non-bootstrap endpoints")
    rate_limit_enabled: bool = Field(True, description="Enable rate limiting")
    rate_limit_requests: int = Field(100, description="Rate limit: requests per window")
    rate_limit_window: int = Field(3600, description="Rate limit window in seconds")

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "ESTConfig":
        """Load configuration from YAML file."""
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data)

    def to_file(self, config_path: Union[str, Path]) -> None:
        """Save configuration to YAML file."""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            yaml.dump(self.dict(), f, default_flow_style=False, indent=2)

    @classmethod
    def create_default(cls,
                      cert_file: Path,
                      key_file: Path,
                      ca_cert: Path,
                      ca_key: Path) -> "ESTConfig":
        """Create default configuration with required certificate files."""
        return cls(
            tls=TLSConfig(cert_file=cert_file, key_file=key_file),
            ca=CAConfig(ca_cert=ca_cert, ca_key=ca_key)
        )