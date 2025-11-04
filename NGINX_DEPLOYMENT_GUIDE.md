# EST Server with Nginx - Complete Deployment Guide

## Overview

This guide documents the **production-ready solution** for RA certificate authentication using nginx as a reverse proxy.

### Why Nginx?

The direct uvicorn approach fails because `request.scope['transport']` is None in Docker containers. **Nginx solves this** by:

1. **TLS Termination**: Nginx handles the TLS handshake and extracts client certificates reliably
2. **Header Forwarding**: Nginx passes the certificate to Python via HTTP headers
3. **Platform Independent**: Works on Windows, Linux, Docker, Kubernetes
4. **Industry Standard**: This is how production systems handle client certs in containers

### Architecture

```
┌─────────────────┐
│  IQE Gateway    │
│  (with RA cert) │
└────────┬────────┘
         │
         │ HTTPS + TLS Client Cert
         │ Port 8445
         ▼
┌─────────────────────────────────────┐
│  Nginx Container                    │
│  - TLS termination                  │
│  - Extract client certificate       │
│  - Validate against CA              │
│  - Forward cert via headers         │
└────────┬────────────────────────────┘
         │
         │ HTTP + Headers
         │ Internal network
         ▼
┌─────────────────────────────────────┐
│  Python EST Server Container        │
│  - Read cert from headers           │
│  - Validate & authenticate          │
│  - Issue certificates               │
└─────────────────────────────────────┘
```

## Files Created

### Configuration Files

1. **`nginx/nginx.conf`** - Nginx configuration
   - TLS termination on port 8445
   - Client certificate extraction
   - Header forwarding to Python backend

2. **`docker-compose-nginx.yml`** - Docker Compose orchestration
   - Python EST server container (HTTP on port 8000)
   - Nginx container (HTTPS on port 8445)
   - Health checks and networking

3. **`config-nginx.yaml`** - Python EST server config for nginx mode
   - HTTP on port 8000 (not HTTPS)
   - TLS config still present (for cert operations)

### Code Changes

4. **`src/python_est/server.py`** - Updated middleware and startup
   - Middleware reads client cert from nginx headers (`X-SSL-Client-Cert`)
   - Supports both nginx mode (HTTP) and standalone mode (HTTPS)
   - Controlled via `NGINX_MODE` environment variable

5. **`Dockerfile`** - Updated health checks
   - Supports both nginx mode (port 8000) and standalone (port 8445)

### Scripts

6. **`deploy-nginx.sh`** - Automated deployment
   - Validates certificates
   - Builds Docker images
   - Starts services
   - Runs health checks

7. **`test-ra-nginx.sh`** - Comprehensive testing
   - Tests RA authentication
   - Validates certificates
   - Checks server logs
   - Confirms RA auth is working

## Deployment Instructions

### Prerequisites

1. **Docker and Docker Compose installed**
   ```bash
   docker --version
   docker-compose --version
   ```

2. **Certificates generated**
   ```bash
   ls -la certs/
   # Should have:
   # - ca-cert.pem, ca-key.pem
   # - server.crt, server.key
   # - iqe-ra-cert.pem, iqe-ra-key.pem
   ```

3. **On Ubuntu VM** (not Windows - for production deployment)

### Step-by-Step Deployment

#### 1. Push Code to Git

```bash
# On Windows development machine
git add .
git commit -m "feat: Add nginx reverse proxy for RA authentication

- Nginx handles TLS termination and client cert extraction
- Python EST server reads certs from nginx headers
- Supports both nginx mode (HTTP) and standalone mode (HTTPS)
- Production-ready solution for Docker/K8s environments

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin deploy_v1
```

#### 2. Deploy on Ubuntu VM

```bash
# SSH into Ubuntu VM
ssh interop@ansible-virtual-machine

# Navigate to project
cd ~/Desktop/python-est

# Pull latest code
git pull origin deploy_v1

# Make scripts executable
chmod +x deploy-nginx.sh test-ra-nginx.sh

# Deploy!
./deploy-nginx.sh
```

#### 3. Verify Deployment

The deployment script will:
- ✓ Check prerequisites
- ✓ Validate certificates
- ✓ Build Docker images
- ✓ Start services (nginx + Python)
- ✓ Wait for health checks
- ✓ Test endpoints

Expected output:
```
================================================================
DEPLOYMENT COMPLETE
================================================================

EST Server Details:
  URL:        https://localhost:8445
  Dashboard:  https://localhost:8445/
  Mode:       Nginx proxy with RA authentication
...
```

#### 4. Test RA Authentication

```bash
# Run automated tests
./test-ra-nginx.sh
```

Expected output:
```
================================================================
SUCCESS: RA CERTIFICATE AUTHENTICATION WORKING!
================================================================

The EST server with nginx is correctly:
  ✓ Extracting client certificates from TLS
  ✓ Forwarding certificates via HTTP headers
  ✓ Authenticating based on RA certificate
  ✓ Issuing certificates

Ready for IQE integration!
```

