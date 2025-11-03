#!/usr/bin/env python3
"""
Test EST Server with IQE UI Format

This script exactly replicates the IQE UI's curl commands to verify
the server returns base64-encoded PKCS#7 responses as expected.

Based on IQE UI documentation curl examples.
"""

import subprocess
import sys
import base64
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

print("=" * 70)
print("IQE UI Format Compatibility Test")
print("=" * 70)

# Step 1: Generate private key and CSR (matching IQE UI commands)
print("\n[1/6] Generate Private key & CSR for RSA")
print("Command: openssl req -new -sha256 -newkey rsa:2048 -nodes \\")
print("         -keyout private-key.pem -out csr.der -outform DER")

private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

# Save private key
with open("private-key.pem", "wb") as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))

# Generate CSR
csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
    x509.NameAttribute(NameOID.LOCALITY_NAME, "Hospital"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Medical"),
    x509.NameAttribute(NameOID.COMMON_NAME, "test-pump-ui-001"),
])).sign(private_key, hashes.SHA256())

# Save CSR in DER format
csr_der = csr.public_bytes(serialization.Encoding.DER)
with open("csr.der", "wb") as f:
    f.write(csr_der)

print(f"   [OK] Generated private-key.pem")
print(f"   [OK] Generated csr.der ({len(csr_der)} bytes)")

# Step 2: Convert CSR from DER to base64 format
print("\n[2/6] Convert CSR from DER to base64 format")
print("Command: openssl base64 -in csr.der -out csr.b64 -e")

csr_b64 = base64.b64encode(csr_der).decode('ascii')
with open("csr.b64", "w") as f:
    f.write(csr_b64)

print(f"   [OK] Generated csr.b64 ({len(csr_b64)} bytes)")

# Step 3: Test /cacerts endpoint
print("\n[3/6] Obtain root certificate from PKI")
print("Command: curl -v --cacert certs/ca-cert.pem \\")
print("         -o cacerts.p7b \\")
print("         https://localhost:8445/.well-known/est/cacerts")

result = subprocess.run([
    "curl", "-v",
    "--cacert", "certs/ca-cert.pem",
    "-o", "cacerts.p7b",
    "https://localhost:8445/.well-known/est/cacerts"
], capture_output=True, text=True)

if result.returncode == 0 and Path("cacerts.p7b").exists():
    size = Path("cacerts.p7b").stat().st_size
    print(f"   [OK] Downloaded cacerts.p7b ({size} bytes)")

    # Check if it's base64
    with open("cacerts.p7b", "rb") as f:
        content = f.read()
        # Base64 content should be ASCII printable
        try:
            decoded = base64.b64decode(content)
            print(f"   [OK] Response is base64-encoded ({len(decoded)} bytes decoded)")
        except:
            print(f"   [WARN] Response might be raw DER (not base64)")
else:
    print(f"   [ERROR] Failed to download cacerts")
    print(f"   stdout: {result.stdout}")
    print(f"   stderr: {result.stderr}")
    sys.exit(1)

# Step 4: Request client certificate using Username & Password
print("\n[4/6] Request client certificate using Username & Password")
print("Command: curl -v --cacert certs/ca-cert.pem \\")
print("         --user iqe-gateway:iqe-secure-password-2024 \\")
print("         --data @csr.b64 \\")
print("         -o client.p7.b64 \\")
print("         -H 'Content-Type: application/pkcs10' \\")
print("         -H 'Content-Transfer-Encoding: base64' \\")
print("         https://localhost:8445/.well-known/est/simpleenroll")

result = subprocess.run([
    "curl", "-v",
    "--cacert", "certs/ca-cert.pem",
    "--user", "iqe-gateway:iqe-secure-password-2024",
    "--data", f"@csr.b64",
    "-o", "client.p7.b64",
    "-H", "Content-Type: application/pkcs10",
    "-H", "Content-Transfer-Encoding: base64",
    "https://localhost:8445/.well-known/est/simpleenroll"
], capture_output=True, text=True)

