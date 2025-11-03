#!/usr/bin/env python3
"""
Certificate Setup Script for Python-EST Server (Pure Python version)

This script generates all required certificates using Python's cryptography library.
Works on Windows without requiring OpenSSL configuration.
"""

import os
from pathlib import Path
from datetime import datetime, timedelta

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def setup_directories():
    """Create required directories."""
    print("\n=== Setting Up Directories ===")
    dirs = ["certs", "data", "certs/issued"]
    for directory in dirs:
        Path(directory).mkdir(exist_ok=True)
        print(f"[OK] Created directory: {directory}")


def generate_ca_certificate():
    """Generate Root CA certificate and private key."""
    print("\n=== Generating Root CA Certificate ===")

    # Generate CA private key
    print("[INFO] Generating CA private key (4096-bit RSA)...")
    ca_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )

    # Save CA private key
    with open("certs/ca-key.pem", "wb") as f:
        f.write(ca_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print("[OK] CA private key saved to: certs/ca-key.pem")

    # Generate CA certificate
    print("[INFO] Generating CA certificate (10 years validity)...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Test"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test CA"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Python-EST Root CA"),
    ])

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=3650))  # 10 years
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_private_key.public_key()),
            critical=False,
        )
        .sign(ca_private_key, hashes.SHA256())
    )

    # Save CA certificate
    with open("certs/ca-cert.pem", "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
    print("[OK] CA certificate saved to: certs/ca-cert.pem")

    return ca_private_key, ca_cert


def generate_server_certificate(ca_private_key, ca_cert):
    """Generate server certificate for TLS."""
    print("\n=== Generating Server Certificate ===")

    # Generate server private key
    print("[INFO] Generating server private key (2048-bit RSA)...")
    server_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Save server private key
    with open("certs/server.key", "wb") as f:
        f.write(server_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print("[OK] Server private key saved to: certs/server.key")

    # Generate server certificate
    print("[INFO] Generating server certificate (1 year validity)...")
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Test"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Python-EST Server"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    server_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(server_private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))  # 1 year
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
            ]),
            critical=True,
        )
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("127.0.0.1"),
            ]),
            critical=False,
        )
        .sign(ca_private_key, hashes.SHA256())
    )

    # Save server certificate
    with open("certs/server.crt", "wb") as f:
        f.write(server_cert.public_bytes(serialization.Encoding.PEM))
    print("[OK] Server certificate saved to: certs/server.crt")

    return server_cert


def generate_client_certificate(ca_private_key, ca_cert):
    """Generate sample client certificate for testing."""
    print("\n=== Generating Sample Client Certificate ===")

    # Generate client private key
    print("[INFO] Generating client private key (2048-bit RSA)...")
    client_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Save client private key
    with open("certs/client.key", "wb") as f:
        f.write(client_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print("[OK] Client private key saved to: certs/client.key")

    # Generate client certificate
    print("[INFO] Generating client certificate (1 year validity)...")
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Test"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Python-EST Client"),
        x509.NameAttribute(NameOID.COMMON_NAME, "test-client"),
    ])

    client_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(client_private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))  # 1 year
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        )
        .sign(ca_private_key, hashes.SHA256())
    )

    # Save client certificate
    with open("certs/client.crt", "wb") as f:
        f.write(client_cert.public_bytes(serialization.Encoding.PEM))
    print("[OK] Client certificate saved to: certs/client.crt")

    return client_cert


def display_certificate_info(ca_cert, server_cert, client_cert):
    """Display information about generated certificates."""
    print("\n=== Certificate Information ===")

    print("\nCA Certificate:")
    print(f"  Subject: {ca_cert.subject.rfc4514_string()}")
    print(f"  Serial: {ca_cert.serial_number}")
    print(f"  Valid from: {ca_cert.not_valid_before}")
    print(f"  Valid until: {ca_cert.not_valid_after}")

    print("\nServer Certificate:")
    print(f"  Subject: {server_cert.subject.rfc4514_string()}")
    print(f"  Serial: {server_cert.serial_number}")
    print(f"  Valid from: {server_cert.not_valid_before}")
    print(f"  Valid until: {server_cert.not_valid_after}")

    print("\nClient Certificate:")
    print(f"  Subject: {client_cert.subject.rfc4514_string()}")
    print(f"  Serial: {client_cert.serial_number}")
    print(f"  Valid from: {client_cert.not_valid_before}")
    print(f"  Valid until: {client_cert.not_valid_after}")


def verify_setup():
    """Verify that all required files exist."""
    print("\n=== Verifying Setup ===")

    required_files = [
        "certs/ca-cert.pem",
        "certs/ca-key.pem",
        "certs/server.crt",
        "certs/server.key",
        "certs/client.crt",
        "certs/client.key",
    ]

    all_good = True
    for file_path in required_files:
        if Path(file_path).exists():
            size = Path(file_path).stat().st_size
            print(f"[OK] {file_path} ({size} bytes)")
        else:
            print(f"[MISSING] {file_path}")
            all_good = False

    return all_good


def main():
    """Main certificate setup function."""
    print("=" * 60)
    print("Python-EST Certificate Setup (Pure Python)")
    print("=" * 60)
    print(f"Setup started at: {datetime.now()}")

    try:
        # Setup process
        setup_directories()

        # Generate certificates
        ca_private_key, ca_cert = generate_ca_certificate()
        server_cert = generate_server_certificate(ca_private_key, ca_cert)
        client_cert = generate_client_certificate(ca_private_key, ca_cert)

        # Display info
        display_certificate_info(ca_cert, server_cert, client_cert)

        # Verify
        if verify_setup():
            print("\n" + "=" * 60)
            print("[SUCCESS] Certificate setup completed!")
            print("=" * 60)
            print()
            print("Generated certificates:")
            print("  - certs/ca-cert.pem      (Root CA certificate)")
            print("  - certs/ca-key.pem       (Root CA private key)")
            print("  - certs/server.crt       (EST server certificate)")
            print("  - certs/server.key       (EST server private key)")
            print("  - certs/client.crt       (Test client certificate)")
            print("  - certs/client.key       (Test client private key)")
            print()
            print("Next steps:")
            print("  1. Start server: python est_server.py --config config-iqe.yaml")
            print("  2. Access dashboard: https://localhost:8445/")
            print("  3. Create bootstrap user: python -m python_est.cli add-user iqe-gateway")
            print()
            print("Certificate validity:")
            print("  - CA Certificate: 10 years")
            print("  - Server Certificate: 1 year")
            print("  - Client Certificate: 1 year")
            print()
        else:
            print("\n[ERROR] Setup verification failed!")
            return 1

    except Exception as e:
        print(f"\n[ERROR] Certificate generation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
