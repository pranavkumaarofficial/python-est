#!/usr/bin/env python3
"""
Test script to verify IQE mode (DER response format) works correctly.
"""

import asyncio
import base64
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509.oid import NameOID

from src.python_est.config import ESTConfig, CAConfig, TLSConfig
from src.python_est.ca import CertificateAuthority


async def test_der_mode():
    """Test that DER mode returns raw binary (not base64)."""
    print("=" * 60)
    print("TEST 1: DER Mode (IQE Compatibility)")
    print("=" * 60)

    # Create config with DER response format
    config = ESTConfig(
        response_format="der",  #  IQE mode
        tls=TLSConfig(
            cert_file=Path("certs/server.crt"),
            key_file=Path("certs/server.key")
        ),
        ca=CAConfig(
            ca_cert=Path("certs/ca-cert.pem"),
            ca_key=Path("certs/ca-key.pem")
        )
    )

    # Initialize CA
    ca = CertificateAuthority(config.ca)

    # Test 1: Get CA certificates
    print("\n[TEST] Test 1a: get_ca_certificates_pkcs7(encode_base64=False)")
    ca_certs = await ca.get_ca_certificates_pkcs7(encode_base64=False)

    if isinstance(ca_certs, bytes):
        print("  [PASS] Returned bytes (raw DER) - CORRECT for IQE")
        print(f"  [INFO] Length: {len(ca_certs)} bytes")
        print(f"  [INFO] First 20 bytes (hex): {ca_certs[:20].hex()}")

        # Verify it's valid PKCS#7
        try:
            certs = pkcs7.load_der_pkcs7_certificates(ca_certs)
            print(f"  [PASS] Valid PKCS#7 structure with {len(certs)} certificate(s)")
            print(f"  [INFO] Certificate subject: {certs[0].subject.rfc4514_string()}")
        except Exception as e:
            print(f"  [FAIL] Failed to parse PKCS#7: {e}")
            return False
    else:
        print(f"  [FAIL] Returned {type(ca_certs)} instead of bytes - WRONG")
        return False

    # Test 2: Bootstrap enrollment
    print("\n[TEST] Test 1b: bootstrap_enrollment(encode_base64=False)")

    # Generate test CSR
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "test-pump-001"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Hospital"),
    ])).sign(private_key, hashes.SHA256())

    csr_pem = csr.public_bytes(serialization.Encoding.PEM)

    result = await ca.bootstrap_enrollment(csr_pem, "test-user", encode_base64=False)

    if isinstance(result.certificate_pkcs7, bytes):
        print("  [PASS] Returned bytes (raw DER) - CORRECT for IQE")
        print(f"   Length: {len(result.certificate_pkcs7)} bytes")
        print(f"   First 20 bytes (hex): {result.certificate_pkcs7[:20].hex()}")

        # Verify it's valid PKCS#7
        try:
            certs = pkcs7.load_der_pkcs7_certificates(result.certificate_pkcs7)
            print(f"  [PASS] Valid PKCS#7 structure with {len(certs)} certificate(s)")
            print(f"   Certificate CN: {certs[0].subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value}")
            print(f"   Serial number: {result.serial_number}")
        except Exception as e:
            print(f"  [FAIL] Failed to parse PKCS#7: {e}")
            return False
    else:
        print(f"  [FAIL] Returned {type(result.certificate_pkcs7)} instead of bytes - WRONG")
        return False

    print("\n[PASS] DER Mode Test PASSED - IQE compatibility confirmed!")
    return True


async def test_base64_mode():
    """Test that base64 mode returns base64-encoded string (RFC 7030)."""
    print("\n" + "=" * 60)
    print("TEST 2: Base64 Mode (RFC 7030 Compliance)")
    print("=" * 60)

    # Create config with base64 response format (default)
    config = ESTConfig(
        response_format="base64",  #  RFC 7030 mode
        tls=TLSConfig(
            cert_file=Path("certs/server.crt"),
            key_file=Path("certs/server.key")
        ),
        ca=CAConfig(
            ca_cert=Path("certs/ca-cert.pem"),
            ca_key=Path("certs/ca-key.pem")
        )
    )

    # Initialize CA
    ca = CertificateAuthority(config.ca)

    # Test: Get CA certificates
    print("\n Test 2a: get_ca_certificates_pkcs7(encode_base64=True)")
    ca_certs = await ca.get_ca_certificates_pkcs7(encode_base64=True)

    if isinstance(ca_certs, str):
        print("  [PASS] Returned string (base64) - CORRECT for RFC 7030")
        print(f"   Length: {len(ca_certs)} characters")
        print(f"   First 50 chars: {ca_certs[:50]}...")

        # Verify it's valid base64
        try:
            der_bytes = base64.b64decode(ca_certs)
            certs = pkcs7.load_der_pkcs7_certificates(der_bytes)
            print(f"  [PASS] Valid base64-encoded PKCS#7 with {len(certs)} certificate(s)")
            print(f"   Certificate subject: {certs[0].subject.rfc4514_string()}")
        except Exception as e:
            print(f"  [FAIL] Failed to decode/parse: {e}")
            return False
    else:
        print(f"  [FAIL] Returned {type(ca_certs)} instead of str - WRONG")
        return False

    # Test 2: Bootstrap enrollment
    print("\n Test 2b: bootstrap_enrollment(encode_base64=True)")

    # Generate test CSR
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "standard-client-001"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Standard Org"),
    ])).sign(private_key, hashes.SHA256())

    csr_pem = csr.public_bytes(serialization.Encoding.PEM)

    result = await ca.bootstrap_enrollment(csr_pem, "standard-user", encode_base64=True)

    if isinstance(result.certificate_pkcs7, str):
        print("  [PASS] Returned string (base64) - CORRECT for RFC 7030")
        print(f"   Length: {len(result.certificate_pkcs7)} characters")
        print(f"   First 50 chars: {result.certificate_pkcs7[:50]}...")

        # Verify it's valid base64
        try:
            der_bytes = base64.b64decode(result.certificate_pkcs7)
            certs = pkcs7.load_der_pkcs7_certificates(der_bytes)
            print(f"  [PASS] Valid base64-encoded PKCS#7 with {len(certs)} certificate(s)")
            print(f"   Certificate CN: {certs[0].subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value}")
            print(f"   Serial number: {result.serial_number}")
        except Exception as e:
            print(f"  [FAIL] Failed to decode/parse: {e}")
            return False
    else:
        print(f"  [FAIL] Returned {type(result.certificate_pkcs7)} instead of str - WRONG")
        return False

    print("\n[PASS] Base64 Mode Test PASSED - RFC 7030 compliance confirmed!")
    return True


async def main():
    """Run all tests."""
    print("\n")
    print("=" * 60)
    print("     IQE Gateway Support - Functionality Tests")
    print("=" * 60)
    print()

    # Run tests
    der_passed = await test_der_mode()
    base64_passed = await test_base64_mode()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"DER Mode (IQE):         {'[PASS] PASSED' if der_passed else '[FAIL] FAILED'}")
    print(f"Base64 Mode (RFC 7030): {'[PASS] PASSED' if base64_passed else '[FAIL] FAILED'}")
    print()

    if der_passed and base64_passed:
        print("SUCCESS: ALL TESTS PASSED! IQE gateway support is working correctly.")
        print()
        print("Next steps:")
        print("  1. Start server: python est_server.py --config config-iqe.yaml")
        print("  2. Test with curl (see IQE_INTEGRATION.md)")
        print("  3. Coordinate with IQE team for integration testing")
        return 0
    else:
        print("FAILURE: SOME TESTS FAILED! Review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
