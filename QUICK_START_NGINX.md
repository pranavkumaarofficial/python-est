# Quick Start - EST Server with Nginx

## TL;DR

```bash
# 1. Push code
git add . && git commit -m "feat: Add nginx reverse proxy for RA auth" && git push origin deploy_v1

# 2. Deploy on Ubuntu VM
ssh interop@ansible-virtual-machine
cd ~/Desktop/python-est
git pull origin deploy_v1
chmod +x deploy-nginx.sh test-ra-nginx.sh
./deploy-nginx.sh

# 3. Test
./test-ra-nginx.sh

# Expected: ✅ SUCCESS: RA CERTIFICATE AUTHENTICATION WORKING!
```

## What Changed?

### The Problem
- ❌ Uvicorn `transport` is `None` in Docker (even on Linux!)
- ❌ Cannot extract client certificates directly
- ❌ RA authentication fails with HTTP 401

### The Solution
- ✅ **Nginx reverse proxy** handles TLS termination
- ✅ Nginx extracts client certificates reliably
- ✅ Forwards certificate to Python via HTTP headers
- ✅ Industry-standard approach for containers

## Architecture

```
IQE Gateway → Nginx (HTTPS:8445) → Python EST (HTTP:8000)
              [extracts cert]        [reads from headers]
```

## New Files

| File | Purpose |
|------|---------|
| `nginx/nginx.conf` | Nginx config for TLS + client certs |
| `docker-compose-nginx.yml` | Orchestrates nginx + Python |
| `config-nginx.yaml` | Python config for nginx mode |
| `deploy-nginx.sh` | Automated deployment |
| `test-ra-nginx.sh` | RA authentication testing |
| `NGINX_DEPLOYMENT_GUIDE.md` | Complete documentation |

## Modified Files

| File | Change |
|------|--------|
| `src/python_est/server.py` | Middleware reads cert from headers |
| `Dockerfile` | Support both nginx and standalone modes |

## Commands

```bash
# Deploy
./deploy-nginx.sh

# Test
./test-ra-nginx.sh

# Logs
docker-compose -f docker-compose-nginx.yml logs -f

# Stop
docker-compose -f docker-compose-nginx.yml down

# Restart
docker-compose -f docker-compose-nginx.yml restart
```

## Verification

After deployment, you should see:

```
INFO: Starting EST server in NGINX MODE on http://0.0.0.0:8000
INFO: TLS termination handled by nginx proxy
...
INFO: ✅ Client certificate found (from nginx): CN=iqe-gateway,O=Hospital,C=US
INFO: 🔐 Attempting RA certificate authentication...
INFO: ✅ RA Certificate authentication successful for: iqe-gateway
```

## For IQE Team

No changes needed on IQE side! They still connect to:
- **URL**: `https://10.42.56.101:8445`
- **Certs**: Same as before (ca-cert.pem, iqe-ra-cert.pem, iqe-ra-key.pem)

The nginx proxy is transparent to IQE.

## Next Steps

1. ✅ Deploy on Ubuntu VM
2. ✅ Run tests (should pass!)
3. ✅ Check logs (should see RA authentication)
4. 📤 Ready for IQE integration!

See [NGINX_DEPLOYMENT_GUIDE.md](NGINX_DEPLOYMENT_GUIDE.md) for full details.
