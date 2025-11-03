# Registration Authority (RA) Certificate Guide for IQE

## Overview

The RA certificate approach is an alternative (and more secure) method for IQE to authenticate to your EST server. Instead of using username/password (bootstrap), IQE uses client certificate authentication.

## How It Works

```
Medical Pump  -->  IQE Gateway  -->  EST Server
                   (uses RA cert)     (validates RA cert)
```

1. **IQE authenticates** using the RA certificate (client cert authentication)
2. **EST server validates** that the RA cert is signed by its CA
3. **IQE requests certificates** on behalf of pumps
4. **EST server issues certificates** to IQE
5. **IQE distributes certificates** to pumps

## RA Certificate vs Password Authentication

| Feature | Password (Bootstrap) | RA Certificate |
|---------|---------------------|----------------|
| Security | Basic Auth credentials | Mutual TLS authentication |
| Scalability | Single credential | Certificate-based, renewable |
| EST Standard | RFC 7030 Bootstrap | RFC 7030 Client Auth |
| Current Status | Getting 500 errors | Worth trying - might bypass issues |
| Endpoints Used | `/bootstrap` | `/simpleenroll` |

## Files Generated

1. **certs/iqe-ra-key.pem** - RA private key (keep secure!)
2. **certs/iqe-ra-cert.pem** - RA certificate (signed by your CA)

Certificate Details:
- Subject: CN=IQE Registration Authority,O=IQE Gateway,L=Hospital,ST=CA,C=US
- Issuer: CN=Python-EST Root CA (your CA)
- Validity: 2 years (until 2027-11-03)
- Purpose: CLIENT_AUTH (TLS client authentication)

## Upload to IQE UI

1. In IQE UI, navigate to the enrollment/EST configuration section
2. Look for these fields:
   - **Registration Authority Key File**: Upload `certs/iqe-ra-key.pem`
   - **Registration Authority Certificate File**: Upload `certs/iqe-ra-cert.pem`
3. Also provide your EST server URLs:
   - CA Certs: `https://10.42.56.101:8445/.well-known/est/cacerts`
   - Enrollment: `https://10.42.56.101:8445/.well-known/est/simpleenroll`
   - (Note: With RA cert, you use `/simpleenroll`, NOT `/bootstrap`)

## Same EST Endpoints (with one change)

Yes, you still hit the same EST endpoints, with ONE important difference:

| Endpoint | Password Auth | RA Certificate Auth |
|----------|--------------|---------------------|
| `/cacerts` | Yes | Yes |
| `/bootstrap` | **YES** (for initial enrollment) | **NO** (skip this) |
| `/simpleenroll` | NO (requires existing cert) | **YES** (uses RA cert) |

**Why the difference?**
- `/bootstrap` is for password-based initial enrollment (what you were using before)
- `/simpleenroll` is for certificate-based enrollment (what RA cert uses)
- With RA cert, IQE already HAS a certificate, so it goes straight to `/simpleenroll`

## Authentication Flow Comparison

### Password Approach (Current):
```
1. IQE --> GET /cacerts --> EST Server (download CA cert)
2. IQE --> POST /bootstrap + Basic Auth (user:pass) + CSR --> EST Server
3. EST Server validates password, issues cert
```

### RA Certificate Approach (New):
```
1. IQE --> GET /cacerts --> EST Server (download CA cert)
2. IQE --> POST /simpleenroll + Client Cert (RA cert) + CSR --> EST Server
3. EST Server validates RA cert signature, issues cert
```

## Why This Might Fix Your 500 Errors

The current 500 errors might be happening because:
1. Base64 CSR decoding issues (we fixed this)
2. SRP authentication problems
3. Bootstrap flow expectations mismatch

RA certificate authentication:
- Bypasses SRP/password authentication entirely
- Uses standard TLS client certificate validation
- Simpler authentication flow
- More aligned with EST gateway best practices

## Server-Side Configuration

Your EST server is already configured to handle client certificate authentication! Check `config.yaml`:

```yaml
authentication:
  srp:
    enabled: true
    user_db: certs/srp_users.db

  client_certificate:
    enabled: true
    require_cert: false  # Optional client cert
    verify_cn: true
    allowed_subjects: []  # Empty = allow any cert signed by CA
```

