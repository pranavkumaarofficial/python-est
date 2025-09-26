# Quick Start Guide - EST Server Deployment
## Fast Track Setup for Internal Testing

This is a condensed version for quick deployment and testing.

## Server Setup (5 minutes)

### 1. Prepare Linux Server
```bash
# On your Linux server
sudo apt update && sudo apt install python3 python3-pip git openssl -y
git clone https://github.com/pranavkumaarofficial/python-est.git
cd python-est
pip3 install -r requirements.txt
```

### 2. Generate Certificates and Setup Users
```bash
# Generate certificates
python3 setup_certs.py

# Setup SRP bootstrap users
python3 create_srp_users.py setup

# Add your custom user
python3 create_srp_users.py add myuser MySecurePassword123
```

### 3. Configure and Start Server
```bash
# Edit config for your network (optional)
sed -i 's/address = 0.0.0.0/address = 0.0.0.0/' python_est.cfg

# Open firewall
sudo ufw allow 8443/tcp

# Start server
python3 main.py -c python_est.cfg
```

**Your EST server is now running on port 8443!**

## Client Testing (2 minutes)

### 1. Setup Client Machine
```bash
# On client machine (different from server)
git clone https://github.com/pranavkumaarofficial/python-est.git
cd python-est
pip3 install tlslite-ng requests cryptography
```

### 2. Copy the test client script (from CLIENT_SETUP.md)
```bash
# Copy the est_client_test.py script from CLIENT_SETUP.md
# Or download it directly:
wget https://raw.githubusercontent.com/your-fork/python-est/main/est_client_test.py
chmod +x est_client_test.py
```

### 3. Run Tests
```bash
# Replace YOUR_SERVER_IP with your server's IP address
python3 est_client_test.py YOUR_SERVER_IP -u myuser -P MySecurePassword123

# Quick test - just CA certificates (no auth needed)
python3 est_client_test.py YOUR_SERVER_IP --cacerts-only
```

## Expected Output

### Successful Test Results
```
EST Client Test Tool
==================================================
Server: YOUR_SERVER_IP:8443
Username: myuser
==================================================
Testing /cacerts endpoint on YOUR_SERVER_IP:8443
✅ /cacerts endpoint working - CA certificates retrieved!
📁 CA certificates saved to ca_certs.p7b

Testing SRP bootstrap authentication for user: myuser
Performing SRP handshake...
✅ SRP authentication successful!
Connected with cipher: SRP_SHA_WITH_AES_128_CBC_SHA
SRP username: myuser
✅ Bootstrap page accessible with SRP authentication!

Testing bootstrap login form submission...
✅ Bootstrap login form submission successful!
🔐 Ready for certificate enrollment!

🔧 Generating CSR for test-device...
✅ CSR generated: test-device.csr

Testing certificate enrollment for test-device...
✅ Certificate enrollment successful!
📁 Certificate saved to test-device_cert.p7b
📁 PEM certificate saved to test-device_cert.pem

==================================================
TEST RESULTS:
  CA Certificates:     ✅ PASS
  SRP Authentication:  ✅ PASS
  Bootstrap Login:     ✅ PASS
  Certificate Enroll:  ✅ PASS

OVERALL: ✅ ALL TESTS PASSED
```

## Troubleshooting Quick Fixes

### Can't Connect to Server
```bash
# Check if server is running
netstat -tuln | grep 8443

# Test basic connectivity
telnet YOUR_SERVER_IP 8443

# Check firewall
sudo ufw status
```

### TLS Handshake Failures
```bash
# Check server logs
tail -f /path/to/python-est/server.log

# Try with curl (should fail but shows connectivity)
curl -k https://YOUR_SERVER_IP:8443/.well-known/est/cacerts
```

### Authentication Issues
```bash
# Check SRP users
python3 create_srp_users.py list

# Verify password
python3 create_srp_users.py add testuser testpass123  # Add test user
```

## Next Steps

1. **Security**: Change default passwords, use proper certificates
2. **Monitoring**: Setup logging and monitoring
3. **Integration**: Connect to your existing PKI infrastructure
4. **Documentation**: Read full guides in DEPLOYMENT_GUIDE.md and CLIENT_SETUP.md

## Files Generated During Testing
- `ca_certs.p7b` - CA certificates in PKCS#7 format
- `test-device.key` - Private key for enrolled certificate
- `test-device.csr` - Certificate signing request
- `test-device_cert.p7b` - Enrolled certificate in PKCS#7 format
- `test-device_cert.pem` - Enrolled certificate in PEM format

🎉 **Congratulations!** Your EST server is working and ready for certificate operations!