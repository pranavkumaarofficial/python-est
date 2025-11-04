# Manual Deployment Guide - EST Server with Nginx

## Complete Step-by-Step Commands

This guide provides **all commands** to manually deploy and test the EST server with nginx reverse proxy.

---

## Part 1: Pre-Deployment Checks

### Step 1.1: Verify Docker Installation

```bash
# Check Docker version
docker --version
# Expected: Docker version 20.x or higher

# Check Docker Compose version
docker-compose --version
# Expected: Docker Compose version 1.29.x or 2.x

# Test Docker is running
docker ps
# Should show running containers (or empty list if none running)
```

### Step 1.2: Verify Certificate Files

```bash
# Navigate to project directory
cd ~/Desktop/python-est

# List certificate files
ls -la certs/

# Should show:
# ca-cert.pem
# ca-key.pem
# server.crt
# server.key
# iqe-ra-cert.pem
# iqe-ra-key.pem
# srp_users.db
```

### Step 1.3: Verify Certificate Chain

```bash
# Verify server certificate
openssl verify -CAfile certs/ca-cert.pem certs/server.crt
# Expected: certs/server.crt: OK

# Verify RA certificate
openssl verify -CAfile certs/ca-cert.pem certs/iqe-ra-cert.pem
# Expected: certs/iqe-ra-cert.pem: OK

# Check server cert details
openssl x509 -in certs/server.crt -noout -subject -issuer -dates -ext subjectAltName

# Should show:
# subject=CN=python-est-server,O=Hospital,C=US
# issuer=CN=Python-EST Root CA,O=Test CA,L=Test,ST=CA,C=US
# notBefore=...
# notAfter=...
# X509v3 Subject Alternative Name:
#     DNS:localhost, DNS:python-est-server, DNS:10.42.56.101, IP Address:10.42.56.101

# Check RA cert details
openssl x509 -in certs/iqe-ra-cert.pem -noout -subject -issuer -dates

# Should show:
# subject=CN=iqe-gateway,O=Hospital,C=US
# issuer=CN=Python-EST Root CA,O=Test CA,L=Test,ST=CA,C=US
```

### Step 1.4: Verify Configuration Files

```bash
# Check nginx config exists
ls -la nginx/nginx.conf
# Should exist

# Check Docker Compose config exists
ls -la docker-compose-nginx.yml
# Should exist

# Check nginx mode config exists
ls -la config-nginx.yaml
# Should exist

# Quick validation of nginx config syntax (requires nginx installed locally)
# Skip this if nginx not installed on host
# nginx -t -c nginx/nginx.conf
```

---

## Part 2: Stop Existing Containers

### Step 2.1: Stop Old Containers

```bash
# Stop and remove old standalone EST server (if running)
docker stop python-est-server 2>/dev/null || true
docker rm python-est-server 2>/dev/null || true

# Stop nginx-based deployment (if running)
docker-compose -f docker-compose-nginx.yml down

# Verify nothing is running
docker ps -a | grep -E "python-est|nginx"
# Should show nothing (or only exited containers)

# Remove old containers completely
docker-compose -f docker-compose-nginx.yml down --volumes --remove-orphans
```

### Step 2.2: Clean Docker Images (Optional - Force Fresh Build)

```bash
# Remove old EST server images (optional - forces rebuild)
docker rmi python-est-server 2>/dev/null || true
docker rmi python-est_python-est-server 2>/dev/null || true

# Remove dangling images
docker image prune -f
```

---

## Part 3: Build Docker Images

### Step 3.1: Build Python EST Server Image

```bash
# Build with no cache (ensures fresh build with new code)
docker-compose -f docker-compose-nginx.yml build --no-cache python-est-server

# This will:
# - Build from Dockerfile
# - Install Python dependencies
# - Copy source code
# - Create directories

# Expected output:
# Building python-est-server
# Step 1/15 : FROM python:3.11-slim
# ...
# Successfully built <image-id>
# Successfully tagged python-est_python-est-server:latest
```

### Step 3.2: Pull Nginx Image

```bash
# Pull nginx alpine image
docker pull nginx:1.25-alpine

# Verify image pulled
docker images | grep nginx
# Should show: nginx  1.25-alpine  <image-id>  <size>
```

---

## Part 4: Start Services

### Step 4.1: Start Services in Detached Mode

