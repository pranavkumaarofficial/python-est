# Pump Certificate Flow - Visual Guide

## What Happens to the Pump? Complete Journey

---

## Stage 1: Certificate Issuance (via IQE)

### Step 1: IQE Generates CSR for Pump

```
IQE Gateway (on behalf of pump NPPBBB4)
│
├─ Generates RSA key pair
│  ├─ pump-private-key.pem (KEEP SECRET!)
│  └─ pump-public-key.pem (embedded in CSR)
│
└─ Creates Certificate Signing Request (CSR)
   Subject: CN=NPPBBB4, O=Ferrari Medical Inc
   Public Key: [pump's public key]
   Signature: [signed with pump's private key to prove ownership]
```

### Step 2: IQE Sends CSR to EST Server

```
       IQE                               EST Server
        │                                     │
        │  HTTPS POST /simpleenroll           │
        │  Headers:                           │
        │    Content-Type: application/pkcs10 │
        │  Auth:                              │
        │    Client Cert: iqe-ra-cert.pem     │
        │    Client Key: iqe-ra-key.pem       │
        │  Body:                              │
        │    [CSR in DER format]              │
        ├────────────────────────────────────▶│
        │                                     │
        │                                     │ ✓ Validate RA cert
        │                                     │ ✓ Parse CSR
        │                                     │ ✓ Extract Subject: CN=NPPBBB4
        │                                     │ ✓ Extract Public Key
        │                                     │
        │                                     │ Sign CSR:
        │                                     │ ├─ Load ca-key.pem
        │                                     │ ├─ Create X.509 certificate
        │                                     │ ├─ Set Issuer: CN=Python-EST Root CA
        │                                     │ ├─ Set Subject: CN=NPPBBB4
        │                                     │ ├─ Set Public Key: [from CSR]
        │                                     │ ├─ Set Validity: 365 days
        │                                     │ └─ Sign with ca-key.pem
        │                                     │
        │                                     │ Package as PKCS#7:
        │                                     │ ├─ pump-cert.pem (signed)
        │                                     │ └─ ca-cert.pem (chain)
        │                                     │
        │  HTTP 200 OK                        │
        │  Body: base64(PKCS#7)               │
        │◀────────────────────────────────────┤
        │                                     │
        │ Extract pump-cert.pem from PKCS#7   │
        │                                     │
```

### Step 3: IQE Installs Certificates on Pump

```
IQE connects to Pump NPPBBB4 and installs:

┌────────────────────────────────────────────────┐
│ Pump NPPBBB4 File System                      │
├────────────────────────────────────────────────┤
│                                                │
│ /etc/cert/wifi_root_cert.pem                  │
│ ┌────────────────────────────────────┐        │
│ │ -----BEGIN CERTIFICATE-----         │        │
│ │ EST CA Certificate (Public)         │        │
│ │ Issuer: CN=Python-EST Root CA       │        │
│ │ Subject: CN=Python-EST Root CA      │        │
│ │ Public Key: [EST CA public key]     │        │
│ │ Purpose: Verify RADIUS server cert  │        │
│ │ -----END CERTIFICATE-----           │        │
│ └────────────────────────────────────┘        │
│                                                │
│ /etc/cert/wifi_cert.pem                       │
│ ┌────────────────────────────────────┐        │
│ │ -----BEGIN CERTIFICATE-----         │        │
│ │ Pump Certificate (Public)           │        │
│ │ Issuer: CN=Python-EST Root CA       │ ◀──┐   │
│ │ Subject: CN=NPPBBB4                 │    │   │
│ │ Organization: Ferrari Medical Inc   │    │   │
│ │ Public Key: [pump's public key]     │    │   │
│ │ Valid: 2024-11-11 to 2025-11-11     │    │   │
│ │ Signature: [signed by EST CA]       │ ───┘   │
│ │ Purpose: Pump identity              │        │
│ │ -----END CERTIFICATE-----           │        │
│ └────────────────────────────────────┘        │
│                                                │
│ /etc/cert/wifi_private_key.prv                │
│ ┌────────────────────────────────────┐        │
│ │ -----BEGIN PRIVATE KEY-----         │        │
│ │ Pump Private Key (SECRET!)          │        │
│ │ NEVER transmitted over network      │        │
│ │ Used to prove pump owns certificate │        │
│ │ Purpose: Sign TLS challenges        │        │
│ │ -----END PRIVATE KEY-----           │        │
│ └────────────────────────────────────┘        │
│                                                │
│ /etc/wpa_supplicant/wpa_supplicant.conf       │
│ ┌────────────────────────────────────┐        │
│ │ network={                           │        │
│ │   ssid="Ferrari2"                   │        │
│ │   key_mgmt=WPA-EAP                  │        │
│ │   eap=TLS                           │        │
│ │   identity="NPPBBB4"                │        │
│ │   ca_cert="/etc/cert/wifi_root_cert.pem"    │
│ │   client_cert="/etc/cert/wifi_cert.pem"     │
│ │   private_key="/etc/cert/wifi_private_key.prv"
│ │ }                                   │        │
│ └────────────────────────────────────┘        │
└────────────────────────────────────────────────┘
```

