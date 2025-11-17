# Authentication Summary - Quick Reference

## Two Separate Authentication Flows

### 1. RA Authentication (IQE → EST Server)

**Purpose:** Certificate issuance
**Happens:** Once per pump (or on renewal)

```
┌─────────┐                           ┌──────────┐
│   IQE   │  Client Cert Auth         │   EST    │
│ Gateway │──────────────────────────▶│  Server  │
│         │  (iqe-ra-cert.pem)        │          │
│         │                           │          │
│         │◀──────────────────────────│          │
│         │  Pump Certificate         │          │
└─────────┘  (pump-cert.pem)          └──────────┘
```

**What's validated:**
- ✅ IQE's RA certificate signed by EST CA
- ✅ Certificate not expired
- ✅ IQE owns the private key (TLS handshake)

**Result:** EST issues pump certificate

---

### 2. EAP-TLS Authentication (Pump → RADIUS)

**Purpose:** WiFi access
**Happens:** Every time pump connects to WiFi

```
┌─────────┐     ┌─────────┐     ┌──────────┐
│  Pump   │────▶│   WLC   │────▶│  RADIUS  │
│         │ WiFi│         │ UDP │          │
│         │     │         │ 1812│          │
│         │     │         │     │          │
│         │     │         │     │ Validates│
│         │     │         │     │ against  │
│         │     │         │     │ ca-cert  │
│         │     │         │     │          │
│         │◀────│         │◀────│          │
│Connected│Access│         │Accept│         │
└─────────┘     └─────────┘     └──────────┘
```

**What's validated:**
1. **Certificate Signature** - Cryptographically verified using EST CA public key
2. **Issuer DN** - `/C=US/ST=CA/L=Test/O=Test CA/CN=Python-EST Root CA`
3. **Expiration** - Not expired
4. **Common Name** - Matches pump identity (e.g., NPPBBB4)
5. **Private Key Ownership** - Pump proves it owns the key via TLS handshake

**Result:** Pump gets WiFi access

---

## RADIUS Authentication Policy Details

### Configuration File: `radius/eap`

```ini
# What RADIUS checks:
ca_file = /etc/freeradius/certs/ca/ca-cert.pem  # EST CA certificate
check_cert_issuer = "/C=US/ST=CA/L=Test/O=Test CA/CN=Python-EST Root CA"
check_cert_cn = %{User-Name}  # Match CN to identity
require_client_cert = yes
```

### Validation Process

```python
# Pseudocode of RADIUS validation
def validate_pump_certificate(pump_cert, ca_cert, user_name):
    # 1. Signature verification
    if not verify_signature(pump_cert, ca_cert.public_key):
        return "REJECT: Certificate not signed by trusted CA"

    # 2. Issuer DN check
    expected_issuer = "/C=US/ST=CA/L=Test/O=Test CA/CN=Python-EST Root CA"
    if pump_cert.issuer_dn != expected_issuer:
        return "REJECT: Issuer DN mismatch"

    # 3. Expiration check
    if pump_cert.not_before > now() or pump_cert.not_after < now():
        return "REJECT: Certificate expired or not yet valid"

    # 4. Common Name check (optional)
    if pump_cert.subject_cn != user_name:
        return "REJECT: CN doesn't match identity"

    # 5. Private key ownership (TLS handshake)
    challenge = generate_random()
    signature = pump_signs_challenge(challenge)
    if not verify_signature(signature, pump_cert.public_key, challenge):
        return "REJECT: Pump doesn't own private key"

    # All checks passed!
    return "ACCEPT: Pump authenticated"
```

### Command-Line Equivalent

```bash
# This is essentially what RADIUS does:
openssl verify -CAfile /etc/freeradius/certs/ca/ca-cert.pem pump-cert.pem
# Output: pump-cert.pem: OK  (or error message)
```

---

## What Pump Receives from IQE

### Certificates Installed on Pump

After IQE requests certificate from EST:

```
/etc/cert/
├── wifi_root_cert.pem       ← EST CA certificate (public)
│                              Used to verify RADIUS server cert
│
├── wifi_cert.pem            ← Pump certificate (public)
│                              Pump's identity, signed by EST CA
│                              Contains: CN=NPPBBB4, O=Ferrari Medical Inc
│
└── wifi_private_key.prv     ← Pump private key (secret!)
                               Used to prove pump owns the certificate
                               Never transmitted, only used for signing
```

