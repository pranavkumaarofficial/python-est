# IQE UI 500 Error Fix - Base64 CSR Support

## Problem

IQE UI was failing with **500 Internal Server Error** when trying to enroll certificates, even though manual curl tests worked fine.

### Root Cause

**IQE UI sends base64-encoded CSRs** with header:
```
Content-Transfer-Encoding: base64
```

But your EST server was expecting **raw binary DER or PEM** CSRs.

**Error in logs**:
```
WARNING: Could not extract device ID from enrollment CSR: error parsing asn1 value
ERROR: Certificate enrollment failed: error parsing asn1 value
```

This happened because the server tried to parse base64 text as raw DER binary, causing ASN.1 parse errors.

---

## Solution

Added **automatic base64 decoding** for incoming CSRs in both endpoints:
- `POST /.well-known/est/bootstrap`
- `POST /.well-known/est/simpleenroll`

### Code Changes

**File**: `src/python_est/server.py`

**Changes**:
1. Added `import base64` at top
2. Added base64 detection and decoding in both endpoints:

```python
# Check if CSR is base64-encoded (IQE UI compatibility)
content_transfer_encoding = request.headers.get("Content-Transfer-Encoding", "").lower()
if content_transfer_encoding == "base64":
    try:
        # Decode base64-encoded CSR
        csr_data = base64.b64decode(csr_data)
        logger.info(f"Decoded base64-encoded CSR ({len(csr_data)} bytes)")
    except Exception as e:
        logger.error(f"Failed to decode base64 CSR: {e}")
        raise HTTPException(status_code=400, detail="Invalid base64-encoded CSR")
```

This code:
- Checks for `Content-Transfer-Encoding: base64` header
- If present, decodes the base64 CSR to raw DER
- Logs the decoding for debugging
- Returns 400 error if base64 is invalid

---

## What This Fixes

### Before:
- ❌ IQE UI enrollment: **500 Error** (ASN.1 parse failure)
- ✅ Manual curl with raw DER: **Works**

### After:
- ✅ IQE UI enrollment: **Works** (base64 decoded automatically)
- ✅ Manual curl with raw DER: **Still works** (backward compatible)
- ✅ Manual curl with base64: **Now works** (new feature)

---

## Testing

### Test 1: IQE UI Should Now Work

The IQE UI enrollment should now succeed. Check the server logs for:
```
INFO: Decoded base64-encoded CSR (XXX bytes)
INFO: Tracked enrollment for device: <device-name>
```

### Test 2: Manual Base64 CSR (Simulates IQE UI)

```bash
# Generate CSR
openssl req -new -newkey rsa:2048 -nodes \
  -keyout test-key.pem -out test-csr.der -outform DER \
  -subj "/CN=test-pump-002/O=Hospital/C=US"

# Base64 encode it
base64 test-csr.der > test-csr.b64

# POST with base64 header (like IQE UI does)
curl -vk -u iqe-gateway:iqe-secure-password-2024 \
  -H "Content-Type: application/pkcs10" \
  -H "Content-Transfer-Encoding: base64" \
  --data @test-csr.b64 \
  https://10.42.56.101:8445/.well-known/est/simpleenroll \
  -o cert.p7

# Should succeed and return certificate
```

### Test 3: Raw DER Still Works (Backward Compatibility)

```bash
# Generate PEM CSR
openssl req -new -newkey rsa:2048 -nodes \
  -keyout test-key2.pem -out test-csr2.pem \
  -subj "/CN=test-pump-003/O=Hospital/C=US"

# POST without base64 header (traditional EST)
curl -vk -u iqe-gateway:iqe-secure-password-2024 \
  -H "Content-Type: application/pkcs10" \
  --data-binary @test-csr2.pem \
  https://10.42.56.101:8445/.well-known/est/simpleenroll \
  -o cert2.p7

# Should still work
```

---

## Response Format Remains Unchanged

**Important**: This fix only affects **incoming CSRs** (requests from IQE).

**Outgoing certificates** (responses to IQE) still follow your `response_format` config:
- `response_format: der` → Returns raw binary DER PKCS#7
- `response_format: base64` → Returns base64-encoded PKCS#7

Based on your logs, IQE seems to handle **binary DER responses** correctly, so keep:
```yaml
# config-iqe.yaml
response_format: der
```

---

## Why This Works

### IQE UI Flow:
1. User generates CSR in browser
2. IQE UI base64-encodes CSR
3. IQE UI POSTs with `Content-Transfer-Encoding: base64` header
4. **Your server now detects this header and decodes**
5. Server processes raw DER CSR normally
6. Returns certificate (in DER or base64, per config)

### Manual curl Flow (unchanged):
1. You generate raw DER/PEM CSR
2. You POST without base64 header
3. Server receives raw DER/PEM
4. **No decoding needed, processes directly**
5. Returns certificate

---

## Deployment

### Quick Deploy (Ubuntu VM):

```bash
# Pull latest code
git pull origin deploy_v1

# Restart server (if running as systemd service)
sudo systemctl restart python-est

# Or restart Docker container
docker restart est-server-iqe

# Or kill and restart manually
pkill -f est_server.py
python3 est_server.py --config config-iqe.yaml
```

### Verify Fix in Logs:

```bash
# Watch logs
tail -f /var/log/python-est/server.log
# OR
docker logs -f est-server-iqe

# You should see for IQE UI enrollments:
# "INFO: Decoded base64-encoded CSR (XXX bytes)"
```

---

## If Still Getting 500 Error

### Check Server Logs For:

1. **"Decoded base64-encoded CSR"** → Good, base64 decoding worked
2. **"Failed to decode base64 CSR"** → Bad base64 data from IQE
3. **"error parsing asn1 value"** → CSR is still not valid DER (even after decoding)

### If "error parsing asn1 value" Persists:

The issue might be with **how IQE generates the CSR**. Ask IQE team:

**Q: "What format is the CSR before you base64-encode it?"**
- Should be: DER format (binary)
- Not: PEM format (text with -----BEGIN CERTIFICATE REQUEST-----)

If they're base64-encoding an already-PEM CSR, you'd get double-encoded data.

### Debug Command:

```bash
# On IQE side, before enrollment:
# Save the base64 CSR they're sending
cat csr.b64 | base64 -d > csr.decoded

# Check what it is
file csr.decoded
# Should show: "Certificate Request"

# Try to parse it
openssl req -in csr.decoded -inform DER -text -noout
# Should show CSR details
```

---

## Summary

✅ **Fixed**: Added automatic base64 decoding for CSRs with `Content-Transfer-Encoding: base64` header

✅ **Compatible**: Backward compatible with raw DER/PEM CSRs (manual curl still works)

✅ **Testing**: Test with IQE UI after deploying this fix

⚠️ **Monitor**: Check server logs for "Decoded base64-encoded CSR" messages

📊 **Impact**: Should fix IQE UI 500 errors while maintaining all existing functionality

---

## Next Steps

1. **Deploy fix** to Ubuntu VM
2. **Test with IQE UI** enrollment
3. **Check server logs** for base64 decode messages
4. **If still fails**: Check CSR format from IQE (might be double-encoded)
5. **Once working**: Commit and document

---

**Status**: ✅ Fix ready, needs deployment and testing

**Files Changed**: `src/python_est/server.py` (added base64 import and decoding logic)

**Risk**: Low (only adds new functionality, doesn't break existing)

**Testing Required**: IQE UI enrollment

---

**Date**: 2025-11-03
**Issue**: IQE UI 500 errors
**Root Cause**: Base64-encoded CSRs not decoded
**Fix**: Automatic base64 decoding when header present
