# Decoupled Deployment Guide - EST + FreeRADIUS

This guide covers deploying EST and FreeRADIUS on **separate VMs** for maximum flexibility and scalability.

---

## Prerequisites

- **VM 1** (EST Server): Ubuntu 20.04+, Docker, Docker Compose, Git
- **VM 2** (RADIUS Server): Ubuntu 20.04+, Docker, Docker Compose, Git
- SSH access between VMs (for certificate copy)
- Network connectivity:
  - IQE Gateway → EST VM (port 8445/tcp)
  - Cisco WLC → RADIUS VM (ports 1812/udp, 1813/udp)

---

## Part 1: Deploy EST Server (VM1 - 10.42.56.101)

### Step 1: Clone Repository

```bash
cd ~/Desktop
git clone <your-repo-url> python-est
cd python-est
git checkout deploy_v1
```

### Step 2: Generate EST Certificates

```bash
# Generate CA and server certificates
python generate_certificates_python.py

# Generate RA certificate for IQE authentication
python generate_ra_certificate.py

# Verify certificates generated
ls -la certs/
# Should show:
#   ca-cert.pem
#   ca-key.pem
#   iqe-ra-cert.pem
#   iqe-ra-key.pem
#   server.pem
#   server.key
```

### Step 3: Verify Configuration

```bash
# Check nginx mode config
cat config-nginx.yaml | grep -A 5 "server:"

# Should show:
#   host: "0.0.0.0"
#   port: 8000
#   nginx_mode: true
```

### Step 4: Deploy EST Server + Nginx

```bash
# Deploy using EST-only compose file (NO RADIUS)
docker-compose -f docker-compose-nginx.yml up -d --build

# Watch logs
docker-compose -f docker-compose-nginx.yml logs -f
```

### Step 5: Verify EST Server Running

```bash
# Check containers
docker-compose -f docker-compose-nginx.yml ps
# Expected:
#   python-est-server   Up
#   est-nginx           Up   0.0.0.0:8445->8445/tcp

# Test health endpoint
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"Python-EST Server"}

# Test via nginx
curl -k https://localhost:8445/health
# Expected: {"status":"healthy","service":"Python-EST Server"}
```

### Step 6: Test EST with RA Certificate

```bash
# Test CA certificates endpoint
curl -k --cert certs/iqe-ra-cert.pem --key certs/iqe-ra-key.pem \
  https://localhost:8445/.well-known/est/cacerts

# Expected: base64-encoded PKCS#7 response
```

### Step 7: Configure Firewall

```bash
# Allow EST port only from IQE network
# Replace IQE_NETWORK with actual IQE IP/subnet
sudo ufw allow from IQE_NETWORK to any port 8445 proto tcp

# Allow SSH (if not already allowed)
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable
sudo ufw status
```

### Step 8: Backup Critical Files

```bash
# Backup CA private key (CRITICAL - store securely!)
tar -czf est-ca-backup-$(date +%Y%m%d).tar.gz \
  certs/ca-key.pem \
  certs/ca-cert.pem \
  certs/iqe-ra-cert.pem \
  certs/iqe-ra-key.pem

# Move to secure location (e.g., encrypted USB drive, vault)
# DO NOT leave ca-key.pem exposed!
```

---

## Part 2: Deploy FreeRADIUS (VM2 - 10.42.56.102)

### Step 1: Clone Repository

```bash
cd ~/Desktop
git clone <your-repo-url> python-est
cd python-est
git checkout deploy_v1
```

### Step 2: Generate RADIUS Server Certificates

```bash
# Generate RADIUS server's own certificates (self-signed)
bash radius/generate_radius_certs.sh

# Verify
ls -la radius-server-certs/
# Should show:
#   server.pem
#   server.key
```

### Step 3: Copy EST CA Certificate from EST VM

```bash
# Create directory for CA certificates
mkdir -p radius-certs

# Copy from EST VM (replace user and IP)
scp user@10.42.56.101:/home/user/Desktop/python-est/certs/ca-cert.pem \
  radius-certs/

# Verify
cat radius-certs/ca-cert.pem
# Should show PEM certificate
```

### Step 4: Configure RADIUS Clients (WLC)

```bash
# Edit clients.conf
nano radius/clients.conf
```

Update with your WLC details:

```conf
client cisco_wlc {
    ipaddr = 10.42.56.50        # CHANGE: Your WLC IP
    secret = YourStrongSecret123 # CHANGE: Use strong secret (32+ chars)
    shortname = cisco-wlc
    nastype = cisco
    require_message_authenticator = yes
}
```

