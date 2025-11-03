# Critical Questions for IQE Team

## Background
We've implemented an EST server that supports both password-based bootstrap and RA (Registration Authority) certificate authentication. We're getting 500 errors with the IQE UI, but manual curl tests work fine.

## CRITICAL Issue: CA Trust Store

**Question 1: CA Certificate Import**

You previously answered "No" when asked if you import the EST server's CA cert into your trust store. This is likely causing TLS connection failures.

**Options:**
- **Option A (Recommended)**: Can you import our CA certificate into IQE's trust store?
  - We will provide: `ca-cert.pem`
  - Purpose: To validate our EST server's TLS certificate
  - This is the standard approach for private EST servers

- **Option B**: Should we get a public CA-signed certificate?
  - Example: Let's Encrypt, DigiCert, etc.
  - More expensive and complex
  - Only needed if you cannot import custom CA certs

**Which option works for your setup?**

---

## RA Certificate Authentication

**Question 2: RA Certificate Upload**

The IQE UI has fields for:
- Registration Authority Key File
- Registration Authority Certificate File

**Can you confirm:**
- Does the UI accept PEM format? (Our files are in PEM format)
- Any specific naming requirements for the files?
- Is this the preferred method over username/password bootstrap?

---

**Question 3: Endpoint Configuration with RA Certificate**

When using RA certificate authentication:
- Do we configure `/simpleenroll` endpoint only?
- OR do you still need both `/bootstrap` AND `/simpleenroll`?

**Background**:
- `/bootstrap` is for password-based initial enrollment
- `/simpleenroll` is for certificate-based enrollment
- With RA cert, the gateway already has a certificate, so logically it should only use `/simpleenroll`

---

## Current 500 Error Debugging

**Question 4: Detailed Error Logs**

Can you share:
- The exact error message from IQE logs when the 500 error occurs?
- Any TLS handshake errors?
- Any certificate validation errors?
- The full error stack trace if available?

**What we know so far:**
- Manual curl with raw DER CSR works: ✓
- IQE UI enrollment fails with 500 error: ✗
- We've added support for base64-encoded CSRs (IQE UI wraps CSRs in base64)

---

**Question 5: Base64 CSR Encoding**

Your documentation shows curl examples with:
```bash
base64 csr.der > csr.b64
curl -H "Content-Transfer-Encoding: base64" --data @csr.b64
```

**Can you confirm:**
- Does IQE UI send CSRs with `Content-Transfer-Encoding: base64` header?
- Does IQE UI expect base64-encoded responses, or raw DER?
- We've implemented base64 detection/decoding - can you test again?

---

## Files We Can Provide

**For Password Authentication (Bootstrap):**
1. `ca-cert.pem` - Import into your trust store (REQUIRED)
2. EST endpoints:
   - `/cacerts`: https://10.42.56.101:8445/.well-known/est/cacerts
   - `/bootstrap`: https://10.42.56.101:8445/.well-known/est/bootstrap
3. Credentials: `iqe-gateway` / `iqe-secure-password-2024`

**For RA Certificate Authentication (Recommended):**
1. `ca-cert.pem` - Import into your trust store (REQUIRED)
2. `iqe-ra-cert.pem` - Upload to IQE UI
3. `iqe-ra-key.pem` - Upload to IQE UI (keep secure!)
4. EST endpoints:
   - `/cacerts`: https://10.42.56.101:8445/.well-known/est/cacerts
   - `/simpleenroll`: https://10.42.56.101:8445/.well-known/est/simpleenroll

---

## Testing Request

**Question 6: Can you test with curl from IQE server?**

To isolate the issue, can you run these commands from the IQE server:

**Test 1: /cacerts (should work without auth)**
```bash
curl -vk https://10.42.56.101:8445/.well-known/est/cacerts -o cacerts.p7
```

**Test 2: /bootstrap with password (base64 CSR)**
```bash
# Generate test CSR
openssl req -new -sha256 -newkey rsa:2048 -nodes \
  -keyout test-key.pem -out test-csr.der -outform DER \
  -subj "/CN=test-pump-001"

# Base64 encode it
base64 test-csr.der > test-csr.b64

# Enroll with base64
curl -vk -u iqe-gateway:iqe-secure-password-2024 \
  -H "Content-Type: application/pkcs10" \
  -H "Content-Transfer-Encoding: base64" \
  --data @test-csr.b64 \
  https://10.42.56.101:8445/.well-known/est/bootstrap \
  -o test-cert.p7
```

**Test 3: /simpleenroll with RA certificate** (after we provide RA cert files)
```bash
curl -vk \
  --cert iqe-ra-cert.pem \
  --key iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @test-csr.der \
  https://10.42.56.101:8445/.well-known/est/simpleenroll \
  -o test-cert.p7
```

Share the output (especially any error messages) from these tests.

---

## Summary of What We Need

1. **Confirmation on CA trust store** - Can you import our CA cert, or do we need public CA cert?
2. **RA certificate support details** - File format, naming, preferred over password?
3. **Endpoint configuration** - Which endpoints to configure with RA cert?
4. **Detailed error logs** - Full stack trace from the 500 errors
5. **Base64 encoding confirmation** - Does UI send base64? Expect base64 response?
6. **Curl test results** - Can you test manually from IQE server with the commands above?

---

## Priority

**HIGHEST PRIORITY**: Question 1 (CA trust store)
- This is likely the root cause of all issues
- Without CA trust, IQE cannot establish TLS connection to EST server
- Everything else is blocked until this is resolved

**SECOND PRIORITY**: Question 6 (curl tests)
- Will help isolate whether issue is IQE UI code or network/config
- If curl works but UI fails, it's an IQE UI bug
- If curl also fails, it's a server configuration issue

**THIRD PRIORITY**: Questions 2-5 (RA cert and debugging)
- RA cert approach might bypass current issues entirely
- But still needs CA trust store to be configured first

---

## Contact

If you have any questions about these questions (meta!), or need clarification on any technical details, please let us know.

We're happy to provide:
- Test certificates
- More detailed logs from our server
- Screen sharing session to debug together
- Any other information needed

Our goal is to get IQE successfully enrolling devices through our EST server!
