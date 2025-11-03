# IQE EST Integration: Two Approaches Comparison

## Quick Summary

You have TWO working options for IQE to authenticate to your EST server. Both are implemented and ready to test.

## Side-by-Side Comparison

| Aspect | Approach 1: Password Auth | Approach 2: RA Certificate |
|--------|---------------------------|----------------------------|
| **EST Endpoint** | `/bootstrap` | `/simpleenroll` |
| **Authentication** | HTTP Basic Auth (username/password) | TLS Client Certificate |
| **Credentials** | `iqe-gateway` / `iqe-secure-password-2024` | `iqe-ra-cert.pem` + `iqe-ra-key.pem` |
| **Security Level** | Medium (password-based) | High (certificate-based) |
| **RFC 7030 Compliance** | Bootstrap flow (Section 4.1) | Simple Enrollment (Section 4.2) |
| **Gateway Pattern** | Works, but not ideal | **Recommended for gateways** |
| **Initial Setup** | Simple (just username/password) | Slightly more complex (upload cert files) |
| **Renewal** | Change password periodically | Renew certificate before expiry (2 years) |
| **Debugging** | Auth errors can be opaque | TLS errors are well-defined |
| **Current Status** | Getting 500 errors (base64 fix may resolve) | Not yet tested by IQE |

## Files Required for Each Approach

### Approach 1: Password Authentication
```
IQE Team Needs:
1. ca-cert.pem (import into trust store)
2. Username: iqe-gateway
3. Password: iqe-secure-password-2024
4. Endpoints:
   - /cacerts: https://10.42.56.101:8445/.well-known/est/cacerts
   - /bootstrap: https://10.42.56.101:8445/.well-known/est/bootstrap
```

### Approach 2: RA Certificate Authentication
```
IQE Team Needs:
1. ca-cert.pem (import into trust store)
2. iqe-ra-cert.pem (upload to UI)
3. iqe-ra-key.pem (upload to UI - keep secure!)
4. Endpoints:
   - /cacerts: https://10.42.56.101:8445/.well-known/est/cacerts
   - /simpleenroll: https://10.42.56.101:8445/.well-known/est/simpleenroll
```

## Authentication Flow Diagrams

### Approach 1: Password Bootstrap
```
[IQE Gateway] --- 1. GET /cacerts ---> [EST Server]
              <-- 2. CA cert (PKCS#7) ---

[IQE Gateway] --- 3. POST /bootstrap ---> [EST Server]
              |   + Basic Auth header
              |   + CSR (base64 or DER)
              |
              <-- 4. Validate password ---
              <-- 5. Issue certificate ---
              <-- 6. Client cert (PKCS#7) --

[IQE Gateway] --- 7. Send cert to pump ---> [Medical Pump]
```

### Approach 2: RA Certificate
```
[IQE Gateway] --- 1. GET /cacerts ---> [EST Server]
              <-- 2. CA cert (PKCS#7) ---

[IQE Gateway] --- 3. TLS Handshake ---> [EST Server]
              |   + Client Cert (RA cert)
              |
              <-- 4. Validate RA cert ---
              |   (Check signature by CA)

[IQE Gateway] --- 5. POST /simpleenroll ---> [EST Server]
              |   + CSR (base64 or DER)
              |
              <-- 6. Issue certificate ---
              <-- 7. Client cert (PKCS#7) --

[IQE Gateway] --- 8. Send cert to pump ---> [Medical Pump]
```

## Which Approach to Use?

### Use Approach 1 (Password) If:
- IQE UI doesn't support RA certificate upload
- You want simpler initial setup
- You're okay with password-based authentication
- The 500 errors get resolved with base64 fix

### Use Approach 2 (RA Certificate) If:
- IQE UI supports RA certificate upload (which it does!)
- You want industry best practices
- You want higher security
- You want to bypass potential SRP/password auth issues
- You're following RFC 7030 gateway recommendations

**Recommendation**: **Try Approach 2 first** (RA Certificate)
- It's more secure
- It's the proper way for EST gateways
- It might bypass the current 500 errors completely
- IQE UI specifically has fields for RA cert upload, suggesting it's supported

## Common Requirements (Both Approaches)

