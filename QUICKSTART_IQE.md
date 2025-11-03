# Quick Start: IQE Gateway Integration

## Prerequisites

✅ Python 3.8+ installed
✅ All dependencies installed: `pip install -r requirements.txt`
✅ You have this codebase cloned

---

## Step 1: Generate Certificates

```bash
# Use the Python-based certificate generator (works on Windows without OpenSSL config)
python generate_certificates_python.py
```

**Expected output**:
```
[SUCCESS] Certificate setup completed!

Generated certificates:
  - certs/ca-cert.pem      (Root CA certificate)
  - certs/ca-key.pem       (Root CA private key)
  - certs/server.crt       (EST server certificate)
  - certs/server.key       (EST server private key)
```

---

## Step 2: Create Bootstrap User

```bash
# Create user for IQE gateway to use
python -m python_est.cli add-user iqe-gateway

# Enter password when prompted (e.g., "iqe-secure-password")
# Remember this - you'll give it to IQE team
```

---

## Step 3: Test the Server (DER Mode)

```bash
# Start server with IQE configuration
python est_server.py --config config-iqe.yaml
```

**Expected output**:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on https://0.0.0.0:8445
```

**In another terminal**, test it works:

```bash
# Test 1: Get CA cert (should return binary DER)
curl -k https://localhost:8445/.well-known/est/cacerts --output cacerts.p7b

# Verify it's binary (not base64)
file cacerts.p7b
# Expected: "cacerts.p7b: data"

# Test 2: Verify it's valid PKCS#7
openssl pkcs7 -in cacerts.p7b -inform DER -print_certs -out ca.pem
cat ca.pem
# Should show CA certificate
```

---

## Step 4: Provide to IQE Team

**Send them**:

1. **CA Certificate**: `certs/ca-cert.pem`
   ```bash
   cat certs/ca-cert.pem
   ```

2. **EST Server URL**: `https://your-server-ip:8445`

3. **Bootstrap Credentials**:
   - Username: `iqe-gateway`
   - Password: `<password you created in Step 2>`

4. **Integration Guide**: `IQE_INTEGRATION.md`

---

## Step 5: Get Clarification from IQE Team

**Critical questions to ask**:

1. **TLS Trust** (MOST IMPORTANT):
   ```
   Q: "Can you import our ca-cert.pem into IQE's trust store?
      Without this, HTTPS connections will fail.

      If you can't, we'll need to get a public CA certificate (Let's Encrypt).

      Which option works for you?"
   ```

2. **Device Naming**:
   ```
   Q: "What Common Name (CN) format will you use in CSRs for pumps?
      Example formats:
      - ward-a-pump-001
      - icu-infusion-pump-042
      - pump-12345

      This CN will appear in our dashboard."
   ```

3. **Test Environment**:
   ```
   Q: "Do you have a test IQE instance we can use for integration testing
      before going to production?"
   ```

---

## Step 6: Test with IQE

Once IQE team is ready:

### Test 1: IQE Fetches CA Cert
```bash
curl -k https://your-server:8445/.well-known/est/cacerts --output cacerts.p7b
file cacerts.p7b  # Should show "data" (binary)
```

### Test 2: IQE Performs Bootstrap

**IQE generates CSR for pump**:
```bash
openssl req -new -newkey rsa:2048 -nodes \
  -keyout pump-001-key.pem \
  -out pump-001-csr.pem \
  -subj "/CN=ward-a-pump-001/O=Hospital/C=US"
```

**IQE POSTs to bootstrap**:
```bash
curl -k -X POST https://your-server:8445/.well-known/est/bootstrap \
  -u iqe-gateway:iqe-secure-password \
  -H "Content-Type: application/pkcs10" \
  --data-binary @pump-001-csr.pem \
  --output pump-001-cert.p7b

# Verify binary DER response
file pump-001-cert.p7b  # Should show "data"
```

**Verify certificate**:
```bash
openssl pkcs7 -in pump-001-cert.p7b -inform DER -print_certs -out pump-001-cert.pem
openssl x509 -in pump-001-cert.pem -text -noout | grep Subject
# Should show: CN=ward-a-pump-001
```

### Test 3: Check Dashboard

Open browser: `https://localhost:8445/`

You should see:
- Device: `ward-a-pump-001`
- Status: `bootstrap_only` or `enrolled`
- Certificate serial number
- Timestamp

---

## Troubleshooting

### Issue: Certificate generation fails

**Symptom**: `generate_certificates.py` fails with OpenSSL error

**Solution**: Use Python version:
```bash
python generate_certificates_python.py
```

### Issue: Server won't start - "Address already in use"

**Symptom**: `ERROR: [Errno 10048] error while attempting to bind on address`

**Solution**: Kill existing server:
```bash
# Windows
taskkill /F /IM python.exe

# Or change port in config-iqe.yaml
server:
  port: 8446  # Use different port
```

### Issue: IQE reports "invalid format"

**Symptom**: IQE can't parse certificate response

**Check**: Verify config has `response_format: der`
```bash
grep response_format config-iqe.yaml
# Should show: response_format: der
```

**Test**:
```bash
curl -k https://localhost:8445/.well-known/est/cacerts --output test.p7b
file test.p7b
# MUST show "data" (binary), NOT "ASCII text" (base64)
```

### Issue: TLS connection fails

**Symptom**: IQE can't connect to EST server

**Solutions**:

