#!/usr/bin/env python3
"""
Simple test client to check basic EST server functionality
"""
import socket
from tlslite.api import TLSConnection

def test_basic_connection():
    """Test basic TLS connection without SRP"""
    print("Testing basic TLS connection to EST server...")

    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect(('localhost', 8443))

        # Create TLS connection
        connection = TLSConnection(sock)

        # Try handshake without client authentication
        print("Attempting TLS handshake...")
        connection.handshakeClientCert()

        print("OK TLS connection successful!")
        print(f"Protocol: {connection.version}")
        print(f"Cipher: {connection.getCipherName()}")

        # Test /cacerts endpoint
        print("\nTesting /cacerts endpoint...")
        http_request = "GET /.well-known/est/cacerts HTTP/1.1\r\nHost: localhost:8443\r\nConnection: close\r\n\r\n"
        connection.write(http_request.encode())

        # Read response
        response = b""
        while True:
            try:
                data = connection.read(max=4096)
                if not data:
                    break
                response += data
            except:
                break

        response_str = response.decode('utf-8', errors='ignore')
        if "HTTP/1.1 200" in response_str and "application/pkcs7-mime" in response_str:
            print("OK /cacerts endpoint working! (No authentication required)")
            print(f"Response length: {len(response)} bytes")
        else:
            print("FAIL /cacerts endpoint failed")
            print(f"Response: {response_str[:500]}")

        connection.close()
        sock.close()
        return True

    except Exception as e:
        print(f"FAIL Connection failed: {e}")
        try:
            connection.close()
            sock.close()
        except:
            pass
        return False

def test_srp_connection():
    """Test SRP-authenticated connection"""
    print("\n" + "="*50)
    print("Testing SRP authentication...")

    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect(('localhost', 8443))

        # Create TLS connection
        connection = TLSConnection(sock)

        # Try SRP handshake
        print("Attempting SRP handshake with testuser...")
        connection.handshakeClientSRP("testuser", "testpass123")

        print(f"OK SRP authentication successful!")
        print(f"SRP username: {connection.session.srpUsername}")

        # Test bootstrap page
        print("\nTesting bootstrap page access...")
        http_request = "GET /bootstrap HTTP/1.1\r\nHost: localhost:8443\r\nConnection: close\r\n\r\n"
        connection.write(http_request.encode())

        # Read response
        response = b""
        while True:
            try:
                data = connection.read(max=4096)
                if not data:
                    break
                response += data
            except:
                break

        response_str = response.decode('utf-8', errors='ignore')
        if "HTTP/1.1 200" in response_str and "EST Bootstrap Login" in response_str:
            print("OK Bootstrap page accessible with SRP auth!")
        else:
            print("FAIL Bootstrap page failed")
            print(f"Response: {response_str[:500]}")

        connection.close()
        sock.close()
        return True

    except Exception as e:
        print(f"FAIL SRP authentication failed: {e}")
        try:
            connection.close()
            sock.close()
        except:
            pass
        return False

if __name__ == '__main__':
    print("EST Server Basic Test")
    print("=" * 50)

    basic_ok = test_basic_connection()
    srp_ok = test_srp_connection()

    print(f"\n{'=' * 50}")
    print("Test Results:")
    print(f"  Basic TLS + /cacerts: {'OK PASS' if basic_ok else 'FAIL FAIL'}")
    print(f"  SRP Auth + Bootstrap: {'OK PASS' if srp_ok else 'FAIL FAIL'}")