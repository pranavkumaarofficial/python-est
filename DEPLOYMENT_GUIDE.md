# Python-EST Server Deployment Guide
## Production Setup on Linux Server

This guide covers setting up the Python-EST server on a Linux server for internal organizational use with client testing.

## Prerequisites

### Server Requirements
- Linux server (Ubuntu 20.04+, CentOS 8+, or similar)
- Python 3.7+
- Network connectivity on desired port (default: 8443)
- SSL/TLS certificates or ability to generate self-signed ones

### Client Requirements
- Python 3.7+ with pip
- Network access to EST server
- Client certificates (if not using bootstrap)

## Server Setup

### 1. Prepare the Server Environment

```bash
# Update system
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
# OR
sudo yum update -y                      # CentOS/RHEL

# Install Python 3 and pip if not present
sudo apt install python3 python3-pip python3-venv git -y  # Ubuntu/Debian
# OR
sudo yum install python3 python3-pip git -y              # CentOS/RHEL

# Install OpenSSL for certificate operations
sudo apt install openssl -y  # Ubuntu/Debian
# OR
sudo yum install openssl -y  # CentOS/RHEL
```

### 2. Clone and Setup the EST Server

```bash
# Clone the repository
git clone https://github.com/pranavkumaarofficial/python-est.git
cd python-est

# Create virtual environment (recommended)
python3 -m venv est-server-env
source est-server-env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Generate Certificates for Production Use

```bash
# Make setup script executable
chmod +x setup_certs.py

# Generate development certificates (modify for production)
python setup_certs.py

# For production, customize the certificate generation:
# Edit the setup_certs.py to include your organization details
# Or use your existing PKI infrastructure
```

### 4. Configure the Server

```bash
# Edit the configuration file
cp python_est.cfg python_est.cfg.backup
nano python_est.cfg
```

**Key configuration changes for production:**

```ini
[DEFAULT]
debug = False  # Set to False for production

[Daemon]
address = 0.0.0.0    # Listen on all interfaces
port = 8443          # Default EST port (or use 443)
key_file = certs/server.key
cert_file = certs/server.crt

[CAhandler]
handler_file = python_est/handlers/openssl_ca_handler_fixed.py
issuing_ca_key = certs/ca-key.pem
issuing_ca_cert = certs/ca-cert.pem
ca_cert_chain_list = ["certs/ca-cert.pem"]
cert_validity_days = 365
cert_save_path = certs/issued/

[SRP]
userdb = certs/srp_users.db

[Bootstrap]
enabled = true
endpoint = /.well-known/est/bootstrap
```

### 5. Setup SRP Bootstrap Users

```bash
# Create SRP user database
python create_srp_users.py setup

# Add custom users for your organization
python create_srp_users.py add your_username your_secure_password
python create_srp_users.py add device_01 Device_SecurePass_2024
python create_srp_users.py add admin_user Admin_SecurePass_2024

# List users to verify
python create_srp_users.py list
```

### 6. Configure Firewall

```bash
# Ubuntu/Debian with UFW
sudo ufw allow 8443/tcp
sudo ufw enable

# CentOS/RHEL with firewalld
sudo firewall-cmd --permanent --add-port=8443/tcp
sudo firewall-cmd --reload

# Or for traditional iptables
sudo iptables -A INPUT -p tcp --dport 8443 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

### 7. Start the EST Server

```bash
# For testing
python main.py -c python_est.cfg

# For production with logging
nohup python main.py -c python_est.cfg > est_server.log 2>&1 &

# Or create a systemd service (recommended)
```

### 8. Create Systemd Service (Production)

```bash
# Create service file
sudo nano /etc/systemd/system/python-est.service
```

```ini
[Unit]
Description=Python EST Server
After=network.target

[Service]
Type=simple
User=est-server  # Create dedicated user
WorkingDirectory=/path/to/python-est
ExecStart=/path/to/python-est/est-server-env/bin/python main.py -c python_est.cfg
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Create dedicated user
sudo useradd -r -s /bin/false est-server
sudo chown -R est-server:est-server /path/to/python-est

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable python-est
sudo systemctl start python-est
sudo systemctl status python-est
```

## Network Configuration

### Security Considerations
1. **Firewall**: Only open port 8443 to trusted networks
2. **Network Segmentation**: Place EST server in management network
3. **Access Control**: Use organization's existing firewall rules
4. **Monitoring**: Enable logging for all certificate operations

### DNS Configuration (Optional)
```bash
# Add DNS entry in your organization's DNS server
est-server.yourdomain.com  A  YOUR_SERVER_IP
```

## Verification Steps

### 1. Check Server Status
```bash
# Check if server is listening
netstat -tuln | grep 8443
# OR
ss -tuln | grep 8443

# Check service status (if using systemd)
sudo systemctl status python-est

# Check logs
tail -f est_server.log
```

### 2. Test from Server Localhost
```bash
# Test /cacerts endpoint (no auth required)
curl -k https://localhost:8443/.well-known/est/cacerts

# Should return PKCS#7 certificate data
```

### 3. Test from Network Client
```bash
# Replace SERVER_IP with your server's IP
curl -k https://SERVER_IP:8443/.well-known/est/cacerts
```

## Next Steps
- Set up client testing (see CLIENT_SETUP.md)
- Configure network access
- Test bootstrap and enrollment process
- Set up monitoring and logging

## Important Security Notes
- Change default SRP passwords immediately
- Use proper certificates in production (not self-signed)
- Implement proper network security
- Monitor certificate operations
- Regular backup of certificate database and keys