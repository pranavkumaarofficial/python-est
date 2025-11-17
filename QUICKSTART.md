# Quick Start - Same VM Deployment (Recommended)

Deploy both EST and RADIUS on the **same VM** (10.42.56.101) as completely decoupled services.

---

## Why Same VM Works

- ✅ **Different compose files** → Independent deployments
- ✅ **Different ports** → EST (8445/tcp), RADIUS (1812/udp)
- ✅ **No shared networks** → Truly decoupled
- ✅ **Independent restarts** → Restart one without affecting the other
- ✅ **Easy to migrate later** → Move RADIUS to different VM anytime

---

## Prerequisites

You already have EST server running! We'll just add RADIUS alongside it.

**Current Setup:**
```
VM: 10.42.56.101
Running: docker-compose-nginx.yml (EST + Nginx)
Ports: 8445/tcp
```

**After Adding RADIUS:**
```
VM: 10.42.56.101
Running:
  - docker-compose-nginx.yml (EST + Nginx) ← NO CHANGES
  - docker-compose-radius.yml (RADIUS)     ← NEW
Ports: 8445/tcp, 1812/udp, 1813/udp
```

---

## Step 1: Your EST Server (Already Running)

**Nothing to change!** Your current setup continues as-is:

```bash
# Verify EST still running
docker-compose -f docker-compose-nginx.yml ps

# Test EST health
curl -k https://localhost:8445/health
# Expected: {"status":"healthy","service":"Python-EST Server"}
```

---

## Step 2: Add RADIUS Server (Same VM)

### 2.1 Generate RADIUS Server Certificates

```bash
cd ~/Desktop/python-est

# Generate RADIUS server's own certificates (local to this VM)
bash radius/generate_radius_certs.sh

# Verify
ls -la radius-server-certs/
# Expected: server.pem, server.key
```

### 2.2 Copy EST CA Certificate

Since we're on the **same VM**, just copy locally:

```bash
# Create directory for RADIUS CA certs
mkdir -p radius-certs

# Copy EST CA certificate locally
cp certs/ca-cert.pem radius-certs/

# Verify
cat radius-certs/ca-cert.pem
# Should show PEM certificate
```

### 2.3 Configure Cisco WLC Details

```bash
# Edit RADIUS clients configuration
nano radius/clients.conf
```

**Update with your WLC info:**
```conf
client cisco_wlc {
    ipaddr = 10.42.56.50        # CHANGE: Your actual WLC IP
    secret = PUT_STRONG_SECRET_HERE  # CHANGE: Use output from command below
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

### 2.4 Deploy RADIUS Server

```bash
# Deploy RADIUS (completely independent from EST)
docker-compose -f docker-compose-radius.yml up -d --build

# Watch logs
docker logs -f freeradius-server
# Press Ctrl+C to exit logs
```

### 2.5 Verify RADIUS Running

```bash
# Check both services running
docker ps

# Expected output:
# freeradius-server     Up      1812/udp, 1813/udp
# est-nginx             Up      8445/tcp
# python-est-server     Up

# Test RADIUS
docker exec -it freeradius-server radtest test test localhost 0 testing123
# Expected: Access-Reject (normal - user doesn't exist)
```

### 2.6 Verify Certificate Paths

```bash
# Check EST CA cert accessible to RADIUS
docker exec -it freeradius-server cat /etc/freeradius/certs/ca/ca-cert.pem

# Check RADIUS server cert accessible
docker exec -it freeradius-server cat /etc/freeradius/certs/server/server.pem

# Check EAP config points to correct paths
docker exec -it freeradius-server grep ca_file /etc/freeradius/mods-enabled/eap
# Expected: ca_file = /etc/freeradius/certs/ca/ca-cert.pem
```

### 2.7 Configure Firewall

```bash
# Allow RADIUS ports from WLC (replace WLC_IP with actual IP)
sudo ufw allow from WLC_IP to any port 1812 proto udp
sudo ufw allow from WLC_IP to any port 1813 proto udp

