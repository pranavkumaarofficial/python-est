# Decoupled Architecture - EST + FreeRADIUS

## Overview

This architecture **completely decouples** EST server and FreeRADIUS server into separate deployments that can run on different VMs. This provides:

- **Scalability**: Each service can scale independently
- **Flexibility**: Move RADIUS to different VM anytime
- **Resilience**: EST failure doesn't affect RADIUS (and vice versa)
- **Security**: Minimize attack surface by separating certificate issuance from validation

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Network Topology                         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────┐          ┌──────────────────────────┐
│   VM 1: EST Server       │          │   VM 2: RADIUS Server    │
│   (10.42.56.101)         │          │   (10.42.56.102)         │
├──────────────────────────┤          ├──────────────────────────┤
│                          │          │                          │
│  ┌────────────────────┐  │          │  ┌────────────────────┐  │
│  │ Nginx (8445)       │  │          │  │ FreeRADIUS         │  │
│  │ - TLS termination  │  │          │  │ - Port 1812/udp    │  │
│  │ - RA cert check    │  │          │  │ - Port 1813/udp    │  │
│  └─────────┬──────────┘  │          │  │                    │  │
│            │             │          │  │ Uses:              │  │
│            ▼             │          │  │ - EST CA cert      │  │
│  ┌────────────────────┐  │          │  │   (copied once)    │  │
│  │ Python EST Server  │  │          │  │ - Own server cert  │  │
│  │ - Port 8000        │  │          │  │   (generated)      │  │
│  │ - Issues certs     │  │          │  └─────────┬──────────┘  │
│  └────────────────────┘  │          │            │             │
│                          │          │            │             │
│  Certificates:           │          │            │             │
│  ├─ ca-cert.pem         │          │            │             │
│  ├─ ca-key.pem          │          │            │             │
│  ├─ iqe-ra-cert.pem     │          │            │             │
│  ├─ iqe-ra-key.pem      │          │            │             │
│  ├─ server.pem          │          │            │             │
│  └─ server.key          │          │            │             │
└──────────┬───────────────┘          └────────────┬─────────────┘
           │                                       │
           │ HTTPS (8445)                          │ RADIUS (1812/udp)
           │ Client cert auth                      │ EAP-TLS
           │                                       │
    ┌──────▼──────┐                         ┌─────▼──────┐
    │             │                         │            │
    │ IQE Gateway │                         │ Cisco WLC  │
    │             │                         │            │
    └─────────────┘                         └──────┬─────┘
           │                                       │
           │                                       │ 802.1X EAP-TLS
           │                                       │
           │                                ┌──────▼──────┐
           │                                │             │
           │                                │   Medical   │
           └───────────────────────────────▶│   Pumps     │
             Requests cert on behalf of     │             │
             pumps (HTTPS POST)             └─────────────┘
                                              Uses cert from EST
```

---

## Key Principles

### 1. **Complete Decoupling**

- **EST VM** and **RADIUS VM** do NOT share Docker networks
- **No runtime dependencies** between services
- Can deploy, restart, or update either service independently
- Can move RADIUS to different VM without touching EST

### 2. **One-Time Certificate Transfer**

RADIUS only needs EST CA certificate **once** during initial setup:

```bash
# Copy from EST VM to RADIUS VM (one-time operation)
scp user@10.42.56.101:/path/to/python-est/certs/ca-cert.pem \
    user@10.42.56.102:/path/to/radius-certs/
```

After this, RADIUS VM is **completely independent**.

### 3. **Separation of Concerns**

| Service | Purpose | VM | Ports | Clients |
|---------|---------|-----|-------|---------|
| **EST Server** | Certificate **issuance** | VM1 (10.42.56.101) | 8445/tcp | IQE Gateway |
| **FreeRADIUS** | Certificate **validation** | VM2 (10.42.56.102) | 1812/udp, 1813/udp | Cisco WLC |

### 4. **Network Mode: Host**

RADIUS uses `network_mode: host` to:
- Bind directly to host's network interfaces
- Allow Cisco WLC (external device) to reach RADIUS
- Avoid Docker network NAT complexity
- Improve performance for UDP traffic

---

## Directory Structure

### EST VM (10.42.56.101)

```
python-est/
├── docker-compose-nginx.yml        # EST-only deployment (NO RADIUS)
├── Dockerfile
├── nginx/
│   └── nginx.conf
├── src/
│   └── python_est/
├── certs/                           # EST certificates
│   ├── ca-cert.pem                 ← Copy this to RADIUS VM
│   ├── ca-key.pem
│   ├── iqe-ra-cert.pem
│   ├── iqe-ra-key.pem
│   ├── server.pem
│   └── server.key
├── config-nginx.yaml
└── data/
```

**Deploy command:**
```bash
docker-compose -f docker-compose-nginx.yml up -d --build
```

### RADIUS VM (10.42.56.102)

```
python-est/                          # Same repo, different VM
├── docker-compose-radius.yml        # RADIUS-only deployment (NO EST)
├── Dockerfile.radius
├── radius/
│   ├── clients.conf                # Configure WLC IP here
│   ├── eap                         # Points to /etc/freeradius/certs/ca/
│   ├── radiusd.conf
│   └── generate_radius_certs.sh    # Generate RADIUS server certs
├── radius-certs/                    # CA certificates (copied from EST VM)
│   └── ca-cert.pem                 ← Copied from EST VM
└── radius-server-certs/             # RADIUS server's own certs (generated locally)
    ├── server.pem
    └── server.key
