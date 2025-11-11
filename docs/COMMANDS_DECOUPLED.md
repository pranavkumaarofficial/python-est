# Deployment Commands - Decoupled EST + FreeRADIUS

## Quick Start - Separate VMs (Recommended for Production)

This is the **recommended architecture** for production deployments where EST and RADIUS run on completely independent VMs.

---

## Part 1: EST Server Deployment (VM1)

### VM1 Info
- **IP Address**: 10.42.56.101
- **Purpose**: Certificate issuance via EST protocol
- **Clients**: IQE Gateway only
- **Ports**: 8445/tcp (HTTPS)

### Commands

```bash
# ============================================
# EST SERVER - VM1 (10.42.56.101)
# ============================================

# 1. Clone repository
cd ~/Desktop
git clone <repo-url> python-est
cd python-est
git checkout deploy_v1

# 2. Generate EST certificates
python generate_certificates_python.py
python generate_ra_certificate.py

# 3. Verify certificates
ls -la certs/
# Expected: ca-cert.pem, ca-key.pem, iqe-ra-cert.pem, iqe-ra-key.pem, server.pem, server.key

# 4. Deploy EST server (EST-only, NO RADIUS)
docker-compose -f docker-compose-nginx.yml up -d --build

# 5. Verify deployment
docker-compose -f docker-compose-nginx.yml ps
curl http://localhost:8000/health
curl -k https://localhost:8445/health

# 6. Test RA authentication
curl -k --cert certs/iqe-ra-cert.pem --key certs/iqe-ra-key.pem \
  https://localhost:8445/.well-known/est/cacerts

# 7. Configure firewall (replace IQE_IP)
sudo ufw allow from IQE_IP to any port 8445 proto tcp
sudo ufw allow 22/tcp
sudo ufw enable

# 8. Backup CA private key (CRITICAL!)
tar -czf est-ca-backup-$(date +%Y%m%d).tar.gz certs/ca-key.pem certs/ca-cert.pem
# Move to secure offline storage!

# DONE - EST server ready for IQE integration
```

---

## Part 2: RADIUS Server Deployment (VM2)

### VM2 Info
- **IP Address**: 10.42.56.102 (can be different VM)
- **Purpose**: WiFi authentication (802.1X) for medical pumps
- **Clients**: Cisco WLC only
- **Ports**: 1812/udp, 1813/udp (RADIUS)

### Commands

```bash
# ============================================
# RADIUS SERVER - VM2 (10.42.56.102)
# ============================================

# 1. Clone repository
cd ~/Desktop
git clone <repo-url> python-est
cd python-est
git checkout deploy_v1

# 2. Generate RADIUS server certificates (local to this VM)
bash radius/generate_radius_certs.sh

# 3. Copy EST CA certificate from EST VM (ONE-TIME operation)
mkdir -p radius-certs
scp user@10.42.56.101:/home/user/Desktop/python-est/certs/ca-cert.pem radius-certs/

# 4. Configure Cisco WLC details
nano radius/clients.conf
# Update:
#   ipaddr = YOUR_WLC_IP       (e.g., 10.42.56.50)
#   secret = STRONG_SECRET     (use: openssl rand -base64 32)

# 5. Deploy RADIUS server (RADIUS-only, NO EST)
docker-compose -f docker-compose-radius.yml up -d --build

# 6. Verify deployment
docker ps | grep freeradius
docker logs freeradius-server

# 7. Test RADIUS functionality
docker exec -it freeradius-server radtest test test localhost 0 testing123
# Expected: Access-Reject (normal - user doesn't exist)

# 8. Verify certificates accessible
docker exec -it freeradius-server cat /etc/freeradius/certs/ca/ca-cert.pem
docker exec -it freeradius-server cat /etc/freeradius/certs/server/server.pem

# 9. Configure firewall (replace WLC_IP)
sudo ufw allow from WLC_IP to any port 1812 proto udp
sudo ufw allow from WLC_IP to any port 1813 proto udp
sudo ufw allow 22/tcp
sudo ufw enable

# DONE - RADIUS server ready for WLC integration
```

