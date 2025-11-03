# IQE Integration Setup - Complete Summary

## ✅ What's Done

### 1. Certificates Generated
```
certs/ca-cert.pem      (2.0K) ← Give this to IQE team
certs/ca-key.pem       (3.2K) - Keep secure!
certs/server.crt       (1.7K)
certs/server.key       (1.7K)
certs/client.crt       (1.6K)
certs/client.key       (1.7K)
```

### 2. Bootstrap User Created
```
Username: iqe-gateway
Password: iqe-secure-password-2024
```

### 3. Code Changes Ready
- ✅ DER mode implemented and tested
- ✅ Base64 mode (default) still works
- ✅ Configuration: `config-iqe.yaml`
- ✅ All tests passing

---

## 📤 Git Commands (Run These Now)

```bash
# 1. Make sure you're on deploy_v1 branch
git status
git checkout deploy_v1

# 2. Stage all IQE changes
git add src/python_est/config.py
git add src/python_est/ca.py
git add src/python_est/server.py
git add config-iqe.yaml
git add generate_certificates_python.py
git add create_iqe_user.py
git add IQE_INTEGRATION.md
git add IQE_CHANGES_SUMMARY.md
git add QUICKSTART_IQE.md
git add SETUP_SUMMARY.md
git add test_iqe_mode.py
git add TEST_RESULTS.md

# 3. Commit
git commit -m "feat: Add IQE gateway support with DER response format

- Add response_format config option (base64 or der)
- Modify CA module to support raw DER PKCS#7 responses
- Update all EST endpoints to conditionally return DER or base64
- Add IQE-specific configuration and documentation
- Include Windows-compatible certificate generator
- Add user creation script
- Add automated test suite (all tests passing)
- Maintain 100% backward compatibility

Tested: DER mode and base64 mode both verified working
For: IQE medical device gateway integration
Docs: QUICKSTART_IQE.md and IQE_INTEGRATION.md"

# 4. Push to GitHub
git push origin deploy_v1
```

---

## 🐳 Ubuntu VM Setup (After Pulling Code)

### Prerequisites on Ubuntu VM

```bash
# Install Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Clone repo
git clone <your-repo-url>
cd python-est
git checkout deploy_v1
```

### Option 1: Run Without Docker (Simpler for Testing)

```bash
# Install Python dependencies
pip3 install -r requirements.txt

# Install package
pip3 install -e .

# Generate certificates
python3 generate_certificates_python.py

# Create bootstrap user
python3 create_iqe_user.py

# Start server
python3 est_server.py --config config-iqe.yaml
```

### Option 2: Run With Docker

```bash
# Build image
docker build -t python-est-iqe:latest .

# Generate certificates (FIRST TIME ONLY)
docker run --rm -v $(pwd)/certs:/app/certs \
  python-est-iqe:latest python generate_certificates_python.py

# Create bootstrap user (FIRST TIME ONLY)
docker run --rm -v $(pwd)/certs:/app/certs \
  python-est-iqe:latest python create_iqe_user.py

# Run server
docker run -d \
  --name est-server-iqe \
  -p 8445:8445 \
  -v $(pwd)/certs:/app/certs:ro \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config-iqe.yaml:/app/config.yaml:ro \
  --restart unless-stopped \
  python-est-iqe:latest

# Check logs
docker logs -f est-server-iqe

# Check status
docker ps
```

### Test Server on Ubuntu VM

```bash
# Test 1: CA certs endpoint (should return binary DER)
curl -k https://localhost:8445/.well-known/est/cacerts --output cacerts.p7b
file cacerts.p7b
# Expected: "cacerts.p7b: data"

# Test 2: Verify it's valid PKCS#7
openssl pkcs7 -in cacerts.p7b -inform DER -print_certs -out ca.pem
cat ca.pem
# Should show CA certificate

# Test 3: Bootstrap enrollment
openssl req -new -newkey rsa:2048 -nodes \
  -keyout test-pump-key.pem \
  -out test-pump-csr.pem \
  -subj "/CN=test-pump-001/O=Hospital/C=US"

curl -k -X POST https://localhost:8445/.well-known/est/bootstrap \
  -u iqe-gateway:iqe-secure-password-2024 \
  -H "Content-Type: application/pkcs10" \
  --data-binary @test-pump-csr.pem \
  --output test-pump-cert.p7b

file test-pump-cert.p7b
# Expected: "data" (binary)

# Verify certificate
openssl pkcs7 -in test-pump-cert.p7b -inform DER -print_certs -out test-pump-cert.pem
openssl x509 -in test-pump-cert.pem -text -noout | grep Subject
# Should show: CN=test-pump-001
```

### Open Firewall Port

```bash
# Ubuntu UFW
sudo ufw allow 8445/tcp
sudo ufw status

# Or iptables
sudo iptables -A INPUT -p tcp --dport 8445 -j ACCEPT
sudo iptables-save
```

---

## 📋 Provide to IQE Team

### 1. CA Certificate

```bash
# From Ubuntu VM
cat certs/ca-cert.pem
```

**Send them this file**. They MUST import it into their trust store.

### 2. EST Server URL

```
https://<ubuntu-vm-ip>:8445
```

Replace `<ubuntu-vm-ip>` with your actual VM IP address.

### 3. Bootstrap Credentials