```

**Setup commands:**
```bash
# 1. Generate RADIUS server certificates
bash radius/generate_radius_certs.sh

# 2. Copy EST CA certificate from EST VM
mkdir -p radius-certs
scp user@10.42.56.101:/path/to/python-est/certs/ca-cert.pem radius-certs/

# 3. Configure WLC IP in clients.conf
nano radius/clients.conf

# 4. Deploy RADIUS
docker-compose -f docker-compose-radius.yml up -d --build
```

---

## Certificate Flow

### Certificate Issuance (EST VM)

```
IQE Gateway
    │
    │ HTTPS POST (with RA cert)
    ▼
Nginx (8445)
    │
    │ Validates RA cert
    │ Forwards to backend
    ▼
Python EST Server (8000)
    │
    │ Generates pump certificate
    │ Signs with ca-key.pem
    │ Returns PKCS#7
    ▼
IQE Gateway
    │
    │ Extracts certificate
    │ Installs on pump
    ▼
Medical Pump
```

### Certificate Validation (RADIUS VM)

```
Medical Pump
    │
    │ Connects to WiFi with certificate
    ▼
Cisco WLC
    │
    │ RADIUS Access-Request (EAP-TLS)
    ▼
FreeRADIUS (1812/udp)
    │
    │ Validates pump cert against ca-cert.pem
    │ Checks:
    │   - Signature valid?
    │   - Not expired?
    │   - Issued by trusted CA?
    ▼
    │ If valid → Access-Accept
    │ If invalid → Access-Reject
    ▼
Cisco WLC
    │
    │ Grants/denies network access
    ▼
Medical Pump (connected to WiFi)
```

**Key point**: RADIUS never talks to EST server. It only validates using the CA certificate.

---

## Security Considerations

### 1. **Principle of Least Privilege**

- **EST VM** has CA private key (`ca-key.pem`) - **CRITICAL ASSET**
- **RADIUS VM** only has CA public cert (`ca-cert.pem`) - **READ-ONLY**
- If RADIUS VM compromised, attacker **cannot** issue new certificates

### 2. **Network Isolation**

- EST server only accessible from IQE network
- RADIUS server only accessible from WLC
- Use firewall rules to enforce:

```bash
# On EST VM
sudo ufw allow from IQE_IP to any port 8445 proto tcp

