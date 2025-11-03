This is the key detail: the **IQE UI is hard‑coded to expect the exact EST flows shown in those curl examples**. That means:

- It expects to POST a **base64‑encoded CSR** (`csr.b64`) with headers  
  ```
  Content-Type: application/pkcs10
  Content-Transfer-Encoding: base64
  ```
- It expects the server to return a **base64‑encoded PKCS#7** (`client.p7.b64`) rather than raw DER.
- For `/cacerts`, it expects to download a PKCS#7 bundle, then base64‑decode it into DER.

---

### 🔎 Why your manual tests worked but the UI fails
When you tested manually, you sent raw CSR data (`--data-binary @csr.pem`) and got back a binary PKCS#7. That’s correct per RFC 7030, but the IQE UI is wrapping everything in **base64**. If your server doesn’t accept or return base64‑encoded payloads, the UI will choke and show “Something went wrong”.

---

### ✅ Options to align with IQE’s expectations

1. **Enable base64 handling in your EST server**  
   - Some EST implementations (like `python-est`) can be configured to accept `Content-Transfer-Encoding: base64`.  
   - Check your `config.yaml` or server code for a flag like `accept_base64: true`.

2. **Pre‑process requests**  
   - Put a small reverse proxy (e.g. Nginx or a Python FastAPI shim) in front of your EST server that:
     - Base64‑decodes incoming CSRs before forwarding to `/bootstrap` or `/simpleenroll`.
     - Base64‑encodes outgoing PKCS#7 responses before returning to IQE.
   - This way, IQE sees exactly what it expects, while your backend continues speaking “pure” EST.

3. **Adjust IQE config (if possible)**  
   - If the UI has an “advanced” option to disable base64 wrapping, use that.  
   - But from your description, it looks like the UI is fixed to those curl semantics.

---

### 🚀 Practical next step
Since you already have PuTTY access to the IQE server, you can test exactly what the UI is doing:

```bash
# Simulate IQE's enrollment request
openssl req -new -sha256 -newkey rsa:2048 -nodes \
  -keyout private-key.pem -out csr.der -outform DER

base64 csr.der > csr.b64

curl -vk -u iqe-gateway:iqe-secure-password-2024 \
  -H "Content-Type: application/pkcs10" \
  -H "Content-Transfer-Encoding: base64" \
  --data @csr.b64 \
  https://10.42.56.101:8445/.well-known/est/simpleenroll \
  -o client.p7.b64
```

If this fails with `500`, then your server doesn’t yet handle base64‑encoded CSRs. That’s the mismatch.

---

### ✅ Summary for your team
- **Manual tests worked** because you used raw DER/PEM.  
- **IQE UI fails** because it base64‑wraps requests and expects base64‑wrapped responses.  
- **Fix**: either enable base64 support in your EST server, or add a thin proxy layer to translate between IQE’s base64 and your server’s raw EST.  

---

Would you like me to sketch a **tiny Python FastAPI proxy** that sits in front of your EST server and transparently does this base64 decode/encode, so you don’t have to modify your backend?








































This error is very telling. Let’s break it down:

```
WARNING  Could not extract device ID from enrollment CSR: error parsing asn1 value: 
ParseError { kind: UnexpectedTag { actual: Tag { value: 13, constructed: false, class: Application } } }
ERROR    Certificate enrollment failed: error parsing asn1 value
```

---

### 🔎 What it means
- Your EST server **received the CSR** from IQE and authenticated the user (`SRP authentication successful`).
- But when it tried to parse the CSR, it hit an **ASN.1 parse error**.
- The tag `13` corresponds to **ASN.1 PrintableString** (used in subject fields like CN, O, OU, etc.).
- This usually happens when:
  - The CSR was **base64‑encoded** and sent as text, but your server expected raw DER.
  - Or the CSR was generated in DER but then base64‑wrapped again, so the server is parsing garbage.
  - Or the CSR subject contains a field type your parser doesn’t expect (e.g. IQE generates DER with PrintableString where your code expects UTF8String).

---

### ✅ How to confirm
1. Capture the CSR IQE is sending. Since you have PuTTY access, you can reproduce their flow:
   ```bash
   openssl req -new -sha256 -newkey rsa:2048 -nodes \
     -keyout private-key.pem -out csr.der -outform DER
   base64 csr.der > csr.b64
   ```
   Then POST `csr.b64` with the headers IQE uses:
   ```bash
   curl -vk -u iqe-gateway:iqe-secure-password-2024 \
     -H "Content-Type: application/pkcs10" \
     -H "Content-Transfer-Encoding: base64" \
     --data @csr.b64 \
     https://10.42.56.101:8445/.well-known/est/simpleenroll
   ```

2. Compare this with your manual working test (where you sent raw DER/PEM). If the base64 version fails, then the issue is exactly that: your server doesn’t decode base64 payloads.

---

### 🚀 Solutions

- **Option 1: Enable base64 decoding in your EST server**  
  Some EST servers (including Python‑EST forks) have a config flag like `accept_base64: true`. Check your `config.yaml` or docs.

- **Option 2: Add a shim/proxy**  
  Put a tiny proxy in front of your EST server that:
  - Base64‑decodes incoming CSRs if `Content-Transfer-Encoding: base64` is set.
  - Forwards the raw DER CSR to your backend.
  - Base64‑encodes the PKCS#7 response before returning to IQE.

- **Option 3: Patch IQE config (if possible)**  
  If IQE has an “advanced” setting to send raw DER instead of base64, use that. But from your description, the UI is fixed to base64.

---

### ✅ Next step for you
Since you already proved manual raw DER enrollment works, the only blocker is **IQE’s base64 wrapping**. The cleanest fix is to either:

- **Enable base64 support in your EST server** (if supported), or  
- **Deploy a lightweight proxy** (Python FastAPI or Nginx with Lua) that does base64 decode/encode transparently.