# Verify firewall rules
sudo ufw status
```

---

## Step 3: Configure Cisco WLC

### Via Web Interface

1. Login to WLC: `https://YOUR_WLC_IP`
2. Navigate: **Security → RADIUS → Authentication Servers**
3. Click **New**
4. Fill in:
   - **Server IP Address**: `10.42.56.101` (same VM as EST)
   - **Port**: `1812`
   - **Shared Secret**: Same as in `radius/clients.conf`
   - **Status**: Enabled
5. Click **Apply**
6. Navigate: **WLANs → Ferrari2**
7. **Security Tab → Layer 2:**
   - Layer 2 Security: `WPA+WPA2`
   - WPA2 Policy: ✓ Enabled
   - Encryption: `AES`
   - Auth Key Mgmt: ✓ **802.1X** (uncheck PSK)
8. **Security Tab → AAA Servers:**
   - Authentication Server: `10.42.56.101:1812`
9. Click **Apply**

### Via CLI

```bash
ssh admin@YOUR_WLC_IP

# Add RADIUS server (same IP as EST, different port)
config radius auth add 1 10.42.56.101 1812 ascii YOUR_SHARED_SECRET
config radius auth enable 1

# Verify
show radius auth summary
ping 10.42.56.101

# Test connectivity
show radius summary
```

---

## Step 4: Test Complete Independence

### Test 1: Restart RADIUS (EST unaffected)

```bash
# Restart RADIUS
docker-compose -f docker-compose-radius.yml restart

# Test EST still works (no downtime)
curl -k https://localhost:8445/health
# Expected: Success (EST unaffected)
```

### Test 2: Restart EST (RADIUS unaffected)

```bash
# Restart EST
docker-compose -f docker-compose-nginx.yml restart

# Test RADIUS still works (no downtime)
docker exec -it freeradius-server radtest test test localhost 0 testing123
# Expected: Access-Reject (RADIUS unaffected)
```

**This proves complete decoupling!** ✅

---

## Step 5: End-to-End Testing

### Test IQE → EST (Certificate Issuance)

```bash
# Generate test CSR
openssl req -new -newkey rsa:2048 -nodes \
  -keyout test-pump-key.pem \
  -out test-pump-csr.der -outform DER \
  -subj "/CN=TEST-PUMP-001/O=Ferrari Medical Inc"

# Submit to EST
curl -k \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @test-pump-csr.der \
  https://localhost:8445/.well-known/est/simpleenroll \
  -o test-pump-cert.p7

# Extract certificate
openssl pkcs7 -print_certs -in test-pump-cert.p7 -out test-pump-cert.pem

# Verify
openssl x509 -in test-pump-cert.pem -noout -subject
# Expected: subject=CN = TEST-PUMP-001, O = Ferrari Medical Inc
```

### Test Pump → WLC → RADIUS (WiFi Auth)

**Monitor RADIUS logs:**
```bash
# Watch RADIUS authentication attempts
docker logs -f freeradius-server
```

**On pump, configure wpa_supplicant.conf:**
```conf
network={
    ssid="Ferrari2"
    key_mgmt=WPA-EAP
    eap=TLS
    identity="TEST-PUMP-001"
    ca_cert="/etc/cert/ca-cert.pem"
    client_cert="/etc/cert/test-pump-cert.pem"
    private_key="/etc/cert/test-pump-key.pem"
}
```

**Connect pump to WiFi:**
```bash
# On pump
wpa_cli reconfigure
wpa_cli status
# Expected: wpa_state=COMPLETED
```

**Check RADIUS logs (on VM):**
```
Expected output:
(0) Received Access-Request from 10.42.56.50 (WLC IP)
(0) eap_tls: TLS - User authenticated successfully
(0) Sent Access-Accept
```

---

## Quick Reference Commands

### View Logs

```bash
# EST server logs
docker-compose -f docker-compose-nginx.yml logs -f

# RADIUS logs
docker logs -f freeradius-server
```

### Restart Services

```bash
# Restart EST only
docker-compose -f docker-compose-nginx.yml restart

# Restart RADIUS only
docker-compose -f docker-compose-radius.yml restart

# Restart both (independent restarts)
docker-compose -f docker-compose-nginx.yml restart
docker-compose -f docker-compose-radius.yml restart
```

