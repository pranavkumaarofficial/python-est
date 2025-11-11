# Complete EST + FreeRADIUS Deployment Guide

## Architecture Overview

```
Medical Pump (EAP-TLS Client)
    ↓
Cisco Wireless LAN Controller (WLC)
    ↓ RADIUS Auth (Port 1812/1813)
FreeRADIUS Server (Validates pump certificates)
    ↑
    Uses EST CA certificate for validation
    ↑
EST Server (Issues certificates to pumps via IQE)
```

---

## Prerequisites

- Ubuntu VM (10.42.56.101)
- Docker and Docker Compose installed
- Cisco WLC access (for configuration)
- Certificates already generated

---

## Step 1: Deploy Complete Stack

### On Ubuntu VM:

```bash
cd ~/Desktop/python-est

# Pull latest code
git pull origin deploy_v1

# Stop old containers
docker-compose -f docker-compose-nginx.yml down

# Build and start complete stack (EST + RADIUS)
docker-compose -f docker-compose-full.yml up -d --build

# Check status
docker-compose -f docker-compose-full.yml ps

# Expected output:
# NAME                    STATUS
# python-est-server       Up (healthy)
# est-nginx               Up (healthy)
# freeradius-server       Up
```

---

## Step 2: Verify Services

### Test EST Server
```bash
curl -k https://localhost:8445/health
# Expected: {"status":"healthy","service":"Python-EST Server"}
```

### Test RADIUS Server
```bash
# Install radtest tool
docker exec -it freeradius-server radtest test test localhost 0 testing123

# Expected: Access-Reject (because user doesn't exist - this is OK)
# Important: RADIUS is responding!
```

### View RADIUS Logs
```bash
docker-compose -f docker-compose-full.yml logs -f freeradius
# Should see: "Ready to process requests"
```

---

## Step 3: Configure Cisco WLC

### A. Add RADIUS Server

1. **Log into Cisco WLC Web Interface**
   - URL: `https://your-wlc-ip/`

2. **Navigate to Security → RADIUS → Authentication**
   - Click "New"
   - Server IP Address: **10.42.56.101**
   - Shared Secret: **testing123** (or your custom secret)
   - Port: **1812**
   - Server Status: **Enabled**
   - Click "Apply"

3. **Add Accounting Server** (optional but recommended)
   - Navigate to Security → RADIUS → Accounting
   - Click "New"
   - Server IP Address: **10.42.56.101**
   - Shared Secret: **testing123**
   - Port: **1813**
   - Server Status: **Enabled**
   - Click "Apply"

### B. Create AAA Server Group

1. **Navigate to Security → AAA → RADIUS → Authentication**
   - Click "New"
   - Server Group Name: **EST-RADIUS**
   - Add your RADIUS server (10.42.56.101) to the group
   - Click "Apply"

### C. Configure WLAN for 802.1X

1. **Navigate to WLANs → Edit your WLAN (e.g., "Ferrari2")**

2. **Security Tab:**
   - Layer 2 Security: **WPA+WPA2** or **WPA3**
   - WPA+WPA2 Parameters:
     - WPA2 Policy: **Enabled**
     - WPA2 Encryption: **AES**
   - Auth Key Mgmt: **802.1X**

3. **AAA Servers Tab:**
   - Authentication Servers: Select **EST-RADIUS**
   - Accounting Servers: Select **EST-RADIUS** (if configured)

4. **Click "Apply" and "Save Configuration"**

---

## Step 4: Update RADIUS Client Configuration

**IMPORTANT:** Update the WLC IP in `radius/clients.conf`

```bash
# Edit the file
vi ~/Desktop/python-est/radius/clients.conf

# Find this section:
client cisco_wlc {
    ipaddr = 0.0.0.0/0  # CHANGE THIS
    secret = testing123  # CHANGE THIS

# Replace with:
client cisco_wlc {
    ipaddr = 10.42.56.X/32  # Your actual WLC IP
    secret = YourSecureSecret123!

# Restart RADIUS
docker-compose -f docker-compose-full.yml restart freeradius
```

---

## Step 5: Test with a Pump

### Prepare Pump Certificate

#### Option A: Via IQE (Recommended)
```bash
# IQE team requests certificate from EST server
# IQE delivers certificate to pump
# (This is the production flow)
```