```
Username: iqe-gateway
Password: iqe-secure-password-2024
```

**IMPORTANT**: Send these securely (not via email/Slack). Use encrypted channel.

### 4. EST Endpoints

IQE will use these:
```
GET  /.well-known/est/cacerts        - Get CA certificate (no auth)
POST /.well-known/est/bootstrap      - Initial enrollment (basic auth)
POST /.well-known/est/simpleenroll   - Certificate enrollment (basic auth or client cert)
```

### 5. Device Naming Convention

**Ask IQE**: What Common Name (CN) format will you use in CSRs?

Examples:
- `ward-a-pump-001`
- `icu-infusion-pump-042`
- `pump-12345`

This CN will appear in the EST dashboard.

---

## ⚠️ Critical Questions for IQE Team

### Question 1: TLS Trust (MOST IMPORTANT)

**YOU MUST ASK THIS**:

> "Can you import our CA certificate (ca-cert.pem) into IQE's trust store?
>
> Without this, HTTPS connections will fail with certificate verification errors.
>
> Options:
> - A) You import our ca-cert.pem (recommended)
> - B) We get a public CA certificate (Let's Encrypt)
>
> Which option works for you?"

**If they say "we can't import your cert"**: You'll need to get a Let's Encrypt certificate for your EST server.

### Question 2: Test Environment

> "Do you have a test IQE instance we can use for integration testing before production?"

### Question 3: Device Naming

> "What Common Name (CN) format will you use in CSRs for pumps?
>
> This CN will appear in our dashboard for tracking."

---

## 🎯 Testing Checklist

### On Your Side (Ubuntu VM)

- [ ] Server starts without errors
- [ ] CA certs endpoint returns binary DER: `file cacerts.p7b` shows "data"
- [ ] Bootstrap enrollment works with test CSR
- [ ] Dashboard accessible at `https://<vm-ip>:8445/`
- [ ] Test device appears in dashboard

### With IQE Team

- [ ] IQE can fetch CA cert from `/.well-known/est/cacerts`
- [ ] IQE receives binary DER (not base64)
- [ ] IQE can POST CSR to `/bootstrap` endpoint
- [ ] IQE receives binary DER certificate response
- [ ] IQE can parse PKCS#7 and extract certificate
- [ ] Device appears in dashboard with correct CN

---

## 📊 Dashboard Access

**URL**: `https://<ubuntu-vm-ip>:8445/`

**No authentication required** (read-only dashboard)

**Shows**:
- Enrolled devices with human-readable names
- Enrollment status (bootstrap_only / enrolled)
- Certificate serial numbers
- Enrollment timestamps
- Delete buttons (for re-enrollment)

---

## 🔧 Troubleshooting

### Server Won't Start

```bash
# Check if port is in use
sudo netstat -tulpn | grep 8445

# Check Docker logs
docker logs est-server-iqe

# Run in foreground to see errors
python3 est_server.py --config config-iqe.yaml
```

### IQE Can't Connect

```bash
# Test from IQE machine
curl -k https://<ubuntu-vm-ip>:8445/.well-known/est/cacerts

# If this fails: firewall issue
# If this works but with CA cert fails: they need to import ca-cert.pem
```

### IQE Reports "Invalid Format"

```bash
# Check response format
curl -k https://<ubuntu-vm-ip>:8445/.well-known/est/cacerts --output test.p7b
file test.p7b

# MUST show "data" (binary DER)
# If shows "ASCII text": config has wrong response_format
```

Check `config-iqe.yaml`:
```yaml
response_format: der  # ← Must be "der" not "base64"
```

---

## 📁 Files Reference

| File | Purpose | Share with IQE? |
|------|---------|-----------------|
| `certs/ca-cert.pem` | CA certificate | ✅ YES |
| `certs/ca-key.pem` | CA private key | ❌ NO (keep secret!) |
| `certs/server.crt` | Server TLS cert | ❌ NO |
| `certs/server.key` | Server TLS key | ❌ NO (keep secret!) |
| `config-iqe.yaml` | IQE configuration | ℹ️ Reference only |
| `QUICKSTART_IQE.md` | Quick start guide | ✅ YES |
| `IQE_INTEGRATION.md` | Full integration guide | ✅ YES |

---

## 🎉 Success Criteria

You'll know it's working when:

1. ✅ Server starts on Ubuntu VM without errors
2. ✅ `curl -k https://<vm-ip>:8445/.well-known/est/cacerts` returns binary data
3. ✅ IQE can fetch CA cert and receives DER format
4. ✅ IQE can POST CSR and receives DER certificate
5. ✅ Device appears in dashboard with correct CN
6. ✅ IQE can provision certificates to pumps

---

## 📞 Next Steps

1. **NOW**: Push code to GitHub (deploy_v1 branch)
2. **TODAY**: Set up Ubuntu VM and test locally
3. **THIS WEEK**: Coordinate with IQE team
4. **NEXT WEEK**: Joint integration testing

---

**Questions?** Check:
- `QUICKSTART_IQE.md` - Quick reference
- `IQE_INTEGRATION.md` - Detailed guide
- `TEST_RESULTS.md` - Test verification

**Status**: ✅ Ready for deployment!

---

**Last Updated**: 2025-11-03
**Author**: Pranav Kumar
**Project**: Python-EST IQE Gateway Integration
