# Deployment Commands - Complete EST + FreeRADIUS Stack

## Part 1: Commit All Changes

```bash
# Stage all new files
git add -A

# Commit with descriptive message
git commit -m "feat: Add FreeRADIUS container for complete EST + RADIUS stack

Components:
- Dockerfile.radius - FreeRADIUS container with EST CA trust
- radius/clients.conf - RADIUS client config for Cisco WLC
- radius/eap - EAP-TLS configuration for certificate auth
- docker-compose-full.yml - Complete stack orchestration
- DEPLOY_COMPLETE_STACK.md - Deployment guide
- CISCO_WLC_CONFIG.md - WLC configuration guide

Architecture:
- Medical Pumps → Cisco WLC → FreeRADIUS (validates certs)
- IQE → Nginx → EST Server (issues certs)
- All containerized and orchestrated via Docker Compose"

# Push to remote
git push origin deploy_v1
```

---

## Part 2: Deploy on Ubuntu VM (10.42.56.101)

### Step 1: Pull Latest Code
```bash
cd ~/Desktop/python-est
git pull origin deploy_v1
```

### Step 2: Verify Certificate Files Exist
```bash
ls -la certs/
# Should show:
#   ca-cert.pem
#   ca-key.pem
#   iqe-ra-cert.pem
#   iqe-ra-key.pem
#   server.pem
#   server.key
```

If missing, regenerate:
```bash
python generate_certificates_python.py
python generate_ra_certificate.py
```

### Step 3: Update RADIUS Configuration

**Update Cisco WLC IP in clients.conf:**
```bash
nano radius/clients.conf
```

Change:
```conf
client cisco_wlc {
    ipaddr = YOUR_WLC_IP_HERE  # Example: 10.42.56.50
    secret = your_strong_secret_here  # CHANGE THIS!
    shortname = cisco-wlc
    nastype = cisco
    require_message_authenticator = yes
}
```

**Generate strong secret:**
```bash
openssl rand -base64 32
# Copy output and paste as 'secret' above
```

### Step 4: Deploy Complete Stack
```bash
# Build and start all services
docker-compose -f docker-compose-full.yml up -d --build

# Watch logs
docker-compose -f docker-compose-full.yml logs -f
```

### Step 5: Verify All Services Running
```bash
# Check service status
docker-compose -f docker-compose-full.yml ps

# Expected output:
# NAME                  STATUS    PORTS
# python-est-server     Up
# est-nginx             Up        0.0.0.0:8445->8445/tcp
# freeradius-server     Up        0.0.0.0:1812->1812/udp, 0.0.0.0:1813->1813/udp
```

### Step 6: Test Each Service

**Test EST Server Health:**
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"Python-EST Server"}
```

**Test Nginx → EST:**
```bash
curl -k https://localhost:8445/health
# Expected: {"status":"healthy","service":"Python-EST Server"}
```

**Test FreeRADIUS:**
```bash
docker exec -it freeradius-server radtest test test localhost 0 testing123
# Expected: Access-Reject (normal - user doesn't exist yet)
```

**Test FreeRADIUS Listening:**
```bash
docker exec -it freeradius-server netstat -ulnp | grep 1812
# Expected: udp 0.0.0.0:1812
```

### Step 7: Check Ubuntu Firewall
```bash
# Check firewall status
sudo ufw status

# Allow RADIUS from WLC (replace with actual WLC IP)
sudo ufw allow from YOUR_WLC_IP to any port 1812 proto udp
sudo ufw allow from YOUR_WLC_IP to any port 1813 proto udp

# Allow EST from IQE network
sudo ufw allow 8445/tcp
```

### Step 8: Verify RADIUS Can Access EST CA Certificate
```bash
# Check cert file exists in container
docker exec -it freeradius-server ls -la /etc/freeradius/certs/est/

# Expected:
#   ca-cert.pem
#   iqe-ra-cert.pem
#   iqe-ra-key.pem

# Verify CA certificate is readable
docker exec -it freeradius-server cat /etc/freeradius/certs/est/ca-cert.pem
```

---

## Part 3: IQE Integration Steps

### Files to Provide to IQE Team

**1. RA Certificate and Key:**
```bash
# Location: certs/iqe-ra-cert.pem and certs/iqe-ra-key.pem

# View RA certificate details
openssl x509 -in certs/iqe-ra-cert.pem -noout -text
# Subject: CN = IQE-RA-Gateway, O = Ferrari Medical Inc
```

**2. CA Certificate:**
```bash
# Location: certs/ca-cert.pem

