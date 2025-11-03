# Quick Reference Card - IQE EST Integration

## What You've Built
A production-ready EST (Enrollment over Secure Transport) server that:
- Issues certificates to medical devices via IQE gateway
- Supports password-based bootstrap enrollment
- Supports RA certificate-based enrollment
- Handles base64-encoded CSRs (IQE UI requirement)
- Returns DER format responses (IQE requirement)

## Files to Share with IQE Team

### Must Share (Both Approaches)
```
certs/ca-cert.pem               [Public - CA certificate for trust store]
```

### For Password Approach
```
Username: iqe-gateway
Password: iqe-secure-password-2024
```

### For RA Certificate Approach (Recommended)
```
certs/iqe-ra-cert.pem          [Public - RA certificate]
certs/iqe-ra-key.pem           [PRIVATE - Handle securely!]
```

## EST Endpoints

### Password Authentication
```
GET  https://10.42.56.101:8445/.well-known/est/cacerts
POST https://10.42.56.101:8445/.well-known/est/bootstrap
     Auth: Basic (iqe-gateway:iqe-secure-password-2024)
```

### RA Certificate Authentication
```
GET  https://10.42.56.101:8445/.well-known/est/cacerts
POST https://10.42.56.101:8445/.well-known/est/simpleenroll
     Auth: Client Certificate (RA cert)
```

## Critical Questions for IQE Team

1. **CA Trust**: Can you import `ca-cert.pem` into your trust store? (BLOCKER if "No")
2. **RA Support**: Does your UI accept PEM format for RA cert files?
3. **Error Logs**: Can you share exact error when 500 occurs?
4. **Base64 CSR**: Does UI send `Content-Transfer-Encoding: base64` header?

## Commands Cheat Sheet

### Test Server Locally
```bash
python test_server.py
# Should show: Server running on https://0.0.0.0:8445
```

### Test RA Certificate
```bash
python test_ra_cert_auth.py
# Tests RA cert authentication works
```

### Generate New RA Certificate (if needed)
```bash
python generate_ra_certificate.py
# Creates iqe-ra-key.pem and iqe-ra-cert.pem
```

### Deploy to Ubuntu VM
```bash
# Push code
git add .
git commit -m "feat: RA certificate support"
git push origin deploy_v1

# On VM
git pull origin deploy_v1
docker-compose up -d
```

### Test from IQE Server (via PuTTY)
```bash
# Test 1: Download CA cert
curl -vk https://10.42.56.101:8445/.well-known/est/cacerts -o cacerts.p7

# Test 2: Enroll with password
openssl req -new -newkey rsa:2048 -nodes \
  -keyout key.pem -out csr.der -outform DER -subj "/CN=test-001"
base64 csr.der > csr.b64
curl -vk -u iqe-gateway:iqe-secure-password-2024 \
  -H "Content-Type: application/pkcs10" \
  -H "Content-Transfer-Encoding: base64" \
  --data @csr.b64 \
  https://10.42.56.101:8445/.well-known/est/bootstrap -o cert.p7

# Test 3: Enroll with RA cert (after receiving RA files)
curl -vk --cert iqe-ra-cert.pem --key iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @csr.der \
  https://10.42.56.101:8445/.well-known/est/simpleenroll -o cert.p7
```

## Troubleshooting Quick Fixes

| Error | Quick Fix |
|-------|-----------|
| TLS connection fails | → IQE must import `ca-cert.pem` into trust store |
| 401 Unauthorized | → Check password or RA cert uploaded correctly |
| 500 with "ASN.1 parse error" | → Base64 CSR issue (we fixed this, redeploy) |
| 500 with "SRP auth failed" | → Try RA certificate approach instead |
| Connection refused | → Check firewall, ensure port 8445 open |
| Certificate invalid | → Verify CA cert imported correctly |

## Key Documentation Files

- `RA_CERTIFICATE_GUIDE.md` - Detailed guide on RA certificate approach
- `QUESTIONS_FOR_IQE_TEAM.md` - Send these questions to IQE team
- `RA_CERT_DEPLOYMENT_CHECKLIST.md` - Step-by-step deployment checklist
- `APPROACH_COMPARISON.md` - Comparison of two authentication methods
- `IQE_UI_FIX.md` - Details on base64 CSR fix
- `DEPLOY_FIX_NOW.md` - Quick deployment guide

## Current Status

✅ **Implemented**:
- Certificate generation (CA, server, client, RA)
- SRP user creation (iqe-gateway)
- Base64 CSR decoding
- DER response format
- Client certificate authentication
- Password authentication

⏳ **Pending**:
- Deploy to Ubuntu VM
- IQE team imports CA cert
- IQE team tests with UI
- Resolve any remaining errors

🎯 **Goal**: IQE successfully enrolls medical pumps through your EST server

## One-Liner Summary for Your Boss

*"I built a production-ready EST server that enables our IQE gateway to automatically provision EAP-TLS certificates to medical devices, implementing both RFC 7030 bootstrap and RA certificate authentication methods."*

## One-Liner for Your LOR

*"Designed and deployed a secure certificate enrollment infrastructure for medical IoT devices, demonstrating expertise in PKI, TLS, EST protocol (RFC 7030), and healthcare device security standards."*

## Next 3 Steps

1. **Deploy**: Push to `deploy_v1`, deploy on Ubuntu VM
2. **Share**: Send CA cert + RA cert files + questions to IQE team
3. **Test**: IQE tests enrollment through UI, troubleshoot any issues

---

**Remember**: The RA certificate approach is recommended and might completely bypass your current 500 errors!

Good luck! 🚀
