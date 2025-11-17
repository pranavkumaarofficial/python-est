# Authentication Flow - Complete End-to-End

## Overview

Two completely separate authentication flows:
1. **IQE → EST Server**: RA certificate authentication (certificate issuance)
2. **Pump → RADIUS Server**: EAP-TLS authentication (WiFi access)

---

## Flow 1: Certificate Issuance (IQE → EST)

### What's Being Compared?

**EST Server validates IQE's RA certificate:**

```
IQE sends:
- Client Certificate: iqe-ra-cert.pem
- Private Key: iqe-ra-key.pem (proves IQE owns the cert)

EST Server checks (via Nginx):
1. Certificate signed by EST CA? ✓
2. Certificate not expired? ✓
3. Certificate subject DN contains "IQE-RA-Gateway"? ✓
4. TLS handshake successful? ✓

If all pass → IQE authenticated → EST issues pump certificate
```

### Step-by-Step Flow

```
┌─────────────┐                    ┌──────────────┐                ┌─────────────┐
│ IQE Gateway │                    │ Nginx (8445) │                │ EST Server  │
└──────┬──────┘                    └──────┬───────┘                └──────┬──────┘
       │                                  │                               │
       │ 1. HTTPS POST /simpleenroll      │                               │
       │    + Client Cert (iqe-ra-cert)   │                               │
       ├─────────────────────────────────▶│                               │
       │                                  │                               │
       │                                  │ 2. Verify client cert:        │
       │                                  │    - Check signature (CA)     │
       │                                  │    - Check expiration         │
       │                                  │    - Extract Subject DN       │
       │                                  │                               │
       │                                  │ 3. Forward to backend:        │
       │                                  │    X-SSL-Client-Verify: SUCCESS
       │                                  │    X-SSL-Client-S-DN: CN=IQE-RA-Gateway
       │                                  ├──────────────────────────────▶│
       │                                  │                               │
       │                                  │                               │ 4. Verify RA auth:
       │                                  │                               │    - Check header
       │                                  │                               │    - Trust nginx
       │                                  │                               │
       │                                  │                               │ 5. Process CSR:
       │                                  │                               │    - Validate PKCS#10
       │                                  │                               │    - Sign with CA key
       │                                  │                               │    - Create PKCS#7
       │                                  │                               │
       │                                  │ 6. PKCS#7 response            │
       │                                  │◀──────────────────────────────┤
       │                                  │                               │
       │ 7. HTTP 200 + PKCS#7 cert        │                               │
       │◀─────────────────────────────────┤                               │
       │                                  │                               │
       │ 8. Extract pump certificate      │                               │
       │    from PKCS#7                   │                               │
       │                                  │                               │
```

### What IQE Receives

**Response:** base64-encoded PKCS#7 (SignedData structure)

**Contains:**
- Pump certificate (signed by EST CA)
- EST CA certificate (chain)

**IQE extracts:**
```bash
# IQE decodes PKCS#7 to get pump certificate
openssl pkcs7 -print_certs -in response.p7 -out pump-cert.pem
```

---

## Flow 2: WiFi Authentication (Pump → RADIUS)

### What's Being Compared?

**RADIUS validates pump's certificate using cryptographic verification:**

```
Pump sends:
- Client Certificate: pump-cert.pem (issued by EST)
- Private Key: pump-key.pem (proves pump owns the cert)

RADIUS checks:
1. Certificate signed by trusted CA? ✓ (checks against ca-cert.pem)
2. Certificate not expired? ✓
3. Certificate issuer DN matches expected? ✓
4. Certificate CN matches User-Name? ✓ (optional)
5. Pump can prove it owns the private key? ✓ (TLS handshake)

If all pass → Pump authenticated → Access-Accept → WiFi connected
```

### Authentication Method: EAP-TLS (802.1X)

**EAP-TLS = Extensible Authentication Protocol - Transport Layer Security**

**Key principle:** Mutual certificate authentication
- Pump proves identity with certificate (signed by EST CA)
- RADIUS proves identity with certificate (self-signed)
- Both verify each other's certificates
- TLS handshake proves possession of private keys

### Step-by-Step Flow

