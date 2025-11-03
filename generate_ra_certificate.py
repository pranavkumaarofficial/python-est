#!/usr/bin/env python3
"""
Generate Registration Authority (RA) certificate for IQE Gateway.

This creates a client certificate that IQE can use to authenticate to the EST server
instead of using username/password (more secure and proper for EST gateways).
"""

from pathlib import Path
from datetime import datetime, timedelta

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_ra_certificate():
    """Generate RA certificate and private key for IQE."""
    print("=" * 60)
    print("Generating RA Certificate for IQE Gateway")
    print("=" * 60)

    # Load CA certificate and key
    print("\n[1/5] Loading CA certificate and key...")
    with open("certs/ca-cert.pem", "rb") as f:
        ca_cert = x509.load_pem_x509_certificate(f.read())
    print(f"   [OK] CA cert loaded: {ca_cert.subject.rfc4514_string()}")

    with open("certs/ca-key.pem", "rb") as f:
        ca_key = serialization.load_pem_private_key(f.read(), password=None)
    print(f"   [OK] CA key loaded")

    # Generate RA private key
    print("\n[2/5] Generating RA private key (2048-bit RSA)...")
    ra_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    print("   [OK] RA private key generated")

    # Create RA certificate
    print("\n[3/5] Creating RA certificate...")
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Hospital"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "IQE Gateway"),
        x509.NameAttribute(NameOID.COMMON_NAME, "IQE Registration Authority"),
    ])

    ra_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(ra_private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=730))  # 2 years
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )
    print(f"   [OK] RA certificate created")
    print(f"      Subject: {ra_cert.subject.rfc4514_string()}")
    print(f"      Serial: {ra_cert.serial_number}")
    print(f"      Valid: {ra_cert.not_valid_before} to {ra_cert.not_valid_after}")

    # Save RA private key
    print("\n[4/5] Saving RA private key...")
    ra_key_path = Path("certs/iqe-ra-key.pem")
    with open(ra_key_path, "wb") as f:
        f.write(ra_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"   [OK] Saved: {ra_key_path}")

    # Save RA certificate
    print("\n[5/5] Saving RA certificate...")
    ra_cert_path = Path("certs/iqe-ra-cert.pem")
    with open(ra_cert_path, "wb") as f:
        f.write(ra_cert.public_bytes(serialization.Encoding.PEM))
    print(f"   [OK] Saved: {ra_cert_path}")

    # Display summary
    print("\n" + "=" * 60)
    print("SUCCESS! RA Certificate Generated")
    print("=" * 60)
    print()
    print("Files created:")
    print(f"  1. {ra_key_path} - RA private key (for IQE)")
    print(f"  2. {ra_cert_path} - RA certificate (for IQE)")
    print()
    print("=" * 60)
    print("NEXT STEPS - Upload to IQE UI")
    print("=" * 60)
    print()
    print("1. In IQE UI, go to the enrollment section")
    print("2. Select 'Registration Authority' option")
    print("3. Upload files:")
    print(f"   - RA Key File: {ra_key_path}")
    print(f"   - RA Cert File: {ra_cert_path}")
    print()
    print("4. IQE will now authenticate using this certificate")
    print("   instead of username/password")
    print()
    print("5. This is more secure and bypasses the current 500 error")
    print()
    print("=" * 60)
    print("IMPORTANT: Secure Storage")
    print("=" * 60)
    print()
    print("[WARNING]  The RA private key is sensitive!")
    print("   Only upload to IQE UI - don't share elsewhere")
    print()
    print("Certificate Details:")
    print(f"  - Validity: 2 years (until {ra_cert.not_valid_after.date()})")
    print(f"  - Purpose: Client authentication to EST server")
    print(f"  - Issued by: {ca_cert.subject.rfc4514_string()}")
    print()

    return ra_cert_path, ra_key_path


if __name__ == "__main__":
    try:
        generate_ra_certificate()
        exit(0)
    except Exception as e:
        print(f"\n[ERROR] Failed to generate RA certificate: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
