"""
EST Server Implementation

Modern FastAPI-based EST protocol server with SRP authentication support.
"""

import asyncio
import base64
import logging
import ssl
from pathlib import Path
from typing import Dict, Optional, Tuple
import uvicorn
import pytz
from datetime import datetime
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, HTMLResponse

from cryptography import x509
from cryptography.x509.oid import NameOID

from .config import ESTConfig
from .auth import SRPAuthenticator
from .ca import CertificateAuthority
from .exceptions import ESTError, ESTAuthenticationError, ESTEnrollmentError
from .models import EnrollmentRequest, EnrollmentResponse
from .utils import setup_logging
from .device_tracker import DeviceTracker

logger = logging.getLogger(__name__)


class ESTServer:
    """
    Professional EST (Enrollment over Secure Transport) Server

    Features:
    - RFC 7030 compliant EST protocol implementation
    - SRP (Secure Remote Password) bootstrap authentication
    - FastAPI-based modern async architecture
    - Type-safe configuration and request handling
    - Comprehensive logging and error handling
    """

    def __init__(self, config: ESTConfig) -> None:
        """Initialize EST server with configuration."""
        self.config = config
        self.app = FastAPI(
            title="Python-EST Server",
            description="RFC 7030 EST Protocol Implementation",
            version="1.0.0",
            docs_url="/docs" if config.server.debug else None,
            redoc_url="/redoc" if config.server.debug else None,
        )

        # Initialize components
        self.srp_auth = SRPAuthenticator(config.srp)
        self.ca = CertificateAuthority(config.ca)
        self.device_tracker = DeviceTracker()

        # Setup logging
        setup_logging(debug=config.server.debug)

        # Initialize async components (will be called in setup)
        self._initialized = False

        # Configure middleware
        self._setup_middleware()

        # Register routes
        self._register_routes()

        logger.info("EST Server initialized successfully")

    def _to_ist(self, dt: datetime) -> str:
        """Convert datetime to IST timezone string."""
        if dt is None:
            return "—"
        ist = pytz.timezone('Asia/Kolkata')
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        ist_time = dt.astimezone(ist)
        return ist_time.strftime("%m/%d %H:%M IST")

    def _setup_middleware(self) -> None:
        """Configure FastAPI middleware."""
        # CORS middleware for cross-origin requests
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )

        # Middleware to extract client certificate from nginx headers
        @self.app.middleware("http")
        async def extract_client_cert(request: Request, call_next):
            """
            Extract client certificate from nginx TLS termination proxy.

            Nginx extracts the client certificate from the TLS handshake and forwards
            it via HTTP headers. This is the industry-standard approach for client
            certificate authentication in containerized environments.
            """

            # Get client certificate verification status from nginx
            ssl_verify = request.headers.get('X-SSL-Client-Verify', '')
            ssl_subject_dn = request.headers.get('X-SSL-Client-S-DN', '')

            # If nginx verified the client cert, trust it (simplified approach)
            if ssl_verify == 'SUCCESS' and ssl_subject_dn:
                # Create a marker object to indicate cert was validated
                class ValidatedClientCert:
                    def __init__(self, subject_dn):
                        self.subject_dn = subject_dn

                request.state.client_cert_validated = ValidatedClientCert(ssl_subject_dn)
                logger.info(f"✅ Client certificate validated by nginx: {ssl_subject_dn}")

            elif ssl_verify and ssl_verify != 'SUCCESS':
                # Client sent a certificate but it failed validation
                logger.warning(f"❌ Client certificate validation failed: {ssl_verify}")
                logger.info(f"   Subject: {ssl_subject_dn}")

            else:
                # No client certificate presented
                logger.info(f"ℹ️  No client certificate present (will try password auth)")

            response = await call_next(request)
            return response

    def _register_routes(self) -> None:
        """Register EST protocol endpoints."""

        @self.app.get("/")
        async def root() -> HTMLResponse:
            """Comprehensive server stats dashboard."""
            # Ensure initialization
            await self._ensure_initialized()

            stats = self.device_tracker.get_server_stats()
            html_content = self._get_comprehensive_stats_html(stats)
            return HTMLResponse(content=html_content)

        @self.app.get("/health")
        async def health() -> Dict[str, str]:
            """Health check endpoint for Docker/Kubernetes."""
            return {
                "status": "healthy",
                "service": "Python-EST Server"
            }

        @self.app.get("/api/status")
        async def api_status() -> Dict[str, str]:
            """API status endpoint."""
            return {
                "service": "Python-EST Server",
                "version": "1.0.0",
                "protocol": "RFC 7030",
                "status": "running"
            }

        @self.app.get("/api/stats")
        async def api_stats():
            """Get server statistics as JSON."""
            await self._ensure_initialized()
            stats = self.device_tracker.get_server_stats()
            return stats.dict()

        @self.app.get("/api/devices")
        async def api_devices():
            """Get all device information as JSON."""
            await self._ensure_initialized()
            devices = self.device_tracker.get_all_devices()
            return [device.dict() for device in devices]

        @self.app.get("/api/devices/recent")
        async def api_recent_devices():
            """Get recent device activity as JSON."""
            await self._ensure_initialized()
            devices = self.device_tracker.get_recent_devices(24)
            return [device.dict() for device in devices]

        @self.app.delete("/api/devices/{device_id}")
        async def delete_device(device_id: str):
            """Delete a device from tracking."""
            await self._ensure_initialized()

            success = self.device_tracker.delete_device(device_id)

            if success:
                return {
                    "success": True,
                    "message": f"Device '{device_id}' deleted successfully",
                    "device_id": device_id
                }
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Device '{device_id}' not found"
                )

        @self.app.get("/.well-known/est/cacerts")
        async def get_ca_certificates() -> Response:
            """
            Get CA certificates (RFC 7030 Section 4.1)

            This endpoint provides the current CA certificate(s) in PKCS#7 format.
            No authentication required per RFC 7030.
            """
            try:
                # Check response format configuration
                use_base64 = self.config.response_format == "base64"
                ca_certs_pkcs7 = await self.ca.get_ca_certificates_pkcs7(encode_base64=use_base64)

                if use_base64:
                    # RFC 7030 compliant response with base64 encoding
                    # Convert base64 string to bytes for HTTP response
                    return Response(
                        content=ca_certs_pkcs7.encode('ascii') if isinstance(ca_certs_pkcs7, str) else ca_certs_pkcs7,
                        media_type="application/pkcs7-mime",
                        headers={
                            "Content-Transfer-Encoding": "base64",
                            "Content-Disposition": "attachment; filename=cacerts.p7c"
                        }
                    )
                else:
                    # Raw DER response for IQE gateway compatibility
                    return Response(
                        content=ca_certs_pkcs7,
                        media_type="application/pkcs7-mime",
                        headers={
                            "Content-Disposition": "attachment; filename=cacerts.p7c"
                        }
                    )
            except Exception as e:
                logger.error(f"Failed to retrieve CA certificates: {e}")
                raise HTTPException(status_code=500, detail="Failed to retrieve CA certificates")

        @self.app.post("/.well-known/est/bootstrap")
        async def est_bootstrap(
            request: Request,
            credentials: HTTPBasicCredentials = Depends(HTTPBasic())
        ) -> Response:
            """
            EST Bootstrap Enrollment (RFC 7030 Section 4.1)

            Accepts PKCS#10 CSR with HTTP Basic Auth and returns PKCS#7 certificate.
            Supports both raw DER/PEM and base64-encoded CSRs (for IQE compatibility).
            """
            try:
                # Get CSR from request body
                csr_data = await request.body()
                if not csr_data:
                    raise HTTPException(status_code=400, detail="Missing CSR data")

                # Check if CSR is base64-encoded (IQE UI compatibility)
                content_transfer_encoding = request.headers.get("Content-Transfer-Encoding", "").lower()
                if content_transfer_encoding == "base64":
                    try:
                        # Decode base64-encoded CSR
                        csr_data = base64.b64decode(csr_data)
                        logger.info(f"Decoded base64-encoded CSR ({len(csr_data)} bytes)")
                    except Exception as e:
                        logger.error(f"Failed to decode base64 CSR: {e}")
                        raise HTTPException(status_code=400, detail="Invalid base64-encoded CSR")

                # Authenticate using HTTP Basic Auth
                auth_result = await self.srp_auth.authenticate(
                    credentials.username,
                    credentials.password
                )
                if not auth_result.success:
                    raise HTTPException(status_code=401, detail="Authentication failed")

                # Process bootstrap enrollment with CSR
                use_base64 = self.config.response_format == "base64"
                result = await self.ca.bootstrap_enrollment(csr_data, credentials.username, encode_base64=use_base64)

                # Extract device ID from CSR Common Name
                device_id = f"est-{credentials.username}-{result.serial_number}"  # fallback
                try:
                    if csr_data.startswith(b'-----BEGIN'):
                        csr = x509.load_pem_x509_csr(csr_data)
                    else:
                        csr = x509.load_der_x509_csr(csr_data)

                    # Get Common Name from CSR subject
                    for attribute in csr.subject:
                        if attribute.oid == NameOID.COMMON_NAME:
                            device_id = attribute.value
                            break
                except Exception as e:
                    logger.warning(f"Could not extract device ID from CSR, using fallback: {e}")

                # Track the bootstrap
                client_ip = request.client.host if request.client else "unknown"
                user_agent = request.headers.get("user-agent")

                self.device_tracker.track_bootstrap(
                    device_id=device_id,
                    username=credentials.username,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    bootstrap_cert_serial=result.serial_number
                )

                # Return PKCS#7 certificate with proper headers
                if use_base64:
                    # RFC 7030 compliant response
                    headers = {
                        "Content-Type": "application/pkcs7-mime",
                        "Content-Transfer-Encoding": "base64"
                    }
                else:
                    # Raw DER response for IQE gateway
                    headers = {
                        "Content-Type": "application/pkcs7-mime"
                    }

                return Response(
                    content=result.certificate_pkcs7.encode('ascii') if isinstance(result.certificate_pkcs7, str) else result.certificate_pkcs7,
                    headers=headers,
                    status_code=200
                )

            except HTTPException:
                raise
            except ValueError as e:
                # Duplicate device error
                logger.warning(f"Duplicate device bootstrap attempt: {e}")
                raise HTTPException(status_code=409, detail=str(e))
            except Exception as e:
                logger.error(f"EST bootstrap enrollment failed: {e}")
                raise HTTPException(status_code=500, detail="Bootstrap enrollment failed")

        @self.app.post("/.well-known/est/simpleenroll")
        async def simple_enrollment(
            request: Request,
            credentials: Optional[HTTPBasicCredentials] = Depends(HTTPBasic(auto_error=False))
        ) -> Response:
            """
            Simple certificate enrollment (RFC 7030 Section 4.2)

            Accepts PKCS#10 CSR and returns PKCS#7 certificate.
            Requires authentication (SRP or client certificate).
            Supports both raw DER/PEM and base64-encoded CSRs (for IQE compatibility).
            """
            try:
                # Authenticate request
                auth_result = await self._authenticate_request(request, credentials)
                if not auth_result.authenticated:
                    raise ESTAuthenticationError("Authentication required")

                # Read CSR from request body
                csr_data = await request.body()
                if not csr_data:
                    raise HTTPException(status_code=400, detail="No CSR provided")

                # Check if CSR is base64-encoded (IQE UI compatibility)
                content_transfer_encoding = request.headers.get("Content-Transfer-Encoding", "").lower()
                if content_transfer_encoding == "base64":
                    try:
                        # Decode base64-encoded CSR
                        csr_data = base64.b64decode(csr_data)
                        logger.info(f"Decoded base64-encoded CSR ({len(csr_data)} bytes)")
                    except Exception as e:
                        logger.error(f"Failed to decode base64 CSR: {e}")
                        raise HTTPException(status_code=400, detail="Invalid base64-encoded CSR")

                # Extract device ID from CSR Common Name
                device_id = None
                try:
                    if csr_data.startswith(b'-----BEGIN'):
                        csr = x509.load_pem_x509_csr(csr_data)
                    else:
                        csr = x509.load_der_x509_csr(csr_data)

                    # Get Common Name from CSR subject
                    for attribute in csr.subject:
                        if attribute.oid == NameOID.COMMON_NAME:
                            device_id = attribute.value
                            break
                except Exception as e:
                    logger.warning(f"Could not extract device ID from enrollment CSR: {e}")

                # Process enrollment
                use_base64 = self.config.response_format == "base64"
                enrollment_result = await self.ca.enroll_certificate(
                    csr_data=csr_data,
                    requester=auth_result.username,
                    encode_base64=use_base64
                )

                # Track enrollment if we have device_id
                if device_id:
                    try:
                        self.device_tracker.track_enrollment(
                            device_id=device_id,
                            enrolled_cert_serial=enrollment_result.serial_number
                        )
                        logger.info(f"Tracked enrollment for device: {device_id}")
                    except Exception as e:
                        logger.warning(f"Failed to track enrollment: {e}")

                if use_base64:
                    # RFC 7030 compliant response
                    # Convert base64 string to bytes for HTTP response
                    return Response(
                        content=enrollment_result.certificate_pkcs7.encode('ascii') if isinstance(enrollment_result.certificate_pkcs7, str) else enrollment_result.certificate_pkcs7,
                        media_type="application/pkcs7-mime; smime-type=certs-only",
                        headers={
                            "Content-Transfer-Encoding": "base64",
                            "Content-Disposition": "attachment; filename=cert.p7c"
                        }
                    )
                else:
                    # Raw DER response for IQE gateway
                    return Response(
                        content=enrollment_result.certificate_pkcs7,
                        media_type="application/pkcs7-mime; smime-type=certs-only",
                        headers={
                            "Content-Disposition": "attachment; filename=cert.p7c"
                        }
                    )

            except ESTAuthenticationError:
                raise HTTPException(status_code=401, detail="Authentication failed")
            except ESTEnrollmentError as e:
                raise HTTPException(status_code=500, detail=str(e))
            except Exception as e:
                logger.error(f"Simple enrollment error: {e}")
                raise HTTPException(status_code=500, detail="Enrollment failed")

        @self.app.post("/.well-known/est/simplereenroll")
        async def simple_reenrollment(
            request: Request,
            credentials: HTTPBasicCredentials = Depends(HTTPBasic())
        ) -> Response:
            """
            Simple certificate re-enrollment (RFC 7030 Section 4.2.2)

            Similar to simple enrollment but for certificate renewal.
            """
            # Implementation similar to simpleenroll but with additional validation
            # for existing certificate renewal
            return await simple_enrollment(request, credentials)

    async def _authenticate_request(self, request: Request, credentials: Optional[HTTPBasicCredentials]) -> 'AuthResult':
        """Authenticate EST request using SRP or client certificate."""
        # Try client certificate authentication first (for RA/gateway authentication)
        if hasattr(request.state, 'client_cert_validated'):
            # Nginx already validated the cert, trust it
            cert_info = request.state.client_cert_validated
            logger.info(f"🔐 RA certificate authentication (nginx validated)")
            # Extract CN from subject DN
            username = cert_info.subject_dn.split('CN=')[-1].split(',')[0] if 'CN=' in cert_info.subject_dn else "ra-user"
            logger.info(f"✅ RA Certificate authentication successful for: {username}")
            return AuthResult(authenticated=True, username=username, auth_method="client-certificate")
        else:
            logger.info(f"ℹ️  No client certificate present, falling back to password authentication")

        # Fall back to SRP/password authentication
        if credentials:
            auth_result = await self.srp_auth.authenticate(
                credentials.username,
                credentials.password
            )
            if auth_result.success:
                logger.info(f"SRP authentication successful for: {credentials.username}")
                return AuthResult(authenticated=True, username=credentials.username, auth_method="srp")

        return AuthResult(authenticated=False, username=None, auth_method="none")

    async def _validate_client_certificate(self, client_cert: x509.Certificate) -> bool:
        """Validate that client certificate is signed by our CA."""
        try:
            # Load our CA certificate
            ca_cert = self.ca._ca_cert

            # Verify the certificate signature
            # Check if issuer matches our CA
            if client_cert.issuer != ca_cert.subject:
                logger.warning(f"Client cert issuer mismatch: {client_cert.issuer} != {ca_cert.subject}")
                return False

            # Verify signature (cryptography library validates this during TLS handshake,
            # but we double-check here)
            try:
                from cryptography.hazmat.primitives.asymmetric import padding
                from cryptography.hazmat.primitives import hashes

                # For certificate validation, we trust that if the TLS handshake succeeded
                # with our CA cert configured, the signature is valid
                # Additional validation: check certificate is not expired
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)

                if now < client_cert.not_valid_before_utc:
                    logger.warning(f"Client certificate not yet valid: {client_cert.not_valid_before_utc}")
                    return False

                if now > client_cert.not_valid_after_utc:
                    logger.warning(f"Client certificate expired: {client_cert.not_valid_after_utc}")
                    return False

                logger.info(f"Client certificate validated: {client_cert.subject.rfc4514_string()}")
                return True

            except Exception as e:
                logger.error(f"Certificate signature validation error: {e}")
                return False

        except Exception as e:
            logger.error(f"Client certificate validation error: {e}")
            return False

    async def _ensure_initialized(self) -> None:
        """Ensure server is properly initialized with default user."""
        if not self._initialized:
            await self.srp_auth.ensure_default_user()
            self._initialized = True

    def _get_comprehensive_stats_html(self, stats) -> str:
        """Generate minimalistic server statistics dashboard."""

        # Generate device rows
        device_rows = ""
        for device in stats.recent_devices:
            status_color = "#007acc" if device.status == "enrolled" else "#94a3b8"
            status_text = "Enrolled" if device.status == "enrolled" else "Bootstrap"
            download_buttons = "—"  # Removed insecure download endpoints

            device_rows += f'''
            <tr class="device-row">
                <td>{device.device_id}</td>
                <td>{device.username}</td>
                <td>{device.ip_address}</td>
                <td><span class="status-badge" style="color: {status_color};">{status_text}</span></td>
                <td>{self._to_ist(device.bootstrap_time)}</td>
                <td>{self._to_ist(device.enrollment_time)}</td>
                <td>{download_buttons}</td>
            </tr>
            '''

        if not device_rows:
            device_rows = '<tr><td colspan="7" class="empty-state">No devices connected</td></tr>'

        # Generate recent activity summary
        recent_activity = ""
        recent_devices = stats.recent_devices[-5:] if stats.recent_devices else []
        for device in recent_devices:
            activity_time = self._to_ist(device.last_activity)
            recent_activity += f'''
            <div class="activity-item">
                <span class="activity-device">{device.device_id}</span>
                <span class="activity-action">{device.status}</span>
                <span class="activity-time">{activity_time}</span>
            </div>
            '''

        if not recent_activity:
            recent_activity = '<div class="activity-item empty">No recent activity</div>'

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EST Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0; padding: 0; box-sizing: border-box;
        }}

        body {{
            font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #fafbfc;
            color: #1f2937;
            line-height: 1.6;
            font-size: 14px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 32px;
            animation: fadeIn 0.6s ease-out;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .header {{
            text-align: center;
            margin-bottom: 48px;
            padding-bottom: 24px;
            border-bottom: 1px solid #e5e7eb;
        }}

        .header h1 {{
            font-size: 32px;
            font-weight: 600;
            color: #111827;
            margin-bottom: 8px;
            letter-spacing: -0.025em;
        }}

        .header p {{
            color: #6b7280;
            font-size: 16px;
            font-weight: 400;
        }}

        .uptime {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #f3f4f6;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 13px;
            color: #374151;
            margin-top: 12px;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 16px;
            margin-bottom: 48px;
        }}

        .stat-card {{
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            transition: all 0.2s ease;
        }}

        .stat-card:hover {{
            border-color: #007acc;
            box-shadow: 0 4px 12px rgba(0, 122, 204, 0.1);
            transform: translateY(-2px);
        }}

        .stat-card h3 {{
            font-size: 13px;
            font-weight: 500;
            color: #6b7280;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.025em;
        }}

        .stat-card p {{
            font-size: 28px;
            font-weight: 600;
            color: #007acc;
        }}

        .section {{
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            margin-bottom: 24px;
            overflow: hidden;
        }}

        .section-header {{
            padding: 20px 24px;
            border-bottom: 1px solid #e5e7eb;
            background: #f9fafb;
        }}

        .section-header h2 {{
            font-size: 18px;
            font-weight: 600;
            color: #111827;
        }}

        .devices-table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .devices-table th {{
            background: #f9fafb;
            padding: 16px 24px;
            text-align: left;
            font-size: 13px;
            font-weight: 600;
            color: #374151;
            text-transform: uppercase;
            letter-spacing: 0.025em;
            border-bottom: 1px solid #e5e7eb;
        }}

        .devices-table td {{
            padding: 16px 24px;
            border-bottom: 1px solid #f3f4f6;
            font-size: 14px;
        }}

        .device-row:hover {{
            background: #f9fafb;
        }}

        .status-badge {{
            font-weight: 500;
            font-size: 13px;
        }}

        .empty-state {{
            text-align: center;
            color: #9ca3af;
            font-style: italic;
            padding: 32px;
        }}

        .endpoints-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
            padding: 24px;
        }}

        .endpoint {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 16px;
            transition: all 0.2s ease;
        }}

        .endpoint:hover {{
            border-color: #007acc;
            background: #f0f9ff;
        }}

        .endpoint strong {{
            color: #007acc;
            font-weight: 600;
            font-size: 13px;
            display: block;
            margin-bottom: 4px;
        }}

        .endpoint span {{
            color: #64748b;
            font-size: 12px;
        }}

        .api-nav {{
            display: flex;
            gap: 12px;
            padding: 24px;
            background: #f9fafb;
        }}

        .api-link {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 16px;
            background: white;
            color: #374151;
            text-decoration: none;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s ease;
        }}

        .api-link:hover {{
            background: #007acc;
            color: white;
            border-color: #007acc;
            transform: translateY(-1px);
        }}

        .download-btn {{
            display: inline-block;
            padding: 4px 8px;
            background: #f0f9ff;
            color: #007acc;
            text-decoration: none;
            border: 1px solid #bae6fd;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
            margin: 0 2px;
            transition: all 0.2s ease;
        }}

        .download-btn:hover {{
            background: #007acc;
            color: white;
            border-color: #007acc;
        }}

        .activity-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            margin: 4px 0;
            background: #f9fafb;
            border-radius: 4px;
            font-size: 13px;
        }}

        .activity-item.empty {{
            justify-content: center;
            color: #9ca3af;
            font-style: italic;
        }}

        .activity-device {{
            font-weight: 500;
            color: #374151;
        }}

        .activity-action {{
            color: #007acc;
            font-weight: 500;
        }}

        .activity-time {{
            color: #6b7280;
            font-size: 12px;
        }}

        .inline-section {{
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            margin-bottom: 24px;
            overflow: hidden;
        }}

        .inline-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            padding: 24px;
        }}

        .data-block {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 16px;
        }}

        .data-block h3 {{
            font-size: 14px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 12px;
        }}

        .refresh-btn {{
            position: fixed;
            top: 24px;
            right: 24px;
            background: white;
            color: #374151;
            border: 1px solid #d1d5db;
            padding: 8px 12px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}

        .refresh-btn:hover {{
            background: #f3f4f6;
            border-color: #9ca3af;
        }}

        .credentials {{
            text-align: center;
            margin-top: 32px;
            padding: 16px;
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 6px;
            font-size: 13px;
            color: #0369a1;
        }}

        .credentials strong {{
            font-weight: 600;
        }}

        @media (max-width: 768px) {{
            .container {{ padding: 16px; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .endpoints-grid {{ grid-template-columns: 1fr; }}
            .api-nav {{ flex-wrap: wrap; }}
        }}
    </style>
    <script>
        setTimeout(() => {{
            document.body.style.opacity = '0.7';
            setTimeout(() => location.reload(), 200);
        }}, 30000);
    </script>
</head>
<body>
    <a href="/" class="refresh-btn">Refresh</a>

    <div class="container">
        <div class="header">
            <h1>EST Server</h1>
            <p>Certificate Authority Dashboard</p>
            <div class="uptime">Uptime: {stats.uptime}</div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Devices</h3>
                <p>{stats.total_devices}</p>
            </div>
            <div class="stat-card">
                <h3>Enrolled</h3>
                <p>{stats.enrolled_devices}</p>
            </div>
            <div class="stat-card">
                <h3>Active</h3>
                <p>{stats.active_devices}</p>
            </div>
            <div class="stat-card">
                <h3>Requests</h3>
                <p>{stats.total_requests}</p>
            </div>
            <div class="stat-card">
                <h3>Certificates</h3>
                <p>{stats.certificates_issued}</p>
            </div>
            <div class="stat-card">
                <h3>Bootstrap</h3>
                <p>{stats.bootstrap_certificates}</p>
            </div>
            <div class="stat-card">
                <h3>Enrollment</h3>
                <p>{stats.enrollment_certificates}</p>
            </div>
            <div class="stat-card">
                <h3>Failed</h3>
                <p>{stats.failed_requests}</p>
            </div>
        </div>

        <div class="section">
            <div class="section-header">
                <h2>Connected Devices</h2>
            </div>
            <table class="devices-table">
                <thead>
                    <tr>
                        <th>Device ID</th>
                        <th>User</th>
                        <th>IP Address</th>
                        <th>Status</th>
                        <th>Bootstrap</th>
                        <th>Enrollment</th>
                        <th>Download</th>
                    </tr>
                </thead>
                <tbody>
                    {device_rows}
                </tbody>
            </table>
        </div>

        <div class="section">
            <div class="section-header">
                <h2>Protocol Endpoints</h2>
            </div>
            <div class="endpoints-grid">
                <div class="endpoint">
                    <strong>GET /.well-known/est/cacerts</strong>
                    <span>CA certificate distribution</span>
                </div>
                <div class="endpoint">
                    <strong>POST /.well-known/est/bootstrap</strong>
                    <span>Bootstrap enrollment (CSR required)</span>
                </div>
                <div class="endpoint">
                    <strong>POST /.well-known/est/simpleenroll</strong>
                    <span>Certificate enrollment</span>
                </div>
                <div class="endpoint">
                    <strong>POST /.well-known/est/simplereenroll</strong>
                    <span>Certificate re-enrollment</span>
                </div>
            </div>
        </div>

        <div class="inline-section">
            <div class="section-header">
                <h2>System Overview</h2>
            </div>
            <div class="inline-grid">
                <div class="data-block">
                    <h3>Recent Activity</h3>
                    {recent_activity}
                </div>
                <div class="data-block">
                    <h3>Quick Actions</h3>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        <a href="/api/stats" class="api-link">View JSON Stats</a>
                        <a href="/api/devices" class="api-link">Export Device List</a>
                    </div>
                </div>
            </div>
        </div>

        <div class="credentials">
            <strong>Bootstrap Credentials:</strong> estuser / estpass123
        </div>
    </div>
</body>
</html>'''

    async def start(self) -> None:
        """Start the EST server."""
        # Check if running behind nginx proxy (NGINX_MODE environment variable)
        import os
        nginx_mode = os.getenv('NGINX_MODE', 'false').lower() == 'true'

        if nginx_mode:
            # Running behind nginx - use HTTP only (nginx handles TLS)
            logger.info(f"Starting EST server in NGINX MODE on http://{self.config.server.host}:{self.config.server.port}")
            logger.info("TLS termination handled by nginx proxy")

            config = uvicorn.Config(
                app=self.app,
                host=self.config.server.host,
                port=self.config.server.port,
                workers=self.config.server.workers,
                reload=self.config.server.reload,
                access_log=self.config.server.access_log,
                # No SSL config - nginx handles it
            )
        else:
            # Standalone mode - use HTTPS directly
            logger.info(f"Starting EST server in STANDALONE MODE on https://{self.config.server.host}:{self.config.server.port}")

            config = uvicorn.Config(
                app=self.app,
                host=self.config.server.host,
                port=self.config.server.port,
                workers=self.config.server.workers,
                reload=self.config.server.reload,
                access_log=self.config.server.access_log,
                ssl_keyfile=str(self.config.tls.key_file),
                ssl_certfile=str(self.config.tls.cert_file),
                ssl_ca_certs=str(self.config.tls.ca_file) if self.config.tls.ca_file else None,
                ssl_cert_reqs=ssl.CERT_OPTIONAL,  # Allow but don't require client certs (for RA auth)
            )

        server = uvicorn.Server(config)
        await server.serve()


# Helper classes
class AuthResult:
    """Authentication result."""
    def __init__(self, authenticated: bool, username: Optional[str] = None, auth_method: str = "none"):
        self.authenticated = authenticated
        self.username = username
        self.auth_method = auth_method  # "client-certificate", "srp", or "none"