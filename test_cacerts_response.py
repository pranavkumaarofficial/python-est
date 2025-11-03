#!/usr/bin/env python3
"""
Test /cacerts Response Format

This script tests if the /cacerts endpoint returns valid PKCS#7 that IQE can parse.
"""

import requests
import subprocess
import base64
from pathlib import Path

print("=" * 70)
print("Testing /cacerts Response Format")
print("=" * 70)

SERVER_URL = "https://10.42.56.101:8445"
CA_CERT = "certs/ca-cert.pem"

print(f"\n[1/5] Fetching /cacerts from {SERVER_URL}...")

try:
    response = requests.get(
        f"{SERVER_URL}/.well-known/est/cacerts",
        verify=False,  # Skip cert verification for testing
        timeout=10
    )

    print(f"   Status Code: {response.status_code}")
    print(f"   Content-Type: {response.headers.get('Content-Type')}")
    print(f"   Content-Transfer-Encoding: {response.headers.get('Content-Transfer-Encoding', 'Not set')}")
    print(f"   Response Size: {len(response.content)} bytes")

    if response.status_code != 200:
        print(f"   [ERROR] Expected 200, got {response.status_code}")
        exit(1)

except Exception as e:
    print(f"   [ERROR] Failed to fetch: {e}")
    exit(1)

# Save response
print("\n[2/5] Saving response...")
with open("test-cacerts.p7", "wb") as f:
    f.write(response.content)
print(f"   [OK] Saved to test-cacerts.p7")

# Check if it's base64 or DER
print("\n[3/5] Detecting format...")
is_base64 = False
try:
    # Try to decode as base64
    decoded = base64.b64decode(response.content)
    # If successful and looks like DER (starts with 0x30), it's base64
    if decoded[0:1] == b'\x30':
        is_base64 = True
        print(f"   [DETECTED] Base64-encoded PKCS#7")
        print(f"   [INFO] Decoded size: {len(decoded)} bytes")

        # Save decoded version
        with open("test-cacerts.der", "wb") as f:
            f.write(decoded)
        print(f"   [OK] Saved decoded DER to test-cacerts.der")
    else:
        print(f"   [DETECTED] Not base64 (decoded doesn't look like DER)")
        is_base64 = False
except:
    print(f"   [DETECTED] Raw DER (not base64)")
    is_base64 = False

# Test with openssl (exactly what IQE does!)
print("\n[4/5] Testing with openssl (IQE's method)...")

if is_base64:
    # IQE would first decode base64, then parse
    print("   [INFO] IQE will decode base64 first...")
    test_file = "test-cacerts.der"
else:
    test_file = "test-cacerts.p7"

# Run openssl command (same as IQE)
cmd = [
    "openssl", "pkcs7",
    "-inform", "DER",
    "-in", test_file,
    "-print_certs",
    "-out", "test-cacerts.pem"
]

print(f"   [CMD] {' '.join(cmd)}")
result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode == 0:
    print(f"   [SUCCESS] openssl parsed PKCS#7 successfully!")
    print(f"   [OK] Certificate extracted to test-cacerts.pem")

    # Show certificate
    with open("test-cacerts.pem", "r") as f:
        cert_pem = f.read()
    print(f"\n   Certificate Preview:")
    print(f"   " + "\n   ".join(cert_pem.split("\n")[:10]))

else:
    print(f"   [ERROR] openssl FAILED to parse PKCS#7!")
    print(f"   [ERROR] This is the same error IQE is getting!")
    print(f"\n   stdout: {result.stdout}")
    print(f"   stderr: {result.stderr}")

    if "unable to load PKCS7 object" in result.stderr:
        print(f"\n   ⚠️  EXACT SAME ERROR AS IQE LOGS!")
        print(f"   ⚠️  Your PKCS#7 response is malformed!")

# Final verdict
print("\n[5/5] Final Verdict...")
print("=" * 70)

if result.returncode == 0:
    print("[SUCCESS] Your /cacerts response is VALID!")
    print()
    print("✅ IQE should be able to parse it")
    print("✅ PKCS#7 structure is correct")
    print()
    if is_base64:
        print("Format: Base64-encoded PKCS#7 (RFC 7030 standard)")
        print("IQE will: Download → Decode base64 → Parse DER → Extract cert")
    else:
        print("Format: Raw DER PKCS#7")
        print("IQE will: Download → Parse DER → Extract cert")
    print()
    print("If IQE still fails, the problem is NOT your /cacerts endpoint!")
    print("Possible other issues:")
    print("  - TLS handshake failure (CA trust)")
    print("  - IQE downloading wrong URL")
    print("  - IQE internal bug")

else:
    print("[FAILURE] Your /cacerts response is INVALID!")
    print()
    print("❌ IQE cannot parse your PKCS#7 response")
    print("❌ This matches the error in IQE logs:")
    print("   'unable to load PKCS7 object'")
    print()
    print("Possible causes:")
    print("  1. PKCS#7 structure is corrupted")
    print("  2. Wrong serialization format")
    print("  3. Bug in cryptography library usage")
    print()
    print("Fix needed in: src/python_est/ca.py::_create_pkcs7_response()")

print("=" * 70)
