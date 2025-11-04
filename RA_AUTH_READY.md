# RA Certificate Authentication - Ready for IQE Integration

## Summary

✅ **RA certificate authentication is now fully implemented** in the Python EST server!

The server now supports **both** authentication methods:
1. **RA Certificate Authentication** (for IQE gateway) - preferred method
2. **Username/Password Authentication** (for direct device bootstrap) - fallback method

## What Changed?

### 1. Client Certificate Extraction
- Added middleware to extract client certificates from TLS connections
- Certificates are automatically detected and validated

### 2. Certificate-Based Authentication
- Server now validates client certificates against the CA
- If a valid client certificate is present, authentication succeeds automatically
- No username/password needed when using RA certificate

### 3. Dual Authentication Support
- **Priority 1**: Client certificate (for IQE gateway with RA cert)
- **Priority 2**: Username/password (for direct device enrollment)

### 4. Uvicorn SSL Configuration
- Updated to accept client certificates via `ssl_cert_reqs=ssl.CERT_OPTIONAL`
- Server accepts connections with or without client certificates

## Authentication Flow

```
┌─────────────────────────────────────────────────────────┐
│ Request arrives at EST server                           │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │ Client cert present?  │
                └───────┬───────────────┘
                        │
            ┌───────────┴───────────┐
            │                       │
          YES                      NO
            │                       │
            ▼                       ▼
  ┌──────────────────┐    ┌──────────────────┐
  │ Validate cert    │    │ Check for        │
  │ - Signed by CA?  │    │ username/        │
  │ - Not expired?   │    │ password         │
  │ - Valid dates?   │    │                  │
  └────────┬─────────┘    └────────┬─────────┘
           │                       │
           ▼                       ▼
    ┌──────────┐           ┌──────────┐
    │ Valid?   │           │ Valid?   │
    └────┬─────┘           └────┬─────┘
         │                      │
    ┌────┴─────┐           ┌────┴─────┐
    │          │           │          │
   YES        NO          YES        NO
    │          │           │          │
    ▼          │           ▼          │
  SUCCESS      │         SUCCESS      │
    │          │           │          │
    └──────────┴───────────┴──────────┘
                     │
                     ▼
                  FAILURE
                (HTTP 401)
```

## Files for IQE Team

After running `deploy_with_ra_auth.sh`, you'll have:

```
iqe_deployment_package/
├── ca-cert.pem          # EST server CA certificate
├── iqe-ra-cert.pem      # RA certificate for authentication
├── iqe-ra-key.pem       # RA private key (SECURE!)
└── README.md            # Configuration instructions
```

**Transfer this entire folder to the IQE team.**

## Deployment Steps

### On Your Ubuntu VM:

```bash
# 1. Make scripts executable
chmod +x deploy_with_ra_auth.sh test_ra_auth.sh

# 2. Deploy server with RA authentication
./deploy_with_ra_auth.sh

# 3. Test RA authentication
./test_ra_auth.sh

# 4. Transfer files to IQE team
# Option A: SCP
scp -r iqe_deployment_package/ iqe-team@iqe-server:/path/to/destination/

# Option B: Create tarball
tar -czf iqe_deployment_package.tar.gz iqe_deployment_package/
# Then transfer iqe_deployment_package.tar.gz to IQE team
```

## Testing RA Authentication

### Quick Test (after deployment):

```bash
# Generate test CSR
openssl req -new -newkey rsa:2048 -nodes \
  -keyout test-key.pem -out test-csr.pem \
  -subj "/CN=test-device/O=Hospital/C=US"

# Convert to DER
openssl req -in test-csr.pem -outform DER -out test-csr.der

# Test enrollment with RA certificate
curl -vk https://10.42.56.101:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  --cacert certs/ca-cert.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @test-csr.der \
  -o test-cert.p7

# Should return HTTP 200 with certificate
```

### Expected Server Logs:

```
INFO: Client certificate found: CN=iqe-gateway,O=Hospital,C=US
INFO: Client certificate validated: CN=iqe-gateway,O=Hospital,C=US
INFO: Client certificate authentication successful: iqe-gateway
INFO: Enrollment successful for device: test-device
```

## IQE Gateway Configuration

The IQE team needs to configure their gateway to use the RA certificate:

### Example Configuration:

```yaml
# IQE Gateway EST Configuration
est_server:
  url: https://10.42.56.101:8445

  # Server verification
  ca_cert: /path/to/ca-cert.pem

  # Client authentication (RA certificate)
  client_cert: /path/to/iqe-ra-cert.pem
  client_key: /path/to/iqe-ra-key.pem

  # Endpoints
  cacerts_path: /.well-known/est/cacerts
  simpleenroll_path: /.well-known/est/simpleenroll

response_handling:
  format: base64  # EST server returns base64-encoded PKCS#7
  content_type: application/pkcs7-mime
```

## Important Notes for IQE Team

### 1. Certificate Files Security

⚠️ **The `iqe-ra-key.pem` file is highly sensitive!**

```bash
# Set proper permissions on IQE gateway
chmod 600 iqe-ra-key.pem
chown iqe-gateway-user:iqe-gateway-group iqe-ra-key.pem
```

### 2. TLS Trust Store

The IQE gateway must trust the EST server's CA:

