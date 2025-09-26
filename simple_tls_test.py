#!/usr/bin/env python3
"""
Simplified TLS test for EST server - focuses on working configurations
"""
import sys
import socket
from tlslite.api import TLSConnection, HandshakeSettings

def test_srp_only(server_ip, username, password, port=8443):
    """Test SRP authentication only - this seems to work"""
    print(f"Testing SRP authentication to {server_ip}:{port}")
    print(f"Username: {username}")

    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((server_ip, port))

        # Create TLS connection
        connection = TLSConnection(sock)

        # Simplified settings for SRP
        settings = HandshakeSettings()
        settings.minVersion = (3, 1)  # TLS 1.0
        settings.maxVersion = (3, 3)  # TLS 1.2

        print("Attempting SRP handshake...")
        connection.handshakeClientSRP(username, password, settings=settings)

        print("SUCCESS: SRP authentication established!")
        print(f"Cipher: {connection.getCipherName()}")
        print(f"TLS Version: {connection.version}")

        # Test /cacerts with SRP authentication
        print("\nTesting /cacerts with SRP authentication...")
        request = f"GET /.well-known/est/cacerts HTTP/1.1\r\nHost: {server_ip}:{port}\r\nConnection: close\r\n\r\n"
        connection.write(request.encode())

        response = connection.read(max=8192)
        response_str = response.decode('utf-8', errors='ignore')

        print("Response received:")
        print("-" * 40)
        lines = response_str.split('\r\n')
        for i, line in enumerate(lines[:6]):
            print(f"{i+1:2d}: {line}")

        if "HTTP/1.1 200" in response_str:
            print("\nSUCCESS: /cacerts working with SRP auth!")

            # Test bootstrap page
            connection.close()
            sock.close()

            # New connection for bootstrap
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((server_ip, port))
            connection = TLSConnection(sock)
            connection.handshakeClientSRP(username, password, settings=settings)

            print("\nTesting bootstrap page...")
            request = f"GET /.well-known/est/bootstrap HTTP/1.1\r\nHost: {server_ip}:{port}\r\nConnection: close\r\n\r\n"
            connection.write(request.encode())

            response = connection.read(max=8192)
            response_str = response.decode('utf-8', errors='ignore')

            if "EST Bootstrap Login" in response_str:
                print("SUCCESS: Bootstrap page accessible!")

                # Test form submission
                connection.close()
                sock.close()

                # New connection for form submission
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((server_ip, port))
                connection = TLSConnection(sock)
                connection.handshakeClientSRP(username, password, settings=settings)

                print("\nTesting bootstrap form submission...")
                form_data = f"username={username}&password={password}"
                post_request = f"""POST /bootstrap/login HTTP/1.1\r
Host: {server_ip}:{port}\r
Content-Type: application/x-www-form-urlencoded\r
Content-Length: {len(form_data)}\r
Connection: close\r
\r
{form_data}"""

                connection.write(post_request.encode())
                response = connection.read(max=8192)
                response_str = response.decode('utf-8', errors='ignore')

                if "Bootstrap Authentication Successful" in response_str:
                    print("SUCCESS: Bootstrap form submission working!")
                    return True
                else:
                    print("Bootstrap form submission failed")
                    print(f"Response: {response_str[:300]}")

            else:
                print("Bootstrap page not accessible")

        else:
            print(f"Failed: {lines[0] if lines else 'No response'}")

        return False

    except Exception as e:
        print(f"Error: {e}")
        return False

    finally:
        try:
            connection.close()
            sock.close()
        except:
            pass

def main():
    if len(sys.argv) < 4:
        print("Simple EST TLS Test (SRP Authentication)")
        print("=" * 45)
        print("Usage: python3 simple_tls_test.py <server_ip> <username> <password>")
        print("\nThis tests the working SRP authentication path.")
        sys.exit(1)

    server_ip = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]

    print("Simple EST TLS Test - SRP Authentication")
    print("=" * 50)
    print(f"Server: {server_ip}:8443")
    print(f"Username: {username}")
    print("=" * 50)

    success = test_srp_only(server_ip, username, password)

    print(f"\n{'='*50}")
    if success:
        print("SUCCESS: All SRP-based operations working!")
        print("Your EST server is functional for:")
        print("- SRP Authentication")
        print("- CA Certificate Retrieval")
        print("- Bootstrap Process")
        print("\nReady for certificate enrollment!")
    else:
        print("Some operations failed - check server logs")

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()