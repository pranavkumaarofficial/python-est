# libest Troubleshooting Guide

## Quick Fixes for Common Issues

### Issue 1: Build Fails

**Error**: `configure: error: OpenSSL not found`

**Fix**:
```bash
sudo apt-get install -y libssl-dev pkg-config
./configure --prefix=/usr/local
```

---

### Issue 2: htdigest Command Not Found

**Error**: `htdigest: command not found`

**Fix**:
```bash
sudo apt-get install -y apache2-utils
```

---

### Issue 3: Port Already in Use

**Error**: `Address already in use`

**Fix**: Change port in `runserver.sh`
```bash
nano runserver.sh

# Change -p 8446 to -p 8447
```

---

### Issue 4: Certificate Doesn't Have IP

**Check**:
```bash
cd ~/libest-server/libest/example/server
openssl x509 -in estCA/cacert.crt -text -noout | grep -A5 "Subject Alternative"
```

**Fix**: Edit `estExampleCA.cnf` before running `mfgCerts.sh`:
```bash
nano estExampleCA.cnf

# Add at the end:
[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
IP.2 = 10.42.56.101

# Then regenerate:
rm -rf newcerts estCA
./mfgCAs.sh
./mfgCerts.sh
```

---

### Issue 5: IQE Gets 401 Unauthorized

**Possible Causes**:
1. Wrong username/password
2. htdigest file not found
3. Realm mismatch

**Fix**:
```bash
# Recreate user
cd ~/libest-server/libest/example/server
htdigest -c .htdigest estrealm iqe-gateway
# Enter: iqe-secure-password-2024

# Verify file exists
ls -la .htdigest

# Restart server
pkill estserver
./runserver.sh
```

---

### Issue 6: IQE Gets Certificate Verification Error

**This means IQE doesn't trust your CA cert!**

**Fix Options**:

**Option A**: IQE team imports CA cert
```bash
# Get CA cert
cat ~/libest-server/libest/example/server/estCA/cacert.crt

# Send to IQE team to import into trust store
```

**Option B**: Check if IQE has "skip verification" option in UI
- Look for checkbox: "Allow self-signed certificates"
- Enable it for testing

---

### Issue 7: Server Crashes Immediately

**Check logs**:
```bash
# Check system logs
sudo tail -50 /var/log/syslog | grep est

# Check if certificates exist
ls -la ~/libest-server/libest/example/server/estCA/
```

**Common cause**: Missing certificates

**Fix**:
```bash
cd ~/libest-server/libest/example/server
./mfgCAs.sh
./mfgCerts.sh
./runserver.sh
```

---

### Issue 8: Can't Access from External IP

**Problem**: Server only listening on localhost

**Fix**: Check `runserver.sh` has correct bind address
```bash
nano runserver.sh

# Make sure it has:
./estserver \
  -c estCA/cacert.crt \
  -k estCA/private/cakey.pem \
  -p 8446 \
  # ... other options
```

**Also check firewall**:
```bash
sudo ufw status
sudo ufw allow 8446/tcp
```

---

### Issue 9: IQE Gets 500 Error

**Problem**: Usually certificate format issue

**Check**:
1. Certificate has IP address in SAN
2. Server returns base64 responses (libest does this by default)
3. User authentication works

**Debug**:
```bash
# Test with curl (exactly like IQE UI does):
openssl req -new -newkey rsa:2048 -nodes \
  -keyout test.key -out csr.der -outform DER \
  -subj "/CN=test-001"

openssl base64 -in csr.der -out csr.b64

curl -vvv -k -u iqe-gateway:iqe-secure-password-2024 \
  -H "Content-Type: application/pkcs10" \
  -H "Content-Transfer-Encoding: base64" \
  --data @csr.b64 \
  https://10.42.56.101:8446/.well-known/est/simpleenroll \
  -o client.p7.b64

# Check response
file client.p7.b64
# Should say: ASCII text
```

---

### Issue 10: Need to Use RA Certificate Instead of Password

**From email**: "disable forced HTTP auth when TLS client auth succeeds"

**Fix**: Add `-o` option in `runserver.sh`
```bash
nano runserver.sh

./estserver \
  -c estCA/cacert.crt \
  -k estCA/private/cakey.pem \
  -p 8446 \
  -o \           # ← This disables forced HTTP auth
  -v
```

Then generate RA certificate:
```bash
# Generate RA certificate signed by your CA
openssl req -new -newkey rsa:2048 -nodes \
  -keyout iqe-ra-key.pem \
  -out iqe-ra-csr.pem \
  -subj "/CN=IQE Registration Authority/O=IQE Gateway"

openssl x509 -req \
  -in iqe-ra-csr.pem \
  -CA estCA/cacert.crt \
  -CAkey estCA/private/cakey.pem \
  -CAcreateserial \
  -out iqe-ra-cert.pem \
  -days 730 \
  -sha256
```

Upload to IQE UI:
- RA Key File: `iqe-ra-key.pem`
- RA Cert File: `iqe-ra-cert.pem`

---

## Verification Checklist

Before testing with IQE UI:

- [ ] Server is running: `ps aux | grep estserver`
- [ ] Port is open: `sudo netstat -tulpn | grep 8446`
- [ ] Firewall allows traffic: `sudo ufw status | grep 8446`
- [ ] /cacerts works: `curl -k https://localhost:8446/.well-known/est/cacerts`
- [ ] External access works: `curl -k https://10.42.56.101:8446/.well-known/est/cacerts`
- [ ] Certificate has IP: `openssl x509 -in estCA/cacert.crt -text | grep "IP Address:10.42.56.101"`
- [ ] User can authenticate: Test with curl using `-u iqe-gateway:password`

---

## Useful Commands

### Start/Stop Server
```bash
# Start
cd ~/libest-server/libest/example/server
./runserver.sh

# Stop
pkill estserver

# Check if running
ps aux | grep estserver
```

### View Certificates
```bash
# View CA cert
openssl x509 -in estCA/cacert.crt -text -noout

# View server cert
openssl x509 -in estCA/private/estservercertandkey.pem -text -noout
```

### Test Endpoints
```bash
# Get CA certs
curl -vk https://10.42.56.101:8446/.well-known/est/cacerts -o cacerts.p7

# Enroll (with password)
curl -vk -u iqe-gateway:iqe-secure-password-2024 \
  -H "Content-Type: application/pkcs10" \
  --data-binary @csr.der \
  https://10.42.56.101:8446/.well-known/est/simpleenroll \
  -o cert.p7
```

### Check Logs
```bash
# System logs
sudo tail -f /var/log/syslog | grep est

# If you redirected output:
tail -f ~/libest-server/estserver.log
```

---

## Getting Help

If stuck, check:
1. Cisco libest README: https://github.com/cisco/libest
2. RFC 7030: EST protocol specification
3. Your teammate's working server (10.6.152.122) - ask them for config

---

## Emergency Fallback

If libest doesn't work either, you have options:

1. **Use teammate's server** (10.6.152.122) for demo
2. **Ask IQE team** to enable "skip cert verification" in UI
3. **Postpone demo** and debug properly (not ideal but honest)

---

## Success Indicators

You'll know it's working when:
✅ `curl -k https://10.42.56.101:8446/.well-known/est/cacerts` returns data
✅ IQE UI can connect and download CA cert
✅ IQE UI enrollment returns certificate (not 500 error)
✅ Certificate can be deployed to medical pump
✅ Pump can use cert for EAP-TLS authentication

---

Good luck! You've got this! 🚀