---

## Part 3: Cisco WLC Configuration

```bash
# ============================================
# CISCO WLC CONFIGURATION
# ============================================

# Method 1: Via WLC Web Interface
# 1. Login to WLC: https://WLC_IP
# 2. Navigate: Security → RADIUS → Authentication Servers
# 3. Click "New" and add:
#      Server IP: 10.42.56.102
#      Port: 1812
#      Shared Secret: <same as radius/clients.conf>
#      Status: Enabled
# 4. Navigate: WLANs → Ferrari2
# 5. Security Tab → Layer 2:
#      Layer 2 Security: WPA+WPA2
#      WPA2 Policy: Enabled
#      Encryption: AES
#      Auth Key Mgmt: 802.1X (uncheck PSK)
# 6. Security Tab → AAA Servers:
#      Authentication Server: 10.42.56.102:1812
# 7. Apply

# Method 2: Via WLC CLI
ssh admin@WLC_IP

# Add RADIUS server
config radius auth add 1 10.42.56.102 1812 ascii YOUR_SHARED_SECRET
config radius auth enable 1

# Verify
show radius auth summary
ping 10.42.56.102
```

---

## Part 4: IQE Integration

### Files to Provide to IQE Team

**On EST VM (10.42.56.101):**

```bash
# Location of files for IQE
ls -la certs/iqe-ra-cert.pem    # RA certificate
ls -la certs/iqe-ra-key.pem     # RA private key
ls -la certs/ca-cert.pem        # CA certificate
```

### IQE Configuration

```yaml
# IQE EST Configuration (provide to IQE team)
est_server:
  url: "https://10.42.56.101:8445/.well-known/est"

  tls:
    ca_cert: "/path/to/ca-cert.pem"
    client_cert: "/path/to/iqe-ra-cert.pem"
    client_key: "/path/to/iqe-ra-key.pem"
    verify_hostname: false

  authentication:
    method: "client_certificate"
```

### Test IQE → EST Flow

**On IQE machine or EST VM:**

```bash
# Generate test CSR for pump
openssl req -new -newkey rsa:2048 -nodes \
  -keyout test-pump-key.pem \
  -out test-pump-csr.der -outform DER \
  -subj "/CN=TEST-PUMP-001/O=Ferrari Medical Inc"

# Submit to EST server
curl -k \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @test-pump-csr.der \
  https://10.42.56.101:8445/.well-known/est/simpleenroll \
  -o test-pump-cert.p7

# Extract certificate
openssl pkcs7 -print_certs -in test-pump-cert.p7 -out test-pump-cert.pem

# Verify
openssl x509 -in test-pump-cert.pem -noout -text | grep Subject
# Expected: CN = TEST-PUMP-001
```

---

## Part 5: Testing Complete Flow

### Test 1: EST Independence

```bash
# On RADIUS VM - stop RADIUS
docker-compose -f docker-compose-radius.yml down

# On EST VM - verify EST still works
curl -k https://10.42.56.101:8445/health
# Expected: Success (EST independent of RADIUS)

# On RADIUS VM - restart RADIUS
docker-compose -f docker-compose-radius.yml up -d
```

### Test 2: RADIUS Independence

```bash
# On EST VM - stop EST
docker-compose -f docker-compose-nginx.yml down

# On RADIUS VM - verify RADIUS still works
docker exec -it freeradius-server radtest test test localhost 0 testing123
# Expected: Access-Reject (RADIUS independent of EST)

# On EST VM - restart EST
docker-compose -f docker-compose-nginx.yml up -d --build
```

### Test 3: End-to-End Pump Authentication

**Configure pump wpa_supplicant.conf:**

