#!/usr/bin/env python3
"""
Test RA Certificate Authentication

This script tests that the EST server correctly accepts the RA certificate
for client authentication on the /simpleenroll endpoint.
"""

import requests
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

def test_ra_certificate_authentication():
    """Test that RA certificate can authenticate to /simpleenroll endpoint."""

    print("=" * 60)
    print("Testing RA Certificate Authentication")
    print("=" * 60)

    # Check files exist
    print("\n[1/5] Checking required files...")
    ra_cert_path = Path("certs/iqe-ra-cert.pem")
    ra_key_path = Path("certs/iqe-ra-key.pem")
    ca_cert_path = Path("certs/ca-cert.pem")

    if not ra_cert_path.exists():
        print(f"   [ERROR] {ra_cert_path} not found")
        print("   Run: python generate_ra_certificate.py")
        return False

    if not ra_key_path.exists():
        print(f"   [ERROR] {ra_key_path} not found")
        return False

    if not ca_cert_path.exists():
        print(f"   [ERROR] {ca_cert_path} not found")
        return False

    print(f"   [OK] RA certificate: {ra_cert_path}")
    print(f"   [OK] RA key: {ra_key_path}")
    print(f"   [OK] CA cert: {ca_cert_path}")

    # Generate a test CSR
    print("\n[2/5] Generating test CSR...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Hospital"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Medical Device Co"),
        x509.NameAttribute(NameOID.COMMON_NAME, "test-pump-ra-001"),
    ])).sign(private_key, hashes.SHA256())

    csr_der = csr.public_bytes(serialization.Encoding.DER)
    print(f"   [OK] Generated CSR for CN=test-pump-ra-001")
    print(f"   [OK] CSR size: {len(csr_der)} bytes")

    # Test /cacerts endpoint (no auth required)
    print("\n[3/5] Testing /cacerts endpoint...")
    try:
        response = requests.get(
            "https://localhost:8445/.well-known/est/cacerts",
            verify=str(ca_cert_path),
            timeout=10
        )
        if response.status_code == 200:
            print(f"   [OK] /cacerts returned {len(response.content)} bytes")
        else:
            print(f"   [WARN] /cacerts returned status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("   [WARN] Server not running at https://localhost:8445")
        print("   Start server with: python test_server.py")
        return False
    except Exception as e:
        print(f"   [ERROR] /cacerts failed: {e}")
        return False

    # Test /simpleenroll with RA certificate
    print("\n[4/5] Testing /simpleenroll with RA certificate...")
    try:
        response = requests.post(
            "https://localhost:8445/.well-known/est/simpleenroll",
            data=csr_der,
            headers={
                "Content-Type": "application/pkcs10",
            },
            cert=(str(ra_cert_path), str(ra_key_path)),  # Client cert authentication
            verify=str(ca_cert_path),
            timeout=10
        )

        print(f"   Status Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"   Response Size: {len(response.content)} bytes")

        if response.status_code == 200:
            print(f"   [OK] RA certificate authentication SUCCESSFUL!")
            print(f"   [OK] Received certificate in PKCS#7 format")
            return True
        elif response.status_code == 401:
            print(f"   [ERROR] Authentication failed")
            print(f"   Server rejected RA certificate")
            return False
        elif response.status_code == 500:
            print(f"   [ERROR] Server error")
            print(f"   Response: {response.text[:200]}")
            return False
        else:
            print(f"   [WARN] Unexpected status code: {response.status_code}")
            return False

    except Exception as e:
        print(f"   [ERROR] Request failed: {e}")
        return False

    print("\n[5/5] Verification complete")


if __name__ == "__main__":
    try:
        success = test_ra_certificate_authentication()

        if success:
            print("\n" + "=" * 60)
            print("[SUCCESS] RA Certificate Authentication Works!")
            print("=" * 60)
            print()
            print("Next steps:")
            print("1. Send these files to IQE team:")
            print("   - certs/ca-cert.pem (for their trust store)")
            print("   - certs/iqe-ra-cert.pem (RA certificate)")
            print("   - certs/iqe-ra-key.pem (RA private key - SECURE!)")
            print()
            print("2. IQE team should:")
            print("   - Import ca-cert.pem into their trust store")
            print("   - Upload RA cert/key to IQE UI")
            print("   - Configure EST endpoint: /simpleenroll (not /bootstrap)")
            print()
            print("3. Test enrollment through IQE UI")
            print()
        else:
            print("\n" + "=" * 60)
            print("[FAILED] RA Certificate Authentication Failed")
            print("=" * 60)
            print()
            print("Troubleshooting:")
            print("1. Make sure server is running: python test_server.py")
            print("2. Check server logs for errors")
            print("3. Verify RA certificate was generated correctly:")
            print("   openssl x509 -in certs/iqe-ra-cert.pem -text -noout")
            print()

        exit(0 if success else 1)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