```bash
# Start all services defined in docker-compose-nginx.yml
docker-compose -f docker-compose-nginx.yml up -d

# Expected output:
# Creating network "python-est_est_network" with driver "bridge"
# Creating volume "python-est_nginx_logs" with local driver
# Creating python-est-server ... done
# Creating est-nginx ... done
```

### Step 4.2: Verify Containers Started

```bash
# Check running containers
docker-compose -f docker-compose-nginx.yml ps

# Expected output:
# Name                  Command               State                    Ports
# ----------------------------------------------------------------------------------------------
# python-est-server     /entrypoint.sh start     Up (healthy)   8000/tcp, 8445/tcp
# est-nginx             /docker-entrypoint.sh... Up (healthy)   0.0.0.0:8445->8445/tcp, 80/tcp

# Alternative check
docker ps

# Should show both containers running with "healthy" status
```

### Step 4.3: Wait for Services to Be Healthy

```bash
# Check health status every few seconds
watch -n 2 'docker-compose -f docker-compose-nginx.yml ps'
# Wait until both show "healthy" (Ctrl+C to exit watch)

# Or manually check
docker inspect python-est-server | grep -A 5 '"Health"'
docker inspect est-nginx | grep -A 5 '"Health"'

# Health should show: "Status": "healthy"
```

---

## Part 5: Verify Deployment

### Step 5.1: Check Python EST Server Logs

```bash
# View Python EST server logs
docker-compose -f docker-compose-nginx.yml logs python-est-server

# Look for these key lines:
# INFO: Starting EST server in NGINX MODE on http://0.0.0.0:8000
# INFO: TLS termination handled by nginx proxy
# INFO: CA credentials loaded successfully
# INFO: Device tracker initialized
# INFO: EST Server initialized successfully
# INFO: Started server process [1]
# INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)

# Follow logs in real-time (Ctrl+C to exit)
docker-compose -f docker-compose-nginx.yml logs -f python-est-server
```

### Step 5.2: Check Nginx Logs

```bash
# View nginx logs
docker-compose -f docker-compose-nginx.yml logs nginx

# Should show:
# Attaching to est-nginx
# est-nginx | /docker-entrypoint.sh: Configuration complete; ready for start up

# Follow logs in real-time
docker-compose -f docker-compose-nginx.yml logs -f nginx
```

### Step 5.3: Check Container Networking

```bash
# Inspect the network
docker network inspect python-est_est_network

# Should show both containers connected:
# - python-est-server (172.20.0.x)
# - est-nginx (172.20.0.y)

# Test internal connectivity (from nginx to python)
docker exec est-nginx wget -O- http://python-est-server:8000/ 2>/dev/null | head -20

# Should return HTML (dashboard page)
```

---

## Part 6: Test Endpoints

### Step 6.1: Test Health Endpoint

```bash
# Test health endpoint (no authentication required)
curl -v -k https://localhost:8445/health

# Expected output:
# < HTTP/1.1 200 OK
# < server: nginx
# EST Server OK
```

### Step 6.2: Test CA Certificates Endpoint

```bash
# Retrieve CA certificates (no authentication required)
curl -v -k https://localhost:8445/.well-known/est/cacerts -o /tmp/test-cacerts.p7

# Expected output:
# < HTTP/1.1 200 OK
# < content-type: application/pkcs7-mime; smime-type=certs-only
# < content-transfer-encoding: base64

# Check file was created
ls -lh /tmp/test-cacerts.p7
# Should show file with size > 0

# Check file type
file /tmp/test-cacerts.p7
# Expected: ASCII text (base64)

# Decode and verify PKCS#7
base64 -d /tmp/test-cacerts.p7 > /tmp/test-cacerts-decoded.p7
openssl pkcs7 -inform DER -in /tmp/test-cacerts-decoded.p7 -print_certs -noout

# Expected: should print certificate info without errors
```

### Step 6.3: Test Dashboard

```bash
# Access dashboard via browser or curl
curl -k https://localhost:8445/ | head -50

# Should return HTML with:
# <title>EST Server Dashboard</title>
# <h1>EST Server Dashboard</h1>
```

---

## Part 7: Test RA Certificate Authentication

### Step 7.1: Generate Test CSR