```conf
network={
    ssid="Ferrari2"
    key_mgmt=WPA-EAP
    eap=TLS
    identity="TEST-PUMP-001"
    ca_cert="/etc/cert/ca-cert.pem"           # From EST VM
    client_cert="/etc/cert/test-pump-cert.pem" # From EST server
    private_key="/etc/cert/test-pump-key.pem"  # Generated with CSR
}
```

**Monitor RADIUS authentication:**

```bash
# On RADIUS VM - watch logs
docker logs -f freeradius-server

# On pump - connect to WiFi
wpa_cli reconfigure

# Expected in RADIUS logs:
# (0) Received Access-Request from 10.42.56.50 (WLC IP)
# (0) eap_tls: TLS - User authenticated successfully
# (0) Sent Access-Accept
```

---

## Part 6: Maintenance Commands

### EST VM Operations

```bash
# View logs
docker-compose -f docker-compose-nginx.yml logs -f

# Restart services
docker-compose -f docker-compose-nginx.yml restart

# Stop services
docker-compose -f docker-compose-nginx.yml down

# Update and rebuild
git pull origin deploy_v1
docker-compose -f docker-compose-nginx.yml up -d --build

# Check certificate expiration
openssl x509 -in certs/ca-cert.pem -noout -enddate
```

### RADIUS VM Operations

```bash
# View logs
docker logs -f freeradius-server

# Restart service
docker-compose -f docker-compose-radius.yml restart

# Stop service
docker-compose -f docker-compose-radius.yml down

# Update and rebuild
git pull origin deploy_v1
docker-compose -f docker-compose-radius.yml up -d --build

# Add new WLC client
nano radius/clients.conf  # Add new client block
docker-compose -f docker-compose-radius.yml restart
```

---

## Part 7: Troubleshooting

### Issue: IQE can't reach EST

```bash
# On EST VM
netstat -tlnp | grep 8445
sudo ufw status | grep 8445
docker-compose -f docker-compose-nginx.yml logs nginx

# Allow IQE IP
sudo ufw allow from IQE_IP to any port 8445 proto tcp
```

### Issue: WLC can't reach RADIUS

```bash
# On RADIUS VM
docker exec -it freeradius-server netstat -ulnp | grep 1812
sudo ufw status | grep 1812
docker logs freeradius-server | grep -i error

# Allow WLC IP
sudo ufw allow from WLC_IP to any port 1812 proto udp
sudo ufw allow from WLC_IP to any port 1813 proto udp
```

### Issue: RADIUS rejects pump certificate

```bash
# On RADIUS VM - verify EST CA certificate
docker exec -it freeradius-server cat /etc/freeradius/certs/ca/ca-cert.pem

# Compare with EST VM CA certificate
ssh user@10.42.56.101 "cat ~/Desktop/python-est/certs/ca-cert.pem"

# If different, recopy
scp user@10.42.56.101:~/Desktop/python-est/certs/ca-cert.pem radius-certs/
docker-compose -f docker-compose-radius.yml restart
```

### Issue: Shared secret mismatch

```bash
# On RADIUS VM - check configured secret
docker exec -it freeradius-server cat /etc/freeradius/clients.conf | grep secret

# On WLC - verify same secret
# Security → RADIUS → Authentication Servers → Edit
# Must match exactly (case-sensitive)
```

---

## Part 8: Migration Scenarios

### Move RADIUS to Different VM

**Scenario**: Move RADIUS from VM2 (10.42.56.102) to VM3 (10.42.56.103)

