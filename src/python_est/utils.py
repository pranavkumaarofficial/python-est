"""
Utility Functions

Common utilities for EST protocol implementation.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(debug: bool = False, log_file: str = None) -> None:
    """Setup logging configuration with Rich formatting."""

    log_level = logging.DEBUG if debug else logging.INFO

    # Configure rich handler
    rich_handler = RichHandler(
        console=Console(stderr=True),
        show_time=True,
        show_path=debug,
        markup=True,
        rich_tracebacks=True
    )

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[rich_handler]
    )

    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logging.getLogger().addHandler(file_handler)

    # Set third-party loggers to WARNING to reduce noise
    if not debug:
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("fastapi").setLevel(logging.WARNING)


def create_directories(config_dict: Dict[str, Any]) -> None:
    """Create necessary directories from configuration."""

    directories_to_create = [
        "data",
        "certs",
        "logs"
    ]

    for directory in directories_to_create:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)


def validate_certificate_files(cert_file: Path, key_file: Path, ca_file: Path = None) -> bool:
    """Validate that required certificate files exist and are readable."""

    required_files = [cert_file, key_file]
    if ca_file:
        required_files.append(ca_file)

    for file_path in required_files:
        if not file_path.exists():
            logging.error(f"Certificate file not found: {file_path}")
            return False

        if not file_path.is_file():
            logging.error(f"Path is not a file: {file_path}")
            return False

        try:
            with open(file_path, 'rb') as f:
                content = f.read(100)  # Read first 100 bytes
                if not content:
                    logging.error(f"Certificate file is empty: {file_path}")
                    return False
        except Exception as e:
            logging.error(f"Cannot read certificate file {file_path}: {e}")
            return False

    return True


def generate_self_signed_cert(cert_file: Path, key_file: Path, common_name: str = "localhost") -> bool:
    """Generate self-signed certificate for development/testing."""

    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        from datetime import datetime, timedelta

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        # Create certificate subject and issuer (same for self-signed)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Development"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "EST"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Python-EST Development"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])

        # Create certificate
        certificate = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("127.0.0.1"),
            ]),
            critical=False,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        ).sign(private_key, hashes.SHA256())

        # Write private key
        with open(key_file, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        # Write certificate
        with open(cert_file, "wb") as f:
            f.write(certificate.public_bytes(serialization.Encoding.PEM))

        logging.info(f"Generated self-signed certificate: {cert_file}")
        logging.info(f"Generated private key: {key_file}")

        return True

    except Exception as e:
        logging.error(f"Failed to generate self-signed certificate: {e}")
        return False