```bash
# Create test CSR using Python
python3 << 'EOF'
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generate private key
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# Generate CSR
csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, 'US'),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'Hospital'),
    x509.NameAttribute(NameOID.COMMON_NAME, 'test-medical-pump-manual-001'),
])).sign(key, hashes.SHA256())

# Save private key
with open('/tmp/test-device.key', 'wb') as f:
    f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))

# Save CSR in DER format (EST protocol requirement)
with open('/tmp/test-device.der', 'wb') as f:
    f.write(csr.public_bytes(serialization.Encoding.DER))

print("CSR generated:")
print("  Private key: /tmp/test-device.key")
print("  CSR (DER):   /tmp/test-device.der")
EOF

# Verify files created
ls -lh /tmp/test-device.*
```

### Step 7.2: Test Enrollment WITH RA Certificate

```bash
# Enroll device using RA certificate authentication
curl -v -k https://localhost:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @/tmp/test-device.der \
  -o /tmp/test-device-cert.p7 \
  -w "\nHTTP Status: %{http_code}\n"

# Expected output:
# < HTTP/1.1 200 OK
# < content-type: application/pkcs7-mime; smime-type=certs-only
# < content-transfer-encoding: base64
# HTTP Status: 200

# If you see HTTP 401:
# - RA authentication is NOT working
# - Check logs (next section)

# If you see HTTP 200:
# - RA authentication IS working! ✓
```

### Step 7.3: Verify Issued Certificate

```bash
# Check response file
ls -lh /tmp/test-device-cert.p7
# Should have content

# Check format
file /tmp/test-device-cert.p7
# Expected: ASCII text (base64)

# Decode and extract certificate
base64 -d /tmp/test-device-cert.p7 > /tmp/test-device-cert-decoded.p7
openssl pkcs7 -inform DER -in /tmp/test-device-cert-decoded.p7 -print_certs -out /tmp/test-device-cert.pem

# View certificate details
openssl x509 -in /tmp/test-device-cert.pem -noout -subject -issuer -dates

# Expected output:
# subject=CN = test-medical-pump-manual-001, O = Hospital, C = US
# issuer=C = US, ST = CA, L = Test, O = Test CA, CN = Python-EST Root CA
# notBefore=<date>
# notAfter=<date> (1 year from now)

# Verify certificate chain
openssl verify -CAfile certs/ca-cert.pem /tmp/test-device-cert.pem
# Expected: /tmp/test-device-cert.pem: OK
```

---

## Part 8: Verify RA Authentication in Logs

### Step 8.1: Check Python Logs for RA Authentication

```bash
# View recent Python logs
docker-compose -f docker-compose-nginx.yml logs --tail=50 python-est-server

# Look for these CRITICAL lines:
# INFO: ✅ Client certificate found (from nginx): CN=iqe-gateway,O=Hospital,C=US
# INFO: 🔐 Attempting RA certificate authentication...
# INFO: ✅ RA Certificate authentication successful for: iqe-gateway
# INFO: Enrollment successful for device: test-medical-pump-manual-001
# INFO: 172.20.0.3:XXXXX - "POST /.well-known/est/simpleenroll HTTP/1.1" 200 OK

# If you see these, RA authentication is WORKING! ✓

# If you see this instead:
# INFO: ℹ️  No client certificate present (will try password auth)
# INFO: 172.20.0.3:XXXXX - "POST /.well-known/est/simpleenroll HTTP/1.1" 401 Unauthorized
# Then RA authentication is NOT working - see troubleshooting section
```

### Step 8.2: Check Nginx Logs

```bash
# Check nginx access logs
docker exec est-nginx tail -20 /var/log/nginx/access.log

# Should show:
# 172.20.0.1 - - [date] "POST /.well-known/est/simpleenroll HTTP/1.1" 200 <size> SSL_verify: SUCCESS SSL_subject: CN=iqe-gateway,O=Hospital,C=US

# The key part is: SSL_verify: SUCCESS

# Check nginx error logs
docker exec est-nginx tail -20 /var/log/nginx/error.log

# Should be empty or only show info messages
# If you see SSL errors here, nginx is having trouble with certificates
```

---

## Part 9: Test Password Authentication (Fallback)

### Step 9.1: Test WITHOUT Client Certificate

```bash
# Try enrollment with username/password instead of RA cert
curl -v -k https://localhost:8445/.well-known/est/simpleenroll \
  -u iqe-gateway:iqe-secure-password-2024 \
  -H "Content-Type: application/pkcs10" \
  --data-binary @/tmp/test-device.der \
  -o /tmp/test-device-cert-pwd.p7 \
  -w "\nHTTP Status: %{http_code}\n"

# Expected results:
# - HTTP 200: Password auth working (dual-mode success!)
# - HTTP 401: Password auth failed (may be expected if user doesn't exist)

# Check logs
docker-compose -f docker-compose-nginx.yml logs --tail=20 python-est-server

# Should show:
# INFO: ℹ️  No client certificate present (will try password auth)
# INFO: SRP authentication successful for: iqe-gateway
# (or)
# INFO: SRP authentication failed for: iqe-gateway
```

