#!/usr/bin/env python3
"""
Certificate setup script for Python-EST
Generates development certificates for testing
"""
import os
import subprocess

def run_command(cmd):
    """Run shell command"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    return True

def setup_certificates():
    """Setup development certificates"""
    print("Setting up development certificates...")
    print("WARNING: This generates private keys for development only!")
    print("Do not use these certificates in production!")
    
    # Create certs directory
    os.makedirs('certs', exist_ok=True)
    os.makedirs('certs/issued', exist_ok=True)
    
    # Generate CA key and certificate
    print("\nGenerating CA certificate...")
    ca_commands = [
        'openssl genrsa -out certs/ca-key.pem 4096',
        'openssl req -new -x509 -key certs/ca-key.pem -out certs/ca-cert.pem -days 3650 -subj "/C=US/ST=CA/L=Test/O=Test CA/CN=Python-EST Root CA"',
        'openssl genrsa -out certs/server.key 2048',
        'openssl req -new -key certs/server.key -out certs/server.csr -subj "/C=US/ST=CA/L=Test/O=Test/CN=localhost"',
        'openssl x509 -req -in certs/server.csr -CA certs/ca-cert.pem -CAkey certs/ca-key.pem -CAcreateserial -out certs/server.crt -days 365',
        'openssl genrsa -out certs/client.key 2048',
        'openssl req -new -key certs/client.key -out certs/client.csr -subj "/C=US/ST=CA/L=Test/O=Test/CN=TestClient"',
        'openssl x509 -req -in certs/client.csr -CA certs/ca-cert.pem -CAkey certs/ca-key.pem -CAcreateserial -out certs/client.crt -days 365'
    ]
    
    for cmd in ca_commands:
        if not run_command(cmd):
            return False
    
    print("\n[OK] Certificates generated successfully!")
    print("Files created:")
    print("   - certs/ca-cert.pem (CA Certificate)")
    print("   - certs/ca-key.pem (CA Private Key)")
    print("   - certs/server.crt (Server Certificate)")
    print("   - certs/server.key (Server Private Key)")
    print("   - certs/client.crt (Client Certificate)")
    print("   - certs/client.key (Client Private Key)")
    print("\nSECURITY NOTE:")
    print("   These are development certificates only!")
    print("   Private keys are stored locally and excluded from git.")
    return True

if __name__ == '__main__':
    setup_certificates()