# IQE needs this to verify EST server responses
```

**3. EST Server Details:**
```text
EST Server URL: https://10.42.56.101:8445/.well-known/est/
Authentication: Client Certificate (RA certificate)

Endpoints:
- CA Certificates: GET  https://10.42.56.101:8445/.well-known/est/cacerts
- Simple Enroll:   POST https://10.42.56.101:8445/.well-known/est/simpleenroll
```

### IQE Configuration Requirements

**Provide IQE team with:**

```yaml
# IQE EST Configuration
est_server:
  url: "https://10.42.56.101:8445/.well-known/est"

  tls:
    # CA certificate to verify EST server
    ca_cert: "/path/to/ca-cert.pem"

    # RA certificate for authentication
    client_cert: "/path/to/iqe-ra-cert.pem"
    client_key: "/path/to/iqe-ra-key.pem"

    # Skip hostname verification if using IP
    verify_hostname: false

  authentication:
    method: "client_certificate"
    # No username/password needed - cert-based auth only

# When IQE requests certificate for pump:
request:
  subject:
    CN: "PUMP_SERIAL_NUMBER"  # e.g., NPPBBB4
    O: "Ferrari Medical Inc"

  key_type: "RSA"
  key_size: 2048
```

### Test IQE → EST Integration

**IQE team should test:**

```bash
# 1. Fetch CA certificates
curl -k --cert iqe-ra-cert.pem --key iqe-ra-key.pem \
  https://10.42.56.101:8445/.well-known/est/cacerts

# Expected: base64-encoded PKCS#7 certificate chain

# 2. Request certificate for pump
# (IQE generates CSR internally, this is example)
openssl req -new -newkey rsa:2048 -nodes \
  -keyout pump-key.pem -out pump-csr.der -outform DER \
  -subj "/CN=NPPBBB4/O=Ferrari Medical Inc"

# Submit CSR to EST
curl -k --cert iqe-ra-cert.pem --key iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @pump-csr.der \
  https://10.42.56.101:8445/.well-known/est/simpleenroll

# Expected: base64-encoded PKCS#7 certificate response
```

---

## Part 4: Cisco WLC Configuration

Follow the detailed guide in `CISCO_WLC_CONFIG.md`, but quick summary:

### Step 1: Add RADIUS Server to WLC

**Via Web Interface:**
- Navigate to: `Security → RADIUS → Authentication Servers`
- Click "New"
- Fill in:
  ```
  Server IP:      10.42.56.101
  Port:           1812
  Shared Secret:  <same as in clients.conf>
  Status:         Enabled
  ```

**Via CLI:**
```bash
ssh admin@YOUR_WLC_IP
config radius auth add 1 10.42.56.101 1812 ascii YOUR_SHARED_SECRET
config radius auth enable 1
```

### Step 2: Configure WLAN for 802.1X

**Via Web Interface:**
- Navigate to: `WLANs → Ferrari2 (or your SSID)`
- Security Tab → Layer 2:
  ```
  Layer 2 Security:  WPA+WPA2
  WPA2 Policy:       ✓ Enabled
  Encryption:        AES
  Auth Key Mgmt:     ✓ 802.1X (uncheck PSK)
  ```
- Security Tab → AAA Servers:
  ```
  Authentication Server: 10.42.56.101:1812
  Shared Secret:         YOUR_SHARED_SECRET
  ```

### Step 3: Test WLC → RADIUS

**Via WLC CLI:**
```bash
ping 10.42.56.101
# Should succeed

show radius auth summary
# Should show 10.42.56.101 as Enabled
```

---

## Part 5: End-to-End Testing

### Test 1: IQE Requests Certificate

```bash
# On IQE machine (using test script)
python test_iqe_enrollment.py

# Expected flow:
# IQE → Nginx (8445) → EST Server (8000)
# EST validates RA cert → Issues pump certificate → Returns PKCS#7
```

### Test 2: Pump Connects to WiFi

**Pump wpa_supplicant.conf should have:**
```conf
network={
    ssid="Ferrari2"
    key_mgmt=WPA-EAP
    eap=TLS
    identity="NPPBBB4"
    ca_cert="/path/to/ca-cert.pem"
    client_cert="/path/to/pump-cert.pem"
    private_key="/path/to/pump-key.pem"
}
```

**Expected flow:**
1. Pump attempts to connect to Ferrari2 SSID
2. WLC challenges pump for certificate
3. Pump sends certificate (issued by EST)
4. WLC forwards to FreeRADIUS (10.42.56.101:1812)
5. FreeRADIUS validates cert against EST CA
6. FreeRADIUS sends Access-Accept
7. WLC grants network access to pump

**Monitor on Ubuntu VM:**
```bash
# Watch RADIUS logs
docker logs -f freeradius-server