The `client_certificate` section is already enabled, so your server will automatically:
1. Accept the RA certificate during TLS handshake
2. Validate it's signed by your CA
3. Allow access to `/simpleenroll` endpoint

## Testing RA Certificate Authentication

From the IQE server (via PuTTY), you can test this manually:

```bash
# Generate a test CSR
openssl req -new -sha256 -newkey rsa:2048 -nodes \
  -keyout test-pump-key.pem -out test-csr.pem \
  -subj "/C=US/ST=CA/L=Hospital/O=Medical/CN=pump-12345"

# Convert CSR to DER
openssl req -in test-csr.pem -outform DER -out test-csr.der

# Enroll using RA certificate (client cert auth)
curl -vk \
  --cert /path/to/iqe-ra-cert.pem \
  --key /path/to/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @test-csr.der \
  https://10.42.56.101:8445/.well-known/est/simpleenroll \
  -o pump-cert.p7
```

## CRITICAL: CA Trust Store Issue

From your IQE team's response:
- Question: "Do you import the EST server's CA cert into your trust store?"
- Answer: **"No"**

**This is a problem!** IQE needs to trust your EST server's TLS certificate.

### Two options:

#### Option 1: IQE imports your CA cert (RECOMMENDED)
You need to give IQE team:
- File: `certs/ca-cert.pem`
- Action: Import into IQE's trust store
- Why: So IQE can validate your EST server's TLS certificate

#### Option 2: Get public CA-signed cert for EST server
- Buy/get a certificate from a public CA (Let's Encrypt, DigiCert, etc.)
- Replace `certs/server.crt` with the public CA cert
- IQE would already trust it (public CAs are in default trust stores)
- **Downside**: Costs money, more complex setup

**I strongly recommend Option 1** - just give them `certs/ca-cert.pem` to import.

## Questions for IQE Team

Before proceeding, confirm with IQE team:

1. **CA Trust Store**:
   - Can you import our CA certificate (`certs/ca-cert.pem`) into your trust store?
   - OR do we need to get a public CA-signed certificate for the EST server?

2. **RA Certificate Upload**:
   - Does the UI accept PEM format for RA key/cert files?
   - Any specific file naming requirements?

3. **Endpoint Configuration**:
   - When using RA certificate, do we configure only `/simpleenroll` (not `/bootstrap`)?
   - Or does the UI still need both endpoints configured?

4. **Error Logs**:
   - Can you share the exact error from IQE logs when the 500 error occurs?
   - Any TLS handshake errors or certificate validation errors?

## Next Steps

1. **Share CA certificate with IQE team**:
   ```
   File to send: certs/ca-cert.pem
   Purpose: Import into IQE trust store for TLS validation
   ```

2. **Upload RA certificate to IQE UI**:
   - RA Key: `certs/iqe-ra-key.pem`
   - RA Cert: `certs/iqe-ra-cert.pem`

3. **Configure EST endpoints in IQE UI**:
   - CA Certs: `https://10.42.56.101:8445/.well-known/est/cacerts`
   - Enrollment: `https://10.42.56.101:8445/.well-known/est/simpleenroll`

4. **Test enrollment** through IQE UI

5. **Check logs** on both sides if issues occur

## Files to Share with IQE Team

Create a secure package with:
```
1. certs/ca-cert.pem        (for their trust store)
2. certs/iqe-ra-key.pem     (for RA authentication - KEEP SECURE)
3. certs/iqe-ra-cert.pem    (for RA authentication)
```

**Security note**: The `iqe-ra-key.pem` is sensitive! Only send via secure channel.

## Benefits of RA Certificate Approach

1. **More secure**: No passwords transmitted, uses mutual TLS
2. **Proper EST gateway pattern**: RFC 7030 recommends this for gateways
3. **Easier debugging**: TLS errors are clearer than application-level auth errors
4. **Renewable**: When cert expires, just generate new one (no password rotation)
5. **Might bypass current issues**: Different code path, avoids bootstrap/SRP flow

## Summary

- **Yes, you still use the same EST endpoints** (except use `/simpleenroll` instead of `/bootstrap`)
- **Yes, this is better than password approach** (more secure, proper EST gateway pattern)
- **Main blocker**: IQE needs to import your `ca-cert.pem` into their trust store
- **Worth trying**: Might completely bypass the current 500 errors

Good luck! This approach has a good chance of resolving your issues.