---

## Stage 2: Pump Connects to WiFi (802.1X Authentication)

### WiFi Scan and Association

```
Pump NPPBBB4                  Cisco WLC
     │                             │
     │ 1. WiFi Scan                │
     │    "Looking for networks"   │
     │                             │
     │ 2. Probe Request            │
     │    SSID: Ferrari2           │
     ├────────────────────────────▶│
     │                             │
     │ 3. Probe Response           │
     │    "Ferrari2 here, join me" │
     │◀────────────────────────────┤
     │                             │
     │ 4. Association Request      │
     │    "I want to join Ferrari2"│
     ├────────────────────────────▶│
     │                             │
     │ 5. Association Response     │
     │    "OK, but authenticate    │
     │     first via 802.1X"       │
     │◀────────────────────────────┤
     │                             │
     │ Status: ASSOCIATED          │
     │ Access: BLOCKED (pending auth)
     │                             │
```

### EAP-TLS Authentication Flow

```
Pump                WLC                 RADIUS
 │                   │                     │
 │                   │ WLC initiates 802.1X authentication
 │                   │                     │
 │ EAP-Request       │                     │
 │ Identity          │                     │
 │◀──────────────────┤                     │
 │                   │                     │
 │ EAP-Response      │                     │
 │ Identity=NPPBBB4  │                     │
 ├──────────────────▶│                     │
 │                   │                     │
 │                   │ RADIUS Access-Req   │
 │                   │ User: NPPBBB4       │
 │                   ├────────────────────▶│
 │                   │                     │
 │                   │ Access-Challenge    │
 │                   │ EAP: Start TLS      │
 │                   │◀────────────────────┤
 │                   │                     │
 │ EAP: TLS Start    │                     │
 │◀──────────────────┤                     │
 │                   │                     │
 │─────────────────────────────────────────────┐
 │ Pump prepares TLS Client Hello              │
 │ - Reads wifi_cert.pem                       │
 │ - Reads wifi_private_key.prv                │
 │ - Generates random challenge                │
 │◀────────────────────────────────────────────┘
 │                   │                     │
 │ TLS Client Hello  │                     │
 │ + Certificate     │                     │
 │   [wifi_cert.pem] │                     │
 ├──────────────────▶│                     │
 │                   │                     │
 │                   │ RADIUS Access-Req   │
 │                   │ EAP: Client Hello   │
 │                   │ + Cert              │
 │                   ├────────────────────▶│
 │                   │                     │
 │                   │                     │─────────────────────────┐
 │                   │                     │ RADIUS validates cert:  │
 │                   │                     │                         │
 │                   │                     │ 1. Parse certificate    │
 │                   │                     │    Extract:             │
 │                   │                     │    - Issuer DN          │
 │                   │                     │    - Subject DN (CN)    │
 │                   │                     │    - Public Key         │
 │                   │                     │    - Signature          │
 │                   │                     │    - Validity dates     │
 │                   │                     │                         │
 │                   │                     │ 2. Load CA certificate  │
 │                   │                     │    Read: /etc/freeradius│
 │                   │                     │          /certs/ca/     │
 │                   │                     │          ca-cert.pem    │
 │                   │                     │                         │
 │                   │                     │ 3. Verify signature     │
 │                   │                     │    EST_CA_pubkey.verify(│
 │                   │                     │      pump_cert.signature,
 │                   │                     │      pump_cert.data)    │
 │                   │                     │    Result: ✓ VALID      │
 │                   │                     │                         │
 │                   │                     │ 4. Check Issuer DN      │
 │                   │                     │    Expected: /CN=Python-EST Root CA
 │                   │                     │    Actual: [from cert]  │
 │                   │                     │    Result: ✓ MATCH      │
 │                   │                     │                         │
 │                   │                     │ 5. Check expiration     │
 │                   │                     │    Not Before: 2024-11-11
 │                   │                     │    Not After: 2025-11-11│
 │                   │                     │    Now: 2024-11-11      │
 │                   │                     │    Result: ✓ VALID      │
 │                   │                     │                         │
 │                   │                     │ 6. Check CN             │
 │                   │                     │    Expected: NPPBBB4    │
 │                   │                     │    Actual: [from cert]  │
 │                   │                     │    Result: ✓ MATCH      │
 │                   │                     │                         │
 │                   │                     │ Certificate valid!      │
 │                   │                     │ Now verify key ownership│
 │                   │                     │◀────────────────────────┘
 │                   │                     │
 │                   │ Access-Challenge    │
 │                   │ EAP: Server Hello   │
 │                   │ + Challenge         │
 │                   │◀────────────────────┤
 │                   │                     │
 │ Server Hello      │                     │
 │ + Challenge       │                     │
 │◀──────────────────┤                     │
 │                   │                     │
 │─────────────────────────────────────────────┐
 │ Pump proves key ownership:                  │
 │ 1. Receives challenge from RADIUS           │
 │ 2. Signs challenge with wifi_private_key.prv│
 │ 3. Sends signature to RADIUS                │
 │◀────────────────────────────────────────────┘
 │                   │                     │
 │ Certificate Verify│                     │
 │ [signed challenge]│                     │
 ├──────────────────▶│                     │
 │                   │                     │
 │                   │ RADIUS Access-Req   │
 │                   │ EAP: Cert Verify    │
 │                   ├────────────────────▶│
 │                   │                     │
 │                   │                     │─────────────────────────┐
 │                   │                     │ Verify signature:       │
 │                   │                     │                         │
 │                   │                     │ pump_cert_pubkey.verify(│
 │                   │                     │   signature,            │
 │                   │                     │   challenge)            │
 │                   │                     │                         │
 │                   │                     │ Result: ✓ VALID         │
 │                   │                     │                         │
 │                   │                     │ Pump owns the private   │
 │                   │                     │ key for this cert!      │
 │                   │                     │                         │
 │                   │                     │ ALL CHECKS PASSED!      │
 │                   │                     │ AUTHENTICATION SUCCESS  │
 │                   │                     │◀────────────────────────┘
 │                   │                     │
 │                   │ RADIUS Access-Accept│
 │                   │ (Authentication OK) │
 │                   │◀────────────────────┤
 │                   │                     │
 │ EAP-Success       │                     │
 │◀──────────────────┤                     │
 │                   │                     │
 │ Status: AUTHENTICATED                   │
 │                   │                     │
```

