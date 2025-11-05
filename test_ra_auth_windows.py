#!/usr/bin/env python3
"""
Test RA Certificate Authentication on Windows
"""
import requests
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

print("=" * 60)
print("Testing EST Server RA Authentication")
print("=" * 60)

# 1. Test health endpoint
print("\n[1/4] Testing health endpoint...")
try:
    response = requests.get("https://localhost:8445/health", verify=False)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200
    print("   ✅ Health check passed")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

# 2. Test CA certs endpoint
print("\n[2/4] Testing CA certificates endpoint...")
try:
    response = requests.get("https://localhost:8445/.well-known/est/cacerts", verify=False)
    print(f"   Status: {response.status_code}")
    print(f"   Response length: {len(response.content)} bytes")
    print(f"   Content type: {response.headers.get('Content-Type')}")
    assert response.status_code == 200
    print("   ✅ CA certs endpoint passed")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

# 3. Generate test CSR
print("\n[3/4] Generating test CSR...")
try:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, 'US'),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'Hospital'),
        x509.NameAttribute(NameOID.COMMON_NAME, 'test-device-windows'),
    ])).sign(key, hashes.SHA256())

    csr_der = csr.public_bytes(serialization.Encoding.DER)
    print(f"   CSR size: {len(csr_der)} bytes")
    print("   ✅ CSR generated")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

# 4. Test RA authentication with client certificate
print("\n[4/4] Testing RA certificate authentication...")
try:
    response = requests.post(
        "https://localhost:8445/.well-known/est/simpleenroll",
        data=csr_der,
        headers={"Content-Type": "application/pkcs10"},
        cert=("certs/iqe-ra-cert.pem", "certs/iqe-ra-key.pem"),
        verify=False
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response length: {len(response.content)} bytes")
    print(f"   Content type: {response.headers.get('Content-Type')}")

    if response.status_code == 200:
        print("   ✅ RA authentication SUCCESS!")
        print(f"   Received certificate (PKCS#7): {len(response.content)} bytes")

        # Save the response
        with open("device-cert.p7", "wb") as f:
            f.write(response.content)
        print("   📄 Saved to: device-cert.p7")
    else:
        print(f"   ❌ Failed with status {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        exit(1)

except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print("\nRA Certificate Authentication is working correctly!")
print("The EST server is ready for IQE integration.")
