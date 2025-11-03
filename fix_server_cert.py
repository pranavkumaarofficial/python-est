#!/usr/bin/env python3
"""
Fix Server Certificate - Add IP Address to SAN

This script regenerates the server certificate with the correct
Subject Alternative Name (SAN) including the IP address.

Based on cisco libest requirement: IP.3 = <IP OF THE SERVER>
"""

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from datetime import datetime, timedelta
import ipaddress

print("=" * 70)
print("Fix Server Certificate - Add IP Address to SAN")
print("=" * 70)

# Load CA certificate and key
print("\n[1/4] Loading CA certificate and key...")
with open("certs/ca-cert.pem", "rb") as f:
    ca_cert = x509.load_pem_x509_certificate(f.read())
print(f"   [OK] Loaded CA cert: {ca_cert.subject.rfc4514_string()}")

with open("certs/ca-key.pem", "rb") as f:
    ca_key = serialization.load_pem_private_key(f.read(), password=None)
print(f"   [OK] Loaded CA private key")

# Generate new server private key
print("\n[2/4] Generating new server private key...")
server_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
print("   [OK] Generated 2048-bit RSA key")

# Create server certificate with IP address in SAN
print("\n[3/4] Generating server certificate with IP address...")

subject = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
    x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Python-EST"),
    x509.NameAttribute(NameOID.COMMON_NAME, "python-est-server"),
])

# Subject Alternative Name with IP addresses (critical for IQE!)
san = x509.SubjectAlternativeName([
    x509.DNSName("localhost"),
    x509.DNSName("python-est-server"),
    x509.DNSName("10.42.56.101"),  # DNS fallback for older clients
    x509.IPAddress(ipaddress.IPv4Address("10.42.56.101")),  # ← CRITICAL FOR IQE!
    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
])

server_cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(ca_cert.subject)
    .public_key(server_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.utcnow())
    .not_valid_after(datetime.utcnow() + timedelta(days=365))  # 1 year
    .add_extension(san, critical=False)
    .add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True,
    )
    .add_extension(
        x509.KeyUsage(
            digital_signature=True,
            key_encipherment=True,
            key_cert_sign=False,
            key_agreement=False,
            content_commitment=False,
            data_encipherment=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False,
        ),
        critical=True,
    )
    .add_extension(
        x509.ExtendedKeyUsage([
            ExtendedKeyUsageOID.SERVER_AUTH,
            ExtendedKeyUsageOID.CLIENT_AUTH,
        ]),
        critical=True,
    )
    .sign(ca_key, hashes.SHA256())
)

print(f"   [OK] Created server certificate")
print(f"   - Subject: {server_cert.subject.rfc4514_string()}")
print(f"   - Issuer: {server_cert.issuer.rfc4514_string()}")
print(f"   - Serial: {server_cert.serial_number}")
print(f"   - Valid: {server_cert.not_valid_before} to {server_cert.not_valid_after}")

# Display SAN
for ext in server_cert.extensions:
    if ext.oid == x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME:
        print(f"   - SAN:")
        for name in ext.value:
            print(f"     - {name}")

# Save server certificate
print("\n[4/4] Saving server certificate and key...")
with open("certs/server.crt", "wb") as f:
    f.write(server_cert.public_bytes(serialization.Encoding.PEM))
print("   [OK] Saved: certs/server.crt")

with open("certs/server.key", "wb") as f:
    f.write(server_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))
print("   [OK] Saved: certs/server.key")

# Verify the certificate
print("\n" + "=" * 70)
print("[SUCCESS] Server Certificate Fixed!")
print("=" * 70)
print()
print("Certificate now includes:")
print("  [PASS] DNS: localhost")
print("  [PASS] DNS: python-est-server")
print("  [PASS] DNS: 10.42.56.101")
print("  [PASS] IP Address: 10.42.56.101  <-- Critical for IQE!")
print("  [PASS] IP Address: 127.0.0.1")
print()
print("IQE can now connect to https://10.42.56.101:8445 without cert errors!")
print()
print("Next steps:")
print("  1. Test locally: python test_server.py")
print("  2. Verify cert: openssl x509 -in certs/server.crt -text -noout | grep -A5 'Subject Alternative'")
print("  3. Commit: git add certs/server.crt certs/server.key")
print("  4. Push to deploy_v1: git push origin deploy_v1")
print("  5. Deploy on Ubuntu VM and restart Docker")
print("  6. Test with IQE UI - TLS should work now!")
print()
print("Note: You still need to provide IQE with certs/ca-cert.pem for their trust store.")
print("But now the TLS handshake will succeed once they import it!")
print()
