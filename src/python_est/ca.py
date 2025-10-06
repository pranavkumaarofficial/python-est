"""
Certificate Authority Module

Handles certificate generation, signing, and management for EST protocol.
"""

import asyncio
import base64
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509.oid import NameOID, ExtensionOID

from .config import CAConfig
from .exceptions import ESTCertificateError, ESTEnrollmentError

logger = logging.getLogger(__name__)


@dataclass
class CertificateResult:
    """Result of EST-compliant certificate enrollment."""
    certificate_pkcs7: str  # PKCS#7 format (EST standard response)
    serial_number: str
    valid_until: datetime


@dataclass
class EnrollmentResult:
    """Result of certificate enrollment."""
    certificate_pkcs7: str  # PKCS#7 format
    serial_number: str
    valid_until: datetime


class CertificateAuthority:
    """
    Certificate Authority for EST protocol operations.

    Handles certificate generation, signing, and PKCS#7 formatting
    for EST enrollment and bootstrap operations.
    """

    def __init__(self, config: CAConfig) -> None:
        """Initialize Certificate Authority."""
        self.config = config
        self._ca_cert: Optional[x509.Certificate] = None
        self._ca_key: Optional[rsa.RSAPrivateKey] = None
        self._load_ca_credentials()

    def _load_ca_credentials(self) -> None:
        """Load CA certificate and private key."""
        try:
            # Load CA certificate
            with open(self.config.ca_cert, 'rb') as f:
                self._ca_cert = x509.load_pem_x509_certificate(f.read())

            # Load CA private key
            with open(self.config.ca_key, 'rb') as f:
                if self.config.ca_key_password:
                    password = self.config.ca_key_password.encode()
                else:
                    password = None

                self._ca_key = serialization.load_pem_private_key(
                    f.read(),
                    password=password
                )

            logger.info("CA credentials loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load CA credentials: {e}")
            raise ESTCertificateError(f"Failed to load CA credentials: {e}")

    async def get_ca_certificates_pkcs7(self) -> str:
        """
        Get CA certificates in PKCS#7 format.

        Returns:
            Base64-encoded PKCS#7 containing CA certificate(s)
        """
        try:
            if not self._ca_cert:
                raise ESTCertificateError("CA certificate not loaded")

            # Create proper PKCS#7 response with CA certificate
            return self._create_pkcs7_response([self._ca_cert])

        except Exception as e:
            logger.error(f"Failed to get CA certificates: {e}")
            raise ESTCertificateError(f"Failed to get CA certificates: {e}")


    async def bootstrap_enrollment(self, csr_data: bytes, requester: str) -> CertificateResult:
        """
        Process bootstrap enrollment with CSR (EST-compliant).

        Args:
            csr_data: PKCS#10 Certificate Signing Request
            requester: Authenticated requester identifier

        Returns:
            CertificateResult with PKCS#7 certificate only (no private key)
        """
        try:
            # Parse CSR
            if csr_data.startswith(b'-----BEGIN'):
                # PEM format
                csr = x509.load_pem_x509_csr(csr_data)
            else:
                # Assume DER format
                csr = x509.load_der_x509_csr(csr_data)

            # Validate CSR
            if not csr.is_signature_valid:
                raise ESTEnrollmentError("Invalid CSR signature")

            # Create certificate from CSR
            certificate = self._create_certificate(
                subject=csr.subject,
                public_key=csr.public_key(),
                validity_days=30,  # Short-lived bootstrap certificate
                is_bootstrap=True
            )

            # Create proper PKCS#7 response
            cert_pkcs7 = self._create_pkcs7_response([certificate])
            valid_until = datetime.utcnow() + timedelta(days=30)

            logger.info(f"Bootstrap enrollment successful for requester: {requester}")

            return CertificateResult(
                certificate_pkcs7=cert_pkcs7,
                serial_number=str(certificate.serial_number),
                valid_until=valid_until
            )

        except Exception as e:
            logger.error(f"Bootstrap enrollment failed: {e}")
            raise ESTEnrollmentError(f"Bootstrap enrollment failed: {e}")

    async def enroll_certificate(self, csr_data: bytes, requester: str) -> EnrollmentResult:
        """
        Process certificate enrollment request.

        Args:
            csr_data: PKCS#10 Certificate Signing Request
            requester: Username of requester

        Returns:
            EnrollmentResult with signed certificate
        """
        try:
            # Parse CSR
            if csr_data.startswith(b'-----BEGIN'):
                # PEM format
                csr = x509.load_pem_x509_csr(csr_data)
            else:
                # Assume DER format
                csr = x509.load_der_x509_csr(csr_data)

            # Validate CSR
            if not csr.is_signature_valid:
                raise ESTEnrollmentError("Invalid CSR signature")

            # Create certificate from CSR
            certificate = self._create_certificate(
                subject=csr.subject,
                public_key=csr.public_key(),
                validity_days=self.config.cert_validity_days,
                is_bootstrap=False
            )

            # Create proper PKCS#7 response
            cert_pkcs7 = self._create_pkcs7_response([certificate])

            valid_until = datetime.utcnow() + timedelta(days=self.config.cert_validity_days)

            logger.info(f"Enrolled certificate for requester: {requester}")

            return EnrollmentResult(
                certificate_pkcs7=cert_pkcs7,
                serial_number=str(certificate.serial_number),
                valid_until=valid_until
            )

        except Exception as e:
            logger.error(f"Certificate enrollment failed: {e}")
            raise ESTEnrollmentError(f"Certificate enrollment failed: {e}")

    def _create_certificate(self,
                          subject: x509.Name,
                          public_key,
                          validity_days: int,
                          is_bootstrap: bool = False) -> x509.Certificate:
        """Create and sign X.509 certificate."""
        try:
            if not self._ca_cert or not self._ca_key:
                raise ESTCertificateError("CA credentials not loaded")

            # Generate serial number
            serial_number = x509.random_serial_number()

            # Set validity period
            valid_from = datetime.utcnow()
            valid_until = valid_from + timedelta(days=validity_days)

            # Build certificate
            builder = x509.CertificateBuilder()
            builder = builder.subject_name(subject)
            builder = builder.issuer_name(self._ca_cert.subject)
            builder = builder.public_key(public_key)
            builder = builder.serial_number(serial_number)
            builder = builder.not_valid_before(valid_from)
            builder = builder.not_valid_after(valid_until)

            # Add extensions
            builder = builder.add_extension(
                x509.SubjectKeyIdentifier.from_public_key(public_key),
                critical=False,
            )

            builder = builder.add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(
                    self._ca_cert.public_key()
                ),
                critical=False,
            )

            if is_bootstrap:
                # Bootstrap certificate extensions
                builder = builder.add_extension(
                    x509.KeyUsage(
                        digital_signature=True,
                        key_encipherment=True,
                        content_commitment=False,
                        data_encipherment=False,
                        key_agreement=False,
                        key_cert_sign=False,
                        crl_sign=False,
                        encipher_only=False,
                        decipher_only=False,
                    ),
                    critical=True,
                )
                builder = builder.add_extension(
                    x509.ExtendedKeyUsage([
                        x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                    ]),
                    critical=True,
                )
            else:
                # Regular certificate extensions
                builder = builder.add_extension(
                    x509.KeyUsage(
                        digital_signature=True,
                        key_encipherment=True,
                        content_commitment=False,
                        data_encipherment=False,
                        key_agreement=False,
                        key_cert_sign=False,
                        crl_sign=False,
                        encipher_only=False,
                        decipher_only=False,
                    ),
                    critical=True,
                )
                builder = builder.add_extension(
                    x509.ExtendedKeyUsage([
                        x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                        x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                    ]),
                    critical=True,
                )

            # Get hash algorithm
            if self.config.digest_algorithm == "sha256":
                hash_algorithm = hashes.SHA256()
            elif self.config.digest_algorithm == "sha384":
                hash_algorithm = hashes.SHA384()
            elif self.config.digest_algorithm == "sha512":
                hash_algorithm = hashes.SHA512()
            else:
                hash_algorithm = hashes.SHA256()

            # Sign certificate
            certificate = builder.sign(self._ca_key, hash_algorithm)

            return certificate

        except Exception as e:
            logger.error(f"Certificate creation failed: {e}")
            raise ESTCertificateError(f"Certificate creation failed: {e}")

    async def revoke_certificate(self, serial_number: str, reason: str = "unspecified") -> bool:
        """
        Revoke certificate (for future CRL implementation).

        Args:
            serial_number: Certificate serial number to revoke
            reason: Revocation reason

        Returns:
            True if revocation successful
        """
        try:
            # Implementation would add certificate to CRL
            logger.info(f"Certificate revoked: {serial_number}, reason: {reason}")
            return True

        except Exception as e:
            logger.error(f"Certificate revocation failed: {e}")
            return False

    def _create_pkcs7_response(self, certificates: list) -> str:
        """
        Create proper PKCS#7 response for EST protocol.

        Args:
            certificates: List of x509.Certificate objects

        Returns:
            Base64-encoded PKCS#7 certificate response
        """
        try:
            if not certificates:
                raise ESTCertificateError("No certificates provided for PKCS#7 response")

            # Use the cryptography library's built-in function to create
            # a certificates-only PKCS#7 structure (degenerate PKCS#7)
            # This is exactly what EST RFC 7030 requires
            pkcs7_der = pkcs7.serialize_certificates(
                certificates,
                serialization.Encoding.DER
            )

            # Base64 encode for EST transport as required by RFC 7030
            pkcs7_b64 = base64.b64encode(pkcs7_der).decode()

            logger.debug(f"Created proper PKCS#7 response with {len(certificates)} certificate(s)")
            return pkcs7_b64

        except Exception as e:
            logger.error(f"Failed to create PKCS#7 response: {e}")
            raise ESTCertificateError(f"Failed to create PKCS#7 response: {e}")