#### 5. Manual Testing

```bash
# Generate test CSR
openssl req -new -newkey rsa:2048 -nodes \
  -keyout test-pump.key -out test-pump.csr \
  -subj "/CN=test-pump-001/O=Hospital/C=US"

openssl req -in test-pump.csr -outform DER -out test-pump.der

# Test RA authentication
curl -vk https://localhost:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @test-pump.der \
  -o test-pump-cert.p7 \
  -w "\nHTTP: %{http_code}\n"

# Expected: HTTP 200
```

#### 6. Check Server Logs

```bash
# Python EST server logs
docker-compose -f docker-compose-nginx.yml logs -f python-est-server

# Expected to see:
# INFO: ✅ Client certificate found (from nginx): CN=iqe-gateway,O=Hospital,C=US
# INFO: 🔐 Attempting RA certificate authentication...
# INFO: ✅ RA Certificate authentication successful for: iqe-gateway

# Nginx logs
docker-compose -f docker-compose-nginx.yml logs -f nginx
```

## How It Works

### 1. Nginx TLS Termination

Nginx configuration (`nginx/nginx.conf`):

```nginx
server {
    listen 8445 ssl;

    # Server certificates
    ssl_certificate /etc/nginx/certs/server.crt;
    ssl_certificate_key /etc/nginx/certs/server.key;

    # Client certificate validation
    ssl_client_certificate /etc/nginx/certs/ca-cert.pem;
    ssl_verify_client optional;  # Allow both with and without cert

    location /.well-known/est/ {
        proxy_pass http://python-est-server:8000;

        # Forward client certificate via headers
        proxy_set_header X-SSL-Client-Verify $ssl_client_verify;
        proxy_set_header X-SSL-Client-S-DN $ssl_client_s_dn;
        proxy_set_header X-SSL-Client-Cert $ssl_client_cert;
    }
}
```

**Key Points**:
- `ssl_verify_client optional` - Allows connections with OR without client cert
- `$ssl_client_cert` - Contains the full client certificate in PEM format
- `$ssl_client_verify` - Status: SUCCESS, FAILED, or NONE

### 2. Python Middleware

Updated middleware in `server.py`:

```python
@self.app.middleware("http")
async def extract_client_cert(request: Request, call_next):
    # Get headers from nginx
    ssl_verify = request.headers.get('X-SSL-Client-Verify', '')
    ssl_cert_pem = request.headers.get('X-SSL-Client-Cert', '')

    if ssl_cert_pem and ssl_verify == 'SUCCESS':
        # Parse certificate
        cert = x509.load_pem_x509_certificate(ssl_cert_pem.encode())
        request.state.client_cert = cert
        logger.info(f"✅ Client cert found (from nginx): {cert.subject}")
    else:
        logger.info(f"ℹ️  No client certificate present")

    response = await call_next(request)
    return response
```

### 3. Dual-Mode Server

The Python server supports two modes:

**Nginx Mode** (Production):
```bash
NGINX_MODE=true python -m python_est.cli start --config config-nginx.yaml
# Listens on HTTP port 8000
# Nginx handles TLS
```

**Standalone Mode** (Development):
```bash
python -m python_est.cli start --config config-iqe.yaml
# Listens on HTTPS port 8445
# Direct TLS (but transport is None in Docker)
```

## Troubleshooting

### Issue: HTTP 401 Unauthorized

**Symptoms**:
```
HTTP Status: 401
```

**Check 1**: Verify nginx is forwarding headers

```bash
# Exec into nginx container
docker exec -it est-nginx sh

# Test that nginx can read client cert
cat /etc/nginx/certs/iqe-ra-cert.pem

# Check nginx logs for SSL errors
tail -f /var/log/nginx/error.log
```

**Check 2**: Verify Python is receiving headers

```bash
# Check Python logs
docker-compose -f docker-compose-nginx.yml logs python-est-server | grep "Client certificate"

# Should see:
# INFO: ✅ Client certificate found (from nginx): ...
```

**Check 3**: Test direct connection to Python (bypass nginx)

```bash
# Exec into Python container
docker exec -it python-est-server bash

# Test internal HTTP endpoint
curl http://localhost:8000/

# Should return HTML dashboard
```

### Issue: "Failed to parse client certificate from nginx"

**Cause**: Nginx certificate encoding issue

**Solution**: Check nginx logs and certificate format

```bash
# Enable debug logging in nginx.conf
error_log /var/log/nginx/error.log debug;

# Restart nginx
docker-compose -f docker-compose-nginx.yml restart nginx

# Check logs
docker-compose -f docker-compose-nginx.yml logs nginx | grep SSL
```

### Issue: Services not starting

**Check**: Docker Compose status

```bash
docker-compose -f docker-compose-nginx.yml ps

# Should show:
# python-est-server  healthy
# nginx              healthy
```