1. **Check if IQE imported CA cert**:
   ```bash
   # IQE should be able to connect with CA cert
   curl --cacert certs/ca-cert.pem https://your-server:8445/.well-known/est/cacerts
   ```

2. **Temporarily test with -k (insecure)**:
   ```bash
   curl -k https://your-server:8445/.well-known/est/cacerts
   # If this works but with CA cert doesn't, IQE needs to import CA cert
   ```

### Issue: 401 Authentication failed

**Symptom**: Bootstrap returns 401 Unauthorized

**Check**:
1. User exists:
   ```bash
   python -m python_est.cli list-users
   ```

2. Password correct (try resetting):
   ```bash
   python -m python_est.cli add-user iqe-gateway  # Overwrites existing
   ```

---

## Dashboard Access

**URL**: `https://localhost:8445/`

**Features**:
- View all enrolled devices
- See device IDs (from CSR Common Name)
- Check enrollment status
- View certificate serial numbers
- See enrollment timestamps
- Delete devices (for re-enrollment)

**No authentication required** for dashboard (it's informational only).

---

## Production Deployment

Once testing is complete:

1. **Set proper certificate validity**:
   ```yaml
   # config-iqe.yaml
   ca:
     cert_validity_days: 365  # Adjust as needed
   ```

2. **Enable rate limiting**:
   ```yaml
   rate_limit_enabled: true
   rate_limit_requests: 100
   rate_limit_window: 3600
   ```

3. **Set up monitoring**:
   ```bash
   # Monitor server logs
   journalctl -u python-est -f
   ```

4. **Create systemd service** (Linux):
   ```bash
   sudo systemctl enable python-est
   sudo systemctl start python-est
   ```

5. **Backup regularly**:
   ```bash
   tar -czf est-backup-$(date +%Y%m%d).tar.gz certs/ data/ config-iqe.yaml
   ```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `config-iqe.yaml` | IQE-specific configuration (response_format: der) |
| `certs/ca-cert.pem` | CA certificate (provide to IQE team) |
| `certs/ca-key.pem` | CA private key (KEEP SECURE!) |
| `certs/server.crt` | EST server TLS certificate |
| `certs/server.key` | EST server TLS private key |
| `data/device_tracking.json` | Device enrollment database |
| `certs/srp_users.db.*` | User credentials database |

---

## Next Steps

✅ Certificates generated
✅ Server tested locally
✅ IQE team provided with CA cert and credentials
⏳ **Waiting for**: IQE team confirmation on TLS trust
⏳ **Waiting for**: IQE test environment access
⏳ **Next**: Joint integration testing

---

## Support

- **Integration Guide**: See `IQE_INTEGRATION.md` for detailed documentation
- **Test Results**: See `TEST_RESULTS.md` for code verification
- **Changes Summary**: See `IQE_CHANGES_SUMMARY.md` for technical details

**Questions?** Open an issue on GitHub or reach out to the team.

---

**Last Updated**: 2025-11-03
**Status**: ✅ Ready for IQE integration testing





✅ Everything is Ready! Here's What to Do:
1. Git Commands to Push Code
git checkout deploy_v1
git add src/python_est/config.py src/python_est/ca.py src/python_est/server.py
git add config-iqe.yaml generate_certificates_python.py create_iqe_user.py
git add IQE_INTEGRATION.md IQE_CHANGES_SUMMARY.md QUICKSTART_IQE.md 
git add SETUP_SUMMARY.md test_iqe_mode.py TEST_RESULTS.md

git commit -m "feat: Add IQE gateway support with DER response format

- Add response_format config (base64/der)
- Support raw DER PKCS#7 for IQE gateway
- Add Windows-compatible cert generator
- Add user creation script
- All tests passing, 100% backward compatible

For: IQE medical device integration"

git push origin deploy_v1
2. Bootstrap Credentials (Already Created)
Username: iqe-gateway
Password: iqe-secure-password-2024
Save these - you'll give them to IQE team.
3. On Ubuntu VM (After Pulling)
# Pull code
git clone <your-repo>
cd python-est
git checkout deploy_v1

# Install dependencies
pip3 install -r requirements.txt
pip3 install -e .

# Generate certs
python3 generate_certificates_python.py

# Create user (already has password in script)
python3 create_iqe_user.py

# Start server
python3 est_server.py --config config-iqe.yaml

# OR with Docker:
docker build -t python-est-iqe .
docker run -d --name est-server-iqe -p 8445:8445 \
  -v $(pwd)/certs:/app/certs:ro \
  -v $(pwd)/data:/app/data \
  python-est-iqe
4. Test on Ubuntu
curl -k https://localhost:8445/.well-known/est/cacerts --output test.p7b
file test.p7b  # Should show "data" (binary)
5. Give to IQE Team
✅ CA Certificate: cat certs/ca-cert.pem
✅ Server URL: https://<ubuntu-vm-ip>:8445
✅ Credentials: iqe-gateway / iqe-secure-password-2024
✅ Documentation: SETUP_SUMMARY.md or IQE_INTEGRATION.md
📋 All Files Ready:
✅ Code changes (tested and working)
✅ Certificates generated
✅ Bootstrap user created
✅ Configuration ready
✅ Documentation complete
✅ Test suite passing
You're all set to push to GitHub and deploy on Ubuntu! 🚀 Share updates as you go through the integration - I'm here if you need help!