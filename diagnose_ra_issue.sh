#!/bin/bash

# Diagnostic script to identify why RA authentication isn't working

echo "=========================================="
echo "RA Authentication Diagnostic Tool"
echo "=========================================="
echo ""

echo "1. Checking if code has RA authentication implementation..."
if grep -q "ssl_cert_reqs=ssl.CERT_OPTIONAL" src/python_est/server.py; then
    echo "   ✅ Code has ssl_cert_reqs configured"
else
    echo "   ❌ Code missing ssl_cert_reqs - NOT IMPLEMENTED"
    exit 1
fi

if grep -q "extract_client_cert" src/python_est/server.py; then
    echo "   ✅ Code has client cert extraction middleware"
else
    echo "   ❌ Code missing client cert extraction - NOT IMPLEMENTED"
    exit 1
fi

echo ""
echo "2. Checking git status..."
git log --oneline -1
if git log --oneline -1 | grep -q "RA\|client cert"; then
    echo "   ✅ Latest commit includes RA changes"
else
    echo "   ⚠️  Latest commit doesn't mention RA - might be outdated"
fi

echo ""
echo "3. Checking RA certificate files..."
if [ -f certs/iqe-ra-cert.pem ] && [ -f certs/iqe-ra-key.pem ]; then
    echo "   ✅ RA certificate files exist"
    echo "   Certificate details:"
    openssl x509 -in certs/iqe-ra-cert.pem -noout -subject -issuer -dates | sed 's/^/      /'
else
    echo "   ❌ RA certificate files missing"
    echo "   Generate with: python3 generate_ra_certificate.py"
fi

echo ""
echo "4. Testing client certificate with DEBUG logging..."

# Generate test CSR
openssl req -new -newkey rsa:2048 -nodes \
  -keyout /tmp/test-device.key \
  -out /tmp/test-device.csr \
  -subj "/CN=diagnostic-test/O=Hospital/C=US" 2>/dev/null

openssl req -in /tmp/test-device.csr -outform DER -out /tmp/test-device.der 2>/dev/null

echo "   Testing /simpleenroll with RA certificate..."

# Test with verbose curl
curl -vk https://localhost:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @/tmp/test-device.der \
  -o /tmp/test-response.p7 2>&1 | grep -E "SSL|TLS|certificate|Client cert"

HTTP_CODE=$(curl -sk https://localhost:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @/tmp/test-device.der \
  -o /tmp/test-response.p7 \
  -w "%{http_code}")

echo ""
if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ HTTP 200 - Authentication successful"
else
    echo "   ❌ HTTP $HTTP_CODE - Authentication failed"
fi

echo ""
echo "5. Checking what the server is actually running..."
echo "   CRITICAL: Check if Docker container is using NEW code"
echo ""
echo "   Run these commands on Ubuntu VM:"
echo "   ---------------------------------"
echo "   # Check when Docker image was built"
echo "   docker images | grep python-est-server"
echo ""
echo "   # Check logs for client certificate messages"
echo "   docker logs python-est-server 2>&1 | grep -i 'client cert'"
echo ""
echo "   # If no client cert logs found, rebuild Docker image:"
echo "   docker stop python-est-server"
echo "   docker rm python-est-server"
echo "   docker build --no-cache -t python-est-server:latest ."
echo "   docker run -d --name python-est-server -p 8445:8445 \\"
echo "     -v \$(pwd)/certs:/app/certs \\"
echo "     -v \$(pwd)/data:/app/data \\"
echo "     -v \$(pwd)/config-iqe.yaml:/app/config.yaml \\"
echo "     python-est-server:latest"
echo ""

echo "6. Common Issues and Solutions:"
echo "   ==============================="
echo ""
echo "   Issue: HTTP 401 Unauthorized"
echo "   Possible causes:"
echo "     a) Docker container running OLD code (before RA implementation)"
echo "        Solution: Rebuild Docker image with --no-cache"
echo ""
echo "     b) Client certificate not being sent by curl"
echo "        Solution: Verify cert files exist and are readable"
echo ""
echo "     c) uvicorn not configured to accept client certs"
echo "        Solution: Check server.py line 1047 has ssl_cert_reqs"
echo ""
echo "     d) Middleware not extracting certificate"
echo "        Solution: Check logs for 'Client certificate found' (debug level)"
echo ""
echo "   Issue: No 'client certificate' logs in output"
echo "   Possible causes:"
echo "     a) Logs at DEBUG level (not shown in INFO logs)"
echo "        Solution: Change logger.debug to logger.info in server.py:121"
echo ""
echo "     b) Docker container has OLD code"
echo "        Solution: REBUILD Docker image (not just restart)"
echo ""

echo ""
echo "7. Next Steps:"
echo "   ============"
echo ""
echo "   If HTTP 401 persists:"
echo ""
echo "   Step 1: Enable DEBUG logging to see middleware activity"
echo "   Edit src/python_est/server.py line 121:"
echo "     Change: logger.debug(f\"Client certificate found: ...\")"
echo "     To:     logger.info(f\"Client certificate found: ...\")"
echo ""
echo "   Step 2: Commit and push code"
echo "     git add ."
echo "     git commit -m 'fix: Change client cert logging to INFO level'"
echo "     git push origin deploy_v1"
echo ""
echo "   Step 3: On Ubuntu VM - rebuild Docker with --no-cache"
echo "     git pull origin deploy_v1"
echo "     docker stop python-est-server && docker rm python-est-server"
echo "     docker build --no-cache -t python-est-server:latest ."
echo "     docker run -d --name python-est-server -p 8445:8445 \\"
echo "       -v \$(pwd)/certs:/app/certs \\"
echo "       -v \$(pwd)/data:/app/data \\"
echo "       -v \$(pwd)/config-iqe.yaml:/app/config.yaml \\"
echo "       python-est-server:latest"
echo ""
echo "   Step 4: Test again and check logs"
echo "     docker logs python-est-server | grep -i 'client cert'"
echo ""

echo "=========================================="
echo "Diagnostic Complete"
echo "=========================================="