**Generate strong secret:**
```bash
openssl rand -base64 32
# Copy output and use as 'secret' above
```

### Step 5: Deploy FreeRADIUS

```bash
# Deploy using RADIUS-only compose file (NO EST)
docker-compose -f docker-compose-radius.yml up -d --build

# Watch logs
docker logs -f freeradius-server
```

### Step 6: Verify FreeRADIUS Running

```bash
# Check container
docker ps | grep freeradius
# Expected: freeradius-server   Up

# Test RADIUS with radtest
docker exec -it freeradius-server radtest test test localhost 0 testing123

# Expected: Access-Reject (normal - user doesn't exist)
# Important: No connection errors
```

### Step 7: Verify Certificate Paths

```bash
# Check EST CA certificate accessible
docker exec -it freeradius-server cat /etc/freeradius/certs/ca/ca-cert.pem

# Check RADIUS server certificate accessible
docker exec -it freeradius-server cat /etc/freeradius/certs/server/server.pem

# Check EAP configuration
docker exec -it freeradius-server cat /etc/freeradius/mods-enabled/eap | grep ca_file
# Expected: ca_file = /etc/freeradius/certs/ca/ca-cert.pem
```

### Step 8: Configure Firewall

```bash
# Allow RADIUS ports only from WLC
# Replace WLC_IP with actual Cisco WLC IP
sudo ufw allow from WLC_IP to any port 1812 proto udp
sudo ufw allow from WLC_IP to any port 1813 proto udp

# Allow SSH
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable
sudo ufw status
```

### Step 9: Test RADIUS Listening

```bash
# Check RADIUS is listening on all interfaces
docker exec -it freeradius-server netstat -ulnp | grep 1812

# Expected: 0.0.0.0:1812

# Test from host
nc -vuz localhost 1812
# Expected: Connection to localhost 1812 port [udp/*] succeeded!
```

---

## Part 3: Configure Cisco WLC

### Step 1: Add RADIUS Server

**Via Web Interface:**
1. Login to WLC: `https://WLC_IP`
2. Navigate: `Security → RADIUS → Authentication Servers`
3. Click **New**
4. Fill in:
   - **Server IP**: `10.42.56.102` (RADIUS VM)
   - **Port**: `1812`
   - **Shared Secret**: Same as in `radius/clients.conf`
   - **Status**: Enabled
5. Click **Apply**

**Via CLI:**
```bash
ssh admin@WLC_IP

config radius auth add 1 10.42.56.102 1812 ascii YourStrongSecret123
config radius auth enable 1
show radius auth summary
```

### Step 2: Configure WLAN for 802.1X

**Via Web Interface:**
1. Navigate: `WLANs → Ferrari2` (or your SSID)
2. **General Tab:**
   - Status: Enabled
   - SSID: Ferrari2
3. **Security Tab → Layer 2:**
   - Layer 2 Security: `WPA+WPA2`
   - WPA2 Policy: ✓ Enabled
   - Encryption: `AES`
   - Auth Key Mgmt: ✓ 802.1X (uncheck PSK)
4. **Security Tab → AAA Servers:**
   - Authentication Server: `10.42.56.102:1812`
   - Accounting Server: `10.42.56.102:1813` (optional)
5. Click **Apply**

### Step 3: Test WLC → RADIUS Connectivity

**From WLC CLI:**
```bash
ping 10.42.56.102
# Should succeed

show radius auth summary
# Should show 10.42.56.102 as Enabled
```

---

## Part 4: End-to-End Testing

### Test 1: IQE → EST (Certificate Issuance)

**On IQE machine or EST VM:**

```bash
# Generate test CSR
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

# Verify response
file test-pump-cert.p7
# Expected: test-pump-cert.p7: data

# Extract certificate from PKCS#7
openssl pkcs7 -print_certs -in test-pump-cert.p7 -out test-pump-cert.pem

# Verify certificate
openssl x509 -in test-pump-cert.pem -noout -text | grep -A 2 "Subject:"
# Expected: CN = TEST-PUMP-001, O = Ferrari Medical Inc
```

### Test 2: Pump → WLC → RADIUS (WiFi Authentication)

**Pump wpa_supplicant.conf:**

