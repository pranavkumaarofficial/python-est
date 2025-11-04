# Files for IQE Team - EST Server Integration

## Current Issue

The new IQE version shows:
```
Failed to obtain root certificate. The SSL connection could not be established, see inner exception.
```

This means IQE doesn't trust the EST server's TLS certificate.

## Solution: Import CA Certificate

IQE team needs to import our CA certificate into their trust store.

---

## File to Import: ca-cert.pem

**Location on VM**: `/path/to/python-est/certs/ca-cert.pem`

**Get it with:**
```bash
# From IQE server (brdinterop6332):
curl -k https://10.42.56.101:8445/.well-known/est/cacerts -o /tmp/cacerts.p7
openssl pkcs7 -inform DER -in /tmp/cacerts.p7 -print_certs -out /tmp/ca-cert.pem
cat /tmp/ca-cert.pem
```

**Or copy directly from EST server:**
```bash
scp user@10.42.56.101:/path/to/python-est/certs/ca-cert.pem .
```

---

## How to Import (Depends on IQE Deployment)

### Option 1: System Trust Store (Linux/Ubuntu)
```bash
# Copy to system trust store
sudo cp ca-cert.pem /usr/local/share/ca-certificates/python-est-ca.crt
sudo update-ca-certificates

# Verify
ls -la /etc/ssl/certs/ | grep -i python
```

### Option 2: Container Trust Store (Docker/Kubernetes)
If IQE runs in a container, add to Dockerfile:
```dockerfile
COPY ca-cert.pem /usr/local/share/ca-certificates/python-est-ca.crt
RUN update-ca-certificates
```

Or mount as volume:
```yaml
volumes:
  - ./ca-cert.pem:/usr/local/share/ca-certificates/python-est-ca.crt:ro
```

### Option 3: .NET Application Trust Store
If IQE is a .NET application, they might need to configure `HttpClient`:
```csharp
var handler = new HttpClientHandler();
handler.ServerCertificateCustomValidationCallback =
    HttpClientHandler.DangerousAcceptAnyServerCertificateValidator;
```
(Development only - not for production!)

Or import into .NET certificate store:
```bash
dotnet dev-certs https --trust
# Then import ca-cert.pem
```

### Option 4: Application Configuration
Check if IQE has a configuration setting like:
```yaml
est_server:
  ca_certificate: /path/to/ca-cert.pem
  verify_ssl: true
```

---

## Testing After Import

From IQE server (brdinterop6332):
```bash
# Without CA cert (should fail):
curl -v https://10.42.56.101:8445/.well-known/est/cacerts
# Error: SSL certificate problem: self signed certificate in certificate chain

# With CA cert (should succeed):
curl -v --cacert /tmp/ca-cert.pem https://10.42.56.101:8445/.well-known/est/cacerts
# Success: Returns PKCS#7 data
```

---

## Alternative: Disable Certificate Verification (QUICK TEST ONLY)

If they need to test immediately, they can disable cert verification:

**For testing only** (not secure for production):
```csharp
// In IQE code
ServicePointManager.ServerCertificateValidationCallback =
    (sender, certificate, chain, sslPolicyErrors) => true;
```

Or check if IQE has a config option:
```yaml
est_server:
  verify_ssl: false  # For testing only!
```

---

## CA Certificate Details

**Subject**: CN=Python-EST Root CA, O=Test CA, L=Test, ST=CA, C=US
**Serial**: 63:83:a5:d9:0a:c1:a5:38:76:0b:ac:fe:09:a0:0f:26:98:b9:0e:8c
**Validity**: 10 years (until 2035-11-01)
**Key Size**: RSA 4096-bit
**Signature**: SHA256WithRSAEncryption

---

## Quick Test Script

Run this on brdinterop6332 to get the CA cert and test:

```bash
#!/bin/bash
# Quick test for CA cert trust

echo "=== Downloading CA certificate ==="
curl -k https://10.42.56.101:8445/.well-known/est/cacerts -o /tmp/cacerts.p7
openssl pkcs7 -inform DER -in /tmp/cacerts.p7 -print_certs -out /tmp/ca-cert.pem

echo ""
echo "=== CA Certificate ==="
cat /tmp/ca-cert.pem

echo ""
echo "=== Testing WITHOUT CA cert (should fail) ==="
curl -v https://10.42.56.101:8445/.well-known/est/cacerts 2>&1 | grep -i "SSL certificate"

echo ""
echo "=== Testing WITH CA cert (should succeed) ==="
curl -v --cacert /tmp/ca-cert.pem https://10.42.56.101:8445/.well-known/est/cacerts -o /dev/null

echo ""
echo "=== Result ==="
if [ $? -eq 0 ]; then
    echo "SUCCESS! CA cert works."
    echo "Now import /tmp/ca-cert.pem into IQE's trust store"
else
    echo "FAILED! Check network/firewall"
fi
```

---

## Summary for IQE Team

**Problem**: IQE can't establish SSL connection to EST server
**Cause**: IQE doesn't trust the EST server's CA certificate
**Solution**: Import `ca-cert.pem` into IQE's trust store

**Steps**:
1. Get CA cert from EST server (commands above)
2. Import into IQE's trust store (method depends on deployment)
3. Restart IQE application
4. Test - SSL error should be gone

**Alternative for immediate testing**: Disable SSL verification (not secure!)

---

## Contact

If you need help with the import process, let me know:
- What platform is IQE running on? (Linux/Windows/Container)
- What language/framework? (.NET/Java/Python)
- Do you have access to modify IQE's trust store?

We can provide specific instructions based on your setup.