#### Option B: Manual Test (Direct SSH to pump)
```bash
# 1. Generate CSR on pump or locally
python3 << 'EOF'
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, 'IN'),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, 'KA'),
    x509.NameAttribute(NameOID.LOCALITY_NAME, 'BLR'),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'Baxter'),
    x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, 'MD'),
    x509.NameAttribute(NameOID.COMMON_NAME, 'NPPBBB4'),  # Device serial number
])).sign(key, hashes.SHA256())

with open('/tmp/pump.der', 'wb') as f:
    f.write(csr.public_bytes(serialization.Encoding.DER))
with open('/tmp/pump.key', 'wb') as f:
    f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))
print("CSR created: /tmp/pump.der")
print("Key created: /tmp/pump.key")
EOF

# 2. Request certificate from EST
curl -vk https://10.42.56.101:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @/tmp/pump.der \
  -o /tmp/pump_cert.p7

# 3. Extract certificate from PKCS#7
openssl pkcs7 -in /tmp/pump_cert.p7 -inform DER -print_certs -out /tmp/wifi_cert.pem

# 4. Copy to pump (via SCP or USB)
# scp /tmp/wifi_cert.pem root@pump-ip:/etc/cert/
# scp /tmp/pump.key root@pump-ip:/etc/cert/wifi_private_key.prv
# scp certs/ca-cert.pem root@pump-ip:/etc/cert/wifi_root_cert.pem
```

### Update Pump's wpa_supplicant.conf

```bash
# On the pump (via SSH):
cat > /etc/cert/wpa_supplicant.conf << 'EOF'
ctrl_interface=/run/wpa_supplicant
update_config=1
ap_scan=1

network={
    scan_ssid=1
    ssid="Ferrari2"
    key_mgmt=WPA-EAP
    proto=RSN
    pairwise=CCMP
    group=CCMP
    eap=TLS
    identity="NPPBBB4"
    ca_cert="/etc/cert/wifi_root_cert.pem"
    client_cert="/etc/cert/wifi_cert.pem"
    private_key="/etc/cert/wifi_private_key.prv"
}
EOF

# Restart wpa_supplicant
systemctl restart wpa_supplicant
```

---

## Step 6: Monitor Authentication

### On RADIUS Server:
```bash
# Watch live authentication attempts
docker-compose -f docker-compose-full.yml logs -f freeradius | grep -i "auth:"

# Look for:
# Auth: (x) User-Name = "NPPBBB4"
# Auth: Login OK: [NPPBBB4] (from client cisco-wlc port 0)
```

### On Pump:
```bash
# Check wpa_supplicant status
wpa_cli status

# Expected:
# wpa_state=COMPLETED
# ssid=Ferrari2
# key_mgmt=WPA2-EAP
```

### On Cisco WLC:
```bash
# Monitor → Clients
# Should see pump connected with EAP-TLS authentication
```

---

## Troubleshooting

### RADIUS Not Responding

```bash
# Check if RADIUS is running
docker ps | grep freeradius

# Check RADIUS logs
docker logs freeradius-server --tail 50

# Test locally
docker exec -it freeradius-server radiusd -X
# Look for "Ready to process requests"
```

### Certificate Validation Failing

```bash
# Check RADIUS has EST CA certificate
docker exec freeradius-server ls -la /etc/freeradius/certs/est/

# Expected: ca-cert.pem

# Verify certificate
docker exec freeradius-server openssl x509 -in /etc/freeradius/certs/est/ca-cert.pem -noout -subject
# Should match: CN=Python-EST Root CA
```

### WLC Can't Reach RADIUS

```bash
# From WLC CLI:
ping 10.42.56.101

# Check firewall
sudo ufw status
sudo ufw allow 1812/udp
sudo ufw allow 1813/udp

# Test RADIUS from WLC
# (Use WLC built-in RADIUS test tool if available)
```

### Pump Can't Connect

```bash
# On pump, check wpa_supplicant logs
journalctl -u wpa_supplicant -f

# Common issues:
# - Wrong SSID
# - Wrong certificate path
# - Certificate expired
# - CA certificate mismatch
```

---

## Production Checklist

- [ ] Change RADIUS shared secret from `testing123`
- [ ] Update `radius/clients.conf` with actual WLC IP
- [ ] Configure RADIUS accounting (for audit logs)
- [ ] Set up RADIUS log rotation
- [ ] Configure certificate revocation checking (CRL/OCSP)
- [ ] Test failover (if using multiple RADIUS servers)
- [ ] Document certificate renewal process
- [ ] Set up monitoring alerts
- [ ] Create backup of RADIUS configuration

---

## Architecture Benefits

✅ **Independent** - Your own RADIUS, not dependent on legacy systems
✅ **Scalable** - Docker-based, easy to replicate
✅ **Secure** - Certificate-based auth, no passwords
✅ **Auditable** - All authentications logged
✅ **Maintainable** - Version controlled configuration

---

## Next Steps

1. Deploy and test with one pump
2. Verify authentication logs
3. Integrate with IQE for certificate delivery
4. Roll out to remaining pumps
5. Set up monitoring dashboard

---

## Support

For issues, check:
1. RADIUS logs: `docker logs freeradius-server`
2. EST logs: `docker logs python-est-server`
3. Nginx logs: `docker logs est-nginx`
4. WLC logs: Monitor → Events/Logs
