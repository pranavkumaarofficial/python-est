#!/bin/bash
# Diagnose Proxy PKCS#7 Corruption
# Run this on IQE server (brdinterop6332)

echo "=========================================="
echo "Proxy PKCS#7 Corruption Diagnosis"
echo "=========================================="
echo ""

# Get proxy address from you
read -p "Enter proxy URL (e.g., https://proxy-service:8443): " PROXY_URL
BACKEND_URL="https://10.42.56.101:8445"

echo ""
echo "[1/6] Testing DIRECT connection to EST server..."
curl -vk ${BACKEND_URL}/.well-known/est/cacerts -o /tmp/direct.p7 2>&1 | grep -E "(< HTTP|< Content-Type|< Content-Transfer)"
echo "Downloaded to /tmp/direct.p7"
ls -lh /tmp/direct.p7

echo ""
echo "[2/6] Testing PROXY connection..."
curl -vk ${PROXY_URL}/.well-known/est/cacerts -o /tmp/proxy.p7 2>&1 | grep -E "(< HTTP|< Content-Type|< Content-Transfer)"
echo "Downloaded to /tmp/proxy.p7"
ls -lh /tmp/proxy.p7

echo ""
echo "[3/6] Comparing file sizes..."
DIRECT_SIZE=$(stat -c%s /tmp/direct.p7)
PROXY_SIZE=$(stat -c%s /tmp/proxy.p7)
echo "Direct: $DIRECT_SIZE bytes"
echo "Proxy:  $PROXY_SIZE bytes"

if [ "$DIRECT_SIZE" -ne "$PROXY_SIZE" ]; then
    echo "❌ SIZE MISMATCH! Proxy is modifying the response!"
else
    echo "✅ Sizes match"
fi

echo ""
echo "[4/6] Checking if binary data is intact..."
echo "Direct first 32 bytes (hex):"
xxd /tmp/direct.p7 | head -2

echo ""
echo "Proxy first 32 bytes (hex):"
xxd /tmp/proxy.p7 | head -2

if cmp -s /tmp/direct.p7 /tmp/proxy.p7; then
    echo "✅ Files are IDENTICAL - proxy is working correctly"
else
    echo "❌ FILES DIFFER - proxy is corrupting the response!"
fi

echo ""
echo "[5/6] Testing openssl parsing..."
echo "Parsing DIRECT response:"
openssl pkcs7 -inform DER -in /tmp/direct.p7 -print_certs -noout
DIRECT_RESULT=$?
echo "Direct result: $DIRECT_RESULT"

echo ""
echo "Parsing PROXY response:"
openssl pkcs7 -inform DER -in /tmp/proxy.p7 -print_certs -noout
PROXY_RESULT=$?
echo "Proxy result: $PROXY_RESULT"

echo ""
echo "[6/6] Summary:"
echo "=========================================="
if [ $DIRECT_RESULT -eq 0 ] && [ $PROXY_RESULT -ne 0 ]; then
    echo "❌ DIAGNOSIS: Proxy is corrupting the PKCS#7 response!"
    echo ""
    echo "Possible causes:"
    echo "1. Proxy treating binary as text (charset conversion)"
    echo "2. Proxy compressing response (gzip/deflate)"
    echo "3. Proxy buffering breaking binary data"
    echo "4. Proxy modifying Content-Type header"
    echo ""
    echo "Solution: Fix proxy configuration OR bypass proxy"
    echo ""
    echo "Show me your proxy config and I'll fix it!"
elif [ $DIRECT_RESULT -ne 0 ] && [ $PROXY_RESULT -ne 0 ]; then
    echo "❌ DIAGNOSIS: Backend EST server has PKCS#7 issue!"
    echo ""
    echo "Solution: Check EST server logs and PKCS#7 generation"
elif [ $DIRECT_RESULT -eq 0 ] && [ $PROXY_RESULT -eq 0 ]; then
    echo "✅ Both work! Issue might be intermittent or in IQE code"
else
    echo "⚠️  Unexpected result - need more investigation"
fi
echo "=========================================="
