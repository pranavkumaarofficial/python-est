#!/usr/bin/env python3
"""
Minimal EST server test with basic TLS settings
"""
import socket
from tlslite.api import TLSConnection, HandshakeSettings

def test_minimal_tls():
    """Test with minimal TLS settings"""
    print("Testing minimal TLS connection...")

    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect(('localhost', 8443))

        # Create TLS connection
        connection = TLSConnection(sock)

        # Configure minimal handshake settings
        settings = HandshakeSettings()
        settings.minVersion = (3, 1)  # TLS 1.0
        settings.maxVersion = (3, 4)  # TLS 1.3

        print("Attempting TLS handshake with basic settings...")
        connection.handshakeClientCert(settings=settings)

        print("OK TLS connection successful!")
        print(f"TLS Version: {connection.version}")
        print(f"Cipher: {connection.getCipherName()}")

        # Test /cacerts endpoint
        print("\nTesting /cacerts endpoint...")
        request = "GET /.well-known/est/cacerts HTTP/1.1\r\nHost: localhost:8443\r\nConnection: close\r\n\r\n"
        connection.write(request.encode())

        # Read response
        response = connection.read(max=8192)
        response_str = response.decode('utf-8', errors='ignore')

        print("Response received:")
        print("-" * 30)
        lines = response_str.split('\r\n')
        for i, line in enumerate(lines[:10]):  # First 10 lines
            print(f"{i+1:2d}: {line}")

        if len(lines) > 10:
            print("... (more lines)")

        if "HTTP/1.1 200" in response_str:
            print("\nSUCCESS: /cacerts endpoint returned HTTP 200!")
        else:
            print(f"\nFAILED: Unexpected response")

        connection.close()
        sock.close()
        return True

    except Exception as e:
        print(f"FAILED: {e}")
        return False

if __name__ == '__main__':
    test_minimal_tls()