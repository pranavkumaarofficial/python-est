#!/usr/bin/env python3
"""
Test script to verify base64 CSR decoding works.
Simulates IQE UI sending base64-encoded CSR.
"""

import base64
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def test_base64_csr_decoding():
    """Test that base64 CSR can be decoded properly."""
    print("=" * 60)
    print("Test: Base64 CSR Decoding (IQE UI Simulation)")
    print("=" * 60)

    # Generate test CSR (like IQE UI would)
    print("\n1. Generating test CSR...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "iqe-test-pump-001"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Hospital"),
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
    ])).sign(private_key, hashes.SHA256())

    # Get DER format
    csr_der = csr.public_bytes(serialization.Encoding.DER)
    print(f"   CSR generated: {len(csr_der)} bytes (DER format)")

    # Base64 encode (like IQE UI does)
    csr_b64 = base64.b64encode(csr_der).decode('ascii')
    print(f"   Base64 encoded: {len(csr_b64)} characters")
    print(f"   First 50 chars: {csr_b64[:50]}...")

    # Simulate server receiving and decoding
    print("\n2. Simulating server-side base64 decoding...")
    try:
        # This is what the server does
        decoded_csr = base64.b64decode(csr_b64)
        print(f"   [PASS] Decoded {len(decoded_csr)} bytes")

        # Verify it's valid CSR
        parsed_csr = x509.load_der_x509_csr(decoded_csr)
        cn = parsed_csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        print(f"   [PASS] Valid CSR with CN: {cn}")

        # Check signature
        if parsed_csr.is_signature_valid:
            print(f"   [PASS] CSR signature valid")
        else:
            print(f"   [FAIL] CSR signature invalid")
            return False

    except Exception as e:
        print(f"   [FAIL] Decoding failed: {e}")
        return False

    # Save test files
    print("\n3. Saving test files...")
    with open("test_csr.der", "wb") as f:
        f.write(csr_der)
    print("   Saved: test_csr.der")

    with open("test_csr.b64", "w") as f:
        f.write(csr_b64)
    print("   Saved: test_csr.b64")

    with open("test_key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print("   Saved: test_key.pem")

    print("\n" + "=" * 60)
    print("[SUCCESS] Base64 CSR decoding works correctly!")
    print("=" * 60)
    print()
    print("Test curl command (with your credentials):")
    print()
    print("curl -vk -u iqe-gateway:iqe-secure-password-2024 \\")
    print("  -H 'Content-Type: application/pkcs10' \\")
    print("  -H 'Content-Transfer-Encoding: base64' \\")
    print("  --data @test_csr.b64 \\")
    print("  https://10.42.56.101:8445/.well-known/est/simpleenroll \\")
    print("  -o test_cert.p7")
    print()
    print("This simulates exactly what IQE UI does.")
    print()

    return True


if __name__ == "__main__":
    success = test_base64_csr_decoding()
    exit(0 if success else 1)