### WPA2 Key Exchange

```
Pump                WLC
 │                   │
 │ 4-Way Handshake   │
 │ (WPA2 key exchange)
 │                   │
 │ 1. ANonce         │
 │◀──────────────────┤
 │                   │
 │ 2. SNonce + MIC   │
 ├──────────────────▶│
 │                   │
 │ 3. GTK + MIC      │
 │◀──────────────────┤
 │                   │
 │ 4. ACK            │
 ├──────────────────▶│
 │                   │
 │ Encryption keys   │
 │ derived and       │
 │ installed         │
 │                   │
```

### Network Access

```
Pump                WLC                 Network
 │                   │                     │
 │ DHCP Discover     │                     │
 ├──────────────────▶│                     │
 │                   │                     │
 │                   │ Forward             │
 │                   ├────────────────────▶│
 │                   │                     │
 │                   │ DHCP Offer          │
 │                   │◀────────────────────┤
 │                   │                     │
 │ DHCP Offer        │                     │
 │◀──────────────────┤                     │
 │                   │                     │
 │ DHCP Request      │                     │
 ├──────────────────▶│────────────────────▶│
 │                   │                     │
 │                   │ DHCP ACK            │
 │◀──────────────────┤◀────────────────────┤
 │                   │                     │
 │ IP Assigned!      │                     │
 │ 10.42.56.X        │                     │
 │                   │                     │
 │ Pump is now CONNECTED and can communicate
 │                   │                     │
```

---

## Stage 3: What Pump Can Do Now

### Full Network Access

