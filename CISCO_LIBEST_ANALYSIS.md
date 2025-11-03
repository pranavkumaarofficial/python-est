# Cisco libest vs Our Implementation - Analysis

## Key Insight from the Email

```
"While we have one we use for IQE testing (10.6.152.122),
it is not IT-supported, and it is running on a desktop under my desk.
It may be a good idea to set up another server or two for your testing."
```

**They have a working EST server at 10.6.152.122 that IQE successfully connects to!**

## Critical Difference: CA Trust Store

### Their Setup (Working):
```
IQE Server -----> EST Server (10.6.152.122)
                  ↑
                  Same internal network
                  Desktop under someone's desk
                  Likely using self-signed certs
```

**Question**: How does their IQE trust the libest server's self-signed cert?

### Two Possibilities:

#### Possibility 1: IQE Already Has Their CA Cert
- The libest server's CA cert was already imported into IQE trust store
- That's why it works for them
- **You need to do the same!**

#### Possibility 2: IQE is Configured to Skip Cert Verification (INSECURE)
- IQE might be running with `-k` or `--insecure` flag
- Common in test environments
- **Check if IQE has a "skip cert verification" option in the UI!**

## Check IQE UI for Insecure Mode

Look in the IQE UI for settings like:
- ☐ Skip certificate verification
- ☐ Allow self-signed certificates
- ☐ Insecure mode
- ☐ Disable TLS verification
- ☐ Trust all certificates

**If this option exists, enable it temporarily for testing!**

## Cisco libest Configuration Review

From the email:

### 1. Default User/Pass
```
Default user pass estuser:estpwd
```
Your equivalent: `iqe-gateway:iqe-secure-password-2024` ✓

### 2. IP Address in Certificate
```
Add at the end of ext.conf (in alt_names section):
IP.3 = <IP OF THE SERVER>
```

**⚠️ THIS MIGHT BE THE ISSUE!**

Your server certificate might not have the IP address as a Subject Alternative Name (SAN)!

Let me check your server cert...

### 3. TLS Auth Without Password
```
Edit example/server/runserver.sh
Add -o option while running ./estserver
Sets flag disable_forced_http_auth
"Disabling HTTP authentication when TLS client auth succeeds"
Without this option, TLS authentication succeeds, but it will still expect user name and password
```

This is for RA certificate mode - your server already supports this ✓

## What to Check on Your Server Certificate

The libest email mentions adding the **IP address** to the certificate SAN field.

IQE might be connecting via IP (10.42.56.101) but your cert might only have:
- CN=localhost
- DNS:localhost

**If cert doesn't have SAN IP, TLS handshake will fail!**

## Immediate Actions You Can Take

### 1. Check IQE UI for "Skip Cert Verification" Option
Look through all IQE UI settings for an option to skip/disable certificate verification.

### 2. Check Your Server Certificate SAN
```bash
openssl x509 -in certs/server.crt -text -noout | grep -A5 "Subject Alternative Name"
```

Should show:
```
X509v3 Subject Alternative Name:
    DNS:localhost
    DNS:example.com
    IP Address:10.42.56.101  ← THIS IS CRITICAL!
```

### 3. Ask IQE Team How They Trust libest Server
Email them:
> "I see you have a working libest EST server at 10.6.152.122. How does the IQE gateway trust that server's certificate? Did you:
> a) Import the libest CA cert into IQE's trust store?
> b) Enable a 'skip certificate verification' option in IQE?
> c) Use a publicly-signed certificate?
>
> I need to replicate the same setup for our server at 10.42.56.101."

## CA Trust Store - Can You Import It?

You said you have PuTTY access to the IQE server but can't change anything.

**Check if you have permissions to:**

```bash
# Check if you can write to trust store (Ubuntu/Debian)
ls -la /usr/local/share/ca-certificates/
# Can you create files here?

# Or check system-wide trust store
ls -la /etc/ssl/certs/
# Probably read-only for you

# Check if there's an application-specific trust store
find /opt -name "*.jks" 2>/dev/null  # Java KeyStore
find /opt -name "truststore*" 2>/dev/null
find /opt -name "*cacerts*" 2>/dev/null
```

**If you can't write to these locations, you need IQE team to import the cert.**

## Most Likely Scenario

Based on the email, the libest server is a **test setup**. The IQE team likely:

1. **Generated libest CA cert**
2. **Imported it into IQE trust store** (one-time setup)
3. **Configured IQE UI** with libest endpoints
4. **Everything works**

For your server:
1. ✓ Generated your CA cert
2. ❌ **Need to import YOUR CA cert into IQE trust store**
3. ✓ Configured IQE UI with your endpoints
4. ❌ Fails because IQE doesn't trust your CA

## The Real Question

**How was the libest CA cert imported into IQE?**

Options:
a) Someone with admin access did it
b) IQE UI has a "upload trusted CA" feature
c) IQE has "skip verification" enabled
d) Libest cert chains to a public CA (unlikely for test setup)

**Check the IQE UI for a "Trusted CA Certificates" upload field!**

## Summary

### Why Their Setup Works:
- Libest returns base64 (RFC 7030) ✓
- Libest CA cert is trusted by IQE somehow ✓
- Libest cert has IP in SAN field ✓

### Why Yours Doesn't (Yet):
- ~~Was returning DER~~ → FIXED (now returns base64) ✓
- Your CA cert not trusted by IQE ← **MAIN BLOCKER**
- Your cert might not have IP in SAN ← **CHECK THIS**

### Next Steps:
1. **Check IQE UI** for "skip cert verification" or "trusted CA upload"
2. **Check your server cert** has IP 10.42.56.101 in SAN
3. **Email IQE team** asking how libest CA cert was trusted
4. **If cert missing IP SAN**, regenerate server cert with IP

Let's check your server certificate right now!
