# Cisco Wireless LAN Controller (WLC) Configuration Guide
## For EST + FreeRADIUS Integration

---

## Overview

This guide configures your Cisco WLC to:
1. Use your FreeRADIUS server for 802.1X authentication
2. Enable EAP-TLS (certificate-based) authentication
3. Allow pumps with EST-issued certificates to connect

---

## Prerequisites

- Cisco WLC access (admin credentials)
- WLC software version: 8.x or later
- FreeRADIUS server IP: `10.42.56.101`
- RADIUS shared secret: `testing123` (change in production!)

---

## Configuration Steps

### Step 1: Access WLC

#### Option A: Web Interface (Recommended)
```
1. Open browser: https://your-wlc-ip/
2. Login with admin credentials
3. Click "Advanced" in top-right corner
```

#### Option B: CLI (SSH)
```bash
ssh admin@your-wlc-ip
# Enter password
> enable
# Enter enable password
```

---

### Step 2: Add RADIUS Authentication Server

#### Via Web Interface:

**Path:** `Security → RADIUS → Authentication Servers`

1. Click **"New"** button

2. Fill in details:
   ```
   Server IP Address (IPv4): 10.42.56.101
   Shared Secret Format:    ASCII
   Shared Secret:           testing123
   Port Number:             1812
   Server Status:           Enabled
   Support for RFC 3576:    Disabled
   Server Timeout:          5
   Network User:            Disabled
   Management:              Disabled
   ```

3. Click **"Apply"**

#### Via CLI:
```
config radius auth add 1 10.42.56.101 1812 ascii testing123
config radius auth enable 1
```

---

### Step 3: Add RADIUS Accounting Server (Optional but Recommended)

#### Via Web Interface:

**Path:** `Security → RADIUS → Accounting Servers`

1. Click **"New"** button

2. Fill in details:
   ```
   Server IP Address (IPv4): 10.42.56.101
   Shared Secret Format:    ASCII
   Shared Secret:           testing123
   Port Number:             1813
   Server Status:           Enabled
   Server Timeout:          5
   ```

3. Click **"Apply"**

#### Via CLI:
```
config radius acct add 1 10.42.56.101 1813 ascii testing123
config radius acct enable 1
```

---

### Step 4: Verify RADIUS Server Configuration

#### Via Web Interface:

**Path:** `Security → RADIUS → Authentication Servers`

- Verify server appears in list
- Server Status: **Enabled**
- Click **"Ping"** to test connectivity

#### Via CLI:
```
show radius auth summary
# Expected output:
# Idx  Server Address    Port   ...  Status
# ---  ---------------   ----   ...  ------
#  1   10.42.56.101     1812   ...  Enabled

# Test connectivity
ping 10.42.56.101
```

---

### Step 5: Create/Edit WLAN for 802.1X

#### Via Web Interface:

**Path:** `WLANs → Click your WLAN (e.g., "Ferrari2") or create new**

#### General Tab:
```
Profile Name:   Ferrari2
SSID:           Ferrari2
Status:         Enabled
```

#### Security Tab → Layer 2:
```
Layer 2 Security:           WPA+WPA2
WPA+WPA2 Parameters:
  ☑ WPA2 Policy
  ☐ WPA Policy (optional - enable for older devices)

