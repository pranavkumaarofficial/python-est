# Deploy to Ubuntu VM - Complete Guide

## Important: Certificates Not in Git

Certificates are in `.gitignore`, so you need to regenerate them on the VM!

## Step-by-Step Deployment

### 1. Commit and Push Code (Windows)

```bash
# Commit scripts and config (NOT certs)
git add config-iqe.yaml
git add fix_server_cert.py
git add generate_certificates_python.py
git add create_iqe_user.py
git add generate_ra_certificate.py
git add test_iqe_ui_format.py
git add FIX_SERVER_CERT_IP.md
git add CISCO_LIBEST_ANALYSIS.md
git add IQE_UI_BASE64_FIX.md
git add FINAL_FIXES_SUMMARY.md
git add DEPLOY_TO_VM.md

git commit -m "fix: Add IP to server cert SAN and use base64 response format

Critical fixes for IQE UI compatibility:
- Server cert now has IP Address:10.42.56.101 in SAN
- Response format changed to base64 (RFC 7030)
- Add certificate generation scripts for VM
- Matches cisco libest configuration"

git push origin deploy_v1
```

### 2. SSH to Ubuntu VM

```bash
ssh user@your-vm-ip
# or use PuTTY
```

### 3. Pull Latest Code

```bash
cd /path/to/python-est
git fetch origin
git pull origin deploy_v1

# Verify you got the latest
git log -1 --oneline
```

### 4. Create certs Directory (if needed)

```bash
mkdir -p certs
chmod 755 certs
```

### 5. Generate All Certificates on VM

```bash
# Generate CA, server, and client certificates
python3 generate_certificates_python.py

# Should create:
# - certs/ca-cert.pem
# - certs/ca-key.pem
# - certs/server.crt (with IP Address:10.42.56.101 in SAN!)
# - certs/server.key
# - certs/client.crt
# - certs/client.key
```

**CRITICAL**: Make sure `generate_certificates_python.py` includes the IP address!

Let me check if it does...

Actually, the current `generate_certificates_python.py` doesn't include the IP. You need to use `fix_server_cert.py` after running it:

```bash
# Step 1: Generate CA and basic certs
python3 generate_certificates_python.py

# Step 2: Fix server cert to include IP address
python3 fix_server_cert.py

# Verify IP is in server cert:
openssl x509 -in certs/server.crt -text -noout | grep -A5 "Subject Alternative Name"
# Should show: IP Address:10.42.56.101
```

### 6. Create Bootstrap User

```bash
# Create iqe-gateway user
python3 create_iqe_user.py

# Should create: certs/srp_users.db
```

### 7. Generate RA Certificate (Optional)

```bash
# For RA certificate authentication
python3 generate_ra_certificate.py

# Should create:
# - certs/iqe-ra-key.pem
# - certs/iqe-ra-cert.pem
```

### 8. Set Up Config

```bash
# Use IQE-specific config
ln -sf config-iqe.yaml config.yaml

# Verify config:
grep response_format config.yaml
# Should show: response_format: base64

cat config.yaml | head -20
```

### 9. Install Dependencies (if needed)

```bash
# If not already installed:
pip3 install -r requirements.txt
pip3 install -e .
```

### 10. Restart Docker

```bash
# Stop current containers
docker-compose down

# Start with new config and certs
docker-compose up -d

# Check status
docker-compose ps
```

### 11. Check Logs

```bash
# Watch logs
docker-compose logs -f

# Should see:
# - "Loaded configuration from config.yaml"
# - "response_format: base64"
# - "Server running on https://0.0.0.0:8445"
# - No errors about missing certs
```

### 12. Test from VM

```bash
# Test /cacerts
curl -vk https://localhost:8445/.well-known/est/cacerts -o cacerts.p7b

# Check if response is base64
file cacerts.p7b
# Should show: ASCII text (if base64)

# Test enrollment with base64 CSR
# (Use test_iqe_ui_format.py commands)
```

### 13. Test from External (Your Windows Machine)

```bash
# Test /cacerts from external
curl -vk https://10.42.56.101:8445/.well-known/est/cacerts -o cacerts.p7b

# Should work! (with -k)
# Without -k, will fail until IQE imports ca-cert.pem
```

### 14. Copy CA Cert for IQE Team

```bash
# On VM, display CA cert
cat certs/ca-cert.pem

# Copy this and save as ca-cert.pem on your Windows machine
# Then send to IQE team
```

Or use SCP:
```bash
# From Windows (in PowerShell):
scp user@vm-ip:/path/to/python-est/certs/ca-cert.pem .
```

## Quick Commands Summary

```bash
# On VM:
cd /path/to/python-est
git pull origin deploy_v1
mkdir -p certs
python3 generate_certificates_python.py
python3 fix_server_cert.py  # Critical! Adds IP to cert
python3 create_iqe_user.py
python3 generate_ra_certificate.py
ln -sf config-iqe.yaml config.yaml
docker-compose down
docker-compose up -d
docker-compose logs -f
```

## Verification Checklist

On the VM, verify:

- [ ] Code is latest: `git log -1 --oneline`
- [ ] Certs exist: `ls -la certs/`
- [ ] Server cert has IP: `openssl x509 -in certs/server.crt -text -noout | grep "IP Address:10.42.56.101"`
- [ ] Config is correct: `grep response_format config.yaml` shows `base64`
- [ ] User exists: `ls -la certs/srp_users.db`
- [ ] Docker is running: `docker-compose ps`
- [ ] Server is listening: `curl -vk https://localhost:8445/.well-known/est/cacerts`
- [ ] External access works: `curl -vk https://10.42.56.101:8445/.well-known/est/cacerts`

## Files to Share with IQE Team

After deployment, get these files from VM:

```bash
# 1. CA certificate (REQUIRED for IQE trust store)
certs/ca-cert.pem

# 2. RA certificates (if using RA auth)
certs/iqe-ra-key.pem
certs/iqe-ra-cert.pem
```

Copy from VM:
```bash
# Windows PowerShell:
scp user@vm-ip:/path/to/python-est/certs/ca-cert.pem .
scp user@vm-ip:/path/to/python-est/certs/iqe-ra-cert.pem .
scp user@vm-ip:/path/to/python-est/certs/iqe-ra-key.pem .
```

## Troubleshooting

### Problem: Server cert still doesn't have IP

```bash
# Check what's in the cert:
openssl x509 -in certs/server.crt -text -noout | grep -A10 "Subject Alternative"

# If IP is missing, regenerate:
python3 fix_server_cert.py

# Restart Docker:
docker-compose restart
```

### Problem: Docker won't start

```bash
# Check logs:
docker-compose logs

# Common issues:
# - Missing certs: Run generate_certificates_python.py
# - Permission denied: sudo chmod 644 certs/*.pem certs/*.crt certs/*.key
# - Port in use: docker-compose down, then up -d
```

### Problem: Can't connect from external

```bash
# Check firewall:
sudo ufw status
sudo ufw allow 8445/tcp

# Check if server is listening:
sudo netstat -tulpn | grep 8445
```

## Next Steps After Deployment

1. Send `ca-cert.pem` to IQE team
2. Ask them to import it into trust store OR enable "skip cert verification"
3. Test with IQE UI
4. Celebrate! 🎉

## Important Note

**Do NOT commit certificates to git!** They're in `.gitignore` for security.

Always regenerate on each server. The scripts make it easy:
- `generate_certificates_python.py` - Creates CA and basic certs
- `fix_server_cert.py` - Adds IP to server cert (critical!)
- `create_iqe_user.py` - Creates bootstrap user
- `generate_ra_certificate.py` - Creates RA cert for client auth
