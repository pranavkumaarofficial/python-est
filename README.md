# Python EST Server + FreeRADIUS

Complete containerized solution for certificate-based WiFi authentication in medical device environments.

## 🎯 What This Does

- **EST Server**: Issues certificates to medical pumps (via IQE Gateway)
- **FreeRADIUS**: Validates pump certificates for WiFi access (802.1X EAP-TLS)
- **Completely Decoupled**: Independent services that can run on same or different VMs

## 🚀 Quick Start (Same VM - Recommended)

### Prerequisites
- Ubuntu 20.04+ with Docker & Docker Compose
- Current EST server already running? → **No changes needed!**

### Add RADIUS Server (5 minutes)

```bash
cd ~/Desktop/python-est

# 1. Generate RADIUS certificates
bash radius/generate_radius_certs.sh

# 2. Copy EST CA certificate (same VM)
mkdir -p radius-certs
cp certs/ca-cert.pem radius-certs/

# 3. Configure WLC IP and secret
nano radius/clients.conf
# Update: ipaddr and secret (generate: openssl rand -base64 32)

# 4. Deploy RADIUS
docker-compose -f docker-compose-radius.yml up -d --build

# 5. Verify
docker ps
# Should show: freeradius-server, est-nginx, python-est-server
```

**Done!** Both services running independently on same VM.

See **[QUICKSTART.md](QUICKSTART.md)** for complete setup guide.

---

## 📁 Directory Structure

```
python-est/
├── QUICKSTART.md              ← Start here (same-VM deployment)
├── README.md                  ← This file
│
├── docker-compose-nginx.yml   ← EST server deployment
├── docker-compose-radius.yml  ← RADIUS server deployment (NEW)
├── docker-compose-full.yml    ← Both together (legacy, not recommended)
│
├── docker/
│   ├── Dockerfile             ← EST server container
│   ├── Dockerfile.radius      ← RADIUS server container
│   └── entrypoint.sh          ← EST startup script
│
├── scripts/
│   ├── generate_certificates_python.py  ← Generate EST CA & server certs
│   ├── generate_ra_certificate.py       ← Generate IQE RA certificate
│   ├── create_iqe_user.py               ← Create SRP users (optional)
│   └── test_ra_auth_windows.py          ← Test RA authentication
│
├── radius/
│   ├── generate_radius_certs.sh  ← Generate RADIUS server certs
│   ├── clients.conf              ← Configure WLC IP & secret
│   ├── eap                       ← EAP-TLS configuration
│   └── radiusd.conf              ← RADIUS server config
│
├── certs/                     ← EST certificates (auto-generated)
│   ├── ca-cert.pem            ← CA certificate (copy to RADIUS)
│   ├── ca-key.pem             ← CA private key (CRITICAL - backup!)
│   ├── iqe-ra-cert.pem        ← IQE RA certificate
│   └── server.pem             ← EST server certificate
│
├── radius-certs/              ← RADIUS CA certs (create & copy ca-cert.pem)
├── radius-server-certs/       ← RADIUS server certs (auto-generated)
│
├── nginx/
│   └── nginx.conf             ← TLS termination & RA cert validation
│
├── config-nginx.yaml          ← EST server config (nginx mode)
├── config-iqe.yaml            ← EST server config (standalone mode)
│
├── src/
│   └── python_est/            ← EST server implementation
│
└── docs/                      ← Detailed documentation
    ├── ARCHITECTURE_DECOUPLED.md    ← Architecture diagrams
    ├── DEPLOY_DECOUPLED.md          ← Multi-VM deployment
    ├── COMMANDS_DECOUPLED.md        ← All commands reference
    ├── CISCO_WLC_CONFIG.md          ← WLC configuration guide
    ├── DEPLOY_COMPLETE_STACK.md     ← Legacy full-stack guide
    └── COMMANDS.md                  ← Legacy commands
```

---