```
┌─────────────┐          ┌──────────────┐          ┌─────────────┐          ┌─────────────┐
│ Medical Pump│          │  Cisco WLC   │          │ FreeRADIUS  │          │  EST CA     │
└──────┬──────┘          └──────┬───────┘          └──────┬──────┘          └──────┬──────┘
       │                        │                         │                        │
       │ 1. Probe Request       │                         │                        │
       │    SSID: Ferrari2      │                         │                        │
       ├───────────────────────▶│                         │                        │
       │                        │                         │                        │
       │ 2. Probe Response      │                         │                        │
       │◀───────────────────────┤                         │                        │
       │                        │                         │                        │
       │ 3. Association Request │                         │                        │
       ├───────────────────────▶│                         │                        │
       │                        │                         │                        │
       │ 4. Association Response│                         │                        │
       │    (pending 802.1X)    │                         │                        │
       │◀───────────────────────┤                         │                        │
       │                        │                         │                        │
       │ 5. EAP-Request Identity│                         │                        │
       │◀───────────────────────┤                         │                        │
       │                        │                         │                        │
       │ 6. EAP-Response Identity                         │                        │
       │    Identity: NPPBBB4   │                         │                        │
       ├───────────────────────▶│                         │                        │
       │                        │                         │                        │
       │                        │ 7. RADIUS Access-Request                         │
       │                        │    User-Name: NPPBBB4   │                        │
       │                        │    EAP-Message: Identity │                        │
       │                        ├─────────────────────────▶│                        │
       │                        │                         │                        │
       │                        │ 8. RADIUS Access-Challenge                       │
       │                        │    EAP-Message: Start TLS                        │
       │                        │◀─────────────────────────┤                        │
       │                        │                         │                        │
       │ 9. EAP-Request TLS Start                         │                        │
       │◀───────────────────────┤                         │                        │
       │                        │                         │                        │
       │ 10. EAP-Response        │                         │                        │
       │     TLS Client Hello    │                         │                        │
       ├───────────────────────▶│                         │                        │
       │                        │                         │                        │
       │                        │ 11. RADIUS Access-Request                        │
       │                        │     EAP-Message: Client Hello                    │
       │                        ├─────────────────────────▶│                        │
       │                        │                         │                        │
       │                        │                         │ 12. TLS Server Hello   │
       │                        │                         │     + RADIUS cert      │
       │                        │                         │     + Request client cert
       │                        │                         │                        │
       │                        │ 13. RADIUS Access-Challenge                      │
       │                        │     EAP-Message: Server Hello                    │
       │                        │◀─────────────────────────┤                        │
       │                        │                         │                        │
       │ 14. EAP-Response        │                         │                        │
       │     TLS: Pump Certificate                        │                        │
       │     + Certificate Verify                         │                        │
       │     (signed with pump private key)               │                        │
       ├───────────────────────▶│                         │                        │
       │                        │                         │                        │
       │                        │ 15. RADIUS Access-Request                        │
       │                        │     EAP-Message: Client Cert                     │
       │                        ├─────────────────────────▶│                        │
       │                        │                         │                        │
       │                        │                         │ 16. Verify pump cert:  │
       │                        │                         │     a) Parse certificate
       │                        │                         │     b) Extract issuer  │
       │                        │                         │     c) Load CA cert    │
       │                        │                         │        (ca-cert.pem)   │
       │                        │                         │◀───────────────────────┤
       │                        │                         │                        │
       │                        │                         │ d) Verify signature:   │
       │                        │                         │    openssl verify      │
       │                        │                         │    -CAfile ca-cert.pem │
       │                        │                         │    pump-cert.pem       │
       │                        │                         │                        │
       │                        │                         │ e) Check issuer DN:    │
       │                        │                         │    Expected: /CN=Python-EST Root CA
       │                        │                         │    Actual: [from cert] │
       │                        │                         │    Match? ✓            │
       │                        │                         │                        │
       │                        │                         │ f) Check expiration:   │
       │                        │                         │    Not Before: [date]  │
       │                        │                         │    Not After: [date]   │
       │                        │                         │    Valid? ✓            │
       │                        │                         │                        │
       │                        │                         │ g) Check CN (optional):│
       │                        │                         │    Expected: NPPBBB4   │
       │                        │                         │    Actual: [from cert] │
       │                        │                         │    Match? ✓            │
       │                        │                         │                        │
       │                        │                         │ h) Verify TLS handshake:
       │                        │                         │    Pump must prove it  │
       │                        │                         │    owns private key    │
       │                        │                         │    via signed challenge│
       │                        │                         │    Valid? ✓            │
       │                        │                         │                        │
       │                        │                         │ 17. ALL CHECKS PASSED! │
       │                        │                         │     Authentication OK  │
       │                        │                         │                        │
       │                        │ 18. RADIUS Access-Accept                         │
       │                        │     (Pump authenticated)                         │
       │                        │◀─────────────────────────┤                        │
       │                        │                         │                        │
       │ 19. EAP-Success        │                         │                        │
       │◀───────────────────────┤                         │                        │
       │                        │                         │                        │
       │ 20. 4-way handshake    │                         │                        │
       │     (WPA2 key exchange)│                         │                        │
       │◀──────────────────────▶│                         │                        │
       │                        │                         │                        │
       │ 21. WiFi Connected!    │                         │                        │
       │    IP via DHCP         │                         │                        │
       │◀───────────────────────┤                         │                        │
       │                        │                         │                        │
```

