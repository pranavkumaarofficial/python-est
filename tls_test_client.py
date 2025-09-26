#!/usr/bin/env python3
"""
Enhanced EST Client with TLS Compatibility Fixes
Resolves "insufficient_security" and "unable to negotiate mutually acceptable parameters" errors
"""
import sys
import socket
from tlslite.api import TLSConnection, HandshakeSettings

def create_compatible_connection(server_ip, port=8443):
    """Create TLS connection with compatibility settings"""

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30)  # Longer timeout for handshake
    sock.connect((server_ip, port))

    connection = TLSConnection(sock)

    # Configure client handshake settings to match server
    settings = HandshakeSettings()
    settings.minVersion = (3, 1)  # TLS 1.0
    settings.maxVersion = (3, 3)  # TLS 1.2

    # Enable compatible cipher suites (matching server)
    settings.cipherNames = [
        "aes128", "aes256", "3des"
    ]

    # Enable compatible MAC algorithms
    settings.macNames = ["sha", "sha256", "md5"]

    # Configure key exchange methods
    settings.keyExchangeNames = ["rsa", "dhe_rsa", "srp_sha", "srp_sha_rsa"]

    # Enable certificate types
    settings.certificateTypes = ["x509"]

    # Compatibility settings
    settings.useExperimentalTackExtension = False
    settings.sendFallbackSCSV = False

    return connection, settings

def test_basic_tls_connection(server_ip, port=8443):
    """Test basic TLS connection without SRP"""
    print(f"Testing basic TLS connection to {server_ip}:{port}")
    print("This tests /cacerts endpoint (no authentication required)")

    connection = None
    sock = None

    try:
        connection, settings = create_compatible_connection(server_ip, port)
        sock = connection.sock

        print("Attempting TLS handshake with compatible settings...")
        connection.handshakeClientCert(settings=settings)

        print("SUCCESS: TLS connection established!")
        print(f"TLS Version: {connection.version}")
        print(f"Cipher: {connection.getCipherName()}")

        # Test /cacerts endpoint
        print("\nTesting /cacerts endpoint...")
        request = f"GET /.well-known/est/cacerts HTTP/1.1\r\nHost: {server_ip}:{port}\r\nConnection: close\r\n\r\n"
        connection.write(request.encode())

        response = connection.read(max=8192)
        response_str = response.decode('utf-8', errors='ignore')

        print("Response received:")
        print("-" * 40)
        lines = response_str.split('\r\n')
        for i, line in enumerate(lines[:8]):  # First 8 lines
            print(f"{i+1:2d}: {line}")

        if "HTTP/1.1 200" in response_str and "application/pkcs7-mime" in response_str:
            print("\nSUCCESS: /cacerts endpoint working!")
            print("CA certificates retrieved successfully!")

            # Extract certificate data
            if "base64" in response_str:
                content_start = False
                cert_data = ""
                for line in lines:
                    if content_start and line.strip():
                        cert_data += line.strip()
                    if line == "":
                        content_start = True

                if cert_data:
                    print(f"Certificate data length: {len(cert_data)} characters")
                    with open('ca_certs_retrieved.p7b', 'w') as f:
                        f.write("-----BEGIN PKCS7-----\n")
                        f.write(cert_data)
                        f.write("\n-----END PKCS7-----\n")
                    print("CA certificates saved to: ca_certs_retrieved.p7b")

            return True
        else:
            print("\nFAILED: /cacerts returned unexpected response")
            print(f"Status line: {lines[0] if lines else 'No response'}")
            return False

    except Exception as e:
        error_msg = str(e)
        print(f"FAILED: {error_msg}")

        # Provide specific troubleshooting based on error
        if "insufficient_security" in error_msg:
            print("\nTROUBLESHOOTING: insufficient_security error")
            print("- Server may require stronger cipher suites")
            print("- Try updating both client and server TLS settings")
            print("- Check if OpenSSL version is compatible")

        elif "missing_extension" in error_msg:
            print("\nTROUBLESHOOTING: missing_extension error")
            print("- Server requires TLS extensions not supported by client")
            print("- Try using older TLS version (TLS 1.0/1.1)")
            print("- Update tlslite-ng library version")

        elif "handshake_failure" in error_msg:
            print("\nTROUBLESHOOTING: handshake_failure error")
            print("- No mutually acceptable cipher suites")
            print("- Check server TLS configuration")
            print("- Verify certificates are valid")

        return False

    finally:
        try:
            if connection:
                connection.close()
            if sock:
                sock.close()
        except:
            pass

