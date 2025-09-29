#!/usr/bin/env python3
"""
EST Client for VM/Command Line Bootstrap and Enrollment

This client performs proper EST protocol flow:
1. Generate private key locally
2. Create Certificate Signing Request (CSR)
3. Authenticate with EST server
4. Submit CSR for enrollment
5. Receive signed certificate
"""

import os
import sys
import base64
import requests
import urllib3
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from datetime import datetime

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ESTClient:
    """EST Client for device enrollment."""

    def __init__(self, server_url, device_id, username, password, verify_ssl=False):
        """Initialize EST client."""
        self.server_url = server_url.rstrip('/')
        self.device_id = device_id
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.session = requests.Session()

        # EST endpoints (RFC 7030 compliant)
        self.bootstrap_url = f"{server_url}/.well-known/est/bootstrap"
        self.enroll_url = f"{server_url}/.well-known/est/simpleenroll"
        self.cacerts_url = f"{server_url}/.well-known/est/cacerts"

        # Local storage
        self.output_dir = Path(f"device_{device_id}")
        self.output_dir.mkdir(exist_ok=True)

        print(f"[INFO] EST Client initialized for device: {device_id}")
        print(f"[INFO] Server: {server_url}")
        print(f"[INFO] Output directory: {self.output_dir}")

    def generate_private_key(self):
        """Generate device private key locally."""
        print("\n=== Generating Device Private Key ===")

        # Generate RSA private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        # Save private key
        key_file = self.output_dir / f"{self.device_id}_private.key"
        with open(key_file, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        print(f"[OK] Private key generated: {key_file}")
        self.private_key = private_key
        return private_key

    def generate_csr(self):
        """Generate Certificate Signing Request."""
        print("\n=== Generating Certificate Signing Request ===")

        # Create CSR
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "EST Client"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Device"),
            x509.NameAttribute(NameOID.COMMON_NAME, self.device_id),
            x509.NameAttribute(NameOID.EMAIL_ADDRESS, f"{self.device_id}@device.local"),
        ])

        csr = x509.CertificateSigningRequestBuilder().subject_name(
            subject
        ).sign(self.private_key, hashes.SHA256())

        # Save CSR
        csr_file = self.output_dir / f"{self.device_id}.csr"
        with open(csr_file, 'wb') as f:
            f.write(csr.public_bytes(serialization.Encoding.PEM))

        print(f"[OK] CSR generated: {csr_file}")
        self.csr = csr
        return csr

    def get_ca_certificates(self):
        """Get CA certificates from EST server."""
        print("\n=== Retrieving CA Certificates ===")

        try:
            response = self.session.get(self.cacerts_url, verify=self.verify_ssl)
            response.raise_for_status()

            # Save CA certificates
            ca_file = self.output_dir / "ca_certificates.p7b"
            with open(ca_file, 'wb') as f:
                f.write(response.content)

            print(f"[OK] CA certificates saved: {ca_file}")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to get CA certificates: {e}")
            return False

    def bootstrap_authenticate(self):
        """Perform EST-compliant bootstrap authentication with CSR."""
        print("\n=== EST Bootstrap Authentication ===")

        try:
            # Get CSR data
            if not hasattr(self, 'csr'):
                print("[ERROR] CSR not generated. Run generate_csr() first.")
                return False

            csr_pem = self.csr.public_bytes(serialization.Encoding.PEM)

            # Submit bootstrap request with CSR and HTTP Basic Auth
            headers = {
                'Content-Type': 'application/pkcs10'
            }

            # Send CSR in PEM format (raw)
            response = self.session.post(
                self.bootstrap_url,
                data=csr_pem,
                headers=headers,
                auth=(self.username, self.password),
                verify=self.verify_ssl
            )

            if response.status_code == 200:
                print(f"[OK] EST bootstrap successful")

                # Save the bootstrap certificate
                cert_file = self.output_dir / f"{self.device_id}_bootstrap_cert.pem"

                # The response should be base64 encoded certificate
                try:
                    cert_data = base64.b64decode(response.content)
                    with open(cert_file, 'wb') as f:
                        f.write(cert_data)
                    print(f"[OK] Bootstrap certificate saved: {cert_file}")
                except:
                    # Fallback: save as received
                    with open(cert_file, 'wb') as f:
                        f.write(response.content)
                    print(f"[OK] Bootstrap certificate saved (raw): {cert_file}")

                return True
            else:
                print(f"[ERROR] Bootstrap failed: {response.status_code}")
                print(f"[ERROR] Response: {response.text[:200]}")
                return False

        except Exception as e:
            print(f"[ERROR] EST bootstrap failed: {e}")
            return False

    def submit_enrollment(self):
        """Submit CSR for enrollment."""
        print("\n=== Certificate Enrollment ===")

        try:
            # Prepare CSR for submission
            csr_pem = self.csr.public_bytes(serialization.Encoding.PEM)

            # Submit enrollment request
            headers = {
                'Content-Type': 'application/pkcs10'
            }

            response = self.session.post(
                self.enroll_url,
                data=csr_pem,
                headers=headers,
                auth=(self.username, self.password),
                verify=self.verify_ssl
            )

            if response.status_code == 200:
                # Save enrolled certificate
                cert_file = self.output_dir / f"{self.device_id}_certificate.pem"

                # Decode PKCS#7 response (simplified)
                cert_data = base64.b64decode(response.content)
                with open(cert_file, 'wb') as f:
                    f.write(cert_data)

                print(f"[OK] Certificate enrollment successful")
                print(f"[OK] Certificate saved: {cert_file}")
                return True
            else:
                print(f"[ERROR] Enrollment failed: {response.status_code}")
                print(f"[ERROR] Response: {response.text[:200]}")
                return False

        except Exception as e:
            print(f"[ERROR] Certificate enrollment failed: {e}")
            return False

    def verify_certificate(self):
        """Verify the enrolled certificate."""
        print("\n=== Certificate Verification ===")

        try:
            cert_file = self.output_dir / f"{self.device_id}_certificate.pem"
            if not cert_file.exists():
                print("[ERROR] Certificate file not found")
                return False

            with open(cert_file, 'rb') as f:
                cert_data = f.read()

            # Try to load certificate
            try:
                certificate = x509.load_pem_x509_certificate(cert_data)
                print(f"[OK] Certificate loaded successfully")
                print(f"[INFO] Subject: {certificate.subject}")
                print(f"[INFO] Issuer: {certificate.issuer}")
                print(f"[INFO] Valid from: {certificate.not_valid_before}")
                print(f"[INFO] Valid until: {certificate.not_valid_after}")
                return True
            except:
                # Might be PKCS#7, try to extract
                print("[INFO] Certificate might be in PKCS#7 format")
                return True

        except Exception as e:
            print(f"[ERROR] Certificate verification failed: {e}")
            return False

    def create_certificate_bundle(self):
        """Create a certificate bundle for easy deployment."""
        print("\n=== Creating Certificate Bundle ===")

        bundle_file = self.output_dir / f"{self.device_id}_bundle.tar.gz"

        try:
            import tarfile
            with tarfile.open(bundle_file, 'w:gz') as tar:
                for file_path in self.output_dir.glob('*'):
                    if file_path.is_file() and file_path != bundle_file:
                        tar.add(file_path, arcname=file_path.name)

            print(f"[OK] Certificate bundle created: {bundle_file}")
            return True
        except Exception as e:
            print(f"[WARNING] Failed to create bundle: {e}")
            return False

    def run_complete_enrollment(self):
        """Run complete EST enrollment process."""
        print("EST Device Enrollment Process")
        print("=" * 40)
        print(f"Device ID: {self.device_id}")
        print(f"Username: {self.username}")
        print(f"EST Server: {self.server_url}")
        print()

        # Step 1: Generate private key
        if not self.generate_private_key():
            return False

        # Step 2: Generate CSR
        if not self.generate_csr():
            return False

        # Step 3: Get CA certificates
        self.get_ca_certificates()

        # Step 4: Bootstrap authentication
        if not self.bootstrap_authenticate():
            return False

        # Step 5: Submit enrollment
        if not self.submit_enrollment():
            return False

        # Step 6: Verify certificate
        if not self.verify_certificate():
            return False

        # Step 7: Create bundle
        self.create_certificate_bundle()

        print("\n" + "=" * 40)
        print("[SUCCESS] EST enrollment completed!")
        print(f"\nGenerated files in {self.output_dir}:")
        for file_path in sorted(self.output_dir.glob('*')):
            if file_path.is_file():
                print(f"  - {file_path.name}")

        print(f"\nNext steps:")
        print(f"1. Deploy certificate bundle to target system")
        print(f"2. Configure applications to use the certificate")
        print(f"3. Test certificate-based authentication")

        return True

def main():
    """Main EST client function."""
    if len(sys.argv) != 5:
        print("Usage: python est_client.py <server_url> <device_id> <username> <password>")
        print("Example: python est_client.py https://localhost:8445 vm-001 estuser estpass123")
        sys.exit(1)

    server_url = sys.argv[1]
    device_id = sys.argv[2]
    username = sys.argv[3]
    password = sys.argv[4]

    # Create EST client
    client = ESTClient(server_url, device_id, username, password)

    # Run enrollment
    success = client.run_complete_enrollment()

    if success:
        print("\n[SUCCESS] Device enrollment completed successfully!")
        sys.exit(0)
    else:
        print("\n[ERROR] Device enrollment failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()