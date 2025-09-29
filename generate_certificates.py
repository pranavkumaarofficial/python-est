#!/usr/bin/env python3
"""
Certificate Setup Script for Python-EST Server

This script generates all required certificates for a fresh installation.
Run this after cloning the repository and before starting the server.
"""

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta

def run_command(cmd, description=""):
    """Run a shell command and handle errors."""
    print(f"[INFO] {description}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {cmd}")
        print(f"[ERROR] {e.stderr}")
        return None

def check_openssl():
    """Check if OpenSSL is available."""
    result = run_command("openssl version", "Checking OpenSSL availability")
    if result:
        print(f"[OK] OpenSSL found: {result.strip()}")
        return True
    else:
        print("[ERROR] OpenSSL not found. Please install OpenSSL.")
        return False

def setup_directories():
    """Create required directories."""
    dirs = ["certs", "data", "certs/issued"]
    for directory in dirs:
        Path(directory).mkdir(exist_ok=True)
        print(f"[OK] Created directory: {directory}")

def generate_ca_certificate():
    """Generate Root CA certificate and private key."""
    print("\n=== Generating Root CA Certificate ===")

    # Generate CA private key
    ca_key_cmd = "openssl genrsa -out certs/ca-key.pem 4096"
    if not run_command(ca_key_cmd, "Generating CA private key (4096-bit RSA)"):
        return False

    # Generate CA certificate
    ca_cert_cmd = """openssl req -new -x509 -key certs/ca-key.pem -out certs/ca-cert.pem -days 3650 -subj "/C=US/ST=CA/L=San Francisco/O=Python-EST-CA/OU=Certificate Authority/CN=Python-EST Root CA/emailAddress=ca@python-est.local" """
    if not run_command(ca_cert_cmd, "Generating CA certificate (10 years validity)"):
        return False

    print("[OK] Root CA certificate generated successfully")
    return True

def generate_server_certificate():
    """Generate server certificate for TLS."""
    print("\n=== Generating Server Certificate ===")

    # Generate server private key
    server_key_cmd = "openssl genrsa -out certs/server.key 2048"
    if not run_command(server_key_cmd, "Generating server private key (2048-bit RSA)"):
        return False

    # Generate server certificate request
    server_csr_cmd = """openssl req -new -key certs/server.key -out certs/server.csr -subj "/C=US/ST=CA/L=San Francisco/O=Python-EST/OU=EST Server/CN=localhost/emailAddress=server@python-est.local" """
    if not run_command(server_csr_cmd, "Generating server certificate request"):
        return False

    # Sign server certificate with CA
    server_cert_cmd = "openssl x509 -req -in certs/server.csr -CA certs/ca-cert.pem -CAkey certs/ca-key.pem -CAcreateserial -out certs/server.crt -days 365 -extensions v3_req"
    if not run_command(server_cert_cmd, "Signing server certificate (1 year validity)"):
        return False

    print("[OK] Server certificate generated successfully")
    return True

def generate_client_certificate():
    """Generate sample client certificate for testing."""
    print("\n=== Generating Sample Client Certificate ===")

    # Generate client private key
    client_key_cmd = "openssl genrsa -out certs/client.key 2048"
    if not run_command(client_key_cmd, "Generating client private key (2048-bit RSA)"):
        return False

    # Generate client certificate request
    client_csr_cmd = """openssl req -new -key certs/client.key -out certs/client.csr -subj "/C=US/ST=CA/L=San Francisco/O=Python-EST/OU=Test Client/CN=test-client/emailAddress=client@python-est.local" """
    if not run_command(client_csr_cmd, "Generating client certificate request"):
        return False

    # Sign client certificate with CA
    client_cert_cmd = "openssl x509 -req -in certs/client.csr -CA certs/ca-cert.pem -CAkey certs/ca-key.pem -CAcreateserial -out certs/client.crt -days 365"
    if not run_command(client_cert_cmd, "Signing client certificate (1 year validity)"):
        return False

    print("[OK] Sample client certificate generated successfully")
    return True

def display_certificate_info():
    """Display information about generated certificates."""
    print("\n=== Certificate Information ===")

    # CA Certificate info
    ca_info_cmd = "openssl x509 -in certs/ca-cert.pem -text -noout | grep -E '(Subject:|Validity|Serial Number:)'"
    ca_info = run_command(ca_info_cmd, "CA Certificate Details")
    if ca_info:
        print("CA Certificate:")
        print(ca_info)

    # Server Certificate info
    server_info_cmd = "openssl x509 -in certs/server.crt -text -noout | grep -E '(Subject:|Validity|Serial Number:)'"
    server_info = run_command(server_info_cmd, "Server Certificate Details")
    if server_info:
        print("Server Certificate:")
        print(server_info)

def create_config_file():
    """Create config.yaml from example if it doesn't exist."""
    config_file = Path("config.yaml")
    example_file = Path("config.example.yaml")

    if not config_file.exists() and example_file.exists():
        print("\n=== Creating Configuration File ===")
        config_file.write_text(example_file.read_text())
        print("[OK] Created config.yaml from config.example.yaml")
    else:
        print("[INFO] config.yaml already exists or example not found")

def verify_setup():
    """Verify that all required files exist."""
    print("\n=== Verifying Setup ===")

    required_files = [
        "certs/ca-cert.pem",
        "certs/ca-key.pem",
        "certs/server.crt",
        "certs/server.key",
        "config.yaml"
    ]

    all_good = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"[OK] {file_path}")
        else:
            print(f"[MISSING] {file_path}")
            all_good = False

    return all_good

def main():
    """Main certificate setup function."""
    print("Python-EST Certificate Setup")
    print("=" * 40)
    print(f"Setup started at: {datetime.now()}")
    print()

    # Check prerequisites
    if not check_openssl():
        sys.exit(1)

    # Setup process
    setup_directories()

    if not generate_ca_certificate():
        print("[ERROR] Failed to generate CA certificate")
        sys.exit(1)

    if not generate_server_certificate():
        print("[ERROR] Failed to generate server certificate")
        sys.exit(1)

    if not generate_client_certificate():
        print("[ERROR] Failed to generate client certificate")
        sys.exit(1)

    display_certificate_info()
    create_config_file()

    if verify_setup():
        print("\n" + "=" * 40)
        print("[SUCCESS] Certificate setup completed!")
        print()
        print("Next steps:")
        print("1. Review config.yaml settings")
        print("2. Run: python test_server.py")
        print("3. Access: https://localhost:8445")
        print("4. Credentials: estuser / estpass123")
        print()
        print("Certificate validity:")
        print("- CA Certificate: 10 years")
        print("- Server Certificate: 1 year")
        print("- Client Certificate: 1 year")
    else:
        print("\n[ERROR] Setup verification failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()