---

## Part 10: Comprehensive Status Check

### Step 10.1: Service Status

```bash
# Check all containers
docker-compose -f docker-compose-nginx.yml ps

# Should show:
# python-est-server  Up (healthy)
# est-nginx          Up (healthy)

# Check resource usage
docker stats --no-stream python-est-server est-nginx

# Should show reasonable CPU/memory usage
```

### Step 10.2: Port Bindings

```bash
# Verify port mappings
docker port est-nginx

# Expected:
# 8445/tcp -> 0.0.0.0:8445

# Test port is accessible
netstat -tulpn | grep 8445
# or
ss -tulpn | grep 8445

# Should show nginx listening on 0.0.0.0:8445
```

### Step 10.3: Volume Mounts

```bash
# Check volumes are mounted correctly
docker inspect python-est-server | grep -A 20 '"Mounts"'

# Should show:
# - certs mounted at /app/certs (ro)
# - data mounted at /app/data (rw)
# - config-nginx.yaml mounted at /app/config.yaml (ro)

docker inspect est-nginx | grep -A 20 '"Mounts"'

# Should show:
# - nginx.conf mounted at /etc/nginx/nginx.conf (ro)
# - certs mounted at /etc/nginx/certs (ro)
# - nginx_logs volume mounted at /var/log/nginx
```

---

## Part 11: Troubleshooting Commands

### Issue: HTTP 401 Unauthorized

```bash
# Step 1: Check if nginx is forwarding headers
docker exec est-nginx cat /etc/nginx/nginx.conf | grep -A 5 "X-SSL-Client"

# Should show:
# proxy_set_header X-SSL-Client-Verify $ssl_client_verify;
# proxy_set_header X-SSL-Client-Cert $ssl_client_cert;

# Step 2: Check if Python is receiving headers
docker-compose -f docker-compose-nginx.yml logs python-est-server | grep -i "client certificate"

# If you see "No client certificate present", nginx is NOT forwarding the cert

# Step 3: Check nginx SSL configuration
docker exec est-nginx cat /etc/nginx/nginx.conf | grep -A 3 "ssl_verify_client"

# Should show:
# ssl_verify_client optional;

# Step 4: Test nginx can read certificates
docker exec est-nginx ls -la /etc/nginx/certs/

# Should show all cert files with read permissions

# Step 5: Test internal connection (nginx -> python)
docker exec est-nginx wget -O- http://python-est-server:8000/ 2>/dev/null | head -10

# Should return HTML
```

### Issue: Containers Not Healthy

```bash
# Check health check status
docker inspect python-est-server --format='{{json .State.Health}}' | python3 -m json.tool

# Shows health check details

# Manually run health check command
docker exec python-est-server python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"

# Should succeed without errors

# Check nginx health
docker exec est-nginx wget --spider http://localhost:8445/health

# Should return success
```

### Issue: Certificate Parsing Errors

```bash
# Enable verbose logging
docker-compose -f docker-compose-nginx.yml logs python-est-server | grep -A 5 "Failed to parse"

# Check the certificate format nginx is sending
docker exec est-nginx nginx -T | grep ssl_client_cert

# Test certificate parsing manually
docker exec python-est-server python3 << 'EOF'
import urllib.parse
from cryptography import x509

# Read RA cert
with open('/app/certs/iqe-ra-cert.pem', 'r') as f:
    cert_pem = f.read()

# Try to parse
cert = x509.load_pem_x509_certificate(cert_pem.encode())
print(f"Certificate parsed: {cert.subject}")
EOF

# Should print certificate subject
```

### Issue: Port Already in Use

```bash
# Check what's using port 8445
sudo lsof -i :8445
# or
sudo netstat -tulpn | grep 8445

# If old EST server is running:
docker stop python-est-server
docker rm python-est-server

# If something else is using the port:
# Either stop that service or change the port in docker-compose-nginx.yml
```

---

## Part 12: Management Commands

### View Logs