```bash
# ============================================
# NEW RADIUS VM - VM3 (10.42.56.103)
# ============================================

# 1. Clone repo on new VM
cd ~/Desktop
git clone <repo-url> python-est
cd python-est
git checkout deploy_v1

# 2. Generate RADIUS server certs
bash radius/generate_radius_certs.sh

# 3. Copy EST CA cert (from EST VM, NOT old RADIUS VM)
mkdir -p radius-certs
scp user@10.42.56.101:/home/user/Desktop/python-est/certs/ca-cert.pem radius-certs/

# 4. Copy RADIUS client configuration from old VM
scp user@10.42.56.102:/home/user/Desktop/python-est/radius/clients.conf radius/

# 5. Deploy RADIUS
docker-compose -f docker-compose-radius.yml up -d --build

# 6. Configure firewall
sudo ufw allow from WLC_IP to any port 1812 proto udp
sudo ufw allow from WLC_IP to any port 1813 proto udp
sudo ufw enable

# 7. Update WLC to point to new RADIUS server
# WLC Web: Security → RADIUS → Authentication Servers
# Change IP from 10.42.56.102 to 10.42.56.103

# 8. Test with one pump

# 9. Shutdown old RADIUS VM (10.42.56.102)
# On old VM:
docker-compose -f docker-compose-radius.yml down

# IMPORTANT: EST VM (10.42.56.101) completely unaffected!
```

---

## Part 9: Security Hardening

### Generate Strong Secrets

```bash
# RADIUS shared secret (32+ characters)
openssl rand -base64 32

# Copy output and use in:
# - radius/clients.conf (secret field)
# - WLC RADIUS configuration
```

### Restrict Network Access

```bash
# EST VM - only allow IQE
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow from IQE_IP to any port 8445 proto tcp
sudo ufw enable

# RADIUS VM - only allow WLC
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow from WLC_IP to any port 1812 proto udp
sudo ufw allow from WLC_IP to any port 1813 proto udp
sudo ufw enable
```

### Backup Critical Data

```bash
# EST VM - backup CA private key
tar -czf est-ca-backup-$(date +%Y%m%d).tar.gz \
  certs/ca-key.pem \
  certs/ca-cert.pem \
  certs/iqe-ra-cert.pem \
  certs/iqe-ra-key.pem \
  config-nginx.yaml
# Store in secure offline location!

# RADIUS VM - backup configuration
tar -czf radius-config-backup-$(date +%Y%m%d).tar.gz \
  radius/clients.conf \
  radius/eap \
  radius/radiusd.conf \
  radius-certs/ca-cert.pem
```

---

## Summary

### Decoupled Architecture Benefits

✅ **Complete independence** - EST and RADIUS on separate VMs, no shared networks
✅ **Easy migration** - Move RADIUS to different VM without touching EST
✅ **Independent scaling** - Scale EST and RADIUS separately based on load
✅ **Isolated failures** - EST failure doesn't affect RADIUS (and vice versa)
✅ **Security separation** - CA private key only on EST VM, RADIUS has public cert only
✅ **Flexible updates** - Update, restart, or rebuild either service independently

### Deployment Overview

| VM | IP | Service | Compose File | Purpose |
|----|-----|---------|--------------|---------|
| **VM1** | 10.42.56.101 | EST + Nginx | docker-compose-nginx.yml | Certificate issuance |
| **VM2** | 10.42.56.102 | FreeRADIUS | docker-compose-radius.yml | WiFi authentication |

### Key Files

**EST VM:**
- `docker-compose-nginx.yml` - EST deployment (NO RADIUS)
- `certs/ca-cert.pem` - CA certificate (copy to RADIUS VM once)
- `certs/ca-key.pem` - CA private key (**CRITICAL - backup securely**)

**RADIUS VM:**
- `docker-compose-radius.yml` - RADIUS deployment (NO EST)
- `radius-certs/ca-cert.pem` - EST CA certificate (copied from EST VM)
- `radius-server-certs/` - RADIUS server certificates (generated locally)

### One-Time Setup

1. **EST VM**: Deploy EST, generate certificates, backup CA key
2. **RADIUS VM**: Deploy RADIUS, copy CA cert from EST VM, configure WLC
3. **WLC**: Point to RADIUS VM, configure WLAN for 802.1X
4. **IQE**: Configure with EST endpoint and RA certificates

After setup, both VMs operate **completely independently**!
