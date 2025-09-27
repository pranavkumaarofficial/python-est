"""
EST Client Implementation

Client library for interacting with EST protocol servers.
"""

import asyncio
import base64
import logging
from pathlib import Path
from typing import Optional, Tuple
import ssl
import aiohttp
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from .exceptions import ESTError, ESTNetworkError, ESTEnrollmentError

logger = logging.getLogger(__name__)


class ESTClient:
    """
    EST Protocol Client

    Provides client functionality for EST operations including:
    - CA certificate retrieval
    - Certificate enrollment
    - Certificate re-enrollment
    - Bootstrap authentication
    """

    def __init__(self,
                 server_url: str,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 client_cert: Optional[Path] = None,
                 client_key: Optional[Path] = None,
                 ca_cert: Optional[Path] = None,
                 verify_ssl: bool = True) -> None:
        """
        Initialize EST client.

        Args:
            server_url: EST server URL (e.g., https://est.example.com:8443)
            username: SRP username for bootstrap authentication
            password: SRP password for bootstrap authentication
            client_cert: Client certificate file path
            client_key: Client private key file path
            ca_cert: CA certificate file path for server verification
            verify_ssl: Whether to verify SSL certificates
        """
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.password = password
        self.client_cert = client_cert
        self.client_key = client_key
        self.ca_cert = ca_cert
        self.verify_ssl = verify_ssl

    async def get_ca_certificates(self) -> str:
        """
        Retrieve CA certificates from EST server.

        Returns:
            CA certificates in PKCS#7 format
        """
        try:
            url = f"{self.server_url}/.well-known/est/cacerts"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    ssl=self._create_ssl_context()
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        logger.info("Successfully retrieved CA certificates")
                        return content
                    else:
                        raise ESTNetworkError(f"Failed to retrieve CA certificates: {response.status}")

        except Exception as e:
            logger.error(f"Error retrieving CA certificates: {e}")
            raise ESTNetworkError(f"Failed to retrieve CA certificates: {e}")

    async def bootstrap_authenticate(self, device_id: str) -> Tuple[str, str]:
        """
        Perform bootstrap authentication and get initial certificate.

        Args:
            device_id: Device identifier

        Returns:
            Tuple of (certificate_pem, private_key_pem)
        """
        if not self.username or not self.password:
            raise ESTError("Username and password required for bootstrap")

        try:
            url = f"{self.server_url}/.well-known/est/bootstrap/authenticate"

            form_data = aiohttp.FormData()
            form_data.add_field('username', self.username)
            form_data.add_field('password', self.password)
            form_data.add_field('device_id', device_id)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=form_data,
                    ssl=self._create_ssl_context()
                ) as response:
                    if response.status == 200:
                        # Parse HTML response to extract certificate and key
                        # This is a simplified implementation
                        logger.info(f"Bootstrap authentication successful for device: {device_id}")
                        # In real implementation, parse the HTML response
                        return ("certificate_placeholder", "key_placeholder")
                    else:
                        content = await response.text()
                        raise ESTEnrollmentError(f"Bootstrap failed: {response.status} - {content}")

        except Exception as e:
            logger.error(f"Bootstrap authentication error: {e}")
            raise ESTEnrollmentError(f"Bootstrap authentication failed: {e}")

    async def enroll_certificate(self, csr_pem: str) -> str:
        """
        Enroll certificate using CSR.

        Args:
            csr_pem: Certificate Signing Request in PEM format

        Returns:
            Certificate in PKCS#7 format
        """
        try:
            url = f"{self.server_url}/.well-known/est/simpleenroll"

            # Convert PEM to base64 for EST transport
            csr_b64 = base64.b64encode(csr_pem.encode()).decode()

            auth = None
            if self.username and self.password:
                auth = aiohttp.BasicAuth(self.username, self.password)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=csr_b64,
                    headers={
                        'Content-Type': 'application/pkcs10',
                        'Content-Transfer-Encoding': 'base64'
                    },
                    auth=auth,
                    ssl=self._create_ssl_context()
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        logger.info("Certificate enrollment successful")
                        return content
                    else:
                        content = await response.text()
                        raise ESTEnrollmentError(f"Enrollment failed: {response.status} - {content}")

        except Exception as e:
            logger.error(f"Certificate enrollment error: {e}")
            raise ESTEnrollmentError(f"Certificate enrollment failed: {e}")

    async def reenroll_certificate(self, csr_pem: str) -> str:
        """
        Re-enroll certificate using CSR.

        Args:
            csr_pem: Certificate Signing Request in PEM format

        Returns:
            Certificate in PKCS#7 format
        """
        try:
            url = f"{self.server_url}/.well-known/est/simplereenroll"

            # Convert PEM to base64 for EST transport
            csr_b64 = base64.b64encode(csr_pem.encode()).decode()

            auth = None
            if self.username and self.password:
                auth = aiohttp.BasicAuth(self.username, self.password)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=csr_b64,
                    headers={
                        'Content-Type': 'application/pkcs10',
                        'Content-Transfer-Encoding': 'base64'
                    },
                    auth=auth,
                    ssl=self._create_ssl_context()
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        logger.info("Certificate re-enrollment successful")
                        return content
                    else:
                        content = await response.text()
                        raise ESTEnrollmentError(f"Re-enrollment failed: {response.status} - {content}")

        except Exception as e:
            logger.error(f"Certificate re-enrollment error: {e}")
            raise ESTEnrollmentError(f"Certificate re-enrollment failed: {e}")

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context for client connections."""
        context = ssl.create_default_context()

        if not self.verify_ssl:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        if self.ca_cert and self.ca_cert.exists():
            context.load_verify_locations(str(self.ca_cert))

        if self.client_cert and self.client_key:
            if self.client_cert.exists() and self.client_key.exists():
                context.load_cert_chain(str(self.client_cert), str(self.client_key))

        return context

    @staticmethod
    def generate_csr(common_name: str,
                    organization: str = "EST Client",
                    country: str = "US") -> Tuple[str, str]:
        """
        Generate Certificate Signing Request and private key.

        Args:
            common_name: Certificate common name
            organization: Organization name
            country: Country code

        Returns:
            Tuple of (csr_pem, private_key_pem)
        """
        try:
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )

            # Create CSR
            subject = x509.Name([
                x509.NameAttribute(x509.oid.NameOID.COUNTRY_NAME, country),
                x509.NameAttribute(x509.oid.NameOID.ORGANIZATION_NAME, organization),
                x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, common_name),
            ])

            csr = x509.CertificateSigningRequestBuilder().subject_name(
                subject
            ).sign(private_key, algorithm=None)

            # Convert to PEM format
            csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()
            key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode()

            return csr_pem, key_pem

        except Exception as e:
            logger.error(f"CSR generation error: {e}")
            raise ESTError(f"Failed to generate CSR: {e}")


# Example usage function
async def example_client_usage():
    """Example EST client usage."""

    # Initialize client for bootstrap
    client = ESTClient(
        server_url="https://localhost:8443",
        username="testuser",
        password="testpass123",
        verify_ssl=False  # For development only
    )

    try:
        # Get CA certificates
        ca_certs = await client.get_ca_certificates()
        print(f"CA Certificates: {ca_certs[:100]}...")

        # Generate CSR
        csr_pem, key_pem = ESTClient.generate_csr("test-device-001")
        print(f"Generated CSR: {csr_pem[:100]}...")

        # Enroll certificate
        cert_pkcs7 = await client.enroll_certificate(csr_pem)
        print(f"Enrolled Certificate: {cert_pkcs7[:100]}...")

    except Exception as e:
        print(f"Client error: {e}")


if __name__ == "__main__":
    asyncio.run(example_client_usage())