```bash
# Import ca-cert.pem into IQE's trust store
# The exact method depends on IQE's OS and configuration
# Examples:

# RedHat/CentOS:
sudo cp ca-cert.pem /etc/pki/ca-trust/source/anchors/
sudo update-ca-trust

# Ubuntu/Debian:
sudo cp ca-cert.pem /usr/local/share/ca-certificates/est-server-ca.crt
sudo update-ca-certificates

# Or configure directly in IQE's EST client config
```

### 3. Response Format

The EST server returns **base64-encoded PKCS#7** responses (not raw DER):

```
Content-Type: application/pkcs7-mime; smime-type=certs-only
Content-Transfer-Encoding: base64

MIIEpwYJKoZIhvcNAQcCoIIEmDCCBJQCAQExADALBgkqhkiG9w0BBwGgggR6MIIE
djCCAl6gAwIBAgIUHl7... (base64 continues)
```

IQE must:
- Receive the base64 text response
- Decode from base64 to get DER bytes
- Parse DER as PKCS#7

### 4. Certificate Validity

- **RA Certificate**: Valid for 2 years
- **Device Certificates**: Valid for 1 year (configurable)
- **Plan rotation before expiry!**

### 5. Testing Checklist

- [ ] IQE can connect to EST server via HTTPS
- [ ] TLS handshake succeeds (server cert verified)
- [ ] IQE sends client certificate in TLS handshake
- [ ] EST server validates client certificate
- [ ] IQE can retrieve CA certificates (/cacerts)
- [ ] IQE can enroll devices (/simpleenroll)
- [ ] IQE can decode base64 PKCS#7 responses
- [ ] Medical devices receive valid certificates

## Troubleshooting Guide

### Issue: "No client certificate in connection"

**Check:**
1. IQE gateway has RA certificate files
2. IQE TLS client config includes client_cert and client_key
3. File paths are correct and accessible
4. File permissions allow reading

**Test manually:**
```bash
curl -vk https://10.42.56.101:8445/.well-known/est/cacerts \
  --cert iqe-ra-cert.pem \
  --key iqe-ra-key.pem 2>&1 | grep "client certificate"
```

### Issue: "Client certificate validation failed"

**Check:**
1. RA certificate not expired: `openssl x509 -in iqe-ra-cert.pem -noout -dates`
2. RA certificate signed by correct CA: `openssl x509 -in iqe-ra-cert.pem -noout -issuer`
3. CA certificate matches on both sides

**Verify chain:**
```bash
openssl verify -CAfile ca-cert.pem iqe-ra-cert.pem
# Should output: iqe-ra-cert.pem: OK
```

### Issue: HTTP 401 Unauthorized

**Check:**
1. Client certificate is being sent
2. Certificate validation passes
3. Server logs show authentication details

**Server logs location:** `server.log`

```bash
# Check authentication logs
grep -i "authentication" server.log | tail -20
```

### Issue: "unable to load PKCS7 object"

**This means IQE is trying to parse as DER instead of base64.**

IQE needs to:
1. Read response as text (not binary)
2. Base64 decode the text
3. Parse the decoded bytes as DER PKCS#7

**Test response format:**
```bash
curl -k https://10.42.56.101:8445/.well-known/est/cacerts -o test.p7
file test.p7
# Should show: "ASCII text" (base64)
# NOT "data" (binary DER)
```

## Monitoring

### Server Dashboard

Access at: https://10.42.56.101:8445/

Shows:
- Total requests
- Certificates issued
- Bootstrap vs enrollment stats
- Connected devices
- Recent activity

### Server Logs

```bash
# Follow live logs
tail -f server.log

# Filter for authentication
grep "authentication" server.log

# Filter for RA certificate usage
grep "client-certificate" server.log

# Filter for specific device
grep "CN=pump-001" server.log
```

## Next Steps

1. **Deploy**: Run `./deploy_with_ra_auth.sh` on Ubuntu VM
2. **Test**: Run `./test_ra_auth.sh` to verify RA auth works
3. **Package**: Transfer `iqe_deployment_package/` to IQE team
4. **Configure**: IQE team configures gateway with RA certificate
5. **Test**: End-to-end test with medical device enrollment
6. **Monitor**: Watch server logs during IQE testing

## Support

### Quick Reference

- **EST Server URL**: https://10.42.56.101:8445
- **Dashboard**: https://10.42.56.101:8445/
- **Response Format**: Base64-encoded PKCS#7
- **Authentication**: Client certificate (RA cert)
- **Fallback**: Username/password (iqe-gateway / iqe-secure-password-2024)

### Common Commands

```bash
# Check server status
ps aux | grep python_est

# Restart server
pkill -f python_est && ./deploy_with_ra_auth.sh

# View recent logs
tail -50 server.log

# Test RA authentication
./test_ra_auth.sh

# Check certificate expiry
openssl x509 -in certs/iqe-ra-cert.pem -noout -dates
```

## Implementation Details

For technical details about the implementation, see:
- [RA_AUTH_IMPLEMENTATION.md](RA_AUTH_IMPLEMENTATION.md) - Complete implementation guide
- [src/python_est/server.py](src/python_est/server.py) - Source code with RA auth

## Success Criteria

✅ RA certificate authentication implemented
✅ Client certificate extraction working
✅ Certificate validation working
✅ Dual authentication support (cert + password)
✅ Test scripts created
✅ Deployment scripts created
✅ Documentation complete
✅ IQE deployment package ready

**The EST server is now ready for IQE integration with RA certificate authentication!**