# Look for:
# (0) Received Access-Request Id <id> from 10.42.56.50:xxxxx
# (0) eap_tls: TLS - User authenticated successfully
# (0) Sent Access-Accept Id <id>
```

**Monitor on WLC:**
```bash
# Via WLC CLI
debug client <pump-mac-address>
show client detail <pump-mac-address>

# Via Web Interface
Monitor → Clients → Look for pump MAC
```

### Test 3: Verify Full Stack Health

```bash
# Check all containers running
docker-compose -f docker-compose-full.yml ps

# Check disk space
df -h

# Check logs for errors
docker-compose -f docker-compose-full.yml logs --tail=100

# Test EST health
curl -k https://10.42.56.101:8445/health

# Test RADIUS
docker exec freeradius-server radtest test test localhost 0 testing123
```

---

## Part 6: Troubleshooting

### Issue: WLC Can't Reach RADIUS

```bash
# Check firewall on Ubuntu
sudo ufw status
sudo ufw allow from WLC_IP to any port 1812 proto udp

# Check RADIUS is listening on all interfaces
docker exec freeradius-server netstat -ulnp | grep 1812

# Ping from WLC to Ubuntu VM
# (from WLC): ping 10.42.56.101
```

### Issue: RADIUS Rejects Pump Certificate

```bash
# Check RADIUS logs
docker logs freeradius-server | grep -i reject

# Common causes:
# 1. EST CA not trusted by RADIUS
docker exec freeradius-server cat /etc/freeradius/mods-enabled/eap | grep ca_file

# 2. Certificate expired
openssl x509 -in pump-cert.pem -noout -dates

# 3. Wrong CA used to sign pump cert
openssl verify -CAfile certs/ca-cert.pem pump-cert.pem
```

### Issue: IQE Can't Connect to EST

```bash
# Check nginx logs
docker logs est-nginx | tail -50

# Test with curl
curl -k --cert certs/iqe-ra-cert.pem --key certs/iqe-ra-key.pem \
  https://10.42.56.101:8445/health

# Check certificate matches
openssl x509 -in certs/iqe-ra-cert.pem -noout -subject -issuer
```

---

## Part 7: Production Hardening

### Update Secrets
```bash
# Generate strong RADIUS secret
openssl rand -base64 32

# Update radius/clients.conf
nano radius/clients.conf

# Update WLC with same secret
# Security → RADIUS → Authentication Servers → Edit Server
```

### Restrict RADIUS Client IPs
```bash
# Edit radius/clients.conf
nano radius/clients.conf

# Change from:
ipaddr = 0.0.0.0/0

# To specific WLC IP:
ipaddr = 10.42.56.50/32
```

### Enable Log Rotation
```bash
# Create logrotate config
sudo nano /etc/logrotate.d/docker-est

# Add:
/var/lib/docker/volumes/python-est_nginx_logs/_data/*.log
/var/lib/docker/volumes/python-est_radius_logs/_data/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### Backup Configuration
```bash
# Backup certificates and config
tar -czf est-backup-$(date +%Y%m%d).tar.gz \
  certs/ \
  radius/ \
  config-nginx.yaml \
  docker-compose-full.yml

# Store securely
```

---

## Summary of Components

| Component | Purpose | Port | Protocol |
|-----------|---------|------|----------|
| Python EST Server | Issue certificates to pumps (via IQE) | 8000 (internal) | HTTP |
| Nginx | TLS termination, RA cert validation | 8445 | HTTPS |
| FreeRADIUS | Validate pump certs for WiFi access | 1812, 1813 | UDP (RADIUS) |
| Cisco WLC | WiFi access point controller | N/A | N/A |
| IQE Gateway | Request certs on behalf of pumps | N/A | HTTPS client |
| Medical Pumps | End devices needing WiFi access | N/A | WPA2/WPA3 EAP-TLS |

---

## Quick Reference

**Restart services:**
```bash
docker-compose -f docker-compose-full.yml restart
```

**View logs:**
```bash
docker-compose -f docker-compose-full.yml logs -f [service-name]
```

**Stop all:**
```bash
docker-compose -f docker-compose-full.yml down
```

**Rebuild:**
```bash
docker-compose -f docker-compose-full.yml up -d --build
```

**Check RADIUS status:**
```bash
docker exec freeradius-server radiusd -X -l stdout 2>&1 | grep -i ready
```
