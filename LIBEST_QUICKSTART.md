# Cisco libest Quick Setup for Demo Tomorrow

## Why This Will Work Fast

✅ IQE team already uses libest (10.6.152.122)
✅ Proven compatibility
✅ Setup in < 30 minutes
✅ Demo-ready immediately

## Setup Plan

### 1. New Branch (You Do This)

```bash
git checkout -b cisco-libest
git push -u origin cisco-libest
```

### 2. SSH to Ubuntu VM

Use a **different port** to avoid conflict with your Python EST server:
- Python EST: Port 8445 (keep running)
- libest: Port 8446 (new)

### 3. Install Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    libssl-dev \
    git \
    autoconf \
    automake \
    libtool
```

### 4. Download and Build libest

```bash
# Create separate directory
mkdir -p ~/libest-server
cd ~/libest-server

# Clone cisco libest
git clone https://github.com/cisco/libest.git
cd libest

# Build
./configure --prefix=/usr/local
make
sudo make install
```

**Time estimate**: 10-15 minutes

### 5. Set Up Certificates

```bash
cd example/server

# Generate CA certificate
./mfgCAs.sh

# This creates:
# - estCA/private/cakey.pem (CA private key)
# - estCA/cacert.crt (CA certificate)
```

### 6. CRITICAL: Add IP to Certificate

From the email:
```
Add at the end of ext.conf (in alt_names section):
IP.3 = <IP OF THE SERVER>
```

Edit `estExampleCA.cnf`:
```bash
nano estExampleCA.cnf
```

Find the `[alt_names]` section and add:
```
DNS.1 = localhost
DNS.2 = estserver
IP.1 = 127.0.0.1
IP.2 = 10.42.56.101
```

### 7. Generate Server Certificate

```bash
# Generate server cert with the IP
./mfgCerts.sh

# This creates server certificate with IP address
```

### 8. Configure for IQE

Edit `runserver.sh`:
```bash
nano runserver.sh
```

Change:
```bash
# Original:
./estserver -c estCA/cacert.crt -k estCA/private/cakey.pem ...

# Add these options:
./estserver \
  -c estCA/cacert.crt \
  -k estCA/private/cakey.pem \
  -r estrealm \
  -p 8446 \
  -o \
  -v
```

Options explained:
- `-p 8446`: Use port 8446 (avoid conflict)
- `-o`: Disable forced HTTP auth (allows RA cert auth)
- `-v`: Verbose logging

### 9. Create User

```bash
# Default user is estuser:estpwd
# Or create your user:
# The script uses htdigest
htdigest -c .htdigest estrealm iqe-gateway
# Enter password: iqe-secure-password-2024
```

### 10. Start Server

```bash
./runserver.sh
```

Should see:
```
EST server started on port 8446
```

### 11. Test

```bash
# Test /cacerts
curl -vk https://localhost:8446/.well-known/est/cacerts -o cacerts.p7

# Test enrollment
openssl req -new -newkey rsa:2048 -nodes \
  -keyout test-key.pem -out csr.der -outform DER \
  -subj "/CN=test-pump-001"

openssl base64 -in csr.der -out csr.b64

curl -vk -u iqe-gateway:iqe-secure-password-2024 \
  -H "Content-Type: application/pkcs10" \
  -H "Content-Transfer-Encoding: base64" \
  --data @csr.b64 \
  https://localhost:8446/.well-known/est/simpleenroll \
  -o client.p7.b64
```

### 12. Open Firewall

```bash
sudo ufw allow 8446/tcp
```

### 13. Test from External

```bash
curl -vk https://10.42.56.101:8446/.well-known/est/cacerts
```

### 14. Configure IQE UI

Update IQE UI to use:
- CA Certs URL: `https://10.42.56.101:8446/.well-known/est/cacerts`
- Enrollment URL: `https://10.42.56.101:8446/.well-known/est/simpleenroll`
- Username: `iqe-gateway`
- Password: `iqe-secure-password-2024`

### 15. Share CA Cert with IQE Team

```bash
# Copy CA cert
cat ~/libest-server/libest/example/server/estCA/cacert.crt

# Send this to IQE team to import
```

## Timeline

| Task | Time | Total |
|------|------|-------|
| Install dependencies | 5 min | 5 min |
| Build libest | 10 min | 15 min |
| Generate certificates | 5 min | 20 min |
| Configure & start server | 5 min | 25 min |
| Test locally | 5 min | 30 min |
| Test with IQE UI | 10 min | 40 min |

**Total: ~40 minutes to demo-ready**

## Advantages for Demo Tomorrow

✅ **Proven**: IQE team already uses this
✅ **Fast**: No debugging, works out of the box
✅ **Safe**: Separate port, no conflict
✅ **Fallback**: Keep your Python EST as backup

## Your Python EST Server

**Don't delete it!** Keep it running on port 8445.

Benefits:
- Backup option
- Better for future development
- Has dashboard UI
- More flexible config

After demo succeeds, you can:
1. Show both implementations
2. Highlight Python EST advantages
3. Migrate gradually if needed

## For Your LOR

You can say:
> "Evaluated multiple EST server implementations (cisco libest and custom Python) for medical device certificate provisioning. Successfully deployed cisco libest for rapid production deployment while developing enhanced Python-based solution with improved monitoring and flexibility."

Shows pragmatism AND technical depth!

## Quick Reference

### libest Commands
```bash
# Start server
cd ~/libest-server/libest/example/server
./runserver.sh

# Stop server
pkill estserver

# View logs
tail -f /var/log/syslog | grep est
```

### Troubleshooting

**Problem**: Build fails
```bash
# Install missing dependencies
sudo apt-get install -y pkg-config libssl-dev
```

**Problem**: Port already in use
```bash
# Change port in runserver.sh
-p 8446  # Use different port
```

**Problem**: IQE still gets errors
```bash
# Check certificate has IP
openssl x509 -in server.crt -text -noout | grep "IP Address"

# Should show: IP Address:10.42.56.101
```

## Next Steps After Demo

1. **Demo succeeds with libest** ✅
2. **Get your LOR** ✅
3. **Continue developing Python EST** (better long-term)
4. **Add features**: Dashboard, monitoring, custom policies
5. **Gradual migration** when ready

## Decision Tree

```
Tomorrow's Demo:
├─ Use libest (proven, fast)
│  └─ Success! → Get LOR → Continue Python EST development
│
└─ Python EST still not working?
   └─ libest is your safety net!
```

## My Recommendation

**Do both in parallel:**

1. **Tonight**: Set up libest (1 hour)
2. **Tomorrow morning**: Test libest with IQE (should work!)
3. **Demo**: Use libest (safe, proven)
4. **Next week**: Debug Python EST (for learning/future)

This way you're **covered for demo** and **keep learning** with Python EST!

Good luck with your demo! 🚀
