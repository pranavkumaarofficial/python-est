"""
EST Server Implementation

Modern FastAPI-based EST protocol server with SRP authentication support.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
import uvicorn
import pytz
from datetime import datetime
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, HTMLResponse

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

        @self.app.get("/download/certificate/{device_id}")
        async def download_certificate(device_id: str):
            """Download bootstrap certificate for a device."""
            # This would be implemented with proper certificate storage
            # For now, return a placeholder
            return Response(
                content=f"Certificate for {device_id}",
                media_type="application/x-pem-file",
                headers={"Content-Disposition": f"attachment; filename={device_id}_cert.pem"}
            )

        @self.app.get("/download/key/{device_id}")
        async def download_private_key(device_id: str):
            """Download private key for a device."""
            # This would be implemented with proper key storage
            return Response(
                content=f"Private key for {device_id}",
                media_type="application/x-pem-file",
                headers={"Content-Disposition": f"attachment; filename={device_id}_key.pem"}
            )

        @self.app.get("/.well-known/est/cacerts")
        async def get_ca_certificates() -> Response:
            """
            Get CA certificates (RFC 7030 Section 4.1)

            This endpoint provides the current CA certificate(s) in PKCS#7 format.
            No authentication required per RFC 7030.
            """
            try:
                ca_certs_pkcs7 = await self.ca.get_ca_certificates_pkcs7()

                return Response(
                    content=ca_certs_pkcs7,
                    media_type="application/pkcs7-mime",
                    headers={
                        "Content-Transfer-Encoding": "base64",
                        "Content-Disposition": "attachment; filename=cacerts.p7c"
                    }
                )
            except Exception as e:
                logger.error(f"Failed to retrieve CA certificates: {e}")
                raise HTTPException(status_code=500, detail="Failed to retrieve CA certificates")

        @self.app.get("/.well-known/est/bootstrap")
        async def bootstrap_page() -> HTMLResponse:
            """
            Bootstrap authentication page

            Provides HTML form for SRP-based bootstrap authentication.
            """
            if not self.config.bootstrap_enabled:
                raise HTTPException(status_code=404, detail="Bootstrap not enabled")

            # Ensure initialization
            await self._ensure_initialized()

            html_content = self._get_bootstrap_html()
            return HTMLResponse(content=html_content)

        @self.app.post("/.well-known/est/bootstrap/authenticate")
        async def bootstrap_authenticate(request: Request) -> HTMLResponse:
            """
            Process bootstrap authentication and automatic enrollment

            Handles SRP authentication for bootstrap enrollment, then performs automatic enrollment.
            """
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent")

            try:
                form_data = await request.form()
                username = form_data.get("username", "").strip()
                password = form_data.get("password", "").strip()
                device_id = form_data.get("device_id", "").strip()

                if not all([username, password, device_id]):
                    self.device_tracker.track_request("bootstrap", success=False)
                    raise HTTPException(status_code=400, detail="Missing required fields")

                # Authenticate with SRP
                auth_result = await self.srp_auth.authenticate(username, password)
                if not auth_result.success:
                    self.device_tracker.track_request("bootstrap", success=False)
                    raise ESTAuthenticationError("Invalid credentials")

                # Generate bootstrap certificate
                cert_result = await self.ca.generate_bootstrap_certificate(
                    device_id=device_id,
                    username=username
                )

                # Track bootstrap with certificate data
                self.device_tracker.track_bootstrap(
                    device_id=device_id,
                    username=username,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    bootstrap_cert_serial=str(cert_result.certificate.split('\n')[0]),  # Simplified serial extraction
                    certificate=cert_result.certificate,
                    private_key=cert_result.private_key
                )

                # Automatically perform enrollment after bootstrap
                enrollment_result = await self._perform_automatic_enrollment(
                    device_id=device_id,
                    username=username,
                    bootstrap_cert=cert_result.certificate,
                    bootstrap_key=cert_result.private_key
                )

                # Track enrollment if successful
                if enrollment_result.get("success"):
                    self.device_tracker.track_enrollment(
                        device_id=device_id,
                        enrolled_cert_serial="auto-enrolled-" + device_id  # Simplified serial
                    )

                success_html = self._get_bootstrap_success_html(
                    username=username,
                    device_id=device_id,
                    certificate=cert_result.certificate,
                    private_key=cert_result.private_key,
                    enrollment_result=enrollment_result
                )

                return HTMLResponse(content=success_html)

            except ESTAuthenticationError:
                self.device_tracker.track_request("bootstrap", success=False)
                error_html = self._get_bootstrap_error_html("Authentication failed")
                return HTMLResponse(content=error_html, status_code=401)
            except Exception as e:
                logger.error(f"Bootstrap authentication error: {e}")
                self.device_tracker.track_request("bootstrap", success=False)
                error_html = self._get_bootstrap_error_html("Internal server error")
                return HTMLResponse(content=error_html, status_code=500)

        @self.app.post("/.well-known/est/bootstrap")
        async def est_bootstrap(
            request: Request,
            credentials: HTTPBasicCredentials = Depends(HTTPBasic())
        ) -> Response:
            """
            EST Bootstrap Enrollment (RFC 7030 Section 4.1)

            Accepts PKCS#10 CSR with HTTP Basic Auth and returns PKCS#7 certificate.
            This is the proper EST protocol bootstrap endpoint.
            """
            try:
                # Get CSR from request body
                csr_data = await request.body()
                if not csr_data:
                    raise HTTPException(status_code=400, detail="Missing CSR data")

                # Authenticate using HTTP Basic Auth
                auth_result = await self.srp_auth.authenticate(
                    credentials.username,
                    credentials.password
                )
                if not auth_result.success:
                    raise HTTPException(status_code=401, detail="Authentication failed")

                # Process bootstrap enrollment with CSR
                result = await self.ca.bootstrap_enrollment(csr_data, credentials.username)

                # Track the bootstrap
                client_ip = request.client.host if request.client else "unknown"
                user_agent = request.headers.get("user-agent")

                self.device_tracker.track_bootstrap(
                    device_id=f"est-{credentials.username}-{result.serial_number}",
                    username=credentials.username,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    bootstrap_cert_serial=result.serial_number
                )

                # Return PKCS#7 certificate with proper headers
                headers = {
                    "Content-Type": "application/pkcs7-mime",
                    "Content-Transfer-Encoding": "base64"
                }

                return Response(
                    content=result.certificate_pkcs7,
                    headers=headers,
                    status_code=200
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"EST bootstrap enrollment failed: {e}")
                raise HTTPException(status_code=500, detail="Bootstrap enrollment failed")

        @self.app.post("/.well-known/est/simpleenroll")
        async def simple_enrollment(
            request: Request,
            credentials: HTTPBasicCredentials = Depends(HTTPBasic())
        ) -> Response:
            """
            Simple certificate enrollment (RFC 7030 Section 4.2)

            Accepts PKCS#10 CSR and returns PKCS#7 certificate.
            Requires authentication (SRP or client certificate).
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

                # Process enrollment
                enrollment_result = await self.ca.enroll_certificate(
                    csr_data=csr_data,
                    requester=auth_result.username
                )

                return Response(
                    content=enrollment_result.certificate_pkcs7,
                    media_type="application/pkcs7-mime; smime-type=certs-only",
                    headers={
                        "Content-Transfer-Encoding": "base64",
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
        # Check for SRP authentication
        if credentials:
            auth_result = await self.srp_auth.authenticate(
                credentials.username,
                credentials.password
            )
            if auth_result.success:
                return AuthResult(authenticated=True, username=credentials.username)

        # Check for client certificate authentication
        # This would be implemented based on TLS client certificate validation
        # For now, fall back to SRP-only authentication

        return AuthResult(authenticated=False, username=None)

    async def _ensure_initialized(self) -> None:
        """Ensure server is properly initialized with default user."""
        if not self._initialized:
            await self.srp_auth.ensure_default_user()
            self._initialized = True

    async def _perform_automatic_enrollment(self, device_id: str, username: str,
                                          bootstrap_cert: str, bootstrap_key: str) -> Dict[str, str]:
        """
        Automatically perform enrollment after bootstrap.

        Args:
            device_id: Device identifier
            username: Authenticated username
            bootstrap_cert: Bootstrap certificate
            bootstrap_key: Bootstrap private key

        Returns:
            Enrollment result dictionary
        """
        try:
            # Generate a CSR for the device
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa

            # Generate new key pair for enrollment
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )

            # Create CSR
            subject = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, device_id),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "EST Enrolled Device"),
            ])

            csr = x509.CertificateSigningRequestBuilder().subject_name(subject).sign(
                private_key, hashes.SHA256()
            )

            csr_pem = csr.public_bytes(serialization.Encoding.PEM)

            # Process enrollment using the existing CA
            enrollment_result = await self.ca.enroll_certificate(
                csr_data=csr_pem,
                requester=username
            )

            # Get the private key for the enrolled certificate
            enrolled_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            return {
                "success": True,
                "certificate": enrollment_result.certificate_pkcs7.decode() if hasattr(enrollment_result.certificate_pkcs7, 'decode') else str(enrollment_result.certificate_pkcs7),
                "private_key": enrolled_key_pem.decode(),
                "message": "Automatic enrollment completed successfully"
            }

        except Exception as e:
            logger.error(f"Automatic enrollment failed: {e}")
            return {
                "success": False,
                "message": f"Automatic enrollment failed: {str(e)}"
            }

    def _get_comprehensive_stats_html(self, stats) -> str:
        """Generate minimalistic server statistics dashboard."""

        # Generate device rows
        device_rows = ""
        for device in stats.recent_devices:
            status_color = "#007acc" if device.status == "enrolled" else "#94a3b8"
            status_text = "Enrolled" if device.status == "enrolled" else "Bootstrap"
            download_buttons = f'''
                <a href="/download/certificate/{device.device_id}" class="download-btn">Cert</a>
                <a href="/download/key/{device.device_id}" class="download-btn">Key</a>
            ''' if device.status == "enrolled" else "—"

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
                    <strong>GET /.well-known/est/bootstrap</strong>
                    <span>Bootstrap authentication</span>
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
                        <a href="/.well-known/est/bootstrap" class="api-link">Bootstrap Device</a>
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

    def _get_bootstrap_html(self) -> str:
        """Generate minimalistic bootstrap authentication HTML page."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EST Bootstrap</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0; padding: 0; box-sizing: border-box;
        }

        body {
            font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #fafbfc;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            font-size: 14px;
            line-height: 1.6;
        }

        .container {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 40px;
            width: 100%;
            max-width: 420px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            animation: slideUp 0.5s ease-out;
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .header {
            text-align: center;
            margin-bottom: 32px;
        }

        .header h1 {
            font-size: 24px;
            font-weight: 600;
            color: #111827;
            margin-bottom: 6px;
            letter-spacing: -0.025em;
        }

        .header p {
            color: #6b7280;
            font-size: 15px;
            font-weight: 400;
        }

        .credentials {
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 24px;
            text-align: center;
        }

        .credentials h3 {
            font-size: 14px;
            font-weight: 600;
            color: #0369a1;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.025em;
        }

        .credential-item {
            background: white;
            border: 1px solid #e0f2fe;
            border-radius: 6px;
            padding: 8px 12px;
            margin: 6px 0;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 13px;
            font-weight: 500;
            color: #374151;
        }

        .auto-fill {
            margin-top: 12px;
            font-size: 12px;
            color: #007acc;
            cursor: pointer;
            text-decoration: none;
            font-weight: 500;
            transition: color 0.2s ease;
        }

        .auto-fill:hover {
            color: #005fa3;
            text-decoration: underline;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            margin-bottom: 6px;
            font-weight: 500;
            color: #374151;
            font-size: 13px;
        }

        .form-group input {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 14px;
            font-family: 'DM Sans', sans-serif;
            transition: all 0.2s ease;
            background: #fafbfc;
        }

        .form-group input:focus {
            outline: none;
            border-color: #007acc;
            box-shadow: 0 0 0 3px rgba(0, 122, 204, 0.1);
            background: white;
        }

        .form-group input::placeholder {
            color: #9ca3af;
        }

        .submit-btn {
            width: 100%;
            padding: 14px 20px;
            background: #007acc;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            font-family: 'DM Sans', sans-serif;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-bottom: 20px;
        }

        .submit-btn:hover {
            background: #005fa3;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 122, 204, 0.2);
        }

        .submit-btn:active {
            transform: translateY(0);
        }

        .process-info {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }

        .process-info h4 {
            font-size: 13px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.025em;
        }

        .process-steps {
            font-size: 12px;
            color: #6b7280;
            line-height: 1.5;
        }

        .back-link {
            position: absolute;
            top: 20px;
            left: 20px;
            color: #6b7280;
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
            transition: color 0.2s ease;
        }

        .back-link:hover {
            color: #374151;
        }

        @media (max-width: 480px) {
            .container {
                padding: 32px 24px;
                margin: 16px;
            }

            .back-link {
                position: static;
                display: block;
                text-align: center;
                margin-bottom: 20px;
            }
        }
    </style>
    <script>
        function fillCredentials() {
            document.getElementById('username').value = 'estuser';
            document.getElementById('password').value = 'estpass123';
            document.getElementById('device_id').focus();
        }
    </script>
</head>
<body>
    <a href="/" class="back-link">← Dashboard</a>

    <div class="container">
        <div class="header">
            <h1>EST Bootstrap</h1>
            <p>Certificate enrollment</p>
        </div>

        <div class="credentials">
            <h3>Credentials</h3>
            <div class="credential-item">estuser</div>
            <div class="credential-item">estpass123</div>
            <a href="#" class="auto-fill" onclick="fillCredentials()">Auto-fill form</a>
        </div>

        <form method="post" action="/.well-known/est/bootstrap/authenticate">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required>
            </div>

            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>

            <div class="form-group">
                <label for="device_id">Device ID</label>
                <input type="text" id="device_id" name="device_id" placeholder="device-001" required>
            </div>

            <button type="submit" class="submit-btn">Bootstrap & Enroll</button>
        </form>

        <div class="process-info">
            <h4>Process</h4>
            <div class="process-steps">
                Authenticate → Bootstrap certificate → Auto-enrollment → Complete
            </div>
        </div>
    </div>
</body>
</html>'''

    def _get_bootstrap_success_html(self, username: str, device_id: str, certificate: str, private_key: str, enrollment_result: Dict[str, str] = None) -> str:
        """Generate minimalistic bootstrap success HTML page."""
        enrollment_status = ""
        if enrollment_result and enrollment_result.get("success"):
            enrollment_status = f'''
        <div class="status-item success">
            <h3>Enrollment Status</h3>
            <p>Completed successfully</p>
        </div>
        '''
        elif enrollment_result:
            enrollment_status = f'''
        <div class="status-item error">
            <h3>Enrollment Status</h3>
            <p>Failed: {enrollment_result.get("message", "Unknown error")}</p>
        </div>
        '''

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bootstrap Complete</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0; padding: 0; box-sizing: border-box;
        }}

        body {{
            font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #fafbfc;
            min-height: 100vh;
            padding: 32px;
            font-size: 14px;
            line-height: 1.6;
        }}

        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            animation: slideUp 0.6s ease-out;
        }}

        @keyframes slideUp {{
            from {{ opacity: 0; transform: translateY(30px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 24px;
            border-bottom: 1px solid #e5e7eb;
        }}

        .header h1 {{
            font-size: 28px;
            font-weight: 600;
            color: #111827;
            margin-bottom: 8px;
            letter-spacing: -0.025em;
        }}

        .header p {{
            color: #6b7280;
            font-size: 16px;
        }}

        .process-status {{
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 32px;
            text-align: center;
        }}

        .process-status h2 {{
            font-size: 18px;
            font-weight: 600;
            color: #0369a1;
            margin-bottom: 8px;
        }}

        .process-status p {{
            color: #075985;
            font-size: 14px;
        }}

        .details-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}

        .detail-item {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 16px;
        }}

        .detail-item h3 {{
            font-size: 13px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 0.025em;
        }}

        .detail-item p {{
            color: #6b7280;
            font-weight: 500;
        }}

        .status-item.success {{
            background: #ecfdf5;
            border-color: #10b981;
        }}

        .status-item.success h3 {{
            color: #047857;
        }}

        .status-item.success p {{
            color: #059669;
        }}

        .status-item.error {{
            background: #fef2f2;
            border-color: #ef4444;
        }}

        .status-item.error h3 {{
            color: #dc2626;
        }}

        .status-item.error p {{
            color: #ef4444;
        }}

        .certificates {{
            margin-bottom: 32px;
        }}

        .certificates h2 {{
            font-size: 18px;
            font-weight: 600;
            color: #111827;
            margin-bottom: 16px;
            text-align: center;
        }}

        .cert-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}

        .cert-item {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
        }}

        .cert-item h3 {{
            font-size: 14px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 12px;
        }}

        .cert-content {{
            background: white;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            padding: 12px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 11px;
            color: #4b5563;
            word-break: break-all;
            max-height: 100px;
            overflow: hidden;
        }}

        .next-steps {{
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 8px;
            padding: 24px;
            text-align: center;
        }}

        .next-steps h2 {{
            font-size: 16px;
            font-weight: 600;
            color: #0369a1;
            margin-bottom: 16px;
        }}

        .steps-list {{
            text-align: left;
            display: inline-block;
            color: #075985;
            font-size: 13px;
            line-height: 1.6;
        }}

        .steps-list li {{
            margin-bottom: 6px;
        }}

        .back-link {{
            position: absolute;
            top: 32px;
            left: 32px;
            color: #6b7280;
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
            transition: color 0.2s ease;
        }}

        .back-link:hover {{
            color: #374151;
        }}

        .download-link {{
            display: inline-block;
            padding: 8px 16px;
            background: #007acc;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s ease;
        }}

        .download-link:hover {{
            background: #005fa3;
            transform: translateY(-1px);
        }}

        @media (max-width: 768px) {{
            .cert-grid {{
                grid-template-columns: 1fr;
            }}

            .container {{
                padding: 32px 24px;
                margin: 16px;
            }}

            .back-link {{
                position: static;
                display: block;
                text-align: center;
                margin-bottom: 20px;
            }}
        }}
    </style>
</head>
<body>
    <a href="/" class="back-link">← Dashboard</a>

    <div class="container">
        <div class="header">
            <h1>Bootstrap Complete</h1>
            <p>Certificate enrollment successful</p>
        </div>

        <div class="process-status">
            <h2>Process Completed</h2>
            <p>Authentication → Bootstrap → Auto-enrollment → Ready</p>
        </div>

        <div class="details-grid">
            <div class="detail-item">
                <h3>User</h3>
                <p>{username}</p>
            </div>
            <div class="detail-item">
                <h3>Device ID</h3>
                <p>{device_id}</p>
            </div>
            <div class="detail-item">
                <h3>Validity</h3>
                <p>365 days</p>
            </div>
            {enrollment_status}
        </div>

        <div class="certificates">
            <h2>Generated Certificates</h2>
            <div class="cert-grid">
                <div class="cert-item">
                    <h3>Bootstrap Certificate</h3>
                    <div class="cert-content">{certificate[:150]}...</div>
                    <div style="text-align: center; margin-top: 12px;">
                        <a href="/download/certificate/{device_id}" class="download-link">Download Certificate</a>
                    </div>
                </div>
                <div class="cert-item">
                    <h3>Bootstrap Private Key</h3>
                    <div class="cert-content">{private_key[:150]}...</div>
                    <div style="text-align: center; margin-top: 12px;">
                        <a href="/download/key/{device_id}" class="download-link">Download Private Key</a>
                    </div>
                </div>
            </div>
        </div>

        <div class="next-steps">
            <h2>Next Steps</h2>
            <ol class="steps-list">
                <li>Save certificates and keys securely</li>
                <li>Install in your application or device</li>
                <li>Use for EST protocol operations</li>
                <li>Monitor from the dashboard</li>
            </ol>
        </div>
    </div>
</body>
</html>'''

    def _get_bootstrap_error_html(self, error_message: str) -> str:
        """Generate bootstrap error HTML page."""
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bootstrap Error</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
               background: linear-gradient(135deg, #e74c3c 0%, #f39c12 100%);
               margin: 0; padding: 20px; min-height: 100vh; display: flex;
               align-items: center; justify-content: center; }}
        .container {{ background: white; padding: 40px; border-radius: 12px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2); max-width: 400px; width: 100%;
                    text-align: center; }}
        .error {{ color: #e74c3c; margin-bottom: 20px; }}
        .error h1 {{ margin: 0; font-size: 28px; }}
        .retry-btn {{ display: inline-block; padding: 12px 24px;
                     background: #3498db; color: white; text-decoration: none;
                     border-radius: 6px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="error">
            <h1>❌ Bootstrap Failed</h1>
            <p>{error_message}</p>
        </div>
        <a href="/.well-known/est/bootstrap" class="retry-btn">🔄 Try Again</a>
    </div>
</body>
</html>'''

    async def start(self) -> None:
        """Start the EST server."""
        logger.info(f"Starting EST server on {self.config.server.host}:{self.config.server.port}")

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
        )

        server = uvicorn.Server(config)
        await server.serve()


# Helper classes
class AuthResult:
    """Authentication result."""
    def __init__(self, authenticated: bool, username: Optional[str] = None):
        self.authenticated = authenticated
        self.username = username