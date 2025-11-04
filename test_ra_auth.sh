#!/bin/bash

# Test RA Certificate Authentication
# This script tests that the EST server properly authenticates using RA certificates

set -e

echo "=========================================="
echo "Testing RA Certificate Authentication"
echo "=========================================="
echo ""

# Configuration
EST_SERVER="https://10.42.56.101:8445"
RA_CERT="certs/iqe-ra-cert.pem"
RA_KEY="certs/iqe-ra-key.pem"
CA_CERT="certs/ca-cert.pem"

echo "1. Testing /cacerts endpoint (no auth required)..."
curl -k "${EST_SERVER}/.well-known/est/cacerts" \
  --output /tmp/test-cacerts.p7 \
  --write-out "\nHTTP Status: %{http_code}\n" \
  --silent --show-error

if [ -f /tmp/test-cacerts.p7 ]; then
    echo "✅ Received CA certificates"
    openssl pkcs7 -inform DER -in /tmp/test-cacerts.p7 -print_certs -noout
    if [ $? -eq 0 ]; then
        echo "✅ Valid PKCS#7 format"
    else
        echo "❌ Invalid PKCS#7 format"
        exit 1
    fi
else
    echo "❌ Failed to retrieve CA certificates"
    exit 1
fi

echo ""
echo "2. Generating test CSR for RA authentication..."
openssl req -new -newkey rsa:2048 -nodes \
  -keyout /tmp/test-device-key.pem \
  -out /tmp/test-device-csr.pem \
  -subj "/CN=test-pump-ra-auth/O=Hospital/C=US" 2>/dev/null

if [ ! -f /tmp/test-device-csr.pem ]; then
    echo "❌ Failed to generate CSR"
    exit 1
fi
echo "✅ CSR generated"

echo ""
echo "3. Converting CSR to DER format..."
openssl req -in /tmp/test-device-csr.pem -outform DER -out /tmp/test-device-csr.der
echo "✅ CSR converted to DER"

echo ""
echo "4. Testing /simpleenroll with RA certificate authentication..."
curl -vk "${EST_SERVER}/.well-known/est/simpleenroll" \
  --cert "${RA_CERT}" \
  --key "${RA_KEY}" \
  --cacert "${CA_CERT}" \
  -H "Content-Type: application/pkcs10" \
  --data-binary @/tmp/test-device-csr.der \
  --output /tmp/test-device-cert.p7 \
  --write-out "\nHTTP Status: %{http_code}\n" 2>&1 | tee /tmp/curl-output.log

HTTP_CODE=$(grep "HTTP Status:" /tmp/curl-output.log | tail -1 | cut -d' ' -f3)

echo ""
echo "5. Verifying enrollment result..."
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ HTTP 200 OK - Authentication successful"

    if [ -f /tmp/test-device-cert.p7 ]; then
        echo "✅ Received certificate"

        # Try to parse as DER
        openssl pkcs7 -inform DER -in /tmp/test-device-cert.p7 -print_certs -out /tmp/test-device-cert.pem 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "✅ Valid PKCS#7 DER format"
            echo ""
            echo "Certificate details:"
            openssl x509 -in /tmp/test-device-cert.pem -noout -subject -issuer -dates
            echo ""
            echo "=========================================="
            echo "✅ RA CERTIFICATE AUTHENTICATION WORKING!"
            echo "=========================================="
            exit 0
        else
            # Try base64
            base64 -d /tmp/test-device-cert.p7 > /tmp/test-device-cert-decoded.p7 2>/dev/null
            openssl pkcs7 -inform DER -in /tmp/test-device-cert-decoded.p7 -print_certs -out /tmp/test-device-cert.pem 2>/dev/null
            if [ $? -eq 0 ]; then
                echo "✅ Valid base64-encoded PKCS#7 format"
                echo ""
                echo "Certificate details:"
                openssl x509 -in /tmp/test-device-cert.pem -noout -subject -issuer -dates
                echo ""
                echo "=========================================="
                echo "✅ RA CERTIFICATE AUTHENTICATION WORKING!"
                echo "=========================================="
                exit 0
            else
                echo "❌ Invalid certificate format"
                exit 1
            fi
        fi
    else
        echo "❌ No certificate received"
        exit 1
    fi
elif [ "$HTTP_CODE" = "401" ]; then
    echo "❌ HTTP 401 Unauthorized - RA authentication failed"
    echo "Check server logs for details"
    exit 1
else
    echo "❌ HTTP $HTTP_CODE - Unexpected response"
    exit 1
fi