```conf
network={
    ssid="Ferrari2"
    key_mgmt=WPA-EAP
    eap=TLS
    identity="TEST-PUMP-001"

    # CA certificate - copied from EST VM
    ca_cert="/etc/cert/ca-cert.pem"

    # Client certificate - issued by EST server
    client_cert="/etc/cert/test-pump-cert.pem"

    # Private key - generated during CSR
    private_key="/etc/cert/test-pump-key.pem"
}
```

**On pump:**
```bash
# Restart wpa_supplicant
wpa_cli reconfigure

# Check status
wpa_cli status
# Expected: wpa_state=COMPLETED
```

**Monitor on RADIUS VM:**
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
# Via CLI
debug client <pump-mac-address>
show client detail <pump-mac-address>

# Look for:
# State: Associated
# Authentication: 802.1X
# Status: Authenticated
```

### Test 3: Verify Complete Isolation

**Test RADIUS independence:**

```bash
# On EST VM - stop EST server
cd ~/Desktop/python-est
docker-compose -f docker-compose-nginx.yml down

# On RADIUS VM - verify RADIUS still works
docker exec -it freeradius-server radtest test test localhost 0 testing123
# Expected: Access-Reject (RADIUS still running)

# Pump should still be able to re-authenticate to WiFi
# (using existing certificate, no new EST request)
```

**Test EST independence:**

```bash
# On RADIUS VM - stop RADIUS server
cd ~/Desktop/python-est
docker-compose -f docker-compose-radius.yml down

# On EST VM - verify EST still works
curl -k https://localhost:8445/health
# Expected: {"status":"healthy"}

# IQE should still be able to request new certificates
```

This confirms **complete decoupling** - services are independent!

---

## Part 5: Monitoring and Maintenance

### EST VM Monitoring

```bash
# Check EST server logs
docker-compose -f docker-compose-nginx.yml logs -f python-est-server

# Check nginx logs
docker-compose -f docker-compose-nginx.yml logs -f nginx

# Check disk space
df -h

# Check certificate expiration
openssl x509 -in certs/ca-cert.pem -noout -enddate
openssl x509 -in certs/server.pem -noout -enddate
```

### RADIUS VM Monitoring

```bash
# Check RADIUS logs
docker logs -f freeradius-server

# Check authentication attempts
docker exec -it freeradius-server tail -f /var/log/freeradius/radius.log

# Check container status
docker ps | grep freeradius

# Check port listening
netstat -ulnp | grep 1812
```

### Restart Services

**EST VM:**
```bash
cd ~/Desktop/python-est
docker-compose -f docker-compose-nginx.yml restart
```

**RADIUS VM:**
```bash
cd ~/Desktop/python-est
docker-compose -f docker-compose-radius.yml restart
```

### Update Configuration

**RADIUS (add new WLC):**

```bash
# Edit clients.conf
nano radius/clients.conf

# Add new WLC entry
client cisco_wlc_2 {
    ipaddr = 10.42.56.51
    secret = AnotherStrongSecret123
    shortname = cisco-wlc-2
    nastype = cisco
}

# Restart RADIUS
docker-compose -f docker-compose-radius.yml restart
```

**EST (update CA certificate):**

If CA certificate rotated:
```bash
# On EST VM - generate new CA
python generate_certificates_python.py

# Restart EST
docker-compose -f docker-compose-nginx.yml restart

# Copy new CA to RADIUS VM
scp certs/ca-cert.pem user@10.42.56.102:/home/user/Desktop/python-est/radius-certs/

# On RADIUS VM - restart to pick up new CA
docker-compose -f docker-compose-radius.yml restart
```

---

## Part 6: Troubleshooting

### Issue: IQE Cannot Connect to EST

**Symptoms:**
- `curl` to EST fails with connection timeout
- No logs in nginx

**Checks:**
```bash
# On EST VM - verify nginx listening
netstat -tlnp | grep 8445

# Check firewall
sudo ufw status | grep 8445

# Allow IQE IP
sudo ufw allow from IQE_IP to any port 8445 proto tcp

# Test locally
curl -k https://localhost:8445/health
```

### Issue: WLC Cannot Reach RADIUS

**Symptoms:**
- WLC shows RADIUS server as "Dead"
- Pumps cannot connect to WiFi

**Checks:**
```bash
# On RADIUS VM - verify listening
docker exec -it freeradius-server netstat -ulnp | grep 1812

# Check firewall
sudo ufw status | grep 1812

# Allow WLC IP
sudo ufw allow from WLC_IP to any port 1812 proto udp

