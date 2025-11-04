#!/usr/bin/env python3
"""
Strict test of RA certificate authentication
Mimics real IQE gateway behavior
"""

import sys
import ssl
import urllib.request
import urllib.error
from pathlib import Path

def test_ra_authentication():
    """Test RA certificate authentication with EST server."""

    print("="*60)
    print("RA Certificate Authentication Test")
    print("Mimicking IQE Gateway Behavior")
    print("="*60)
    print()

    # Configuration
    est_url = "https://localhost:8445/.well-known/est/simpleenroll"
    ra_cert = "certs/iqe-ra-cert.pem"
    ra_key = "certs/iqe-ra-key.pem"
    ca_cert = "certs/ca-cert.pem"
    csr_der = "test_device.der"

    # Check files exist
    for file in [ra_cert, ra_key, ca_cert, csr_der]:
        if not Path(file).exists():
            print(f"ERROR: Missing file: {file}")
            return False

    print("1. Files checked - all present")
    print(f"   - RA Cert: {ra_cert}")
    print(f"   - RA Key: {ra_key}")
    print(f"   - CA Cert: {ca_cert}")
    print(f"   - CSR (DER): {csr_der}")
    print()

    # Read CSR
    with open(csr_der, 'rb') as f:
        csr_data = f.read()
    print(f"2. CSR loaded: {len(csr_data)} bytes")
    print()

    # Create SSL context with client certificate
    print("3. Creating SSL context with RA certificate...")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # For self-signed cert testing

    # Load RA certificate and key
    try:
        context.load_cert_chain(certfile=ra_cert, keyfile=ra_key)
        print("   - RA certificate loaded successfully")
    except Exception as e:
        print(f"   ERROR: Failed to load RA certificate: {e}")
        return False
    print()

    # Make request
    print("4. Sending enrollment request with RA certificate...")
    print(f"   URL: {est_url}")
    print(f"   Method: POST")
    print(f"   Content-Type: application/pkcs10")
    print(f"   Client Cert: {ra_cert}")
    print()

    try:
        request = urllib.request.Request(
            est_url,
            data=csr_data,
            headers={
                'Content-Type': 'application/pkcs10',
            },
            method='POST'
        )

        with urllib.request.urlopen(request, context=context, timeout=10) as response:
            status_code = response.status
            content_type = response.headers.get('Content-Type', '')
            response_data = response.read()

            print("="*60)
            print("RESPONSE RECEIVED")
            print("="*60)
            print(f"HTTP Status: {status_code}")
            print(f"Content-Type: {content_type}")
            print(f"Response Size: {len(response_data)} bytes")
            print()

            if status_code == 200:
                print("SUCCESS: RA Certificate Authentication WORKING!")
                print()

                # Save response
                with open('test_response.p7', 'wb') as f:
                    f.write(response_data)
                print("Response saved to: test_response.p7")

                # Check if base64 or DER
                try:
                    decoded = response_data.decode('ascii')
                    print("Response Format: BASE64 (ASCII text)")
                    print(f"First 100 chars: {decoded[:100]}")
                except:
                    print("Response Format: DER (binary)")

                return True
            else:
                print(f"FAILED: Unexpected status code {status_code}")
                return False

    except urllib.error.HTTPError as e:
        print("="*60)
        print("HTTP ERROR")
        print("="*60)
        print(f"Status Code: {e.code}")
        print(f"Reason: {e.reason}")
        print()

        if e.code == 401:
            print("FAILED: RA Certificate Authentication NOT WORKING")
            print()
            print("Possible causes:")
            print("1. Server not configured for client certificates")
            print("2. RA certificate not signed by server's CA")
            print("3. Server middleware not extracting client cert")
            print("4. Docker container running OLD code")

        return False

    except Exception as e:
        print("="*60)
        print("ERROR")
        print("="*60)
        print(f"Exception: {type(e).__name__}")
        print(f"Message: {e}")
        return False

if __name__ == '__main__':
    success = test_ra_authentication()
    sys.exit(0 if success else 1)
