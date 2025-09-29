#!/usr/bin/env python3
"""
EST Client Demo

Demonstrates how to use the Python-EST client library for:
- CA certificate retrieval
- Bootstrap authentication
- Certificate enrollment
- Certificate re-enrollment
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from python_est import ESTClient, ESTError

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def demo_ca_certificates():
    """Demonstrate CA certificate retrieval."""
    print("\n" + "="*60)
    print("🔐 EST Demo: CA Certificate Retrieval")
    print("="*60)

    try:
        # Initialize client (no authentication required for /cacerts)
        client = ESTClient(
            server_url="https://localhost:8443",
            verify_ssl=False  # For development with self-signed certs
        )

        # Get CA certificates
        print("📥 Retrieving CA certificates...")
        ca_certs = await client.get_ca_certificates()

        print(f"✅ Successfully retrieved CA certificates ({len(ca_certs)} bytes)")
        print(f"📜 CA Certificates (first 200 chars):\n{ca_certs[:200]}...")

        # Save to file
        with open("ca_certificates.p7c", "w") as f:
            f.write(ca_certs)
        print("💾 Saved CA certificates to: ca_certificates.p7c")

    except ESTError as e:
        print(f"❌ EST Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")


async def demo_bootstrap_authentication():
    """Demonstrate bootstrap authentication process."""
    print("\n" + "="*60)
    print("🚀 EST Demo: Bootstrap Authentication")
    print("="*60)

    try:
        # Initialize client with SRP credentials
        client = ESTClient(
            server_url="https://localhost:8443",
            username="testuser",  # Default user from initialization
            password="testpass123",  # You'll be prompted to set this
            verify_ssl=False
        )

        # Perform bootstrap authentication
        print("🔑 Performing bootstrap authentication...")
        device_id = "demo-device-001"

        cert_pem, key_pem = await client.bootstrap_authenticate(device_id)

        print(f"✅ Bootstrap authentication successful for device: {device_id}")
        print(f"📜 Certificate (first 200 chars):\n{cert_pem[:200]}...")
        print(f"🔐 Private Key (first 100 chars):\n{key_pem[:100]}...")

        # Save certificate and key
        with open(f"{device_id}.crt", "w") as f:
            f.write(cert_pem)
        with open(f"{device_id}.key", "w") as f:
            f.write(key_pem)

        print(f"💾 Saved bootstrap certificate: {device_id}.crt")
        print(f"💾 Saved private key: {device_id}.key")

    except ESTError as e:
        print(f"❌ EST Error: {e}")
        print("💡 Make sure the server is running and SRP user exists:")
        print("   python-est user add testuser")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")


async def demo_certificate_enrollment():
    """Demonstrate certificate enrollment with CSR."""
    print("\n" + "="*60)
    print("📝 EST Demo: Certificate Enrollment")
    print("="*60)

    try:
        # Initialize client with SRP credentials
        client = ESTClient(
            server_url="https://localhost:8443",
            username="testuser",
            password="testpass123",
            verify_ssl=False
        )

        # Generate CSR and private key
        print("🔧 Generating Certificate Signing Request...")
        device_name = "demo-enrolled-device"
        csr_pem, private_key_pem = ESTClient.generate_csr(
            common_name=device_name,
            organization="EST Demo Organization",
            country="US"
        )

        print(f"✅ Generated CSR for: {device_name}")
        print(f"📝 CSR (first 200 chars):\n{csr_pem[:200]}...")

        # Save CSR and private key
        with open(f"{device_name}.csr", "w") as f:
            f.write(csr_pem)
        with open(f"{device_name}.key", "w") as f:
            f.write(private_key_pem)

        # Enroll certificate
        print("📤 Submitting enrollment request...")
        cert_pkcs7 = await client.enroll_certificate(csr_pem)

        print(f"✅ Certificate enrollment successful!")
        print(f"📜 Certificate PKCS#7 (first 200 chars):\n{cert_pkcs7[:200]}...")

        # Save enrolled certificate
        with open(f"{device_name}.p7c", "w") as f:
            f.write(cert_pkcs7)

        print(f"💾 Saved CSR: {device_name}.csr")
        print(f"💾 Saved private key: {device_name}.key")
        print(f"💾 Saved certificate: {device_name}.p7c")

    except ESTError as e:
        print(f"❌ EST Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")


async def demo_certificate_reenrollment():
    """Demonstrate certificate re-enrollment."""
    print("\n" + "="*60)
    print("🔄 EST Demo: Certificate Re-enrollment")
    print("="*60)

    try:
        # For re-enrollment, you would typically use client certificate authentication
        # For this demo, we'll use SRP authentication
        client = ESTClient(
            server_url="https://localhost:8443",
            username="testuser",
            password="testpass123",
            verify_ssl=False
        )

        # Generate new CSR for re-enrollment
        print("🔧 Generating new CSR for re-enrollment...")
        device_name = "demo-reenrolled-device"
        csr_pem, private_key_pem = ESTClient.generate_csr(
            common_name=device_name,
            organization="EST Demo Organization - Renewed",
            country="US"
        )

        print(f"✅ Generated renewal CSR for: {device_name}")

        # Re-enroll certificate
        print("🔄 Submitting re-enrollment request...")
        cert_pkcs7 = await client.reenroll_certificate(csr_pem)

        print(f"✅ Certificate re-enrollment successful!")
        print(f"📜 Renewed Certificate PKCS#7 (first 200 chars):\n{cert_pkcs7[:200]}...")

        # Save renewed certificate
        with open(f"{device_name}-renewed.csr", "w") as f:
            f.write(csr_pem)
        with open(f"{device_name}-renewed.key", "w") as f:
            f.write(private_key_pem)
        with open(f"{device_name}-renewed.p7c", "w") as f:
            f.write(cert_pkcs7)

        print(f"💾 Saved renewal files: {device_name}-renewed.*")

    except ESTError as e:
        print(f"❌ EST Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")


async def main():
    """Run all EST client demos."""
    print("🔐 Python-EST Client Library Demo")
    print("=" * 60)
    print("This demo shows how to use the EST client library for:")
    print("1. CA Certificate Retrieval")
    print("2. Bootstrap Authentication")
    print("3. Certificate Enrollment")
    print("4. Certificate Re-enrollment")
    print("\n⚠️  Make sure the EST server is running: python-est start")

    # Check if server is accessible
    try:
        client = ESTClient(server_url="https://localhost:8443", verify_ssl=False)
        await client.get_ca_certificates()
        print("✅ EST server is accessible at https://localhost:8443")
    except Exception as e:
        print(f"❌ Cannot connect to EST server: {e}")
        print("💡 Start the server first: python-est start")
        return

    # Run demos
    try:
        await demo_ca_certificates()
        await demo_bootstrap_authentication()
        await demo_certificate_enrollment()
        await demo_certificate_reenrollment()

        print("\n" + "="*60)
        print("🎉 EST Client Demo Completed Successfully!")
        print("="*60)
        print("📁 Generated files:")
        print("   - ca_certificates.p7c (CA certificates)")
        print("   - demo-device-001.crt/.key (Bootstrap certificate)")
        print("   - demo-enrolled-device.csr/.key/.p7c (Enrolled certificate)")
        print("   - demo-reenrolled-device-renewed.* (Re-enrolled certificate)")
        print("\n💡 Next steps:")
        print("   - Examine the generated certificates with: openssl x509 -in <file> -text")
        print("   - Use certificates for TLS client authentication")
        print("   - Integrate with your applications and devices")

    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        logger.exception("Demo failed with exception")


if __name__ == "__main__":
    asyncio.run(main())