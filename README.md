# Python-EST

**Enterprise EST (RFC 7030) Protocol Server in Python**

Python-EST is a production-ready implementation of the EST (Enrollment over Secure Transport) protocol that enables secure certificate enrollment, renewal, and CA certificate distribution for enterprise PKI infrastructure.

## Features

- **RFC 7030 Compliant** - Full EST protocol implementation
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

# Generate development certificates
python setup_certs.py

# Start server
python main.py -c python_est.cfg

# Test endpoints
curl -k https://localhost:8443/.well-known/est/cacerts
```

## EST Endpoints

- `GET /.well-known/est/cacerts` - CA certificate distribution
- `POST /.well-known/est/simpleenroll` - Certificate enrollment
- `POST /.well-known/est/simplereenroll` - Certificate renewal

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
```

## Usage Example

```bash
# Enroll certificate with client authentication
curl -X POST \
  --cert certs/client.crt --key certs/client.key \
  --data-binary @device.csr \
  -H "Content-Type: application/pkcs10" \
  https://localhost:8443/.well-known/est/simpleenroll
```

## Use Cases

- **IoT Device Provisioning** - Automated certificate enrollment for devices
- **Enterprise PKI** - Integration with existing certificate authorities  
- **DevOps Automation** - Certificate lifecycle management
- **Zero-Trust Security** - mTLS authentication infrastructure

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes and test
4. Submit pull request

For bugs and feature requests, please use [GitHub Issues](https://github.com/pranavkumaarofficial/python-est/issues).

Topics: est-protocol, rfc7030, pki, certificate-management,tls, openssl, enterprise-security, python, cryptography, certificate-authority, iot-security, zero-trust, mtls, pkcs7, certificate-enrollment.