### Stop Services

```bash
# Stop EST only
docker-compose -f docker-compose-nginx.yml down

# Stop RADIUS only
docker-compose -f docker-compose-radius.yml down

# Stop both
docker-compose -f docker-compose-nginx.yml down
docker-compose -f docker-compose-radius.yml down
```

### Check Status

```bash
# Check all containers
docker ps

# Check EST health
curl -k https://localhost:8445/health

# Check RADIUS health
docker exec -it freeradius-server radtest test test localhost 0 testing123
```

---

## Maintenance

### Update RADIUS Configuration

```bash
# Add new WLC client
nano radius/clients.conf
# Add new client block

# Restart RADIUS only
docker-compose -f docker-compose-radius.yml restart

# EST continues running (unaffected)
```

### Update EST Configuration

```bash
# Edit EST config
nano config-nginx.yaml

# Restart EST only
docker-compose -f docker-compose-nginx.yml restart

# RADIUS continues running (unaffected)
```

---

## Troubleshooting

### Issue: RADIUS can't find EST CA certificate

```bash
# Verify CA cert exists in radius-certs/
ls -la radius-certs/ca-cert.pem

# If missing, recopy from EST certs
cp certs/ca-cert.pem radius-certs/

# Restart RADIUS
docker-compose -f docker-compose-radius.yml restart
```

### Issue: WLC can't reach RADIUS

```bash
# Check RADIUS listening
docker exec -it freeradius-server netstat -ulnp | grep 1812

# Check firewall
sudo ufw status | grep 1812

# Allow WLC IP
sudo ufw allow from WLC_IP to any port 1812 proto udp
sudo ufw allow from WLC_IP to any port 1813 proto udp
```

### Issue: Shared secret mismatch

```bash
# Check RADIUS config
docker exec -it freeradius-server cat /etc/freeradius/clients.conf | grep secret

# Verify matches WLC configuration
# WLC Web: Security → RADIUS → Authentication Servers → Edit
# Secret must match EXACTLY (case-sensitive)
```

---

## Architecture Overview

```
┌────────────────────────────────────────────────────┐
│  VM: 10.42.56.101 (Ubuntu)                         │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────────────┐   ┌──────────────────┐      │
│  │  EST + Nginx     │   │  FreeRADIUS      │      │
│  │  Port: 8445/tcp  │   │  Port: 1812/udp  │      │
│  │                  │   │  Port: 1813/udp  │      │
│  │  compose:        │   │  compose:        │      │
│  │  nginx.yml       │   │  radius.yml      │      │
│  └────────┬─────────┘   └────────┬─────────┘      │
│           │                      │                │
└───────────┼──────────────────────┼────────────────┘
            │                      │
            │ HTTPS                │ RADIUS
            │ (8445)               │ (1812)
            │                      │
     ┌──────▼──────┐        ┌──────▼──────┐
     │             │        │             │
     │ IQE Gateway │        │ Cisco WLC   │
     │             │        │             │
     └─────────────┘        └──────┬──────┘
            │                      │
            │                      │ 802.1X
            │               ┌──────▼──────┐
            │               │   Medical   │
            └──────────────▶│   Pumps     │
              Requests cert └─────────────┘
```

**Key Points:**
- Same VM, different compose files
- No shared Docker networks
- Different ports (no conflicts)
- Completely independent operations
- Can migrate RADIUS to different VM later (just update WLC IP)

---

## Summary

✅ **EST server** - Already running, no changes needed
✅ **RADIUS server** - Added alongside EST on same VM
✅ **Completely decoupled** - Independent restarts, logs, configs
✅ **Same VM deployment** - Simple to manage, easy to migrate later
✅ **Production ready** - Both services running on 10.42.56.101

**Services Running:**
- `docker-compose-nginx.yml` → EST + Nginx (8445/tcp)
- `docker-compose-radius.yml` → FreeRADIUS (1812/udp, 1813/udp)

**Next Step:** Configure WLC to point to `10.42.56.101:1812` for RADIUS authentication!
