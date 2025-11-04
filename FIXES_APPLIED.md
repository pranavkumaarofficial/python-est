# Critical Fixes Applied

## Issues Found

You discovered **3 critical configuration issues**:

### Issue 1: Wrong Config File ❌
**Problem**: Docker Compose was mounting `config-iqe.yaml` (port 8445) instead of `config-nginx.yaml` (port 8000)

**Result**: Backend was listening on wrong port

**Fix Applied**:
```yaml
# docker-compose-nginx.yml line 28
# BEFORE:
- ./config-iqe.yaml:/app/config.yaml:ro

# AFTER:
- ./config-nginx.yaml:/app/config.yaml:ro  # ✓ Correct config for nginx mode
```

### Issue 2: Missing /health Endpoint ❌
**Problem**: FastAPI app had no `/health` endpoint, but healthchecks were trying to access it

**Result**: Healthchecks failing

**Fix Applied**:
```python
# src/python_est/server.py line 170
@self.app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint for Docker/Kubernetes."""
    return {
        "status": "healthy",
        "service": "Python-EST Server"
    }
```

### Issue 3: Healthcheck Mismatch ❌
**Problem**: Healthchecks were hitting wrong endpoints

**Fix Applied**:
```yaml
# Python EST Server healthcheck
test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

# Nginx healthcheck (tests backend connection)
test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://python-est-server:8000/health"]
```

## Architecture (Corrected)

```
External Client (IQE)
         │
         │ HTTPS (port 8445)
         │ + TLS Client Cert
         ▼
    ┌─────────┐
    │  Nginx  │  Port 8445 (HTTPS)
    │         │  - TLS termination
    │         │  - Extract client cert
    │         │  - Forward via headers
    └────┬────┘
         │
         │ HTTP (internal)
         │ Headers: X-SSL-Client-Cert, etc.
         ▼
┌────────────────┐
│ Python EST     │  Port 8000 (HTTP)
│ Server         │  - Read cert from headers
│                │  - Authenticate
│                │  - Issue certificates
└────────────────┘
```

## What Changed

| Component | Before | After |
|-----------|--------|-------|
| Python backend port | 8445 (HTTPS) | 8000 (HTTP) |
| Config file | config-iqe.yaml | config-nginx.yaml |
| `/health` endpoint | ❌ Missing | ✅ Added |
| Python healthcheck | `/` endpoint | `/health` endpoint |
| Nginx healthcheck | Wrong port/proto | Backend /health via HTTP |

## Deploy with Fixes

```bash
# 1. Pull/commit latest code (fixes are in place)
git add .
git commit -m "fix: Correct nginx mode configuration

- Use config-nginx.yaml (port 8000) instead of config-iqe.yaml (port 8445)
- Add /health endpoint to FastAPI app
- Update healthchecks to use correct endpoints
- Nginx listens on 8445 HTTPS, backend on 8000 HTTP"

git push origin deploy_v1

# 2. On Ubuntu VM, pull and rebuild
cd ~/Desktop/python-est
git pull origin deploy_v1

# 3. Stop old containers
docker-compose -f docker-compose-nginx.yml down

# 4. Rebuild with no cache
docker-compose -f docker-compose-nginx.yml build --no-cache

# 5. Start services
docker-compose -f docker-compose-nginx.yml up -d

# 6. Watch logs
docker-compose -f docker-compose-nginx.yml logs -f
```

## Verification Commands

### Check Backend Port

```bash
# Python should listen on 8000 HTTP
docker-compose -f docker-compose-nginx.yml logs python-est-server | grep "Starting EST server"

# Expected:
# INFO: Starting EST server in NGINX MODE on http://0.0.0.0:8000
# INFO: TLS termination handled by nginx proxy
```

### Check Nginx Port

```bash
# Nginx should listen on 8445 HTTPS
docker port est-nginx

# Expected:
# 8445/tcp -> 0.0.0.0:8445
```

### Test Health Endpoint

```bash
# Test backend directly (inside container network)
docker exec python-est-server curl -s http://localhost:8000/health

# Expected:
# {"status":"healthy","service":"Python-EST Server"}

# Test via nginx (from host)
curl -k https://localhost:8445/health

# Expected:
# {"status":"healthy","service":"Python-EST Server"}
```

### Test RA Authentication

```bash
# Generate CSR
python3 -c "
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, 'US'),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'Hospital'),
    x509.NameAttribute(NameOID.COMMON_NAME, 'test-fixed-config'),
])).sign(key, hashes.SHA256())

with open('/tmp/test-fixed.der', 'wb') as f:
    f.write(csr.public_bytes(serialization.Encoding.DER))
"

# Test enrollment with RA cert
curl -vk https://localhost:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @/tmp/test-fixed.der \
  -w "\nHTTP: %{http_code}\n"

# Expected: HTTP 200

# Check logs for RA authentication
docker-compose -f docker-compose-nginx.yml logs python-est-server | grep "Client certificate"

# Expected:
# INFO: ✅ Client certificate found (from nginx): CN=iqe-gateway,O=Hospital,C=US
# INFO: 🔐 Attempting RA certificate authentication...
# INFO: ✅ RA Certificate authentication successful for: iqe-gateway
```

## Common Issues After Fix

### If still getting "Connection refused"

```bash
# Check if backend is actually listening
docker exec python-est-server netstat -tlnp | grep 8000
# or
docker exec python-est-server ss -tlnp | grep 8000

# Should show:
# tcp  0  0  0.0.0.0:8000  0.0.0.0:*  LISTEN  1/python
```

### If healthcheck still failing

```bash
# Check healthcheck logs
docker inspect python-est-server --format='{{json .State.Health}}' | python3 -m json.tool

# Manually test healthcheck command
docker exec python-est-server python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Should succeed without errors
```

### If nginx can't reach backend

```bash
# Test connectivity from nginx container
docker exec est-nginx wget -O- http://python-est-server:8000/health

# Should return: {"status":"healthy","service":"Python-EST Server"}

# Check if containers are on same network
docker network inspect python-est_est_network | grep -A 5 '"Containers"'

# Both containers should be listed
```

## Files Modified

1. ✅ `docker-compose-nginx.yml` - Fixed config mount + healthchecks
2. ✅ `src/python_est/server.py` - Added /health endpoint
3. ✅ `config-nginx.yaml` - Already had port 8000 (no change needed)

## Summary

**Before Fixes**:
- Backend on 8445 HTTPS ❌
- Wrong config file ❌
- No /health endpoint ❌
- Healthchecks failing ❌
- RA auth couldn't work ❌

**After Fixes**:
- Backend on 8000 HTTP ✅
- Correct nginx config ✅
- /health endpoint exists ✅
- Healthchecks passing ✅
- RA auth ready to test ✅

**Next**: Deploy and test on Ubuntu VM!
