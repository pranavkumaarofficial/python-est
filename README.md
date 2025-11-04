# Python-EST Server

Professional Python implementation of RFC 7030 EST (Enrollment over Secure Transport) protocol with **RA Certificate Authentication** support via Nginx reverse proxy.

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Git
- OpenSSL (for certificate verification)

### Deploy in 5 Minutes

```bash
# 1. Clone/navigate to project
cd ~/python-est

# 2. Deploy with nginx (RA authentication)
docker-compose -f docker-compose-nginx.yml up -d --build

# 3. Check status
docker-compose -f docker-compose-nginx.yml ps

# 4. Access dashboard
curl -k https://localhost:8445/
```

## 📋 Features

- ✅ **RFC 7030 Compliant** - Full EST protocol implementation
- ✅ **RA Certificate Authentication** - Client certificate-based authentication
- ✅ **SRP Authentication** - Username/password fallback
- ✅ **Nginx Reverse Proxy** - Production-ready architecture
- ✅ **Docker & Docker Compose** - Easy deployment
- ✅ **Base64 & DER Response Formats** - IQE gateway compatible
- ✅ **FastAPI Backend** - Modern, async Python framework
- ✅ **Comprehensive Dashboard** - Real-time statistics and monitoring

## 🏗️ Architecture

### With Nginx (Production - RA Authentication)

```
IQE Gateway (with RA cert)
         ↓ HTTPS (8445) + TLS Client Cert
    ┌─────────┐
    │  Nginx  │ TLS termination, cert extraction
    └────┬────┘
         ↓ HTTP (8000) + Headers
┌────────────────┐
│ Python EST     │ Certificate authentication & issuance
└────────────────┘
```

### Standalone (Development)

```
Client
   ↓ HTTPS (8445) + Basic Auth
┌────────────────┐
│ Python EST     │ SRP authentication & issuance
└────────────────┘
```

## 📦 Installation

### Option 1: Docker Compose with Nginx (Recommended)

```bash
# Build and start
docker-compose -f docker-compose-nginx.yml up -d --build

# View logs
docker-compose -f docker-compose-nginx.yml logs -f

# Stop
docker-compose -f docker-compose-nginx.yml down
```

### Option 2: Standalone Docker

```bash
# Build
docker build -t python-est-server .

# Run
docker run -d \
  --name python-est-server \
  -p 8445:8445 \
  -v $(pwd)/certs:/app/certs \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config-iqe.yaml:/app/config.yaml \
  python-est-server

# Logs
docker logs -f python-est-server
```

### Option 3: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python -m python_est.cli start --config config-iqe.yaml
```

## 🔧 Configuration

### Nginx Mode (RA Authentication)

**Use `config-nginx.yaml`:**

```yaml
server:
  host: 0.0.0.0
  port: 8000  # HTTP (nginx forwards here)

response_format: base64  # For IQE compatibility
```

**Docker Compose:**

```yaml
environment:
  - NGINX_MODE=true
  - PORT=8000
volumes:
  - ./config-nginx.yaml:/app/config.yaml:ro
```

### Standalone Mode

**Use `config-iqe.yaml`:**

```yaml
server:
  host: 0.0.0.0
  port: 8445  # HTTPS

response_format: base64
```

## 🔐 Certificate Management

### Generate Certificates

```bash
# Generate CA and server certificates
python3 generate_certificates_python.py

# Create bootstrap user
python3 create_iqe_user.py

# Generate RA certificate for IQE gateway
python3 generate_ra_certificate.py
```

### Verify Certificates

```bash
# Verify server certificate
openssl verify -CAfile certs/ca-cert.pem certs/server.crt

# Verify RA certificate
openssl verify -CAfile certs/ca-cert.pem certs/iqe-ra-cert.pem

# Check certificate details
openssl x509 -in certs/server.crt -noout -text
```

## 🧪 Testing

### Test Health Endpoint

```bash
# Via nginx
curl -k https://localhost:8445/health

# Direct to backend (nginx mode)
docker exec python-est-server curl http://localhost:8000/health
```

### Test CA Certificates

```bash
curl -k https://localhost:8445/.well-known/est/cacerts -o cacerts.p7

# Verify PKCS#7
file cacerts.p7
base64 -d cacerts.p7 | openssl pkcs7 -inform DER -print_certs
```

### Test RA Authentication

```bash
# Generate test CSR
python3 << 'EOF'
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, 'US'),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'Hospital'),
    x509.NameAttribute(NameOID.COMMON_NAME, 'test-device'),
])).sign(key, hashes.SHA256())

with open('/tmp/test.der', 'wb') as f:
    f.write(csr.public_bytes(serialization.Encoding.DER))
print("CSR created at /tmp/test.der")
EOF

# Enroll with RA certificate
curl -vk https://localhost:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @/tmp/test.der \
  -o device-cert.p7

# Expected: HTTP 200
```

## 📊 Monitoring

### Dashboard

Access at: **https://localhost:8445/**

Shows:
- Server statistics
- Connected devices
- Recent activity
- Certificate issuance metrics

### Logs

```bash
# All logs
docker-compose -f docker-compose-nginx.yml logs -f

# Python server only
docker-compose -f docker-compose-nginx.yml logs -f python-est-server

