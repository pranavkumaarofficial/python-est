# RA Certificate Authentication Implementation

## Overview

This document describes the Registration Authority (RA) certificate authentication implementation for the Python EST server. This allows the IQE gateway to authenticate using client certificates instead of username/password.

## What is RA Certificate Authentication?

In EST protocol, there are two primary authentication methods:

1. **Bootstrap Authentication**: Username/password for initial device enrollment
2. **RA Certificate Authentication**: Client certificate-based authentication for gateways/proxies

The IQE gateway acts as a proxy between medical devices and the EST server:

```
Medical Devices → IQE Gateway (with RA cert) → EST Server
```

The IQE gateway authenticates to the EST server using an RA certificate, then proxies enrollment requests from medical devices.

## Implementation Details

### 1. Client Certificate Extraction Middleware

**Location**: `src/python_est/server.py` lines 97-125

The middleware extracts the client certificate from the TLS connection and stores it in the request state:

```python
@self.app.middleware("http")
async def extract_client_cert(request: Request, call_next):
    """Extract client certificate from TLS connection and add to request state."""
    if hasattr(request, 'scope'):
        transport = request.scope.get('transport')
        if transport and hasattr(transport, 'get_extra_info'):
            ssl_object = transport.get_extra_info('ssl_object')
            if ssl_object:
                try:
                    cert_der = ssl_object.getpeercert(binary_form=True)
                    if cert_der:
                        cert = x509.load_der_x509_certificate(cert_der)
                        request.state.client_cert = cert
                except Exception as e:
                    logger.debug(f"No client certificate: {e}")

    response = await call_next(request)
    return response
```

**Key Points**:
- Runs on every HTTP request
- Accesses the SSL object from uvicorn's transport layer
- Converts DER certificate to Python cryptography object
- Stores in `request.state` for authentication handler

### 2. Certificate Validation

**Location**: `src/python_est/server.py` lines 471-512

Validates that the client certificate is signed by the EST server's CA:

```python
async def _validate_client_certificate(self, client_cert: x509.Certificate) -> bool:
    """Validate that client certificate is signed by our CA."""
    ca_cert = self.ca._ca_cert

    # Check issuer matches our CA
    if client_cert.issuer != ca_cert.subject:
        return False

    # Check certificate validity period
    now = datetime.now(timezone.utc)
    if now < client_cert.not_valid_before_utc:
        return False
    if now > client_cert.not_valid_after_utc:
        return False

    return True
```

**Validation Checks**:
1. Certificate issuer matches CA subject (signed by our CA)
2. Current time is after `not_valid_before_utc`
3. Current time is before `not_valid_after_utc`

**Note**: This is a simplified validation. In production, you may want to add:
- Certificate revocation checking (CRL/OCSP)
- Extended key usage validation (CLIENT_AUTH)
- Certificate signature verification

### 3. Authentication Logic

**Location**: `src/python_est/server.py` lines 436-469

Updated authentication to try client certificate first, then fall back to password:

```python
async def _authenticate_request(self, request: Request, credentials: Optional[HTTPBasicCredentials]) -> AuthResult:
    """Authenticate EST request using SRP or client certificate."""

    # Try client certificate authentication first (for RA/gateway auth)
    if hasattr(request.state, 'client_cert'):
        client_cert = request.state.client_cert
        if await self._validate_client_certificate(client_cert):
            # Extract CN from certificate subject
            cn = None
            for attr in client_cert.subject:
                if attr.oid == NameOID.COMMON_NAME:
                    cn = attr.value
                    break

            username = cn or "client-cert-user"
            logger.info(f"Client certificate authentication successful: {username}")
            return AuthResult(authenticated=True, username=username, auth_method="client-certificate")

    # Fall back to SRP/password authentication
    if credentials:
        auth_result = await self.srp_auth.authenticate(
            credentials.username,
            credentials.password
        )
        if auth_result.success:
            logger.info(f"SRP authentication successful: {credentials.username}")
            return AuthResult(authenticated=True, username=credentials.username, auth_method="srp")

    return AuthResult(authenticated=False, username=None, auth_method="none")
```

**Authentication Flow**:
1. Check if request has client certificate
2. If yes, validate certificate
3. If valid, extract CN from certificate subject for username
4. If no client cert or invalid, try SRP/password authentication
5. If both fail, return authentication failure

### 4. Uvicorn SSL Configuration

**Location**: `src/python_est/server.py` lines 1037-1048

Updated uvicorn config to enable client certificate handling:

```python
config = uvicorn.Config(
    app=self.app,
    host=self.config.server.host,
    port=self.config.server.port,
    ssl_keyfile=str(self.config.tls.key_file),
    ssl_certfile=str(self.config.tls.cert_file),
    ssl_ca_certs=str(self.config.tls.ca_file),
    ssl_cert_reqs=ssl.CERT_OPTIONAL,  # Allow but don't require client certs
)
```

**Key Configuration**:
- `ssl_ca_certs`: Path to CA certificate for validating client certificates
- `ssl_cert_reqs=ssl.CERT_OPTIONAL`: Accept connections with or without client certificates

This allows both:
- RA authentication (IQE gateway with client cert)
- Bootstrap authentication (medical devices with username/password)

## Generating RA Certificates

Use the provided script to generate RA certificates:

```bash
python3 generate_ra_certificate.py
```

This creates:
- `certs/iqe-ra-key.pem` - RA private key
- `certs/iqe-ra-cert.pem` - RA certificate with CLIENT_AUTH extended key usage

**⚠️ IMPORTANT**: Provide both files to the IQE team. They need:
1. `iqe-ra-cert.pem` - For authentication
2. `iqe-ra-key.pem` - Private key (keep secure!)
3. `ca-cert.pem` - To verify EST server's TLS certificate

