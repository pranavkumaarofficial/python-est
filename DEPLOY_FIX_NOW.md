# 🚨 URGENT: Deploy Base64 CSR Fix for IQE UI

## The Problem

**IQE UI enrollment failing with 500 errors** even though manual curl works.

**Root Cause**: IQE UI sends base64-encoded CSRs, your server expected raw DER.

---

## ✅ The Fix (Already Applied)

Modified `src/python_est/server.py` to automatically decode base64 CSRs when `Content-Transfer-Encoding: base64` header is present.

**Changes**:
- Added `import base64` at top
- Added base64 decoding in both `/bootstrap` and `/simpleenroll` endpoints
- Backward compatible (raw DER still works)

---

## 📋 Deploy Commands

### On Windows (Local Testing)

```bash
# Already done - code is ready
git status  # See modified files
```

### On Ubuntu VM (Production)

```bash
# 1. Commit and push from Windows
git add src/python_est/server.py
git add IQE_UI_FIX.md
git add test_base64_csr.py
git add DEPLOY_FIX_NOW.md

git commit -m "fix: Add base64 CSR decoding for IQE UI compatibility

- Support Content-Transfer-Encoding: base64 header
- Auto-decode base64 CSRs in bootstrap and simpleenroll
- Maintain backward compatibility with raw DER/PEM
- Fix IQE UI 500 errors (ASN.1 parse failures)

Tested: Base64 decoding works, raw DER still works"

git push origin deploy_v1

# 2. On Ubuntu VM - Pull and restart
git pull origin deploy_v1
sudo systemctl restart python-est
# OR
docker restart est-server-iqe

# 3. Check logs
tail -f /var/log/python-est/server.log
# OR
docker logs -f est-server-iqe
```

---

## 🧪 Test After Deploy

### Test 1: IQE UI Enrollment

**Go to IQE UI and try enrolling a pump.**

**Expected in logs**:
```
INFO: Decoded base64-encoded CSR (XXX bytes)
INFO: Tracked enrollment for device: <pump-name>
```

**Expected Result**: ✅ Enrollment succeeds (no 500 error)

### Test 2: Manual Base64 CSR (Simulates IQE)

**From Ubuntu VM or IQE server**:

```bash
# Use test files generated
curl -vk -u iqe-gateway:iqe-secure-password-2024 \
  -H 'Content-Type: application/pkcs10' \
  -H 'Content-Transfer-Encoding: base64' \
  --data @test_csr.b64 \
  https://10.42.56.101:8445/.well-known/est/simpleenroll \
  -o test_cert.p7

# Should succeed
file test_cert.p7  # Should show "data" (binary)
```

### Test 3: Raw DER Still Works

```bash
# Traditional EST (no base64)
curl -vk -u iqe-gateway:iqe-secure-password-2024 \
  -H 'Content-Type: application/pkcs10' \
  --data-binary @test_csr.der \
  https://10.42.56.101:8445/.well-known/est/simpleenroll \
  -o test_cert2.p7

# Should still work
```

---

## 🔍 Debugging

### If Still Getting 500 Error:

**Check server logs for**:

1. **"Decoded base64-encoded CSR"** → ✅ Good, fix is working
2. **"Failed to decode base64 CSR"** → ❌ Invalid base64 from IQE
3. **"error parsing asn1 value"** → ❌ CSR format issue even after decode

### If Seeing "error parsing asn1 value" After Decode:

**Possible cause**: IQE is sending base64-encoded PEM (not DER)

**Debug on IQE side**:
```bash
# Save what IQE sends (from IQE server)
cat > csr_from_ui.b64  # Paste the base64 CSR IQE sends

# Decode and check
base64 -d csr_from_ui.b64 > decoded.bin
file decoded.bin

# Should show: "Certificate Request"
# If shows: "ASCII text" → It's PEM, not DER (problem)

# Try parsing
openssl req -in decoded.bin -inform DER -text -noout
# Should show CSR details
```

---

## 📊 What Changed

### Before Fix:
```python
# In server.py
csr_data = await request.body()  # Raw bytes
# Directly parse as DER
```

**Problem**: If body is base64 text, parsing fails with ASN.1 error

### After Fix:
```python
# In server.py
csr_data = await request.body()

# Check if base64-encoded
if request.headers.get("Content-Transfer-Encoding") == "base64":
    csr_data = base64.b64decode(csr_data)  # Decode to DER

# Now parse as DER
```

**Solution**: Automatically decodes base64 if header present

---

## ✅ Expected Outcome

| Test Case | Before Fix | After Fix |
|-----------|------------|-----------|
| IQE UI enrollment | ❌ 500 Error | ✅ Works |
| Manual raw DER | ✅ Works | ✅ Still works |
| Manual base64 | ❌ Not supported | ✅ Now works |

---

## 🎯 Success Criteria

You'll know it's working when:

1. ✅ IQE UI enrollment completes without 500 error
2. ✅ Server logs show: "Decoded base64-encoded CSR"
3. ✅ Device appears in dashboard with correct CN
4. ✅ Manual curl with raw DER still works (backward compatible)

---

## 📞 If Issues Persist

### Share These Debug Details:

1. **Server logs** around the failed enrollment
2. **Output of**: `curl -I https://10.42.56.101:8445/.well-known/est/cacerts`
3. **Output of**: Base64 decode test from IQE side (shown above)
4. **IQE UI error message** (if any)

### Quick Questions:

**Q: Is the code deployed?**
```bash
# On Ubuntu VM
git log -1 --oneline
# Should show the commit message about base64 fix
```

**Q: Is server restarted?**
```bash
# Check when server started
ps aux | grep est_server
# OR
docker ps | grep est-server
```

**Q: Are headers being sent?**
```bash
# Check IQE's actual request
tcpdump -i any -A 'port 8445' | grep -A 20 'Content-Transfer'
```

---

## 📁 Files Changed

- `src/python_est/server.py` - Added base64 import and decoding logic
- `IQE_UI_FIX.md` - Detailed explanation
- `test_base64_csr.py` - Test script
- `DEPLOY_FIX_NOW.md` - This file

---

## 🚀 Quick Deploy Checklist

- [ ] Code committed locally
- [ ] Code pushed to `deploy_v1` branch
- [ ] Pulled on Ubuntu VM
- [ ] Server restarted
- [ ] Tested with IQE UI
- [ ] Verified in server logs
- [ ] Device appears in dashboard

---

**Priority**: 🔴 HIGH (Blocking IQE integration)

**Estimated Time**: 5 minutes (deploy + restart)

**Risk**: 🟢 LOW (backward compatible, only adds feature)

**Status**: ✅ Fix ready, needs deployment

---

**Next Action**:
1. Push code to GitHub
2. Deploy on Ubuntu VM
3. Test with IQE UI
4. Share results

---

**Date**: 2025-11-03
**Issue**: IQE UI 500 errors
**Fix**: Base64 CSR auto-decode
**Impact**: Unblocks IQE integration