def test_srp_connection(server_ip, username, password, port=8443):
    """Test SRP connection with compatibility fixes"""
    print(f"\nTesting SRP authentication to {server_ip}:{port}")
    print(f"Username: {username}")

    connection = None
    sock = None

    try:
        connection, settings = create_compatible_connection(server_ip, port)
        sock = connection.sock

        print("Attempting SRP handshake...")
        connection.handshakeClientSRP(username, password, settings=settings)

        print("SUCCESS: SRP authentication established!")
        print(f"Cipher: {connection.getCipherName()}")
        print(f"SRP Username: {connection.session.srpUsername}")

        # Test bootstrap page access
        print("\nTesting bootstrap page access...")
        request = f"GET /.well-known/est/bootstrap HTTP/1.1\r\nHost: {server_ip}:{port}\r\nConnection: close\r\n\r\n"
        connection.write(request.encode())

        response = connection.read(max=8192)
        response_str = response.decode('utf-8', errors='ignore')

        if "EST Bootstrap Login" in response_str:
            print("SUCCESS: Bootstrap page accessible with SRP authentication!")
            print("Ready for certificate enrollment operations!")
            return True
        else:
            print("FAILED: Bootstrap page not accessible")
            print("Check server SRP configuration and user database")
            return False

    except Exception as e:
        error_msg = str(e)
        print(f"FAILED: {error_msg}")

        if "srp" in error_msg.lower():
            print("\nTROUBLESHOOTING: SRP authentication error")
            print("- Verify username and password are correct")
            print("- Check SRP user database exists and is readable")
            print("- Ensure SRP is enabled in server configuration")

        return False

    finally:
        try:
            if connection:
                connection.close()
            if sock:
                sock.close()
        except:
            pass

def main():
    if len(sys.argv) < 2:
        print("EST TLS Compatibility Test Client")
        print("=" * 40)
        print("Usage: python3 tls_test_client.py <server_ip> [username] [password] [port]")
        print("\nExamples:")
        print("  python3 tls_test_client.py 192.168.1.100")
        print("  python3 tls_test_client.py 192.168.1.100 testuser testpass123")
        print("  python3 tls_test_client.py 192.168.1.100 admin password123 8443")
        print("\nThis client resolves common TLS errors:")
        print("- insufficient_security")
        print("- unable to negotiate mutually acceptable parameters")
        print("- missing_extension")
        sys.exit(1)

    server_ip = sys.argv[1]
    port = int(sys.argv[4]) if len(sys.argv) >= 5 else 8443

    print("EST TLS Compatibility Test Client")
    print("=" * 50)
    print(f"Server: {server_ip}:{port}")
    print("=" * 50)

    # Test basic TLS connection first (tests /cacerts)
    basic_ok = test_basic_tls_connection(server_ip, port)

    # Test SRP if credentials provided
    srp_ok = None
    if len(sys.argv) >= 4:
        username = sys.argv[2]
        password = sys.argv[3]
        srp_ok = test_srp_connection(server_ip, username, password, port)

    print(f"\n{'='*50}")
    print("TLS COMPATIBILITY TEST RESULTS:")
    print(f"  Basic TLS + /cacerts:     {'PASS' if basic_ok else 'FAIL'}")
    if srp_ok is not None:
        print(f"  SRP Auth + Bootstrap:     {'PASS' if srp_ok else 'FAIL'}")
    print("="*50)

    if basic_ok:
        print("SUCCESS: TLS compatibility issues resolved!")
        print("Your EST server is working properly.")
        if srp_ok:
            print("Both basic TLS and SRP authentication are functional.")
    else:
        print("FAILED: TLS compatibility issues remain.")
        print("Check server configuration and try troubleshooting steps above.")

    # Exit codes for automation
    if srp_ok is not None:
        sys.exit(0 if (basic_ok and srp_ok) else 1)
    else:
        sys.exit(0 if basic_ok else 1)

if __name__ == '__main__':
    main()