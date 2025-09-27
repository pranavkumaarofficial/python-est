"""
EST Protocol Data Models

Pydantic models for EST request and response data structures.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class EnrollmentRequest(BaseModel):
    """EST enrollment request model."""

    csr: str = Field(..., description="PKCS#10 Certificate Signing Request in PEM format")
    requester: Optional[str] = Field(None, description="Requester identifier")


class EnrollmentResponse(BaseModel):
    """EST enrollment response model."""

    certificate: str = Field(..., description="X.509 certificate in PKCS#7 format")
    serial_number: str = Field(..., description="Certificate serial number")
    valid_until: datetime = Field(..., description="Certificate expiration date")
    issuer: str = Field(..., description="Certificate issuer DN")


class BootstrapRequest(BaseModel):
    """EST bootstrap request model."""

    username: str = Field(..., description="SRP username")
    password: str = Field(..., description="SRP password")
    device_id: str = Field(..., description="Device identifier")


class BootstrapResponse(BaseModel):
    """EST bootstrap response model."""

    certificate: str = Field(..., description="Bootstrap certificate in PEM format")
    private_key: str = Field(..., description="Private key in PEM format")
    valid_until: datetime = Field(..., description="Certificate expiration date")
    device_id: str = Field(..., description="Device identifier")


class CAInfoResponse(BaseModel):
    """CA information response model."""

    ca_certificates: str = Field(..., description="CA certificates in PKCS#7 format")
    trust_anchors: Optional[str] = Field(None, description="Trust anchor certificates")


class ServerStatusResponse(BaseModel):
    """Server status response model."""

    service: str = Field("Python-EST Server", description="Service name")
    version: str = Field("1.0.0", description="Server version")
    protocol: str = Field("RFC 7030", description="Protocol specification")
    status: str = Field("running", description="Server status")
    uptime: Optional[str] = Field(None, description="Server uptime")
    endpoints: list[str] = Field(
        default=[
            "/.well-known/est/cacerts",
            "/.well-known/est/bootstrap",
            "/.well-known/est/simpleenroll",
            "/.well-known/est/simplereenroll"
        ],
        description="Available EST endpoints"
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class DeviceInfo(BaseModel):
    """Device information model for tracking."""

    device_id: str = Field(..., description="Device identifier")
    username: str = Field(..., description="Authenticated username")
    ip_address: str = Field(..., description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    bootstrap_time: datetime = Field(default_factory=datetime.utcnow, description="Bootstrap timestamp")
    enrollment_time: Optional[datetime] = Field(None, description="Enrollment timestamp")
    bootstrap_cert_serial: Optional[str] = Field(None, description="Bootstrap certificate serial number")
    enrolled_cert_serial: Optional[str] = Field(None, description="Enrolled certificate serial number")
    status: str = Field("bootstrap_only", description="Device status (bootstrap_only, enrolled, error)")
    last_activity: datetime = Field(default_factory=datetime.utcnow, description="Last activity timestamp")


class ServerStats(BaseModel):
    """Comprehensive server statistics model."""

    service: str = Field("Python-EST Server", description="Service name")
    version: str = Field("1.0.0", description="Server version")
    protocol: str = Field("RFC 7030", description="Protocol specification")
    status: str = Field("running", description="Server status")
    uptime: str = Field(..., description="Server uptime")

    # Device statistics
    total_devices: int = Field(0, description="Total devices that attempted bootstrap")
    enrolled_devices: int = Field(0, description="Successfully enrolled devices")
    active_devices: int = Field(0, description="Devices active in last 24 hours")

    # Certificate statistics
    certificates_issued: int = Field(0, description="Total certificates issued")
    bootstrap_certificates: int = Field(0, description="Bootstrap certificates issued")
    enrollment_certificates: int = Field(0, description="Enrollment certificates issued")

    # Request statistics
    total_requests: int = Field(0, description="Total requests processed")
    bootstrap_requests: int = Field(0, description="Bootstrap requests")
    enrollment_requests: int = Field(0, description="Enrollment requests")
    failed_requests: int = Field(0, description="Failed requests")

    # Recent activity
    recent_devices: List[DeviceInfo] = Field(default=[], description="Recent device activity")

    # Server configuration
    endpoints: List[str] = Field(
        default=[
            "/.well-known/est/cacerts",
            "/.well-known/est/bootstrap",
            "/.well-known/est/simpleenroll",
            "/.well-known/est/simplereenroll"
        ],
        description="Available EST endpoints"
    )