# Test from WLC
ping 10.42.56.102
```

### Issue: RADIUS Rejects Pump Certificate

**Symptoms:**
- RADIUS logs show "Access-Reject"
- Pump cannot authenticate to WiFi

**Checks:**
```bash
# Check RADIUS has correct CA certificate
docker exec -it freeradius-server cat /etc/freeradius/certs/ca/ca-cert.pem

# Compare with EST CA certificate
diff <(ssh user@10.42.56.101 "cat /home/user/Desktop/python-est/certs/ca-cert.pem") \
     <(docker exec -it freeradius-server cat /etc/freeradius/certs/ca/ca-cert.pem)
# Expected: No differences

# Check pump certificate validity
openssl verify -CAfile radius-certs/ca-cert.pem pump-cert.pem
# Expected: pump-cert.pem: OK

# Check RADIUS EAP configuration
docker exec -it freeradius-server cat /etc/freeradius/mods-enabled/eap | grep ca_file
```

### Issue: Shared Secret Mismatch

**Symptoms:**
- RADIUS logs: "Ignoring request from unknown client"
- WLC shows authentication failures

**Fix:**
```bash
# On RADIUS VM - verify client configured
docker exec -it freeradius-server cat /etc/freeradius/clients.conf | grep -A 5 "cisco_wlc"

# Verify shared secret matches on WLC
# WLC: Security → RADIUS → Authentication Servers → Edit Server
# Must match 'secret' in clients.conf exactly
```

---

## Part 7: Production Hardening

### Security Checklist

**EST VM:**
- [ ] CA private key backed up securely (offline storage)
- [ ] Firewall restricts port 8445 to IQE IP only
- [ ] SSH key-based auth (no password)
- [ ] Regular security updates: `sudo apt update && sudo apt upgrade`
- [ ] Nginx logs rotated (logrotate configured)
- [ ] Non-root user for operations
- [ ] Docker daemon secured (TLS, user namespaces)

**RADIUS VM:**
- [ ] Firewall restricts RADIUS ports to WLC IP only
- [ ] Strong shared secret (32+ chars, random)
- [ ] SSH key-based auth (no password)
- [ ] Regular security updates
- [ ] RADIUS logs rotated
- [ ] Non-root user for operations
- [ ] Docker daemon secured

**Both VMs:**
- [ ] Monitoring alerts configured (disk, CPU, memory)
- [ ] Backup strategy tested (can restore from backup)
- [ ] Incident response plan documented
- [ ] Access logs reviewed regularly

### Performance Tuning

**EST VM (if high IQE traffic):**
```bash
# Increase nginx workers
nano nginx/nginx.conf
# worker_processes auto;

# Restart
docker-compose -f docker-compose-nginx.yml restart nginx
```

**RADIUS VM (if many pumps):**
```bash
# Increase RADIUS threads
nano radius/radiusd.conf
# thread pool {
#     start_servers = 5
#     max_servers = 32
# }

# Restart
docker-compose -f docker-compose-radius.yml restart
```

---

## Summary

### Architecture Benefits

✅ **Complete decoupling** - EST and RADIUS on separate VMs
✅ **Independent scaling** - Scale EST and RADIUS separately
✅ **Independent failure** - EST down doesn't affect RADIUS (and vice versa)
✅ **Easy migration** - Move RADIUS to different VM without touching EST
✅ **Security isolation** - CA private key only on EST VM
✅ **Flexibility** - Update, restart, or replace either service independently

### Deployment Summary

| VM | Service | Ports | Config File | Dependencies |
|----|---------|-------|-------------|--------------|
| **VM1** (10.42.56.101) | EST + Nginx | 8445/tcp | docker-compose-nginx.yml | None |
| **VM2** (10.42.56.102) | FreeRADIUS | 1812/udp, 1813/udp | docker-compose-radius.yml | EST CA cert (one-time copy) |

### Quick Reference Commands

**EST VM:**
```bash
# Deploy
docker-compose -f docker-compose-nginx.yml up -d --build

# Logs
docker-compose -f docker-compose-nginx.yml logs -f

# Restart
docker-compose -f docker-compose-nginx.yml restart

# Stop
docker-compose -f docker-compose-nginx.yml down
```

**RADIUS VM:**
```bash
# Deploy
docker-compose -f docker-compose-radius.yml up -d --build

# Logs
docker logs -f freeradius-server

# Restart
docker-compose -f docker-compose-radius.yml restart

# Stop
docker-compose -f docker-compose-radius.yml down
```
