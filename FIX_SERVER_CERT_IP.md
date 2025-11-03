# Critical Issue: Server Certificate Missing IP Address

## Problem Found

Your server certificate has:
```
X509v3 Subject Alternative Name:
    DNS:localhost, DNS:127.0.0.1
```

**Missing**: `IP Address:10.42.56.101`

## Why This Matters

When IQE connects to `https://10.42.56.101:8445`:

1. IQE initiates TLS handshake
2. Your server presents certificate with SAN: `DNS:localhost, DNS:127.0.0.1`
3. IQE checks: "Does cert have `10.42.56.101`?" → **NO**
4. IQE rejects connection: "Certificate doesn't match hostname"
5. **Connection fails before HTTP even starts!**

This is why you get 500 errors even though `/cacerts` works (you probably tested with `curl -k` which skips verification).

## How Cisco libest Solved This

From the email:
```
Add at the end of ext.conf (in alt_names section):
IP.3 = <IP OF THE SERVER>
```

They added the IP address to the certificate SAN field. **You need to do the same!**

## Two Solutions

### Solution 1: Regenerate Server Certificate (RECOMMENDED)

Fix your server cert to include the IP address.

```bash
# Run this to generate new server cert with IP
python fix_server_cert.py
```

I'll create this script for you.

### Solution 2: IQE Disables Cert Verification (TEMPORARY)

If IQE UI has an option like:
- ☐ Skip certificate verification
- ☐ Allow self-signed certificates
- ☐ Insecure mode

**Enable it temporarily for testing.**

But Solution 1 is better - proper certificates!

## Testing Current Certificate

```bash
# Test with curl (will fail without -k)
curl --cacert certs/ca-cert.pem https://10.42.56.101:8445/.well-known/est/cacerts
# Error: "Certificate doesn't match hostname"

# Test with -k (skip verification, will work)
curl -k https://10.42.56.101:8445/.well-known/est/cacerts
# Works! But insecure.
```

**IQE UI probably doesn't have `-k` option, so it fails!**

## The Fix

I'll create a script to regenerate your server certificate with:
- Common Name: python-est-server
- SAN DNS: localhost
- SAN DNS: 10.42.56.101 (for older clients)
- **SAN IP: 10.42.56.101** ← Critical!
- SAN IP: 127.0.0.1

This will make the certificate valid for:
- https://localhost:8445
- https://10.42.56.101:8445 ← IQE uses this!
- https://127.0.0.1:8445

Then IQE will accept the certificate!

## Why Your `/cacerts` Worked But Enrollment Fails

You probably tested `/cacerts` with:
```bash
curl -k https://10.42.56.101:8445/.well-known/est/cacerts
```

The `-k` flag skips certificate verification!

IQE UI doesn't use `-k`, so it properly validates the certificate and rejects it because the IP doesn't match.

## Summary

**Root Cause**: Server cert missing `IP Address:10.42.56.101` in SAN

**Effect**: TLS handshake fails, IQE can't connect

**Fix**: Regenerate server cert with correct IP

**Alternative**: IQE disables cert verification (if option exists)

Let me create the fix script now...