WPA2 Encryption:            AES
  ☑ AES
  ☐ TKIP (don't use - insecure)

Auth Key Mgmt:
  ☑ 802.1X
  ☐ PSK (disable - we're using certificates)
  ☐ CCKM
  ☐ FT 802.1X
```

#### Security Tab → AAA Servers:
```
Server 1:
  ☑ Enabled
  Server Type:            RADIUS
  Server IP:              10.42.56.101
  Auth Port:              1812
  Acct Port:              1813 (if accounting enabled)
  Shared Secret:          testing123

Fallback (optional):
  ☐ Use local authentication if RADIUS fails
```

#### Security Tab → RADIUS Attributes:
```
☑ Auth Server Retransmit Timeout:  5 seconds
☑ Interim Update:                   Disabled (or set to 600 seconds)
☑ Framed-MTU:                       1300
```

#### Advanced Tab:
```
Allow AAA Override:  Disabled (unless you need dynamic VLANs)
Network Admission Control: Disabled
Session Timeout:     1800 seconds (30 minutes)
Client Idle Timeout: 300 seconds (5 minutes)
```

#### Click **"Apply"** at the top

---

### Step 6: Verify WLAN Configuration

#### Via Web Interface:

**Path:** `WLANs → Your WLAN`

Verify:
- Security: **WPA2-Enterprise (802.1X)**
- Authentication Server: **10.42.56.101:1812**

#### Via CLI:
```
show wlan 1
# Or replace 1 with your WLAN ID

# Look for:
# Security Policies:
#   802.1X:          Enabled
#   Authentication:  Radius
#
# Radius Servers:
#   Authentication: 10.42.56.101:1812
```

---

### Step 7: Test RADIUS Connectivity from WLC

#### Via Web Interface:

**Path:** `Security → RADIUS → Authentication Servers`

1. Select your RADIUS server (10.42.56.101)
2. Click **"Ping Test"** or **"Radius Test"**
3. Expected result: **Success**

#### Via CLI:
```
# Ping test
ping 10.42.56.101

# RADIUS test (if available on your WLC version)
test radius auth 10.42.56.101 username testuser password testpass
# Expected: Access-Reject (but confirms RADIUS is responding)
```

---

### Step 8: Monitor Client Connections

#### Via Web Interface:

**Path:** `Monitor → Clients`

When a pump connects, you should see:
```
Client MAC:         00:04:f3:18:bb:b2
AP Name:            Your-AP-Name
WLAN:               Ferrari2
Status:             Associated
Auth Type:          802.1X
Protocol:           802.11n/ac/ax
RSSI:               -XX dBm
Security Policy:    WPA2
```

#### Path:** `Monitor → Logs → Message Logs`

Look for authentication events:
```
%LWAPP-3-RADIUS_AUTH: Successfully authenticated client
  MAC: 00:04:f3:18:bb:b2
  WLAN: Ferrari2
  RADIUS Server: 10.42.56.101
```

---

## Advanced WLC Configuration

### Enable RADIUS CoA (Change of Authorization)

Allows RADIUS to disconnect clients dynamically.

#### Via Web Interface:
**Path:** `Security → RADIUS → Authentication Servers → Select Server → RFC 3576**

```
Support for RFC 3576:  Enabled
```

### Configure RADIUS Request Timeout

If pumps take time to respond:

#### Via CLI:
```
config radius auth retransmit-timeout 1 10
# Server index 1, timeout 10 seconds
```

### Enable Debug Logs

For troubleshooting:

#### Via CLI:
```
debug client <mac-address>
debug aaa all enable
debug dot1x all enable

# View logs
show logging

# Disable when done
debug aaa all disable
debug dot1x all disable
```

---

## WLC Firewall / ACL Configuration

If WLC has firewall rules, ensure:

```
Allow UDP 1812 (RADIUS Auth) from WLC to 10.42.56.101
Allow UDP 1813 (RADIUS Acct) from WLC to 10.42.56.101
```

#### Via CLI:
```
# Check ACLs
show acl summary
show acl detailed <acl-name>

# Add rule if needed (varies by WLC model)
config acl rule add <acl-name> permit udp any 10.42.56.101 1812
config acl rule add <acl-name> permit udp any 10.42.56.101 1813
```

---

## Troubleshooting

### Issue: WLC Can't Reach RADIUS Server

**Symptoms:**
- "RADIUS server unreachable" in WLC logs
- Ping fails to 10.42.56.101

**Solutions:**
```bash
# On Ubuntu VM, check firewall
sudo ufw status
sudo ufw allow from <wlc-ip> to any port 1812 proto udp
sudo ufw allow from <wlc-ip> to any port 1813 proto udp

# Verify RADIUS is listening
docker exec freeradius-server netstat -ulnp | grep 1812

# Check docker port mapping
docker port freeradius-server
```

### Issue: Authentication Failing

**Symptoms:**
- Client shows "Authentication failed"
- WLC logs: "RADIUS Access-Reject"

**Solutions:**
```bash
# Check RADIUS logs
docker logs freeradius-server | grep -i reject

# Common causes:
# 1. Certificate not trusted (wrong CA)
# 2. Certificate expired
# 3. Client cert doesn't match identity
# 4. Shared secret mismatch
```

### Issue: Shared Secret Mismatch

**Symptoms:**
- WLC logs: "Bad Authenticator"
- RADIUS logs: "Ignoring request - shared secret mismatch"

**Solution:**
```bash
# Ensure secrets match exactly on both sides:
# WLC: Security → RADIUS → Auth Servers → Shared Secret
# RADIUS: radius/clients.conf → secret = "..."

# Secrets are case-sensitive!
```

---

## Production Hardening

### Change Default Shared Secret
```
# Generate strong secret
openssl rand -base64 32

# Update WLC and RADIUS with same secret
```

### Restrict RADIUS Clients by IP
In `radius/clients.conf`:
```
client cisco_wlc {
    ipaddr = 10.42.56.50/32  # Specific WLC IP only
    secret = <strong-secret>
}
```

### Enable RADIUS Accounting
For audit trail of all connections:
```
WLC → Security → AAA Servers → Accounting → Enable
```

### Set up Redundant RADIUS
Add second RADIUS server for high availability:
```
WLC → Security → RADIUS → Auth Servers → Add secondary server
```

---

## Quick Reference Commands

### WLC CLI Quick Commands
```bash
# Show RADIUS config
show radius summary
show radius auth

# Show WLAN config
show wlan summary
show wlan <wlan-id>

# Show connected clients
show client summary
show client detail <mac-address>

# Test connectivity
ping 10.42.56.101
test radius auth 10.42.56.101 username test password test

# Debug
debug client <mac>
debug aaa all enable
show logging
```

### Common WLC Info to Collect
```bash
# WLC details
show sysinfo
show boot
show inventory

# Network config
show interface summary
show network summary

# WLAN details
show wlan summary
show wlan <id>
```

---

## Configuration Checklist

- [ ] RADIUS server added (10.42.56.101:1812)
- [ ] Shared secret configured (both WLC and RADIUS match)
- [ ] RADIUS accounting server added (optional)
- [ ] WLAN security set to WPA2 + 802.1X
- [ ] WLAN AAA server points to RADIUS
- [ ] Ping test from WLC to RADIUS successful
- [ ] Firewall rules allow UDP 1812/1813
- [ ] Test client authentication
- [ ] Logs show successful auth
- [ ] Production secret configured (not "testing123")

---

## Support Contacts

- **Cisco WLC Support:** TAC support or internal network team
- **RADIUS Server:** Your team (logs via `docker logs freeradius-server`)
- **EST Server:** Your team (logs via `docker logs python-est-server`)

---

**Last Updated:** November 2025
**Tested on:** Cisco WLC 5520, 8.x firmware
