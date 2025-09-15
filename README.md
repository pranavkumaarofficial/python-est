# Python-EST

**Enterprise EST (RFC 7030) Protocol Server in Python**

Python-EST is a production-ready implementation of the EST (Enrollment over Secure Transport) protocol that enables secure certificate enrollment, renewal, and CA certificate distribution for enterprise PKI infrastructure.

## Features

- **RFC 7030 Compliant** - Full EST protocol implementation
- **Bootstrap Authentication** - SRP-based initial certificate enrollment
- **Multi-CA Support** - OpenSSL, Microsoft ADCS, XCA, NetGuard integrations
- **TLS 1.3 Security** - Client certificate authentication (mTLS)
- **Enterprise Ready** - Production-grade logging and error handling
- **Modular Design** - Pluggable CA handler architecture

## Quick Start

```bash
# Clone repository
git clone https://github.com/pranavkumaarofficial/python-est.git
cd python-est

# Install dependencies
pip install -r requirements.txt

# Generate development certificates (creates local private keys)
python setup_certs.py

# Setup SRP bootstrap users (for initial enrollment)
python create_srp_users.py setup

# Start server
python main.py -c python_est.cfg

# Test CA certificates endpoint
curl -k https://localhost:8443/.well-known/est/cacerts

# Access bootstrap login (in browser)
# https://localhost:8443/bootstrap
```

## EST Endpoints

### Standard EST Endpoints
- `GET /.well-known/est/cacerts` - CA certificate distribution
- `POST /.well-known/est/simpleenroll` - Certificate enrollment
- `POST /.well-known/est/simplereenroll` - Certificate renewal

### Bootstrap Endpoints (New!)
- `GET /.well-known/est/bootstrap` - Bootstrap login page
- `GET /bootstrap` - Alternative bootstrap access
- `POST /bootstrap/login` - Bootstrap form submission

## Configuration

Edit `python_est.cfg`:

```ini
[Daemon]
port = 8443
cert_file = certs/server.crt
key_file = certs/server.key

[CAhandler]
handler_file = python_est/handlers/openssl_ca_handler_fixed.py
issuing_ca_cert = certs/ca-cert.pem
issuing_ca_key = certs/ca-key.pem

[SRP]
userdb = certs/srp_users.db

[Bootstrap]
enabled = true
endpoint = /.well-known/est/bootstrap
```

## Usage Examples

### Bootstrap Authentication (New Clients)
```bash
# Access bootstrap login page in browser
https://localhost:8443/bootstrap

# Demo credentials:
# Username: testuser | Password: testpass123
# Username: device001 | Password: SecureP@ss001
# Username: admin | Password: AdminP@ss456

# Test SRP authentication programmatically
python test_bootstrap_client.py testuser testpass123
```

### Standard Certificate Operations
```bash
# Get CA certificates (no authentication required)
curl -k https://localhost:8443/.well-known/est/cacerts

# Enroll certificate with existing client certificate
curl -X POST \
  --cert certs/client.crt --key certs/client.key \
  --data-binary @device.csr \
  -H "Content-Type: application/pkcs10" \
  https://localhost:8443/.well-known/est/simpleenroll
```

### SRP User Management
```bash
# List existing users
python create_srp_users.py list

# Add new user
python create_srp_users.py add newuser securepassword123

# Create fresh database with demo users
python create_srp_users.py setup
```

## Use Cases

- **IoT Device Provisioning** - Automated certificate enrollment for devices
- **Enterprise PKI** - Integration with existing certificate authorities
- **DevOps Automation** - Certificate lifecycle management
- **Zero-Trust Security** - mTLS authentication infrastructure
- **Bootstrap Authentication** - Initial certificate enrollment without existing certificates

## Backend Logging & Recording

All authentication attempts and certificate operations are logged:

- **SRP Authentication**: Username, fingerprint, session details
- **Bootstrap Access**: Form submissions, success/failure events
- **Certificate Operations**: Enrollment, renewal, CA certificate requests
- **Security Events**: Authentication failures, unauthorized access attempts

Logs are recorded with timestamps and client IP addresses for audit trails.

## Future Scope & Roadmap

### Phase 2: Enhanced Security
- **Rate Limiting**: Prevent brute force attacks on bootstrap endpoints
- **Account Lockout**: Temporary lockout after failed attempts
- **Certificate Lifecycle**: Automatic short-lived bootstrap certificates
- **Session Management**: Secure session handling and expiration

### Phase 3: Advanced Features
- **Multi-Factor Authentication**: TOTP/SMS integration for bootstrap
- **Certificate Templates**: Configurable certificate profiles for different device types
- **Webhook Integration**: Real-time notifications for certificate events
- **REST API**: Programmatic access to certificate operations

### Phase 4: Enterprise Integration
- **LDAP/Active Directory**: Integration with enterprise identity systems
- **SCEP Support**: Simple Certificate Enrollment Protocol compatibility
- **High Availability**: Clustered deployment with load balancing
- **Database Backend**: PostgreSQL/MySQL for scalable user management

### Phase 5: Cloud & Compliance
- **Cloud Deployment**: Docker containers, Kubernetes support
- **FIPS 140-2**: Federal compliance for government environments
- **HSM Integration**: Hardware Security Module support
- **Audit Compliance**: SOX, HIPAA, PCI-DSS audit trail features

### Development Tools
- **Certificate Monitoring**: Dashboard for certificate expiration tracking
- **API Documentation**: OpenAPI/Swagger specification
- **Testing Framework**: Automated integration testing suite
- **Performance Monitoring**: Metrics and alerting for production deployments

### Architecture Enhancements
- **Plugin System**: Third-party CA handler development framework
- **Configuration Management**: Dynamic configuration without restart
- **Backup/Recovery**: Automated backup of certificates and configurations
- **Migration Tools**: Import/export from other PKI systems

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes and test
4. Submit pull request

For bugs and feature requests, please use [GitHub Issues](https://github.com/pranavkumaarofficial/python-est/issues).

Topics: est-protocol, rfc7030, pki, certificate-management,tls, openssl, enterprise-security, python, cryptography, certificate-authority, iot-security, zero-trust, mtls, pkcs7, certificate-enrollment.