```
┌─────────────────────────────────────────────────┐
│ Pump NPPBBB4 - Connected to Ferrari2 WiFi      │
├─────────────────────────────────────────────────┤
│                                                 │
│ ✓ WiFi: Connected                               │
│ ✓ IP Address: 10.42.56.X (via DHCP)            │
│ ✓ Gateway: 10.42.56.1                           │
│ ✓ DNS: Configured                               │
│ ✓ Encryption: WPA2-AES active                   │
│                                                 │
│ Can now:                                        │
│ ├─ Communicate with hospital systems           │
│ ├─ Send patient data                            │
│ ├─ Receive medication orders                    │
│ ├─ Report status/telemetry                      │
│ └─ Software updates                             │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## What Happens on Reconnection?

### Next Time Pump Connects

```
Scenario: Pump reboots or WiFi drops

Pump                WLC                 RADIUS
 │                   │                     │
 │ WiFi scan         │                     │
 │ Connect Ferrari2  │                     │
 ├──────────────────▶│                     │
 │                   │                     │
 │ EAP-TLS auth      │                     │
 │ (same flow)       │                     │
 │◀─────────────────▶│◀───────────────────▶│
 │                   │                     │
 │ Uses SAME certificates already installed│
 │ - wifi_cert.pem                         │
 │ - wifi_private_key.prv                  │
 │ - wifi_root_cert.pem                    │
 │                   │                     │
 │ Connected!        │                     │
 │                   │                     │

No need to contact EST server again!
Certificates valid for 365 days.
```

### When to Re-Issue Certificate

**Only when:**
- Certificate expires (365 days)
- Certificate compromised (private key leaked)
- Pump identity changes (new serial number)
- CA certificate rotated

**Process:** IQE requests new certificate from EST server (repeat Stage 1)

---

## Summary: What Pump Receives and What It Does

### Files Pump Receives

| File | Purpose | Public/Private | Source |
|------|---------|----------------|--------|
| `wifi_root_cert.pem` | Verify RADIUS server | Public | EST CA cert |
| `wifi_cert.pem` | Pump's identity | Public | Signed by EST |
| `wifi_private_key.prv` | Prove identity | **Private** | Generated by IQE |

### What Pump Does

1. **Stores certificates** in `/etc/cert/`
2. **Configures wpa_supplicant** with cert paths
3. **Scans for WiFi** (Ferrari2)
4. **Attempts connection** to WLC
5. **Presents certificate** during EAP-TLS
6. **Proves key ownership** via TLS handshake
7. **Receives Access-Accept** from RADIUS
8. **Completes WPA2 handshake** with WLC
9. **Gets IP address** via DHCP
10. **Communicates on network** ✅

### Expected Result

```
✓ Pump connects to Ferrari2 WiFi automatically
✓ No username/password needed
✓ Certificate-based authentication
✓ Secure WPA2 encryption
✓ Full network access
✓ Can communicate with hospital systems
```

---

## Monitoring RADIUS Logs

### Successful Authentication

```bash
docker logs -f freeradius-server
```

**Expected output:**
```
(0) Received Access-Request Id 123 from 10.42.56.50:1645 to 10.42.56.101:1812 length 150
(0)   User-Name = "NPPBBB4"
(0)   EAP-Message = 0x...
(0) # Executing section authorize from file /etc/freeradius/sites-enabled/default
(0) eap: Peer sent EAP Response (code 2) ID 1 length 15
(0) eap: EAP-Identity reply, returning 'ok' so we can short-circuit the rest of authorize
(0) [eap] = ok
(0) # Executing section authenticate from file /etc/freeradius/sites-enabled/default
(0) eap: Expiring EAP session with state 0x...
(0) eap: Finished EAP session with state 0x...
(0) eap: Previous EAP request found for state 0x..., released from the list
(0) eap: Peer sent packet with method EAP TLS (13)
(0) eap: Calling submodule eap_tls to process data
(0) eap_tls: Continuing EAP-TLS
(0) eap_tls: TLS - User authenticated successfully
(0) eap: Sending EAP Success (code 3) ID 2 length 4
(0) [eap] = ok
(0) # Executing section post-auth from file /etc/freeradius/sites-enabled/default
(0) Sent Access-Accept Id 123 from 10.42.56.101:1812 to 10.42.56.50:1645 length 0
(0)   MS-MPPE-Recv-Key = 0x...
(0)   MS-MPPE-Send-Key = 0x...
(0)   EAP-Message = 0x03020004
(0)   Message-Authenticator = 0x00000000000000000000000000000000
(0) Finished request
```

**Key lines:**
- ✅ `User-Name = "NPPBBB4"` - Pump identity
- ✅ `TLS - User authenticated successfully` - Certificate validated
- ✅ `Sent Access-Accept` - Pump granted access

---

**The pump is now fully operational on the WiFi network!** 🎉