## 🏗️ Architecture

### Same VM Deployment (Recommended)

```
┌────────────────────────────────────────────────────┐
│  VM: 10.42.56.101 (Ubuntu)                         │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────────────┐   ┌──────────────────┐      │
│  │  EST + Nginx     │   │  FreeRADIUS      │      │
│  │  Port: 8445/tcp  │   │  Port: 1812/udp  │      │
│  │                  │   │  Port: 1813/udp  │      │
│  │  Compose:        │   │  Compose:        │      │
│  │  nginx.yml       │   │  radius.yml      │      │
│  └────────┬─────────┘   └────────┬─────────┘      │
│           │                      │                │
└───────────┼──────────────────────┼────────────────┘
            │                      │
            │ HTTPS                │ RADIUS
            │                      │
     ┌──────▼──────┐        ┌──────▼──────┐
     │ IQE Gateway │        │ Cisco WLC   │
     └──────┬──────┘        └──────┬──────┘
            │                      │
            └──────────▼───────────┘
                  Medical Pumps
```

**Key Points:**
- ✅ Different compose files → Independent deployments
- ✅ Different ports → No conflicts
- ✅ No shared networks → Truly decoupled
- ✅ Restart one without affecting the other

---

## 🔑 Key Features

### EST Server
- **RA Certificate Authentication**: IQE authenticates using client certificates
- **PKCS#7 Responses**: Standard EST protocol compliance
- **Nginx TLS Termination**: Works in containerized environments
- **Health Checks**: `/health` endpoint for monitoring

### FreeRADIUS
- **EAP-TLS**: Certificate-based WiFi authentication (802.1X)
- **EST CA Trust**: Validates certificates issued by EST server
- **Cisco WLC Integration**: Production-tested with Cisco wireless controllers
- **Host Network Mode**: Direct network access for RADIUS UDP traffic

### Decoupled Design
- **Independent Scaling**: Scale EST and RADIUS separately
- **Easy Migration**: Move RADIUS to different VM anytime
- **Isolated Failures**: EST failure doesn't affect RADIUS
- **Security Separation**: CA private key only on EST VM

---

## 🛠️ Common Operations

### View Logs
```bash
# EST logs
docker-compose -f docker-compose-nginx.yml logs -f

# RADIUS logs
docker logs -f freeradius-server
```

### Restart Services
```bash
# Restart EST only (RADIUS unaffected)
docker-compose -f docker-compose-nginx.yml restart

# Restart RADIUS only (EST unaffected)
docker-compose -f docker-compose-radius.yml restart
```

### Stop Services
```bash
# Stop EST
docker-compose -f docker-compose-nginx.yml down

# Stop RADIUS
docker-compose -f docker-compose-radius.yml down
```

### Test Health
```bash
# Test EST
curl -k https://localhost:8445/health

# Test RADIUS
docker exec -it freeradius-server radtest test test localhost 0 testing123
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[QUICKSTART.md](QUICKSTART.md)** | Same-VM deployment (start here) |
| [docs/ARCHITECTURE_DECOUPLED.md](docs/ARCHITECTURE_DECOUPLED.md) | Architecture diagrams & design decisions |
| [docs/DEPLOY_DECOUPLED.md](docs/DEPLOY_DECOUPLED.md) | Multi-VM deployment guide |
| [docs/COMMANDS_DECOUPLED.md](docs/COMMANDS_DECOUPLED.md) | Complete command reference |
| [docs/CISCO_WLC_CONFIG.md](docs/CISCO_WLC_CONFIG.md) | Cisco WLC configuration |

---

## 🔐 Security Considerations

### Critical Files (Backup & Secure)
- `certs/ca-key.pem` - **CA private key** (most critical)
- `certs/ca-cert.pem` - CA public certificate
- `certs/iqe-ra-cert.pem` - IQE RA certificate
- `certs/iqe-ra-key.pem` - IQE RA private key

### Best Practices
1. **Backup CA private key** to secure offline storage
2. **Restrict firewall** to only allow required IPs
3. **Use strong secrets** for RADIUS (32+ characters)
4. **Rotate certificates** before expiration
5. **Monitor logs** for failed authentication attempts
6. **Enable TLS 1.2+** only (disable older protocols)

---

## 🧪 Testing

### Test EST Server
```bash
# Generate test CSR
openssl req -new -newkey rsa:2048 -nodes \
  -keyout test-key.pem -out test-csr.der -outform DER \
  -subj "/CN=TEST-PUMP-001/O=Ferrari Medical Inc"

