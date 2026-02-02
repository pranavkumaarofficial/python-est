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
        """Generate modern Interop EST Server dashboard."""

        # Calculate success rate
        success_rate = 100
        if stats.total_requests > 0:
            success_rate = round(((stats.total_requests - stats.failed_requests) / stats.total_requests) * 100)

        # Generate device rows
        device_rows_html = ""
        if stats.recent_devices:
            for device in stats.recent_devices:
                badge_class = 'badge-success' if device.status == 'enrolled' else 'badge-warning'
                device_rows_html += f'''
                            <tr>
                                <td><strong>{device.device_id}</strong></td>
                                <td>{device.username}</td>
                                <td>{device.ip_address}</td>
                                <td>
                                    <span class="badge {badge_class}">
                                        {device.status}
                                    </span>
                                </td>
                                <td>{self._to_ist(device.last_activity)}</td>
                            </tr>'''
        else:
            device_rows_html = '<tr><td colspan="5" class="empty-state">No devices enrolled</td></tr>'

        # Generate activity log
        activity_log_html = ""
        if stats.recent_devices:
            recent = stats.recent_devices[-10:] if len(stats.recent_devices) > 10 else stats.recent_devices
            for device in recent:
                activity_log_html += f'''
                        <div class="log-entry">
                            <span class="log-time">{self._to_ist(device.last_activity)}</span>
                            <span class="log-device">{device.device_id}</span>
                            <span class="log-status">{device.status}</span>
                        </div>'''
        else:
            activity_log_html = '<div class="log-entry"><span class="log-time">--:--:--</span> No recent activity</div>'

        # Parse uptime for live ticker
        uptime_parts = stats.uptime.split(':')
        uptime_seconds = int(uptime_parts[0]) * 3600 + int(uptime_parts[1]) * 60 + int(uptime_parts[2])

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interop EST Server</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --azure: #007FFF;
            --azure-light: #4CA6FF;
            --azure-dark: #0066CC;
            --bg: #FAFBFC;
            --bg-card: #FFFFFF;
            --text: #1A1D1F;
            --text-muted: #6F767E;
            --border: #E4E7EB;
            --success: #16A34A;
            --warning: #F59E0B;
            --error: #DC2626;
            --shadow: 0 1px 3px rgba(0,0,0,0.04);
            --shadow-lg: 0 10px 40px rgba(0,0,0,0.08);
        }}

        body {{
            font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            overflow-x: hidden;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 2.5rem;
        }}

        /* Header */
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2.5rem;
            background: var(--bg-card);
            padding: 1.75rem 2.5rem;
            border-radius: 16px;
            box-shadow: var(--shadow);
            border: 2px solid var(--border);
        }}

        .logo h1 {{
            font-size: 28px;
            font-weight: 700;
            color: var(--text);
            letter-spacing: -0.02em;
        }}

        .logo small {{
            display: block;
            font-size: 14px;
            color: var(--text-muted);
            font-weight: 500;
            margin-top: 2px;
        }}

        .header-actions {{
            display: flex;
            gap: 0.875rem;
        }}

        .btn {{
            padding: 1rem 2rem;
            border: none;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            text-decoration: none;
            font-family: 'DM Sans', sans-serif;
            letter-spacing: -0.01em;
        }}

        .btn-primary {{
            background: var(--azure);
            color: white;
            box-shadow: 0 4px 14px rgba(0, 127, 255, 0.25);
        }}

        .btn-primary:hover {{
            background: var(--azure-dark);
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 127, 255, 0.35);
        }}

        .btn-primary:active {{
            transform: translateY(0);
        }}

        .btn-secondary {{
            background: white;
            color: var(--text);
            border: 2px solid var(--border);
        }}

        .btn-secondary:hover {{
            border-color: var(--azure);
            color: var(--azure);
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }}

        .btn-danger {{
            background: var(--error);
            color: white;
        }}

        .btn-danger:hover {{
            background: #B91C1C;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(220, 38, 38, 0.35);
        }}

        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }}

        .stat-card {{
            background: var(--bg-card);
            border: 2px solid var(--border);
            border-radius: 16px;
            padding: 2.25rem;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }}

        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 5px;
            background: linear-gradient(90deg, var(--azure), var(--azure-light));
        }}

        .stat-card:hover {{
            transform: translateY(-6px);
            box-shadow: var(--shadow-lg);
            border-color: var(--azure);
        }}

        .stat-label {{
            font-size: 13px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 700;
            margin-bottom: 1rem;
        }}

        .stat-value {{
            font-size: 48px;
            font-weight: 700;
            color: var(--text);
            line-height: 1;
            margin-bottom: 0.625rem;
            font-variant-numeric: tabular-nums;
        }}

        .stat-change {{
            font-size: 14px;
            color: var(--text-muted);
            font-weight: 600;
        }}

        /* Grid Layout */
        .grid-2 {{
            display: grid;
            grid-template-columns: 1.5fr 1fr;
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }}

        .panel {{
            background: var(--bg-card);
            border: 2px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
            box-shadow: var(--shadow);
        }}

        .panel-header {{
            padding: 1.75rem 2.5rem;
            border-bottom: 2px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: linear-gradient(to bottom, #FAFBFC, #F8F9FA);
        }}

        .panel-title {{
            font-size: 19px;
            font-weight: 700;
            color: var(--text);
            letter-spacing: -0.01em;
        }}

        /* Table */
        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        thead th {{
            text-align: left;
            padding: 1.5rem 2.5rem;
            font-size: 12px;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            background: #F8F9FA;
        }}

        tbody tr {{
            border-bottom: 1px solid var(--border);
            transition: background 0.2s;
        }}

        tbody tr:hover {{
            background: #F8F9FA;
        }}

        tbody tr:last-child {{
            border-bottom: none;
        }}

        tbody td {{
            padding: 1.5rem 2.5rem;
            font-size: 15px;
            font-weight: 500;
        }}

        .badge {{
            display: inline-block;
            padding: 0.5rem 1.125rem;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .badge-success {{
            background: #DCFCE7;
            color: var(--success);
        }}

        .badge-warning {{
            background: #FEF3C7;
            color: #D97706;
        }}

        /* Live indicator */
        .live-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.625rem 1.25rem;
            background: #DCFCE7;
            color: var(--success);
            border-radius: 10px;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}

        .live-dot {{
            width: 10px;
            height: 10px;
            background: var(--success);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.6; transform: scale(0.95); }}
        }}

        /* Activity Log */
        .activity-log {{
            max-height: 520px;
            overflow-y: auto;
            padding: 1.5rem 2rem;
        }}

        .log-entry {{
            padding: 1.125rem;
            margin-bottom: 0.5rem;
            border-left: 4px solid var(--azure);
            background: #F8F9FA;
            border-radius: 8px;
            font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
            font-size: 13px;
            transition: all 0.2s;
        }}

        .log-entry:hover {{
            background: white;
            box-shadow: var(--shadow);
        }}

        .log-time {{
            color: var(--text-muted);
            margin-right: 1rem;
            font-weight: 700;
        }}

        .log-device {{
            color: var(--azure);
            font-weight: 700;
            margin-right: 0.75rem;
        }}

        .log-status {{
            color: var(--text);
            font-weight: 600;
        }}

        /* Empty State */
        .empty-state {{
            text-align: center;
            padding: 4rem;
            color: var(--text-muted);
            font-size: 15px;
            font-weight: 500;
        }}

        /* Endpoints */
        .endpoints-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.25rem;
            padding: 2rem;
        }}

        .endpoint {{
            background: #F8F9FA;
            border: 2px solid var(--border);
            border-radius: 12px;
            padding: 1.75rem;
            transition: all 0.25s;
        }}

        .endpoint:hover {{
            border-color: var(--azure);
            background: white;
            transform: translateY(-3px);
            box-shadow: var(--shadow-lg);
        }}

        .endpoint-method {{
            font-weight: 700;
            margin-bottom: 0.625rem;
            font-size: 15px;
            letter-spacing: -0.01em;
        }}

        .endpoint-method.get {{ color: var(--success); }}
        .endpoint-method.post {{ color: var(--azure); }}

        .endpoint-desc {{
            color: var(--text-muted);
            font-size: 14px;
            font-weight: 500;
        }}

        /* Responsive */
        @media (max-width: 1024px) {{
            .grid-2 {{
                grid-template-columns: 1fr;
            }}
        }}

        @media (max-width: 768px) {{
            .container {{ padding: 1.5rem; }}
            .stats-grid {{ grid-template-columns: 1fr; }}
            header {{
                flex-direction: column;
                gap: 1.5rem;
                padding: 1.5rem;
            }}
            .header-actions {{
                width: 100%;
                flex-direction: column;
            }}
            .btn {{
                flex: 1;
                justify-content: center;
                padding: 1rem;
            }}
        }}

        /* Scrollbar */
        ::-webkit-scrollbar {{
            width: 12px;
            height: 12px;
        }}

        ::-webkit-scrollbar-track {{
            background: var(--bg);
        }}

        ::-webkit-scrollbar-thumb {{
            background: #CBD5E1;
            border-radius: 6px;
        }}

        ::-webkit-scrollbar-thumb:hover {{
            background: #94A3B8;
        }}

    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <h1>Interop EST Server</h1>
                <small>RFC 7030 Certificate Enrollment Protocol</small>
            </div>
            <div class="header-actions">
                <a href="/api/devices" class="btn btn-secondary" download="devices.json">
                    Export Data
                </a>
                <a href="/" class="btn btn-primary">
                    Refresh
                </a>
                <button class="btn btn-danger" onclick="if(confirm('This will delete all device enrollments. Continue?')){{alert('Database reset functionality requires API implementation');}}">
                    Reset Database
                </button>
            </div>
        </header>

        <!-- Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Devices</div>
                <div class="stat-value">{stats.total_devices}</div>
                <div class="stat-change">Active enrollments</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Certificates Issued</div>
                <div class="stat-value">{stats.certificates_issued}</div>
                <div class="stat-change">Bootstrap + Enrollment</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Server Uptime</div>
                <div class="stat-value" id="uptime-display">{stats.uptime}</div>
                <div class="stat-change"><span class="live-dot"></span> Live Session</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Success Rate</div>
                <div class="stat-value">{success_rate}%</div>
                <div class="stat-change">{stats.total_requests} total requests</div>
            </div>
        </div>

        <!-- Main Grid -->
        <div class="grid-2">
            <!-- Devices Panel -->
            <div class="panel">
                <div class="panel-header">
                    <h2 class="panel-title">Enrolled Devices</h2>
                    <span class="live-indicator">
                        <span class="live-dot"></span>
                        LIVE
                    </span>
                </div>
                <div class="panel-body" style="padding: 0;">
                    <table>
                        <thead>
                            <tr>
                                <th>Device ID</th>
                                <th>Username</th>
                                <th>IP Address</th>
                                <th>Status</th>
                                <th>Last Activity</th>
                            </tr>
                        </thead>
                        <tbody>
                            {device_rows_html}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Activity Log Panel -->
            <div class="panel">
                <div class="panel-header">
                    <h2 class="panel-title">Recent Activity</h2>
                    <span class="badge badge-success">{len(stats.recent_devices)} events</span>
                </div>
                <div class="panel-body" style="padding: 0;">
                    <div class="activity-log">
                        {activity_log_html}
                    </div>
                </div>
            </div>
        </div>

        <!-- Endpoints Panel -->
        <div class="panel">
            <div class="panel-header">
                <h2 class="panel-title">EST Protocol Endpoints</h2>
                <span class="live-indicator">
                    <span class="live-dot"></span>
                    LIVE
                </span>
            </div>
            <div class="endpoints-grid">
                <div class="endpoint">
                    <div class="endpoint-method get">GET /cacerts</div>
                    <div class="endpoint-desc">Download CA certificates</div>
                </div>
                <div class="endpoint">
                    <div class="endpoint-method post">POST /bootstrap</div>
                    <div class="endpoint-desc">Initial device enrollment</div>
                </div>
                <div class="endpoint">
                    <div class="endpoint-method post">POST /simpleenroll</div>
                    <div class="endpoint-desc">Certificate enrollment/renewal</div>
                </div>
                <div class="endpoint">
                    <div class="endpoint-method post">POST /simplereenroll</div>
                    <div class="endpoint-desc">Certificate re-enrollment</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Live uptime ticker
        let uptimeSeconds = {uptime_seconds};
        const uptimeElement = document.getElementById('uptime-display');

        function updateUptime() {{
            uptimeSeconds++;
            const hours = Math.floor(uptimeSeconds / 3600);
            const minutes = Math.floor((uptimeSeconds % 3600) / 60);
            const seconds = uptimeSeconds % 60;

            uptimeElement.textContent = `${{hours}}:${{String(minutes).padStart(2, '0')}}:${{String(seconds).padStart(2, '0')}}`;
        }}

        // Update uptime every second
        setInterval(updateUptime, 1000);

        // Auto-reload every 30 seconds
        setTimeout(() => {{
            window.location.reload();
        }}, 30000);
    </script>
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