---

## What RADIUS Actually Compares

### 1. Certificate Signature Validation

**RADIUS performs cryptographic verification:**

```c
// Pseudocode of what RADIUS does internally
pump_cert = parse_certificate(client_cert);
ca_cert = load_certificate("/etc/freeradius/certs/ca/ca-cert.pem");

// Extract signature from pump certificate
pump_signature = pump_cert.signature;
pump_tbs_data = pump_cert.tbs_certificate; // "To Be Signed" data

// Verify signature using CA's public key
ca_public_key = ca_cert.public_key;
is_valid = verify_signature(ca_public_key, pump_tbs_data, pump_signature);

if (!is_valid) {
    log("Certificate signature invalid - not signed by trusted CA");
    return ACCESS_REJECT;
}
```

**In practice, OpenSSL does this:**
```bash
openssl verify -CAfile /etc/freeradius/certs/ca/ca-cert.pem pump-cert.pem
# Output: pump-cert.pem: OK  (or error if invalid)
```

### 2. Issuer DN Check

**From [radius/eap:38](radius/eap:38):**
```
check_cert_issuer = "/C=US/ST=CA/L=Test/O=Test CA/CN=Python-EST Root CA"
```

**RADIUS compares:**
```
Expected Issuer DN: /C=US/ST=CA/L=Test/O=Test CA/CN=Python-EST Root CA
Actual Issuer DN:   [extracted from pump certificate]

Match? → Continue
No match? → ACCESS_REJECT
```

### 3. Common Name (CN) Check (Optional)

**From [radius/eap:39](radius/eap:39):**
```
check_cert_cn = %{User-Name}
```

**RADIUS compares:**
```
Expected CN: NPPBBB4 (from EAP-Identity response)
Actual CN:   [extracted from pump certificate Subject DN]

Match? → Continue
No match? → ACCESS_REJECT
```

### 4. Expiration Check

```
Current time: 2024-11-11 16:30:00
Certificate Not Before: 2024-11-01 00:00:00 ✓
Certificate Not After:  2025-11-01 00:00:00 ✓

Valid? → Continue
Expired? → ACCESS_REJECT
```

### 5. Private Key Ownership Proof (TLS Handshake)

**Most critical check:**

```
RADIUS sends challenge (random data)
Pump signs challenge with private key
RADIUS verifies signature using pump's public key (from certificate)

If signature valid → Pump owns private key → Continue
If signature invalid → Pump doesn't own private key → ACCESS_REJECT
```

This prevents someone from stealing just the certificate (without private key).

---

## Complete End-to-End Flow

### Phase 1: Certificate Issuance (One-Time Setup)

```
1. Administrator generates EST CA certificates
   → ca-cert.pem, ca-key.pem created

2. Administrator deploys EST server
   → docker-compose -f docker-compose-nginx.yml up -d

3. IQE requests certificate for Pump NPPBBB4
   → IQE authenticates with RA certificate
   → IQE submits CSR (with CN=NPPBBB4)
   → EST signs CSR with ca-key.pem
   → EST returns pump-cert.pem

4. IQE installs pump-cert.pem on Pump NPPBBB4
   → /etc/cert/wifi_cert.pem (certificate)
   → /etc/cert/wifi_private_key.prv (private key)
   → /etc/cert/wifi_root_cert.pem (CA certificate)
```

### Phase 2: RADIUS Deployment (One-Time Setup)