# On RADIUS VM
sudo ufw allow from WLC_IP to any port 1812 proto udp
sudo ufw allow from WLC_IP to any port 1813 proto udp
```

### 3. **Certificate Rotation**

When EST CA certificate needs rotation:
1. Generate new CA cert on EST VM
2. Update EST server to use new CA
3. **Copy new ca-cert.pem to RADIUS VM**
4. Restart RADIUS container
5. Re-issue all pump certificates

### 4. **Monitoring**

Each VM should monitor independently:

**EST VM:**
- Nginx access logs (failed RA auth attempts)
- EST server logs (CSR validation failures)
- Certificate expiration alerts

**RADIUS VM:**
- RADIUS authentication logs (Access-Reject events)
- Failed EAP-TLS attempts
- Unusual traffic patterns from WLC

---

## Scalability

### Horizontal Scaling

**EST Server:**
- Add more EST VMs behind load balancer
- Share same CA key (secure storage required)
- IQE can distribute requests across EST instances

**RADIUS Server:**
- Add more RADIUS VMs
- Configure multiple RADIUS servers on WLC (failover)
- Each RADIUS VM gets copy of ca-cert.pem

### Vertical Scaling

**EST Server:**
- Increase EST container resources for more concurrent CSR signing
- Add nginx workers for more TLS termination capacity

**RADIUS Server:**
- Increase RADIUS container resources for more concurrent 802.1X authentications
- Configure RADIUS threading in radiusd.conf

---

## Disaster Recovery

### EST VM Failure

**Impact:**
- Cannot issue **new** certificates
- Existing pump certificates still work
- RADIUS validation continues normally

**Recovery:**
- Restore from backup (ca-cert.pem, ca-key.pem)
- Redeploy EST container
- Test with IQE

### RADIUS VM Failure

**Impact:**
- Pumps cannot connect to WiFi (802.1X fails)
- Certificate issuance via EST continues normally

**Recovery:**
- Deploy new RADIUS VM
- Copy ca-cert.pem from EST VM
- Generate new RADIUS server certs
- Update WLC with new RADIUS IP
- Test with one pump

### Complete Disaster (Both VMs Down)

**Prerequisites:**
- Secure backup of EST CA key (`ca-key.pem`) - **CRITICAL**
- Backup of EST CA cert (`ca-cert.pem`)
- Backup of configuration files

**Recovery:**
1. Deploy EST VM first (restore ca-key.pem, ca-cert.pem)
2. Test EST with IQE
3. Deploy RADIUS VM (copy ca-cert.pem from EST)
4. Test RADIUS with one pump

---

## Migration Path

### Moving RADIUS to Different VM

**Before:**
- RADIUS on VM2 (10.42.56.102)

**After:**
- RADIUS on VM3 (10.42.56.103)

**Steps:**
```bash
# 1. On new VM3, clone repo
git clone <repo-url>
cd python-est

# 2. Generate RADIUS server certs
bash radius/generate_radius_certs.sh

# 3. Copy EST CA cert from EST VM
mkdir -p radius-certs
scp user@10.42.56.101:/path/to/python-est/certs/ca-cert.pem radius-certs/

# 4. Configure WLC IP
nano radius/clients.conf

# 5. Deploy RADIUS on VM3
docker-compose -f docker-compose-radius.yml up -d --build

# 6. Update WLC to point to VM3 (10.42.56.103)
# Security → RADIUS → Authentication Servers → Edit

# 7. Test with one pump

# 8. Shutdown old RADIUS on VM2
# (on VM2): docker-compose -f docker-compose-radius.yml down
```

**No EST changes needed!** EST VM completely unaffected.

---

## Cost Optimization

### Shared VM (Development/Testing)

For testing, can deploy both on same VM using different compose files:

```bash
# On single VM (10.42.56.101)
docker-compose -f docker-compose-nginx.yml up -d      # EST
docker-compose -f docker-compose-radius.yml up -d     # RADIUS
```

**Still decoupled** - no shared networks, independent restarts.

### Production (Separate VMs)

- VM1: EST server (low traffic, IQE only)
- VM2: RADIUS server (high traffic, all pumps)

Allocate resources based on traffic patterns:
- EST: 2 vCPU, 4 GB RAM
- RADIUS: 4 vCPU, 8 GB RAM

---

## Comparison: Coupled vs Decoupled

| Aspect | Coupled (docker-compose-full.yml) | Decoupled (nginx + radius yml) |
|--------|-----------------------------------|--------------------------------|
| **Deployment** | Single VM, one command | Two VMs, independent commands |
| **Network** | Shared Docker network | Host network (RADIUS), Bridge (EST) |
| **Dependencies** | RADIUS depends on EST network | Zero runtime dependencies |
| **Scalability** | Scale both together | Scale independently |
| **Resilience** | Single point of failure | Independent failure domains |
| **Migration** | Must move both services | Move RADIUS without touching EST |
| **Maintenance** | Update both together | Update independently |
| **Security** | CA key and validation on same VM | CA key (EST VM) separate from validation (RADIUS VM) |
| **Best for** | Quick demos, dev testing | Production, large deployments |

---

## Recommendation

**Use decoupled architecture** (`docker-compose-nginx.yml` + `docker-compose-radius.yml`) for:
- ✅ Production deployments
- ✅ When you might move RADIUS later
- ✅ When services have different scaling needs
- ✅ When you want independent maintenance windows
- ✅ When security isolation is important

**Use coupled architecture** (`docker-compose-full.yml`) for:
- ⚠️  Quick demos only
- ⚠️  Development testing
- ⚠️  Resource-constrained environments (single VM)

**Your use case**: You want flexibility to move RADIUS later → **Use decoupled architecture**