### CRITICAL: CA Trust Store
**Both approaches require** IQE to import your CA certificate into their trust store.

❌ **Without this**: TLS connection will fail (untrusted certificate error)
✅ **With this**: TLS connection succeeds, authentication can proceed

**File to share**: `certs/ca-cert.pem`

**How IQE imports it** (depends on their system):
```bash
# Option 1: Update-ca-certificates (Ubuntu/Debian)
sudo cp ca-cert.pem /usr/local/share/ca-certificates/python-est-ca.crt
sudo update-ca-certificates

# Option 2: Java keystore (if IQE is Java-based)
keytool -import -trustcacerts -alias python-est-ca \
  -file ca-cert.pem -keystore $JAVA_HOME/lib/security/cacerts

# Option 3: Application-specific trust store
# (Depends on how IQE is implemented)
```

### Base64 CSR Support
**Both approaches support** base64-encoded CSRs (IQE UI requirement).

The server will automatically detect `Content-Transfer-Encoding: base64` header and decode the CSR.

### Response Format
**Both approaches return** DER-encoded PKCS#7 (as per IQE requirements).

Configured in `config.yaml`:
```yaml
gateway:
  response_format: der  # Not base64, not pem - raw DER
```

## Testing Commands

### Test Approach 1 (Password)
```bash
# Generate CSR
openssl req -new -newkey rsa:2048 -nodes \
  -keyout pump-key.pem -out csr.der -outform DER \
  -subj "/CN=test-pump-001"

# Base64 encode (IQE UI does this)
base64 csr.der > csr.b64

# Enroll
curl -vk -u iqe-gateway:iqe-secure-password-2024 \
  -H "Content-Type: application/pkcs10" \
  -H "Content-Transfer-Encoding: base64" \
  --data @csr.b64 \
  https://10.42.56.101:8445/.well-known/est/bootstrap \
  -o pump-cert.p7
```

### Test Approach 2 (RA Certificate)
```bash
# Generate CSR
openssl req -new -newkey rsa:2048 -nodes \
  -keyout pump-key.pem -out csr.der -outform DER \
  -subj "/CN=test-pump-001"

# Enroll with RA cert
curl -vk \
  --cert iqe-ra-cert.pem \
  --key iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @csr.der \
  https://10.42.56.101:8445/.well-known/est/simpleenroll \
  -o pump-cert.p7
```

## Can You Use Both?

**Yes!** Your EST server supports both approaches simultaneously:
- Password authentication is enabled (SRP with user `iqe-gateway`)
- Client certificate authentication is enabled (accepts certs signed by CA)

IQE can use whichever approach works best for them.

## Success Criteria

Regardless of which approach:
✅ IQE can download CA certificate from `/cacerts`
✅ IQE can enroll and receive client certificate
✅ Certificate is valid and signed by your CA
✅ Certificate can be deployed to medical pumps
✅ Pumps can use certificate for EAP-TLS with access points

## Troubleshooting Decision Tree

```
IQE enrollment failing?
|
├─ TLS connection fails?
|  └─ → Import ca-cert.pem into IQE trust store
|
├─ 401 Unauthorized?
|  ├─ Using password? → Check username/password correct
|  └─ Using RA cert? → Check cert uploaded correctly
|
├─ 500 Internal Server Error?
|  ├─ Check if CSR is base64-encoded
|  ├─ Check server logs for parsing errors
|  └─ Try the other approach (password ↔ RA cert)
|
└─ Other error?
   └─ Share full error logs with EST server team
```

## Recommendation for Your Demo

**For impressive demo to higher ops**:
1. **Start with Approach 2** (RA Certificate) - shows you know best practices
2. **Explain the security benefits** - certificate-based vs password-based
3. **Show it working** with IQE UI enrollment
4. **Mention Approach 1 as backup** - if they need simpler setup

**For your LOR**:
- "Implemented industry-standard EST server with RFC 7030 compliance"
- "Designed secure certificate enrollment with both bootstrap and RA authentication"
- "Integrated with medical device gateway for automated EAP-TLS provisioning"
- "Demonstrated understanding of PKI, TLS, and IoT security best practices"

Good luck! 🎯