```
1. Administrator deploys RADIUS server
   → docker-compose -f docker-compose-radius.yml up -d

2. Administrator copies EST CA certificate to RADIUS
   → cp certs/ca-cert.pem radius-certs/
   → RADIUS mounts this at /etc/freeradius/certs/ca/ca-cert.pem

3. Administrator configures WLC
   → RADIUS server: 10.42.56.101:1812
   → WLAN: 802.1X authentication enabled
```

### Phase 3: Pump WiFi Connection (Every Time Pump Connects)

```
1. Pump scans for WiFi
   → Finds SSID "Ferrari2"

2. Pump associates with WLC
   → WLC challenges pump for authentication

3. Pump sends identity
   → Identity: NPPBBB4

4. WLC initiates EAP-TLS
   → WLC requests RADIUS authentication

5. RADIUS starts TLS handshake
   → RADIUS requests pump certificate

6. Pump sends certificate + proves ownership
   → Sends pump-cert.pem
   → Signs challenge with wifi_private_key.prv

7. RADIUS validates certificate
   → Signature check: openssl verify -CAfile ca-cert.pem pump-cert.pem ✓
   → Issuer DN check: /CN=Python-EST Root CA ✓
   → Expiration check: Valid ✓
   → CN check: NPPBBB4 ✓
   → Private key proof: Valid ✓

8. RADIUS sends Access-Accept
   → WLC grants network access

9. Pump completes WPA2 4-way handshake
   → Derives encryption keys

10. Pump connected to WiFi
    → Gets IP address via DHCP
    → Can communicate on network
```

---

## What Pump Receives from IQE

### Files Installed on Pump

```bash
/etc/cert/
├── wifi_root_cert.pem      # EST CA certificate (ca-cert.pem)
├── wifi_cert.pem           # Pump certificate (signed by EST)
└── wifi_private_key.prv    # Pump private key (generated during CSR)
```

### wpa_supplicant.conf Configuration

```conf
network={
    ssid="Ferrari2"
    key_mgmt=WPA-EAP
    eap=TLS
    identity="NPPBBB4"

    # Root CA - to verify RADIUS server certificate
    ca_cert="/etc/cert/wifi_root_cert.pem"

    # Client certificate - pump's identity
    client_cert="/etc/cert/wifi_cert.pem"

    # Private key - proves pump owns the certificate
    private_key="/etc/cert/wifi_private_key.prv"
}
```

---

## Key Differences: RA Auth vs EAP-TLS Auth

| Aspect | RA Auth (IQE → EST) | EAP-TLS Auth (Pump → RADIUS) |
|--------|---------------------|------------------------------|
| **Purpose** | Certificate **issuance** | WiFi **access** |
| **Client** | IQE Gateway | Medical Pump |
| **Server** | EST Server | FreeRADIUS |
| **Protocol** | HTTPS (EST/RFC 7030) | RADIUS + EAP-TLS (802.1X) |
| **Client Auth** | RA certificate (iqe-ra-cert.pem) | Pump certificate (pump-cert.pem) |
| **What's Validated** | IQE is authorized RA | Pump has valid certificate from trusted CA |
| **Result** | New certificate issued | WiFi access granted |
| **Frequency** | Once per pump (or on cert renewal) | Every WiFi connection |

---

## Summary

### What Gets Compared in RADIUS?

1. **Certificate Signature** - Cryptographically verified against EST CA public key
2. **Issuer DN** - Must match `/CN=Python-EST Root CA`
3. **Certificate Expiration** - Must be within validity period
4. **Common Name** - Must match pump identity (NPPBBB4)
5. **Private Key Ownership** - Pump must prove it owns the private key

### Authentication Flow Types

1. **RA Authentication (IQE → EST)**
   - Client cert authentication
   - IQE proves it's authorized to request certificates
   - Result: EST issues pump certificate

2. **EAP-TLS Authentication (Pump → RADIUS)**
   - Mutual certificate authentication
   - Pump proves it has valid certificate from trusted CA
   - RADIUS proves it's legitimate RADIUS server
   - Result: Pump gets WiFi access

### What Pump Expects to Happen

1. **Certificate Installation** (via IQE):
   - Receives pump certificate from EST
   - Receives EST CA certificate
   - Already has private key (generated during CSR)

2. **WiFi Connection** (automatic):
   - Pump attempts to connect to Ferrari2
   - WLC challenges pump
   - Pump presents certificate
   - RADIUS validates certificate
   - Pump gets Access-Accept
   - Pump connects to WiFi
   - Pump gets IP address

**End result:** Pump is connected to WiFi and can communicate on the network!