# Nginx only
docker-compose -f docker-compose-nginx.yml logs -f nginx

# Filter for RA authentication
docker-compose -f docker-compose-nginx.yml logs python-est-server | grep "Client certificate"
```

## 🔍 Troubleshooting

### Common Issues

#### HTTP 401 Unauthorized

**Cause**: RA certificate not being sent or validated

**Fix**:
```bash
# Check nginx is forwarding headers
docker exec est-nginx cat /etc/nginx/nginx.conf | grep "X-SSL-Client"

# Check Python is receiving headers
docker-compose -f docker-compose-nginx.yml logs python-est-server | grep "Client certificate"
```

#### Port Already in Use

**Cause**: Port 8445 is occupied

**Fix**:
```bash
# Find what's using the port
sudo lsof -i :8445

# Stop old containers
docker-compose -f docker-compose-nginx.yml down
docker stop python-est-server 2>/dev/null || true
```

#### Certificate Validation Failed

**Cause**: Certificate chain mismatch

**Fix**:
```bash
# Regenerate all certificates together
rm -rf certs/*
python3 generate_certificates_python.py
python3 create_iqe_user.py
python3 generate_ra_certificate.py
```

### Debug Commands

```bash
# Check container status
docker-compose -f docker-compose-nginx.yml ps

# Exec into Python container
docker exec -it python-est-server bash

# Exec into nginx container
docker exec -it est-nginx sh

# Test backend connectivity
docker exec est-nginx wget -O- http://python-est-server:8000/health

# View nginx config
docker exec est-nginx cat /etc/nginx/nginx.conf
```

## 📚 Documentation

- **[NGINX_DEPLOYMENT_GUIDE.md](NGINX_DEPLOYMENT_GUIDE.md)** - Complete nginx deployment guide
- **[MANUAL_DEPLOYMENT.md](MANUAL_DEPLOYMENT.md)** - Step-by-step manual commands
- **[QUICK_START_NGINX.md](QUICK_START_NGINX.md)** - Quick reference
- **[FIXES_APPLIED.md](FIXES_APPLIED.md)** - Recent bug fixes
- **[RA_AUTH_IMPLEMENTATION.md](RA_AUTH_IMPLEMENTATION.md)** - RA authentication details

## 🚀 Deployment

### Production Checklist

Before deploying to production:

- [ ] Generate fresh certificates
- [ ] Verify certificate chain
- [ ] Configure firewall (allow port 8445)
- [ ] Set up monitoring
- [ ] Configure backups for `data/` directory
- [ ] Review security settings in config
- [ ] Test RA authentication
- [ ] Test fallback password authentication
- [ ] Document restart procedure
- [ ] Set up log rotation

### IQE Integration

For IQE gateway integration:

1. **Generate RA certificate**: `python3 generate_ra_certificate.py`
2. **Package files**:
   ```bash
   mkdir iqe_deployment_package
   cp certs/ca-cert.pem iqe_deployment_package/
   cp certs/iqe-ra-cert.pem iqe_deployment_package/
   cp certs/iqe-ra-key.pem iqe_deployment_package/
   ```
3. **Transfer to IQE team**
4. **IQE configuration**:
   ```yaml
   est_server:
     url: https://10.42.56.101:8445
     ca_cert: /path/to/ca-cert.pem
     client_cert: /path/to/iqe-ra-cert.pem
     client_key: /path/to/iqe-ra-key.pem
   ```

## 🛠️ Development

### Project Structure

```
python-est/
├── src/
│   └── python_est/
│       ├── server.py       # FastAPI server
│       ├── ca.py           # Certificate authority
│       ├── auth.py         # SRP authentication
│       ├── config.py       # Configuration management
│       └── cli.py          # Command-line interface
├── nginx/
│   └── nginx.conf          # Nginx configuration
├── docker/
│   └── entrypoint.sh       # Docker entrypoint
├── certs/                  # Certificates (generated)
├── data/                   # Database (runtime)
├── Dockerfile              # Docker image definition
├── docker-compose-nginx.yml # Docker Compose for nginx mode
├── requirements.txt        # Python dependencies
└── pyproject.toml          # Package metadata
```

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio

# Run tests
pytest tests/

# With coverage
pytest --cov=python_est tests/
```

### Making Changes

```bash
# 1. Make code changes
vim src/python_est/server.py

# 2. Rebuild Docker image
docker-compose -f docker-compose-nginx.yml build --no-cache

# 3. Restart services
docker-compose -f docker-compose-nginx.yml up -d

# 4. Check logs
docker-compose -f docker-compose-nginx.yml logs -f
```

## 📄 License

MIT License - See LICENSE file for details

## 👤 Author

**Pranav Kumaar**

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For issues or questions:

1. Check the [documentation](#-documentation)
2. Review [troubleshooting](#-troubleshooting)
3. Open an issue on GitHub

## 🔗 Links

- **RFC 7030**: https://tools.ietf.org/html/rfc7030
- **FastAPI**: https://fastapi.tiangolo.com/
- **Nginx**: https://nginx.org/
- **Docker**: https://www.docker.com/

---

**Status**: Production-Ready ✅

**Last Updated**: 2025-11-04

**Version**: 1.0.0
