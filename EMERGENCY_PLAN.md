# Emergency Plan for Demo Tomorrow

If libest is being a pain and you're running out of time...

## Plan A: Use Teammate's Server (INSTANT)

From the email:
> "While we have one we use for IQE testing (10.6.152.122)"

**Ask your teammate**:
> "Can I use your libest server (10.6.152.122) for tomorrow's demo? Just to show the IQE team the integration working. I'm setting up my own server in parallel."

**Pros**:
- ✅ Works immediately (0 minutes)
- ✅ Already proven with IQE
- ✅ Demo succeeds
- ✅ You still show your Python EST as "enhanced version in development"

**Demo Flow**:
1. Show working integration with teammate's server
2. Show your Python EST server (port 8445)
3. Explain: "Working integration proven, now building enhanced version"

**For LOR**: Still counts! You showed understanding of EST, IQE integration, and engineering judgment.

---

## Plan B: Fix Your Python EST (CA Trust Issue)

The REAL blocker is probably just the CA trust store issue.

**Quick test to confirm**:

### On IQE Server (via PuTTY):

```bash
# Test WITHOUT cert verification
curl -k -u iqe-gateway:iqe-secure-password-2024 \
  -H "Content-Type: application/pkcs10" \
  -H "Content-Transfer-Encoding: base64" \
  --data @csr.b64 \
  https://10.42.56.101:8445/.well-known/est/simpleenroll \
  -o client.p7.b64
```

**If this works** (`-k` skips cert verification), then your Python EST is FINE!

The issue is just:
1. IQE UI doesn't have your CA cert trusted
2. IQE UI has no "skip verification" option

**Solution**: Get IQE team to import your CA cert OR find the skip verification option!

---

## Plan C: Check IQE UI for Skip Verification

**Look carefully in the IQE UI** for:
- ☐ "Allow self-signed certificates"
- ☐ "Skip certificate verification"
- ☐ "Disable TLS verification"
- ☐ "Insecure mode"
- ☐ "Trust all certificates"
- ☐ Advanced settings / Developer options

**This single checkbox might solve everything!**

Your Python EST server likely works fine - IQE just doesn't trust the cert.

---

## Plan D: Contact IQE Team NOW

Email/Slack them NOW (not tomorrow morning):

> **Subject**: Quick CA Cert Import for Demo Tomorrow
>
> Hi team,
>
> I'm setting up an EST server for tomorrow's demo. The server is running at https://10.42.56.101:8445
>
> **I need your help importing the CA certificate** into IQE's trust store so it can connect via HTTPS.
>
> **CA Certificate attached**: ca-cert.pem
>
> **Alternative**: If IQE has a "skip certificate verification" or "allow self-signed certificates" option in the UI, that would also work for the demo.
>
> Can someone help with this tonight? The server is ready, just needs the trust configuration.
>
> Thanks!

**Include**: `certs/ca-cert.pem` from your Windows machine

---

## Plan E: Test Hypothesis Right Now

**Hypothesis**: Your Python EST works fine, it's just the CA trust issue.

**Test on IQE server** (via PuTTY):

```bash
# 1. Generate test CSR
openssl req -new -newkey rsa:2048 -nodes \
  -keyout test-key.pem -out csr.der -outform DER \
  -subj "/CN=emergency-test"

# 2. Base64 encode
openssl base64 -in csr.der -out csr.b64

# 3. Test with -k (skip verification)
curl -vk -u iqe-gateway:iqe-secure-password-2024 \
  -H "Content-Type: application/pkcs10" \
  -H "Content-Transfer-Encoding: base64" \
  --data @csr.b64 \
  https://10.42.56.101:8445/.well-known/est/simpleenroll \
  -o client.p7.b64

# 4. Check response
file client.p7.b64
# Should say: ASCII text (base64)

# 5. Decode and verify
openssl base64 -in client.p7.b64 -out client.p7.der -d
openssl pkcs7 -inform DER -in client.p7.der -print_certs -out client.pem
cat client.pem
```

**If this works**, YOUR SERVER IS FINE! Just need CA trust!

---

## Plan F: Docker libest (Current Plan)

Use the Docker approach I just created:
- `Dockerfile.libest`
- `docker-compose.libest.yml`
- `DOCKER_LIBEST_DEPLOY.md`

Docker isolates all the libest build issues.

---

## Decision Matrix

| Plan | Time | Success Probability | Notes |
|------|------|---------------------|-------|
| **A: Teammate's server** | 0 min | 99% | Instant success |
| **B: Fix Python EST (CA trust)** | 10 min | 95% | If curl -k works |
| **C: Find skip verification** | 5 min | 70% | If option exists |
| **D: IQE team imports CA** | Overnight | 90% | Need their help |
| **E: Test hypothesis** | 10 min | N/A | Proves what's wrong |
| **F: Docker libest** | 20 min | 85% | Current approach |

---

## My Recommendation RIGHT NOW

**Do these in order:**

### Step 1 (10 min): Test Plan E
Confirm your Python EST works with `-k` flag on IQE server.

**If it works** → Problem is ONLY CA trust → Do Plan D (email IQE team now!)

**If it fails** → Move to Step 2

### Step 2 (5 min): Do Plan C
Search IQE UI thoroughly for "skip verification" option.

**If found** → Enable it → Demo ready with Python EST!

**If not found** → Move to Step 3

### Step 3 (Now): Do Plan D
Email IQE team asking to import CA cert **tonight**.

### Step 4 (Parallel): Do Plan F
While waiting for IQE team response, try Docker libest approach.

### Step 5 (Morning): Do Plan A
If nothing else worked by morning, use teammate's server for demo.

---

## Bottom Line

You have **multiple backup plans**. Don't panic!

**Most likely scenario**: Your Python EST works fine, just needs CA trust. Test with `-k` flag to confirm.

**Worst case**: Use teammate's server, demo still succeeds, you still get your LOR.

**Best case**: Python EST works, you're the hero. 🎯

---

## What to Do RIGHT NOW (Next 30 min)

```bash
# 1. Test Python EST with -k flag (10 min)
#    SSH to IQE server and run curl test

# 2. Email IQE team with CA cert (5 min)
#    Attach: certs/ca-cert.pem
#    Ask: Import into trust store OR enable skip verification

# 3. Commit Docker libest files (2 min)
git add Dockerfile.libest docker-compose.libest.yml DOCKER_LIBEST_DEPLOY.md EMERGENCY_PLAN.md
git commit -m "feat: Docker libest + emergency plans for demo"
git push origin cisco-libest

# 4. Start Docker build on VM (10 min, hands-off)
#    While it builds, you can sleep

# 5. Sleep! 😴
```

**Tomorrow morning**: One of these will work!

Good luck! 🍀
