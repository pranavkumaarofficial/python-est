#!/bin/bash

# Deployment script for EST server with RA certificate authentication
# This script ensures all certificates are regenerated together to avoid fingerprint mismatches

set -e

echo "=========================================="
echo "EST Server Deployment with RA Auth"
echo "=========================================="
echo ""

# Stop any running server
echo "1. Stopping any running EST server..."
pkill -f "python.*est.*server" || true
sleep 2
echo "✅ Server stopped"

echo ""
echo "2. Cleaning old certificates..."
rm -rf certs/*
rm -rf data/*.db
echo "✅ Old certificates removed"

echo ""
echo "3. Generating fresh CA and server certificates..."
python3 generate_certificates_python.py
if [ $? -ne 0 ]; then
    echo "❌ Certificate generation failed"
    exit 1
fi
echo "✅ CA and server certificates generated"

echo ""
echo "4. Creating bootstrap user (iqe-gateway)..."
python3 create_iqe_user.py
if [ $? -ne 0 ]; then
    echo "❌ User creation failed"
    exit 1
fi
echo "✅ Bootstrap user created"

echo ""
echo "5. Generating RA certificate for IQE gateway..."
python3 generate_ra_certificate.py
if [ $? -ne 0 ]; then
    echo "❌ RA certificate generation failed"
    exit 1
fi
echo "✅ RA certificate generated"

echo ""
echo "6. Verifying certificate chain consistency..."

# Extract fingerprints
SERVER_ISSUER_FP=$(openssl x509 -in certs/server.crt -noout -issuer_hash)
CA_SUBJECT_FP=$(openssl x509 -in certs/ca-cert.pem -noout -subject_hash)

if [ "$SERVER_ISSUER_FP" != "$CA_SUBJECT_FP" ]; then
    echo "❌ Certificate chain mismatch!"
    echo "   Server issuer: $SERVER_ISSUER_FP"
    echo "   CA subject:    $CA_SUBJECT_FP"
    exit 1
fi
echo "✅ Certificate chain verified"

echo ""
echo "7. Certificate Summary:"
echo ""
echo "CA Certificate:"
openssl x509 -in certs/ca-cert.pem -noout -subject -issuer -dates -fingerprint | sed 's/^/  /'

echo ""
echo "Server Certificate:"
openssl x509 -in certs/server.crt -noout -subject -issuer -dates -ext subjectAltName -fingerprint | sed 's/^/  /'

echo ""
echo "RA Certificate:"
openssl x509 -in certs/iqe-ra-cert.pem -noout -subject -issuer -dates -ext extendedKeyUsage -fingerprint | sed 's/^/  /'

echo ""
echo "8. Creating deployment package for IQE team..."
mkdir -p iqe_deployment_package
cp certs/ca-cert.pem iqe_deployment_package/
cp certs/iqe-ra-cert.pem iqe_deployment_package/
cp certs/iqe-ra-key.pem iqe_deployment_package/

cat > iqe_deployment_package/README.md << 'EOF'
# IQE Gateway EST Configuration Files

This package contains the files needed to configure the IQE gateway for EST enrollment.

## Files Included

1. **ca-cert.pem** - EST server CA certificate
   - Import this into IQE's trust store to verify EST server's TLS certificate

2. **iqe-ra-cert.pem** - Registration Authority (RA) certificate
   - Use this as the client certificate when connecting to EST server

3. **iqe-ra-key.pem** - RA private key
   - ⚠️ KEEP SECURE! This is the private key for the RA certificate
   - File permissions should be 600 (owner read/write only)

## EST Server Details

- **URL**: https://10.42.56.101:8445
- **Protocol**: RFC 7030 EST
- **Authentication**: Client certificate (mutual TLS)
- **Response Format**: Base64-encoded PKCS#7

## EST Endpoints

- GET  /.well-known/est/cacerts       - Retrieve CA certificates
- POST /.well-known/est/bootstrap     - Bootstrap enrollment (with username/password fallback)
- POST /.well-known/est/simpleenroll  - Simple enrollment (with RA cert)

## IQE Configuration Example

```yaml
est_server:
  url: https://10.42.56.101:8445
  ca_cert: /path/to/ca-cert.pem
  client_cert: /path/to/iqe-ra-cert.pem
  client_key: /path/to/iqe-ra-key.pem

endpoints:
  cacerts: /.well-known/est/cacerts
  simpleenroll: /.well-known/est/simpleenroll
```

## Testing

Test EST server connectivity:

```bash
# Test cacerts endpoint (no auth)
curl -k https://10.42.56.101:8445/.well-known/est/cacerts --output cacerts.p7

# Test enrollment with RA certificate
curl -vk https://10.42.56.101:8445/.well-known/est/simpleenroll \
  --cert iqe-ra-cert.pem \
  --key iqe-ra-key.pem \
  --cacert ca-cert.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @device-csr.der \
  -o device-cert.p7
```

## Security Notes

1. **Protect Private Key**: The iqe-ra-key.pem file must be kept secure
2. **File Permissions**: Set to 600 (chmod 600 iqe-ra-key.pem)
3. **Certificate Validity**: RA certificate valid for 2 years
4. **Rotation**: Plan to rotate RA certificate before expiry

## Support

For issues or questions, contact the EST server administrator.
EOF

echo "✅ Deployment package created: iqe_deployment_package/"

echo ""
echo "9. Starting EST server..."
nohup python3 -m python_est.cli serve --config config-iqe.yaml > server.log 2>&1 &
SERVER_PID=$!

echo "   Server PID: $SERVER_PID"
sleep 3

# Check if server started
if ps -p $SERVER_PID > /dev/null; then
    echo "✅ Server started successfully"
else
    echo "❌ Server failed to start. Check server.log for errors"
    cat server.log
    exit 1
fi

echo ""
echo "10. Testing server endpoints..."

# Test cacerts
echo "   Testing /cacerts..."
curl -k https://10.42.56.101:8445/.well-known/est/cacerts --output /tmp/test-cacerts.p7 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ /cacerts responding"
else
    echo "   ❌ /cacerts failed"
fi

# Test RA authentication
echo "   Testing /simpleenroll with RA cert..."
openssl req -new -newkey rsa:2048 -nodes \
  -keyout /tmp/test-key.pem \
  -out /tmp/test-csr.pem \
  -subj "/CN=deployment-test/O=Hospital/C=US" 2>/dev/null

openssl req -in /tmp/test-csr.pem -outform DER -out /tmp/test-csr.der 2>/dev/null

HTTP_CODE=$(curl -sk https://10.42.56.101:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  --cacert certs/ca-cert.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @/tmp/test-csr.der \
  -o /tmp/test-cert.p7 \
  -w "%{http_code}")

if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ RA authentication working"
else
    echo "   ❌ RA authentication failed (HTTP $HTTP_CODE)"
fi

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "Server Details:"
echo "  URL:        https://10.42.56.101:8445"
echo "  Dashboard:  https://10.42.56.101:8445/"
echo "  PID:        $SERVER_PID"
echo "  Log:        server.log"
echo ""
echo "IQE Deployment Package:"
echo "  Location:   iqe_deployment_package/"
echo "  Files:"
echo "    - ca-cert.pem (EST server CA)"
echo "    - iqe-ra-cert.pem (RA certificate)"
echo "    - iqe-ra-key.pem (RA private key)"
echo "    - README.md (configuration guide)"
echo ""
echo "Next Steps:"
echo "  1. Transfer iqe_deployment_package/ to IQE team"
echo "  2. IQE team configures gateway with RA certificate"
echo "  3. Test enrollment through IQE gateway"
echo ""
echo "Monitor logs:"
echo "  tail -f server.log"
echo ""
echo "Stop server:"
echo "  kill $SERVER_PID"
echo ""
