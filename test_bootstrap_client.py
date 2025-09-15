#!/usr/bin/env python3
"""
Test client for EST bootstrap authentication using SRP
"""
import sys
from tlslite.api import TLSConnection, VerifierDB
import socket

def test_bootstrap_login(username, password, host='localhost', port=8443):
    """Test SRP authentication and bootstrap login"""
    print(f"Testing bootstrap login for user: {username}")

    try:
        # Create socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))

        # Create TLS connection with SRP
        connection = TLSConnection(sock)

        print("Performing SRP handshake...")
        connection.handshakeClientSRP(username, password)

        print("[OK] SRP handshake successful!")
        print(f"Connected with cipher: {connection.getCipherName()}")
        print(f"SRP username: {connection.session.srpUsername}")

        # Test GET request to bootstrap page
        print("\nRequesting bootstrap page...")
        http_request = f"GET /bootstrap HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
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
        print("Response received:")
        print("=" * 50)
        print(response_str[:1000])  # First 1000 chars
        if len(response_str) > 1000:
            print("... (truncated)")
        print("=" * 50)

        # Test POST request to bootstrap login
        print("\nTesting form submission...")
        form_data = f"username={username}&password={password}"
        post_request = f"""POST /bootstrap/login HTTP/1.1\r
Host: {host}:{port}\r
Content-Type: application/x-www-form-urlencoded\r
Content-Length: {len(form_data)}\r
Connection: close\r
\r
{form_data}"""

        # Close previous connection and create new one for POST
        connection.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        connection = TLSConnection(sock)
        connection.handshakeClientSRP(username, password)

        connection.write(post_request.encode())

        # Read POST response
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
        print("POST Response:")
        print("=" * 50)
        print(response_str[:1000])
        if len(response_str) > 1000:
            print("... (truncated)")
        print("=" * 50)

        connection.close()
        return True

    except Exception as e:
        print(f"[ERROR] Error during bootstrap test: {e}")
        return False

def main():
    if len(sys.argv) < 3:
        print("Usage: python test_bootstrap_client.py <username> <password>")
        print("\nAvailable demo users:")
        print("  testuser    | testpass123")
        print("  device001   | SecureP@ss001")
        print("  admin       | AdminP@ss456")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]

    success = test_bootstrap_login(username, password)

    if success:
        print("\n[OK] Bootstrap test completed successfully!")
    else:
        print("\n[ERROR] Bootstrap test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()