## Testing RA Authentication

### Manual Test with curl

```bash
# Generate test CSR
openssl req -new -newkey rsa:2048 -nodes \
  -keyout test-key.pem -out test-csr.pem \
  -subj "/CN=test-pump/O=Hospital/C=US"

# Convert to DER
openssl req -in test-csr.pem -outform DER -out test-csr.der

# Test enrollment with RA certificate
curl -vk https://10.42.56.101:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  --cacert certs/ca-cert.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @test-csr.der \
  -o test-cert.p7

# Verify certificate
openssl pkcs7 -inform DER -in test-cert.p7 -print_certs
```

### Automated Test Script

```bash
chmod +x test_ra_auth.sh
./test_ra_auth.sh
```

The test script will:
1. Retrieve CA certificates
2. Generate a test CSR
3. Enroll using RA certificate authentication
4. Verify the issued certificate

## Server Logs

When RA authentication is used, you'll see logs like:

```
INFO: Client certificate found: CN=iqe-gateway,O=Hospital,C=US
INFO: Client certificate validated: CN=iqe-gateway,O=Hospital,C=US
INFO: Client certificate authentication successful: iqe-gateway
INFO: Enrollment request from: iqe-gateway (RA Certificate Auth)
```

## IQE Gateway Configuration

The IQE team needs to configure their gateway with:

1. **Client Certificate**: `iqe-ra-cert.pem`
2. **Client Private Key**: `iqe-ra-key.pem`
3. **Server CA Certificate**: `ca-cert.pem` (to verify EST server)
4. **EST Server URL**: `https://10.42.56.101:8445`

### Example IQE Configuration

```yaml
est_server:
  url: https://10.42.56.101:8445
  ca_cert: /path/to/ca-cert.pem
  client_cert: /path/to/iqe-ra-cert.pem
  client_key: /path/to/iqe-ra-key.pem

endpoints:
  cacerts: /.well-known/est/cacerts
  bootstrap: /.well-known/est/bootstrap
  simpleenroll: /.well-known/est/simpleenroll
```

## Troubleshooting

### Issue: "No client certificate in connection"

**Cause**: IQE gateway not sending client certificate

**Solutions**:
1. Verify IQE has `iqe-ra-cert.pem` and `iqe-ra-key.pem` configured
2. Check IQE TLS configuration enables client certificate
3. Verify files are readable by IQE process

### Issue: "Client certificate validation failed"

**Causes**:
1. Certificate expired
2. Certificate not signed by EST server's CA
3. Certificate not yet valid

**Solutions**:
1. Check certificate dates: `openssl x509 -in iqe-ra-cert.pem -noout -dates`
2. Verify certificate issuer: `openssl x509 -in iqe-ra-cert.pem -noout -issuer`
3. Regenerate RA certificate if needed

### Issue: HTTP 401 Unauthorized

**Cause**: Authentication failed (no valid client cert and no password)

**Solutions**:
1. Check server logs for authentication details
2. Verify IQE is sending client certificate
3. Try manual curl test to isolate issue

## Security Considerations

### RA Certificate Lifecycle

1. **Generation**: Create RA certificate with long validity (e.g., 2 years)
2. **Distribution**: Securely transfer to IQE team (encrypted channel)
3. **Storage**: IQE must protect private key (file permissions, encryption)
4. **Rotation**: Regenerate before expiry and update IQE configuration
5. **Revocation**: If compromised, remove certificate and regenerate

### Best Practices

1. **Separate RA Certificates**: Each IQE gateway should have unique RA certificate
2. **Monitor Usage**: Track which RA certificates are being used
3. **Audit Logs**: Log all RA authentication attempts
4. **Regular Rotation**: Rotate RA certificates annually
5. **Secure Storage**: Protect RA private keys with file permissions (600)

## Architecture Diagram

```
┌─────────────────┐
│ Medical Devices │
│  (Pumps, etc)   │
└────────┬────────┘
         │
         │ HTTP/TLS (no cert)
         │
         ▼
┌─────────────────────────┐
│    IQE Gateway          │
│                         │
│ RA Certificate:         │
│  - iqe-ra-cert.pem     │
│  - iqe-ra-key.pem      │
└────────┬────────────────┘
         │
         │ HTTPS with client cert
         │ (mutual TLS)
         ▼
┌─────────────────────────┐
│   Python EST Server     │
│                         │
│ 1. Extract client cert  │
│ 2. Validate cert        │
│ 3. Authenticate request │
│ 4. Issue certificate    │
└─────────────────────────┘
```

## Configuration Summary

### EST Server Configuration (`config-iqe.yaml`)

```yaml
tls:
  cert_file: certs/server.crt
  key_file: certs/server.key
  ca_file: certs/ca-cert.pem  # Used to validate client certs

response_format: base64  # IQE expects base64
```

### Files to Provide to IQE Team

1. `certs/ca-cert.pem` - EST server CA certificate
2. `certs/iqe-ra-cert.pem` - RA certificate for authentication
3. `certs/iqe-ra-key.pem` - RA private key (SECURE!)

### Important Notes

- RA authentication takes precedence over username/password
- Both authentication methods work simultaneously
- Medical devices can still use bootstrap (username/password)
- IQE gateway uses RA certificate for all enrollments

## Next Steps

1. ✅ RA authentication implemented
2. ⏳ Deploy updated server to Ubuntu VM
3. ⏳ Test with curl using RA certificates
4. ⏳ Provide RA certificate files to IQE team
5. ⏳ IQE team configures gateway with RA certificates
6. ⏳ Test end-to-end enrollment through IQE gateway

## References

- RFC 7030: Enrollment over Secure Transport (EST)
- Section 3.3.2: Client Authentication
- Section 3.6.1: Explicit TA Database and Implicit TA Database
