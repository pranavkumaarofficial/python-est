#!/bin/bash
# Quick diagnosis script - run this on IQE server or your VM

echo "=========================================="
echo "PKCS#7 Diagnosis"
echo "=========================================="

SERVER="https://10.42.56.101:8445"

echo ""
echo "[1/5] Fetching /cacerts..."
curl -vk ${SERVER}/.well-known/est/cacerts -o /tmp/test-cacerts.p7 2>&1 | grep -E "(< HTTP|< Content-Transfer-Encoding)"

echo ""
echo "[2/5] Checking file type..."
file /tmp/test-cacerts.p7

echo ""
echo "[3/5] First 100 bytes (hex)..."
xxd /tmp/test-cacerts.p7 | head -5

echo ""
echo "[4/5] Testing if it's base64..."
if head -1 /tmp/test-cacerts.p7 | grep -q "^[A-Za-z0-9+/=]*$"; then
    echo "   Looks like base64!"
    echo "   Decoding..."
    base64 -d /tmp/test-cacerts.p7 > /tmp/test-cacerts.der 2>&1 && echo "   Decode successful!" || echo "   Decode FAILED!"

    echo ""
    echo "[5/5] Testing openssl on decoded DER..."
    openssl pkcs7 -inform DER -in /tmp/test-cacerts.der -print_certs -out /tmp/test-cacerts.pem

    if [ $? -eq 0 ]; then
        echo "   ✅ SUCCESS! PKCS#7 is valid!"
        echo ""
        echo "Certificate extracted:"
        head -10 /tmp/test-cacerts.pem
    else
        echo "   ❌ FAILED! PKCS#7 is invalid!"
        echo ""
        echo "   This is YOUR server's bug."
    fi
else
    echo "   Looks like raw DER!"
    echo ""
    echo "[5/5] Testing openssl on raw DER..."
    openssl pkcs7 -inform DER -in /tmp/test-cacerts.p7 -print_certs -out /tmp/test-cacerts.pem

    if [ $? -eq 0 ]; then
        echo "   ✅ SUCCESS! PKCS#7 is valid!"
    else
        echo "   ❌ FAILED! PKCS#7 is invalid!"
    fi
fi

echo ""
echo "=========================================="
echo "Summary:"
echo "=========================================="
echo "If openssl succeeded: Your server is CORRECT, IQE has a bug"
echo "If openssl failed: Your server PKCS#7 is broken"