### Pump WiFi Configuration

**File:** `/etc/wpa_supplicant/wpa_supplicant.conf`

```conf
network={
    ssid="Ferrari2"
    key_mgmt=WPA-EAP          # WPA2/WPA3 Enterprise with EAP
    eap=TLS                   # EAP-TLS (certificate-based auth)
    identity="NPPBBB4"        # Pump serial number

    # Certificates for authentication
    ca_cert="/etc/cert/wifi_root_cert.pem"      # Verify RADIUS
    client_cert="/etc/cert/wifi_cert.pem"       # Pump identity
    private_key="/etc/cert/wifi_private_key.prv" # Prove ownership
}
```

---

## Complete Flow: From Certificate Issuance to WiFi Connection

### Phase 1: Setup (One-Time)

```
1. Admin deploys EST server
   ├─ Generates CA certificates (ca-cert.pem, ca-key.pem)
   ├─ Generates RA certificate for IQE
   └─ Starts docker-compose-nginx.yml

2. Admin deploys RADIUS server
   ├─ Copies ca-cert.pem from EST server
   ├─ Generates RADIUS server certificates
   ├─ Configures WLC IP in clients.conf
   └─ Starts docker-compose-radius.yml

3. Admin configures Cisco WLC
   ├─ Adds RADIUS server (10.42.56.101:1812)
   ├─ Configures WLAN for 802.1X
   └─ Tests connectivity
```

### Phase 2: Certificate Issuance (Per Pump)

```
IQE Gateway                    EST Server
     │                              │
     │ 1. Generate pump CSR         │
     │    CN=NPPBBB4                │
     │                              │
     │ 2. HTTPS POST /simpleenroll  │
     │    + RA certificate          │
     │    + CSR                     │
     ├─────────────────────────────▶│
     │                              │
     │                              │ 3. Validate RA cert
     │                              │ 4. Sign CSR with ca-key.pem
     │                              │
     │ 5. PKCS#7 response           │
     │◀─────────────────────────────┤
     │                              │
     │ 6. Extract pump-cert.pem     │
     │    from PKCS#7               │
     │                              │
     │ 7. Install on pump:          │
     │    - wifi_cert.pem           │
     │    - wifi_private_key.prv    │
     │    - wifi_root_cert.pem      │
     └──────────────────────────────┘
```

### Phase 3: WiFi Authentication (Every Connection)

```
Pump                WLC               RADIUS
 │                   │                   │
 │ 1. Connect to     │                   │
 │    Ferrari2       │                   │
 ├──────────────────▶│                   │
 │                   │                   │
 │ 2. WLC challenges │                   │
 │    for identity   │                   │
 │◀──────────────────┤                   │
 │                   │                   │
 │ 3. Send identity  │                   │
 │    (NPPBBB4)      │                   │
 ├──────────────────▶│                   │
 │                   │                   │
 │                   │ 4. RADIUS Request │
 │                   │    User: NPPBBB4  │
 │                   ├──────────────────▶│
 │                   │                   │
 │                   │ 5. Start EAP-TLS  │
 │                   │◀──────────────────┤
 │                   │                   │
 │ 6. Start TLS      │                   │
 │◀──────────────────┤                   │
 │                   │                   │
 │ 7. Send pump cert │                   │
 │    + prove key    │                   │
 ├──────────────────▶│                   │
 │                   │                   │
 │                   │ 8. Forward cert   │
 │                   ├──────────────────▶│
 │                   │                   │
 │                   │                   │ 9. Validate cert:
 │                   │                   │    ✓ Signature
 │                   │                   │    ✓ Issuer DN
 │                   │                   │    ✓ Expiration
 │                   │                   │    ✓ CN match
 │                   │                   │    ✓ Key ownership
 │                   │                   │
 │                   │ 10. Access-Accept │
 │                   │◀──────────────────┤
 │                   │                   │
 │ 11. Success!      │                   │
 │◀──────────────────┤                   │
 │                   │                   │
 │ 12. WPA2 handshake│                   │
 │◀─────────────────▶│                   │
 │                   │                   │
 │ 13. WiFi Connected│                   │
 │    Get IP (DHCP)  │                   │
 └───────────────────┴───────────────────┘
```

