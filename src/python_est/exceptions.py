"""
EST Protocol Exceptions

Custom exception classes for EST protocol operations.
"""

from typing import Optional


class ESTError(Exception):
    """Base exception for all EST protocol errors."""

    def __init__(self, message: str, error_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class ESTAuthenticationError(ESTError):
    """Raised when EST authentication fails."""

    def __init__(self, message: str = "EST authentication failed") -> None:
        super().__init__(message, error_code=401)


class ESTEnrollmentError(ESTError):
    """Raised when certificate enrollment fails."""

    def __init__(self, message: str = "Certificate enrollment failed") -> None:
        super().__init__(message, error_code=500)


class ESTConfigurationError(ESTError):
    """Raised when EST server configuration is invalid."""

    def __init__(self, message: str = "EST configuration error") -> None:
        super().__init__(message, error_code=500)


class ESTCertificateError(ESTError):
    """Raised when certificate operations fail."""

    def __init__(self, message: str = "Certificate operation failed") -> None:
        super().__init__(message, error_code=500)


class ESTNetworkError(ESTError):
    """Raised when network operations fail."""

    def __init__(self, message: str = "Network operation failed") -> None:
        super().__init__(message, error_code=503)