```bash
# All logs
docker-compose -f docker-compose-nginx.yml logs

# Python only
docker-compose -f docker-compose-nginx.yml logs python-est-server

# Nginx only
docker-compose -f docker-compose-nginx.yml logs nginx

# Follow logs (real-time)
docker-compose -f docker-compose-nginx.yml logs -f

# Last 50 lines
docker-compose -f docker-compose-nginx.yml logs --tail=50

# Filter for specific keyword
docker-compose -f docker-compose-nginx.yml logs | grep "Client certificate"
```

### Restart Services

```bash
# Restart all services
docker-compose -f docker-compose-nginx.yml restart

# Restart Python only
docker-compose -f docker-compose-nginx.yml restart python-est-server

# Restart nginx only
docker-compose -f docker-compose-nginx.yml restart nginx
```

### Stop Services

```bash
# Stop all services (keeps containers)
docker-compose -f docker-compose-nginx.yml stop

# Stop and remove containers
docker-compose -f docker-compose-nginx.yml down

# Stop, remove containers, and volumes
docker-compose -f docker-compose-nginx.yml down --volumes

# Stop, remove everything including images
docker-compose -f docker-compose-nginx.yml down --rmi all --volumes
```

### Rebuild Services

```bash
# Rebuild and restart (after code changes)
docker-compose -f docker-compose-nginx.yml up -d --build

# Force rebuild without cache
docker-compose -f docker-compose-nginx.yml build --no-cache
docker-compose -f docker-compose-nginx.yml up -d
```

### Execute Commands in Containers

```bash
# Get shell in Python container
docker exec -it python-est-server bash

# Get shell in nginx container
docker exec -it est-nginx sh

# Run one-off command in Python container
docker exec python-est-server python3 --version

# View files in Python container
docker exec python-est-server ls -la /app/certs/

# View nginx config in nginx container
docker exec est-nginx cat /etc/nginx/nginx.conf
```

---

## Part 13: Success Verification Checklist

After completing all steps, verify:

```bash
# ✓ Containers running and healthy
docker-compose -f docker-compose-nginx.yml ps | grep healthy
# Both should show "healthy"

# ✓ Health endpoint working
curl -k https://localhost:8445/health | grep "OK"

# ✓ CA certs endpoint working
curl -k https://localhost:8445/.well-known/est/cacerts > /tmp/verify.p7 && test -s /tmp/verify.p7 && echo "OK"

# ✓ RA authentication working
docker-compose -f docker-compose-nginx.yml logs python-est-server | grep "✅ RA Certificate authentication successful"
# Should show at least one success line

# ✓ Certificate issued successfully
test -f /tmp/test-device-cert.pem && openssl x509 -in /tmp/test-device-cert.pem -noout -subject && echo "OK"
```

If all checks pass:

```
================================================================
✅ SUCCESS: EST SERVER WITH NGINX IS WORKING!
================================================================

RA certificate authentication is operational.
Ready for IQE integration!
```

---

## Part 14: Next Steps

### For IQE Integration

1. **Package certificates for IQE team**:
   ```bash
   mkdir -p iqe_deployment_package
   cp certs/ca-cert.pem iqe_deployment_package/
   cp certs/iqe-ra-cert.pem iqe_deployment_package/
   cp certs/iqe-ra-key.pem iqe_deployment_package/

   # Create tarball
   tar -czf iqe_deployment_package.tar.gz iqe_deployment_package/

   # Transfer to IQE team
   scp iqe_deployment_package.tar.gz iqe-team@iqe-server:/path/
   ```

2. **Monitor during IQE testing**:
   ```bash
   # Follow logs during IQE testing
   docker-compose -f docker-compose-nginx.yml logs -f

   # Filter for IQE requests
   docker-compose -f docker-compose-nginx.yml logs -f | grep -E "Client certificate|RA|authentication"
   ```

3. **Production checklist**:
   - [ ] All tests passing
   - [ ] Logs show RA authentication working
   - [ ] Certificates valid for at least 6 months
   - [ ] Backup data/ directory
   - [ ] Document restart procedure
   - [ ] Set up monitoring/alerts

---

## Summary

This manual deployment covers:
- ✅ Pre-flight checks (Docker, certs, config)
- ✅ Container build and startup
- ✅ Service verification
- ✅ Endpoint testing
- ✅ RA authentication testing
- ✅ Log verification
- ✅ Troubleshooting commands
- ✅ Management commands

**Your EST server with nginx is production-ready!** 🚀
