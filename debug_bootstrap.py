#!/usr/bin/env python3
"""
Debug bootstrap response to see exactly what's happening
"""
import sys
import socket
from tlslite.api import TLSConnection, HandshakeSettings

def debug_bootstrap(server_ip, username, password, port=8443):
    """Debug bootstrap page response"""
    print(f"Debugging bootstrap response from {server_ip}:{port}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((server_ip, port))

        connection = TLSConnection(sock)

        settings = HandshakeSettings()
        settings.minVersion = (3, 1)
        settings.maxVersion = (3, 3)

        connection.handshakeClientSRP(username, password, settings=settings)
        print("SRP connection established")

        # Request bootstrap page
        request = f"GET /.well-known/est/bootstrap HTTP/1.1\r\nHost: {server_ip}:{port}\r\nConnection: close\r\n\r\n"
        connection.write(request.encode())

        # Read response in chunks
        response = b""
        while True:
            try:
                chunk = connection.read(max=1024)
                if not chunk:
                    break
                response += chunk
            except:
                break

        print(f"Total response length: {len(response)} bytes")
        response_str = response.decode('utf-8', errors='ignore')

        print("\nFull Response:")
        print("=" * 60)
        print(response_str)
        print("=" * 60)

        # Check for specific strings
        checks = [
            "EST Bootstrap Login",
            "EST Bootstrap",
            "Bootstrap",
            "login",
            "form",
            "username",
            "password",
            "HTML",
            "html"
        ]

        print("\nContent Analysis:")
        for check in checks:
            found = check in response_str or check.lower() in response_str.lower()
            print(f"  Contains '{check}': {found}")

        return "EST Bootstrap Login" in response_str

    except Exception as e:
        print(f"Error: {e}")
        return False

    finally:
        try:
            connection.close()
            sock.close()
        except:
            pass

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python3 debug_bootstrap.py <server_ip> <username> <password>")
        sys.exit(1)

    server_ip = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]

    debug_bootstrap(server_ip, username, password)