**Fix**: Check logs for errors

```bash
docker-compose -f docker-compose-nginx.yml logs

# Common issues:
# - Port 8445 already in use
# - Certificate files not found
# - Permission issues with volumes
```

## Configuration Reference

### Environment Variables

| Variable | Purpose | Default | Nginx Mode | Standalone |
|----------|---------|---------|------------|------------|
| `NGINX_MODE` | Enable nginx proxy mode | `false` | `true` | `false` |
| `PORT` | HTTP/HTTPS port | `8445` | `8000` | `8445` |
| `PYTHONUNBUFFERED` | Disable output buffering | `0` | `1` | - |

### Ports

| Port | Service | Protocol | Purpose |
|------|---------|----------|---------|
| 8445 | Nginx | HTTPS | Public EST endpoint |
| 8000 | Python | HTTP | Internal backend (nginx forwards here) |

### Volumes

| Volume | Purpose | Mode |
|--------|---------|------|
| `./certs:/etc/nginx/certs` | Nginx certificates | ro (read-only) |
| `./certs:/app/certs` | Python certificates | ro |
| `./data:/app/data` | Python database | rw (read-write) |
| `./config-nginx.yaml:/app/config.yaml` | Python config | ro |
| `nginx_logs:/var/log/nginx` | Nginx logs | rw |

## Commands Reference

### Deployment

```bash
# Deploy with nginx
./deploy-nginx.sh

# Deploy manually
docker-compose -f docker-compose-nginx.yml up -d --build
```

### Testing

```bash
# Run automated tests
./test-ra-nginx.sh

# Manual enrollment test
curl -vk https://localhost:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @test-csr.der
```

### Monitoring

```bash
# Follow all logs
docker-compose -f docker-compose-nginx.yml logs -f

# Python logs only
docker-compose -f docker-compose-nginx.yml logs -f python-est-server

# Nginx logs only
docker-compose -f docker-compose-nginx.yml logs -f nginx

# Check service status
docker-compose -f docker-compose-nginx.yml ps
```

### Management

```bash
# Stop services
docker-compose -f docker-compose-nginx.yml down

# Restart services
docker-compose -f docker-compose-nginx.yml restart

# Rebuild and restart
docker-compose -f docker-compose-nginx.yml up -d --build --force-recreate

# View resource usage
docker stats python-est-server est-nginx
```

## IQE Integration

### Files for IQE Team

Package these files for the IQE team:

```
iqe_deployment_package/
├── ca-cert.pem          # EST server CA (for TLS verification)
├── iqe-ra-cert.pem      # RA certificate (for authentication)
├── iqe-ra-key.pem       # RA private key (SECURE!)
└── README.md            # Configuration instructions
```

### IQE Configuration

The IQE team needs to configure their gateway:

```yaml
est_server:
  url: https://10.42.56.101:8445
  ca_cert: /path/to/ca-cert.pem
  client_cert: /path/to/iqe-ra-cert.pem
  client_key: /path/to/iqe-ra-key.pem

endpoints:
  cacerts: /.well-known/est/cacerts
  simpleenroll: /.well-known/est/simpleenroll
```

### Expected Behavior

When IQE connects:

1. **TLS Handshake**: IQE sends RA certificate during TLS handshake
2. **Nginx Validates**: Nginx verifies cert is signed by CA
3. **Header Forwarding**: Nginx forwards cert to Python via headers
4. **Python Authenticates**: Python validates and authenticates
5. **Certificate Issued**: Python signs and returns device certificate

**Server Logs**:
```
INFO: ✅ Client certificate found (from nginx): CN=iqe-gateway,O=Hospital,C=US
INFO: 🔐 Attempting RA certificate authentication...
INFO: ✅ RA Certificate authentication successful for: iqe-gateway
INFO: Enrollment successful for device: pump-001
INFO: 172.20.0.3:45678 - "POST /.well-known/est/simpleenroll HTTP/1.1" 200 OK
```

## Production Checklist

Before going to production:

- [ ] All certificates generated and valid
- [ ] Certificate chain verified (server and RA certs signed by CA)
- [ ] Deploy script runs without errors
- [ ] Test script confirms RA authentication working
- [ ] Server logs show client certificate extraction
- [ ] Nginx logs show no SSL errors
- [ ] Health checks passing
- [ ] Dashboard accessible at https://localhost:8445/
- [ ] IQE deployment package created and transferred
- [ ] IQE team configured gateway with RA certificate
- [ ] End-to-end test with IQE successful

## Summary

**The nginx solution provides**:
- ✅ Reliable client certificate extraction (no transport limitations)
- ✅ Production-ready architecture (used by major companies)
- ✅ Platform-independent (works everywhere)
- ✅ Scalable (can add load balancing, rate limiting, etc.)
- ✅ Secure (TLS termination at edge, HTTP internally)

**Your EST server is now production-ready for IQE integration!** 🚀