# Request certificate from EST
curl -k --cert certs/iqe-ra-cert.pem --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @test-csr.der \
  https://localhost:8445/.well-known/est/simpleenroll \
  -o test-cert.p7

# Extract certificate
openssl pkcs7 -print_certs -in test-cert.p7 -out test-cert.pem

# Verify
openssl x509 -in test-cert.pem -noout -subject
```

### Test RADIUS Server
```bash
# Monitor RADIUS logs
docker logs -f freeradius-server

# In another terminal, trigger pump WiFi connection
# Watch for: "Access-Accept" in logs
```

---

## 🐛 Troubleshooting

### EST Issues

**Problem**: IQE can't connect to EST
```bash
# Check firewall
sudo ufw status | grep 8445

# Allow IQE IP
sudo ufw allow from IQE_IP to any port 8445 proto tcp

# Check logs
docker-compose -f docker-compose-nginx.yml logs nginx
```

### RADIUS Issues

**Problem**: WLC can't reach RADIUS
```bash
# Check firewall
sudo ufw status | grep 1812

# Allow WLC IP
sudo ufw allow from WLC_IP to any port 1812 proto udp

# Check RADIUS listening
docker exec -it freeradius-server netstat -ulnp | grep 1812
```

**Problem**: RADIUS rejects pump certificate
```bash
# Verify RADIUS has correct CA certificate
docker exec -it freeradius-server cat /etc/freeradius/certs/ca/ca-cert.pem

# Compare with EST CA
diff certs/ca-cert.pem radius-certs/ca-cert.pem
# Should be identical
```

---

## 🤝 IQE Integration

### Files to Provide IQE Team
1. `certs/ca-cert.pem` - CA certificate (for verifying EST responses)
2. `certs/iqe-ra-cert.pem` - RA certificate (for authentication)
3. `certs/iqe-ra-key.pem` - RA private key

### EST Endpoint
```
URL: https://10.42.56.101:8445/.well-known/est/
Authentication: Client Certificate (RA cert)

Endpoints:
- GET  /cacerts       - Fetch CA certificates
- POST /simpleenroll  - Request certificate (submit PKCS#10 CSR)
```

### IQE Configuration Example
```yaml
est_server:
  url: "https://10.42.56.101:8445/.well-known/est"
  tls:
    ca_cert: "/path/to/ca-cert.pem"
    client_cert: "/path/to/iqe-ra-cert.pem"
    client_key: "/path/to/iqe-ra-key.pem"
  authentication:
    method: "client_certificate"
```

---

## 📝 License

See [LICENSE](LICENSE) file.

---

## 🔗 Quick Links

- **Start Deployment**: [QUICKSTART.md](QUICKSTART.md)
- **Architecture Details**: [docs/ARCHITECTURE_DECOUPLED.md](docs/ARCHITECTURE_DECOUPLED.md)
- **Command Reference**: [docs/COMMANDS_DECOUPLED.md](docs/COMMANDS_DECOUPLED.md)
- **WLC Setup**: [docs/CISCO_WLC_CONFIG.md](docs/CISCO_WLC_CONFIG.md)

---

**Note**: This repository contains production-ready code for medical device infrastructure. Handle CA private keys with extreme care and follow your organization's security policies.
