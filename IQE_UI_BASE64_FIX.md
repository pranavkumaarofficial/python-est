# IQE UI Base64 Response Fix

## Problem Identified

Your config had `response_format: der` (raw binary), but the **IQE UI expects base64-encoded responses**.

### Evidence from IQE UI Documentation:

```bash
# IQE UI receives base64 response:
curl ... -o client.p7.b64  # Note: .b64 extension

# Then IQE UI decodes it:
openssl base64 -in client.p7.b64 -out client.p7.der -d
```

The IQE UI curl examples clearly show:
1. Response is saved as `.p7.b64` (base64 format)
2. IQE then runs `openssl base64 ... -d` to decode it
3. This is **RFC 7030 standard** behavior

## Root Cause

The cisco libest server mentioned in the email returns base64-encoded responses by default (RFC 7030 compliant). Your server was configured for raw DER, which the IQE UI couldn't process.

## The Fix

Changed `config-iqe.yaml`:

```yaml
# BEFORE (WRONG):
response_format: der  # Raw binary - IQE UI can't handle this

# AFTER (CORRECT):
response_format: base64  # Base64-encoded - RFC 7030 standard
```

## Why This Matters

### IQE UI Flow:
```
1. IQE sends base64-encoded CSR
   Content-Transfer-Encoding: base64
   Body: MIICzjCCAboCAQAwgYYxCzAJBgNVBAYTAlVT...

2. Your server decodes CSR (already working ✓)

3. Your server issues certificate

4. Your server returns base64-encoded PKCS#7
   ← THIS WAS THE PROBLEM (was returning raw DER)

5. IQE UI receives base64 response
   Saves as client.p7.b64

6. IQE UI decodes: openssl base64 -d
   Gets client.p7.der

7. IQE UI extracts cert: openssl pkcs7 -print_certs
   Gets client.pem

8. IQE sends cert to medical pump ✓
```

With `response_format: der`, step 4 was returning raw binary DER, and the IQE UI failed at step 6 when trying to base64-decode it.

## Testing the Fix

Run the test script that matches IQE UI's exact curl commands:

```bash
python test_iqe_ui_format.py
```

This script:
1. Generates CSR (matching IQE: `openssl req -new ...`)
2. Base64-encodes CSR (matching IQE: `openssl base64 -e`)
3. Sends to `/simpleenroll` with `Content-Transfer-Encoding: base64`
4. Receives base64-encoded PKCS#7 response
5. Decodes it (matching IQE: `openssl base64 -d`)
6. Extracts certificate (matching IQE: `openssl pkcs7 -print_certs`)

If this passes, IQE UI will work!

## Why cisco libest Works

From the email, the team was using cisco's libest server (https://github.com/cisco/libest). That server:
- Returns base64-encoded responses by default (RFC 7030 compliant)
- Accepts both password auth and RA certificate auth
- Has been battle-tested with IQE UI

Your Python EST server now behaves the same way!

## Comparison: DER vs Base64 Response

| Response Format | Use Case | IQE UI Compatible? |
|----------------|----------|-------------------|
| `der` | Raw binary, non-standard | ❌ NO - UI expects base64 |
| `base64` | RFC 7030 standard | ✅ YES - exactly what UI expects |

## Files Changed

1. **config-iqe.yaml**
   - Changed: `response_format: der` → `response_format: base64`
   - Why: Match RFC 7030 standard and IQE UI expectations

## Deployment Steps

```bash
# 1. Commit the fix
git add config-iqe.yaml test_iqe_ui_format.py IQE_UI_BASE64_FIX.md
git commit -m "fix: Change response format to base64 for IQE UI compatibility

- IQE UI expects base64-encoded PKCS#7 responses (RFC 7030)
- Was returning raw DER which IQE UI couldn't decode
- Add test script matching IQE UI curl examples
- Matches behavior of cisco libest server"

# 2. Push to deploy_v1
git push origin deploy_v1

# 3. On Ubuntu VM
cd /path/to/python-est
git pull origin deploy_v1

# 4. Update config symlink (if needed)
ln -sf config-iqe.yaml config.yaml

# 5. Restart Docker
docker-compose down
docker-compose up -d

# 6. Verify
docker-compose logs -f
# Should show: "Loaded configuration from config.yaml"
# Should show: "response_format: base64"
```

## What IQE Team Needs to Do

### Still Required:
1. **Import CA certificate** into IQE trust store
   - File: `certs/ca-cert.pem`
   - Without this, HTTPS connection will fail
   - This is **still the critical blocker**

### IQE UI Configuration:

**Option 1: Username/Password Auth**
```
Username: iqe-gateway
Password: iqe-secure-password-2024
CA Certs URL: https://10.42.56.101:8445/.well-known/est/cacerts
Enrollment URL: https://10.42.56.101:8445/.well-known/est/simpleenroll
```

**Option 2: RA Certificate Auth** (More secure)
```
RA Key File: iqe-ra-key.pem
RA Cert File: iqe-ra-cert.pem
CA Certs URL: https://10.42.56.101:8445/.well-known/est/cacerts
Enrollment URL: https://10.42.56.101:8445/.well-known/est/simpleenroll
```

Note: Both use `/simpleenroll` endpoint (NOT `/bootstrap`)

## Expected Outcome

After deploying this fix and IQE importing your CA cert:

✅ IQE UI enrollment should succeed
✅ Medical pumps receive valid certificates
✅ No more 500 errors
✅ Certificates work for EAP-TLS authentication

## If Still Failing

Check these in order:

1. **CA Trust Store** (most likely issue)
   ```bash
   # Test from IQE server:
   curl -v https://10.42.56.101:8445/.well-known/est/cacerts
   # Should NOT show "certificate verify failed"
   ```

2. **Config Applied**
   ```bash
   # On your VM:
   grep response_format config.yaml
   # Should show: response_format: base64
   ```

3. **Server Logs**
   ```bash
   # Check what format server is returning:
   docker-compose logs | grep "response_format"
   docker-compose logs | grep "base64"
   ```

4. **Test with curl** (same as IQE UI does)
   ```bash
   # From IQE server, run test_iqe_ui_format.py equivalents
   # See "Testing Request" section in QUESTIONS_FOR_IQE_TEAM.md
   ```

## Summary

**Problem**: Server returned raw DER, IQE UI expected base64

**Solution**: Change config to `response_format: base64`

**Result**: Server now matches RFC 7030 standard and IQE UI expectations

**Remaining**: IQE must import CA cert into trust store (critical!)

This fix aligns your server with the cisco libest server behavior that IQE has been testing with. Should resolve the 500 errors!
