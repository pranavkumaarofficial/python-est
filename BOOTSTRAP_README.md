# EST Bootstrap Authentication Implementation

## Overview

This implementation adds SRP (Secure Remote Password) bootstrap authentication to the Python-EST server, allowing clients to obtain initial certificates without requiring existing certificates.

## New Features

### 1. Bootstrap Authentication Endpoints

- **Login Page**: `https://localhost:8443/bootstrap` - HTML form for SRP credentials
- **Form Handler**: `/bootstrap/login` - Processes login form submissions
- **EST Endpoint**: `/.well-known/est/bootstrap` - RFC 7030 compliant bootstrap endpoint

### 2. SRP User Management

- **Database**: `certs/srp_users.db` - Stores SRP verifiers (not passwords)
- **Management Script**: `create_srp_users.py` - Add/list/manage SRP users

### 3. Configuration

Added to `python_est.cfg`:
```ini
[SRP]
userdb = certs/srp_users.db

[Bootstrap]
enabled = true
endpoint = /.well-known/est/bootstrap
```

## Quick Start

1. **Setup SRP Users**:
   ```bash
   python create_srp_users.py setup
   ```

2. **Start Server**:
   ```bash
   python main.py -c python_est.cfg
   ```

3. **Access Bootstrap**:
   - Open browser to `https://localhost:8443/bootstrap`
   - Login with demo credentials (see below)

## Demo Users

```
Username: testuser    | Password: testpass123
Username: device001   | Password: SecureP@ss001
Username: admin       | Password: AdminP@ss456
```

## Security Features

- **SRP Protocol**: No plaintext passwords transmitted
- **Verifier Storage**: Server stores password verifiers, not passwords
- **Dual Authentication**: SRP for bootstrap, certificates for production
- **Session Validation**: Form submissions validated against SRP session

## Files Modified

- `python_est/core/est_handler.py` - Added bootstrap endpoints and authentication logic
- `python_est/core/secureserver.py` - Modified to allow connections without client certificates
- `python_est/core/helper.py` - Updated TLS options for bootstrap compatibility
- `python_est.cfg` - Added SRP and Bootstrap configuration sections

## Files Added

- `create_srp_users.py` - SRP user management utility
- `test_bootstrap_client.py` - Test client for SRP authentication

## Known Issues

- TLS handshake compatibility with some clients (curl)
- SRP database user listing has encoding issues (functional but cosmetic)

## Next Steps

1. Fix TLS handshake compatibility
2. Add certificate generation for successful bootstrap logins
3. Implement certificate lifecycle management
4. Add rate limiting and security hardening

## Architecture

```
Client → SRP Handshake → Bootstrap Login → Future: Certificate Enrollment
   ↓
   └── Production: Certificate-based authentication
```

This implementation provides the foundation for secure certificate bootstrap while maintaining backward compatibility with existing certificate-based authentication.