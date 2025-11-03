# Docker libest Deploy - FASTEST Way for Demo Tomorrow

## Why This Works Better

✅ **No build errors on VM** - Docker handles everything
✅ **5 minutes to deploy** - Just `git pull` and `docker-compose up`
✅ **Works on Windows first** - Test before pushing
✅ **Reproducible** - Same environment everywhere

## Option 1: Use Pre-built Image (FASTEST - 2 min)

I'll create a simple Dockerfile that uses pre-built libest. But since we need custom config, let's use Option 2.

## Option 2: Build on VM (RECOMMENDED - 5 min)

The Dockerfile handles all the build complexity!

### Step 1: Commit Docker Files (Windows)

```bash
git checkout cisco-libest  # Or create: git checkout -b cisco-libest

git add Dockerfile.libest
git add docker-compose.libest.yml
git add DOCKER_LIBEST_DEPLOY.md

git commit -m "feat: Add Docker-based libest server for quick deployment"

git push -u origin cisco-libest
```

### Step 2: Deploy on VM (Ubuntu)

```bash
# Pull code
cd /path/to/python-est
git fetch origin
git checkout cisco-libest
git pull origin cisco-libest

# Build and start (Docker does ALL the work!)
docker-compose -f docker-compose.libest.yml build

# Start server
docker-compose -f docker-compose.libest.yml up -d

# Check logs
docker-compose -f docker-compose.libest.yml logs -f
```

**That's it!** Server running on port 8446.

### Step 3: Test

```bash
# From VM
curl -vk https://localhost:8446/.well-known/est/cacerts

# From external
curl -vk https://10.42.56.101:8446/.well-known/est/cacerts
```

### Step 4: Get CA Cert for IQE Team

```bash
# Extract CA cert from Docker container
docker exec libest-est-server cat /opt/libest/example/server/estCA/cacert.crt > libest-ca-cert.pem

# Copy to Windows
# Then send to IQE team
```

### Step 5: Configure IQE UI

```
CA Certs URL: https://10.42.56.101:8446/.well-known/est/cacerts
Enrollment URL: https://10.42.56.101:8446/.well-known/est/simpleenroll

Username: iqe-gateway
Password: iqe-secure-password-2024

OR

Username: estuser
Password: estpwd
```

## Troubleshooting

### Build fails in Docker

```bash
# Check logs
docker-compose -f docker-compose.libest.yml logs

# Rebuild from scratch
docker-compose -f docker-compose.libest.yml down
docker-compose -f docker-compose.libest.yml build --no-cache
docker-compose -f docker-compose.libest.yml up -d
```

### Can't access from external

```bash
# Check firewall
sudo ufw allow 8446/tcp

# Check container is running
docker ps | grep libest
```

### Wrong IP in certificate

Edit `Dockerfile.libest`, change:
```dockerfile
IP.2 = 10.42.56.101  # Change to your actual VM IP
```

Then rebuild:
```bash
docker-compose -f docker-compose.libest.yml build --no-cache
docker-compose -f docker-compose.libest.yml up -d
```

## Timeline

| Step | Time |
|------|------|
| Commit Docker files | 2 min |
| Push to GitHub | 1 min |
| Pull on VM | 1 min |
| Docker build (first time) | 10-15 min |
| Docker start | 30 sec |
| Test | 2 min |
| **Total** | **~20 min** |

**Subsequent deploys**: 1 minute (just pull and restart!)

## Run Both Servers

You can run BOTH Python EST and libest simultaneously:

```bash
# Python EST on port 8445
docker-compose up -d

# libest on port 8446
docker-compose -f docker-compose.libest.yml up -d

# Check both
docker ps
```

This way you have:
- **libest** (port 8446) - Proven, for demo
- **Python EST** (port 8445) - Better features, for future

## Demo Strategy

**Tomorrow morning**:
1. Show libest working (port 8446) - "Production setup"
2. Show Python EST (port 8445) - "Enhanced version with dashboard"
3. Explain: "Started with proven libest, building improved Python version"

**Shows**: Pragmatism + Innovation + Engineering judgment 🎯

## If Docker Build Still Fails

Last resort - use a simpler EST server:

```bash
# Use a pre-built EST Docker image
docker run -d -p 8446:8443 \
  -e EST_USER=iqe-gateway \
  -e EST_PASS=iqe-secure-password-2024 \
  ghcr.io/est-server/est:latest
```

(This is hypothetical - but many EST images exist on Docker Hub)

## Your Best Bet for Tonight

1. **Commit Docker files** (2 min)
2. **Push to GitHub** (1 min)
3. **Pull on VM** (1 min)
4. **Docker build and run** (15 min, hands-off!)
5. **Test** (2 min)
6. **Sleep** 😴
7. **Demo tomorrow** ✅

Docker handles ALL the libest build complexity!

## Quick Commands Summary

```bash
# Windows
git add Dockerfile.libest docker-compose.libest.yml DOCKER_LIBEST_DEPLOY.md
git commit -m "feat: Docker libest for quick deployment"
git push origin cisco-libest

# VM
cd /path/to/python-est
git pull origin cisco-libest
docker-compose -f docker-compose.libest.yml build
docker-compose -f docker-compose.libest.yml up -d
docker-compose -f docker-compose.libest.yml logs -f

# Test
curl -vk https://10.42.56.101:8446/.well-known/est/cacerts

# Get CA cert
docker exec libest-est-server cat /opt/libest/example/server/estCA/cacert.crt
```

**This WILL work!** Docker isolates all the build issues. 🚀