---

## Key Takeaways

### 1. Two Independent Systems

| System | Purpose | Auth Type | Frequency |
|--------|---------|-----------|-----------|
| **EST** | Issue certificates | RA cert (IQE) | Once per pump |
| **RADIUS** | Validate WiFi access | EAP-TLS (Pump) | Every connection |

### 2. What RADIUS Actually Does

**NOT a username/password check!**

**Instead:** Cryptographic certificate validation
- Verifies certificate signature using EST CA public key
- Checks certificate was issued by trusted CA
- Verifies pump owns the private key
- All done via standard TLS/PKI cryptography

### 3. Security Model

```
EST Server (10.42.56.101)
├─ Has: CA private key (ca-key.pem)
├─ Does: Signs pump certificates
└─ Critical: Backup ca-key.pem securely!

RADIUS Server (same or different VM)
├─ Has: CA public cert (ca-cert.pem) only
├─ Does: Validates pump certificates
└─ Cannot: Issue new certificates (no private key)
```

**Even if RADIUS is compromised:** Attacker can't issue certificates!

### 4. What Pump Expects

**After IQE installs certificates:**
1. Pump scans for WiFi
2. Finds "Ferrari2" SSID
3. Attempts to connect
4. WLC challenges pump
5. Pump presents certificate
6. RADIUS validates certificate
7. **Pump gets Access-Accept**
8. **Pump connects to WiFi**
9. **Pump gets IP address**
10. **Pump can communicate on network**

---

## Troubleshooting

### Pump Can't Connect to WiFi

**Check RADIUS logs:**
```bash
docker logs -f freeradius-server
```

**Common errors:**

| Error Message | Cause | Fix |
|---------------|-------|-----|
| `Certificate signature invalid` | Pump cert not signed by EST CA | Verify ca-cert.pem matches between EST and RADIUS |
| `Certificate has expired` | Pump cert expired | Re-issue certificate from EST |
| `Issuer DN mismatch` | Wrong CA cert loaded | Copy correct ca-cert.pem from EST |
| `TLS handshake failed` | Pump doesn't have private key | Re-install wifi_private_key.prv on pump |
| `No response from RADIUS` | WLC can't reach RADIUS | Check firewall, allow WLC IP on port 1812/udp |

---

## Files Reference

### EST Server
- `certs/ca-cert.pem` - CA certificate (copy to RADIUS)
- `certs/ca-key.pem` - CA private key (**CRITICAL - BACKUP!**)
- `certs/iqe-ra-cert.pem` - IQE RA certificate (give to IQE)
- `certs/iqe-ra-key.pem` - IQE RA key (give to IQE)

### RADIUS Server
- `radius-certs/ca-cert.pem` - EST CA cert (copied from EST)
- `radius-server-certs/server.pem` - RADIUS server cert (self-signed)
- `radius/eap` - EAP-TLS configuration (validation rules)
- `radius/clients.conf` - WLC IP and shared secret

### Pump
- `/etc/cert/wifi_root_cert.pem` - EST CA cert
- `/etc/cert/wifi_cert.pem` - Pump certificate
- `/etc/cert/wifi_private_key.prv` - Pump private key
- `/etc/wpa_supplicant/wpa_supplicant.conf` - WiFi config

---

## Next Steps

1. ✅ EST server deployed and tested
2. ⏭️ Deploy RADIUS server (follow [QUICKSTART.md](QUICKSTART.md))
3. ⏭️ Configure WLC (follow [docs/CISCO_WLC_CONFIG.md](docs/CISCO_WLC_CONFIG.md))
4. ⏭️ Request certificate for test pump via IQE
5. ⏭️ Install certificate on pump
6. ⏭️ Test pump WiFi connection
7. ⏭️ Monitor RADIUS logs for Access-Accept

See **[docs/AUTHENTICATION_FLOW.md](docs/AUTHENTICATION_FLOW.md)** for detailed flow diagrams.