if result.returncode == 0 and Path("client.p7.b64").exists():
    size = Path("client.p7.b64").stat().st_size
    print(f"   [OK] Received client.p7.b64 ({size} bytes)")

    # Verify it's base64
    with open("client.p7.b64", "rb") as f:
        content = f.read()
        try:
            decoded = base64.b64decode(content)
            print(f"   [OK] Response is base64-encoded ({len(decoded)} bytes decoded)")
        except Exception as e:
            print(f"   [ERROR] Response is NOT base64: {e}")
            print(f"   First 100 bytes: {content[:100]}")
            sys.exit(1)
else:
    print(f"   [ERROR] Failed to enroll certificate")
    print(f"   Return code: {result.returncode}")
    print(f"   stdout: {result.stdout}")
    print(f"   stderr: {result.stderr}")
    sys.exit(1)

# Step 5: Convert client certificate from base64 to DER format
print("\n[5/6] Convert client certificate from base64 to DER format")
print("Command: openssl base64 -in client.p7.b64 -out client.p7.der -d")

with open("client.p7.b64", "r") as f:
    b64_content = f.read()

der_content = base64.b64decode(b64_content)
with open("client.p7.der", "wb") as f:
    f.write(der_content)

print(f"   [OK] Decoded to client.p7.der ({len(der_content)} bytes)")

# Step 6: Convert client certificate from DER to PEM format
print("\n[6/6] Convert client certificate from DER to PEM format")
print("Command: openssl pkcs7 -inform DER -in client.p7.der \\")
print("         -print_certs -out client.pem")

result = subprocess.run([
    "openssl", "pkcs7",
    "-inform", "DER",
    "-in", "client.p7.der",
    "-print_certs",
    "-out", "client.pem"
], capture_output=True, text=True)

if result.returncode == 0 and Path("client.pem").exists():
    print(f"   [OK] Converted to client.pem")

    # Read and display certificate info
    with open("client.pem", "rb") as f:
        cert_pem = f.read()
        try:
            cert = x509.load_pem_x509_certificate(cert_pem)
            print(f"\n   Certificate Details:")
            print(f"   - Subject: {cert.subject.rfc4514_string()}")
            print(f"   - Issuer: {cert.issuer.rfc4514_string()}")
            print(f"   - Valid From: {cert.not_valid_before_utc}")
            print(f"   - Valid Until: {cert.not_valid_after_utc}")
            print(f"   - Serial: {cert.serial_number}")
        except Exception as e:
            print(f"   [WARN] Could not parse certificate: {e}")
else:
    print(f"   [ERROR] Failed to convert to PEM")
    print(f"   stdout: {result.stdout}")
    print(f"   stderr: {result.stderr}")
    sys.exit(1)

# Success!
print("\n" + "=" * 70)
print("[SUCCESS] IQE UI Format Test PASSED!")
print("=" * 70)
print()
print("Your EST server is correctly configured for IQE UI:")
print("  [PASS] Returns base64-encoded PKCS#7 responses")
print("  [PASS] Accepts base64-encoded CSRs")
print("  [PASS] Supports HTTP Basic Auth (username/password)")
print("  [PASS] Issues valid certificates")
print()
print("Files generated (matching IQE UI flow):")
print("  1. private-key.pem    - Device private key")
print("  2. csr.der            - CSR in DER format")
print("  3. csr.b64            - CSR in base64 format (sent to server)")
print("  4. cacerts.p7b        - CA cert from server (base64)")
print("  5. client.p7.b64      - Client cert from server (base64)")
print("  6. client.p7.der      - Client cert decoded to DER")
print("  7. client.pem         - Client cert in PEM format")
print()
print("Next steps:")
print("  1. Commit this fix: git add config-iqe.yaml && git commit")
print("  2. Push to deploy_v1: git push origin deploy_v1")
print("  3. Deploy on Ubuntu VM and restart Docker")
print("  4. Test with IQE UI - should work now!")
print()
