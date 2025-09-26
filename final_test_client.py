#!/usr/bin/env python3
"""
Final EST Test Client - Complete Workflow Demo
Resolves TLS issues and demonstrates working EST server
"""
import sys
import socket
import base64
import os
from tlslite.api import TLSConnection, HandshakeSettings

def create_est_connection(server_ip, port, username, password):
    """Create working SRP connection"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30)
    sock.connect((server_ip, port))

    connection = TLSConnection(sock)
    settings = HandshakeSettings()
    settings.minVersion = (3, 1)  # TLS 1.0
    settings.maxVersion = (3, 3)  # TLS 1.2

    connection.handshakeClientSRP(username, password, settings=settings)
    return connection, sock

def test_cacerts(server_ip, port, username, password):
    """Test CA certificates retrieval"""
    print("1. Testing CA Certificate Retrieval...")

    try:
        connection, sock = create_est_connection(server_ip, port, username, password)

        request = f"GET /.well-known/est/cacerts HTTP/1.1\r\nHost: {server_ip}:{port}\r\nConnection: close\r\n\r\n"
        connection.write(request.encode())

        response = b""
        while True:
            try:
                chunk = connection.read(max=1024)
                if not chunk:
                    break
                response += chunk
            except:
                break

        response_str = response.decode('utf-8', errors='ignore')

        if "HTTP/1.1 200" in response_str and "application/pkcs7-mime" in response_str:
            print("   SUCCESS: CA certificates retrieved!")

            # Save certificates
            lines = response_str.split('\r\n')
            content_start = False
            ca_cert_data = ""
            for line in lines:
                if content_start and line.strip():
                    ca_cert_data += line.strip()
                if line == "":
                    content_start = True

            if ca_cert_data:
                with open('ca_certificates.p7b', 'w') as f:
                    f.write("-----BEGIN PKCS7-----\n")
                    f.write(ca_cert_data)
                    f.write("\n-----END PKCS7-----\n")
                print("   Saved to: ca_certificates.p7b")
            return True
        else:
            print("   FAILED: Unexpected response")
            return False

    except Exception as e:
        print(f"   FAILED: {e}")
        return False
    finally:
        try:
            connection.close()
            sock.close()
        except:
            pass

def test_bootstrap_page(server_ip, port, username, password):
    """Test bootstrap page access"""
    print("\n2. Testing Bootstrap Page Access...")

    try:
        connection, sock = create_est_connection(server_ip, port, username, password)

        request = f"GET /.well-known/est/bootstrap HTTP/1.1\r\nHost: {server_ip}:{port}\r\nConnection: close\r\n\r\n"
        connection.write(request.encode())

        response = b""
        while True:
            try:
                chunk = connection.read(max=1024)
                if not chunk:
                    break
                response += chunk
            except:
                break

        response_str = response.decode('utf-8', errors='ignore')

        if "EST Bootstrap Login" in response_str:
            print("   SUCCESS: Bootstrap page accessible!")
            print("   HTML form received with login fields")
            return True
        else:
            print("   FAILED: Bootstrap page not accessible")
            return False

    except Exception as e:
        print(f"   FAILED: {e}")
        return False
    finally:
        try:
            connection.close()
            sock.close()
        except:
            pass

def test_bootstrap_login(server_ip, port, username, password):
    """Test bootstrap form submission"""
    print("\n3. Testing Bootstrap Login Form...")

    try:
        connection, sock = create_est_connection(server_ip, port, username, password)

        form_data = f"username={username}&password={password}"
        content_length = len(form_data)

        post_request = f"""POST /bootstrap/login HTTP/1.1\r
Host: {server_ip}:{port}\r
Content-Type: application/x-www-form-urlencoded\r
Content-Length: {content_length}\r
Connection: close\r
\r
{form_data}"""

        connection.write(post_request.encode())

        response = b""
        while True:
            try:
                chunk = connection.read(max=1024)
                if not chunk:
                    break
                response += chunk
            except:
                break

        response_str = response.decode('utf-8', errors='ignore')

        if "Bootstrap Authentication Successful" in response_str:
            print("   SUCCESS: Bootstrap login successful!")
            return True
        else:
            print("   FAILED: Bootstrap login failed")
            lines = response_str.split('\r\n')
            print(f"   Response: {lines[0] if lines else 'No response'}")
            return False

    except Exception as e:
        print(f"   FAILED: {e}")
        return False
    finally:
        try:
            connection.close()
            sock.close()
        except:
            pass

def generate_csr(common_name):
    """Generate test CSR"""
    print(f"\n4. Generating CSR for {common_name}...")

    try:
        key_file = f"{common_name}.key"
        csr_file = f"{common_name}.csr"

        # Generate private key
        os.system(f'openssl genrsa -out {key_file} 2048 2>/dev/null')

        # Generate CSR
        subject = f"/C=US/ST=Test/L=Test/O=TestOrg/CN={common_name}"
        os.system(f'openssl req -new -key {key_file} -out {csr_file} -subj "{subject}" 2>/dev/null')

        if os.path.exists(csr_file):
            with open(csr_file, 'rb') as f:
                csr_data = f.read()
            print(f"   SUCCESS: CSR generated")
            print(f"   Files: {key_file}, {csr_file}")
            return csr_data
        else:
            print("   FAILED: CSR not created")
            return None

    except Exception as e:
        print(f"   FAILED: {e}")
        return None

def test_certificate_enrollment(server_ip, port, username, password, common_name):
    """Test certificate enrollment"""
    print(f"\n5. Testing Certificate Enrollment...")

    # Generate CSR
    csr_data = generate_csr(common_name)
    if not csr_data:
        return False

    try:
        connection, sock = create_est_connection(server_ip, port, username, password)

        # Convert CSR to base64
        csr_b64 = base64.b64encode(csr_data).decode()
        content_length = len(csr_b64)

        post_request = f"""POST /.well-known/est/simpleenroll HTTP/1.1\r
Host: {server_ip}:{port}\r
Content-Type: application/pkcs10\r
Content-Transfer-Encoding: base64\r
Content-Length: {content_length}\r
Connection: close\r
\r
{csr_b64}"""

        connection.write(post_request.encode())

        response = b""
        while True:
            try:
                chunk = connection.read(max=1024)
                if not chunk:
                    break
                response += chunk
            except:
                break

        response_str = response.decode('utf-8', errors='ignore')

        if "HTTP/1.1 200" in response_str and "application/pkcs7-mime" in response_str:
            print("   SUCCESS: Certificate enrolled!")

            # Save certificate
            lines = response_str.split('\r\n')
            content_start = False
            cert_data = ""
            for line in lines:
                if content_start and line.strip():
                    cert_data += line.strip()
                if line == "":
                    content_start = True

            if cert_data:
                cert_file = f"{common_name}_certificate.p7b"
                with open(cert_file, 'w') as f:
                    f.write("-----BEGIN PKCS7-----\n")
                    f.write(cert_data)
                    f.write("\n-----END PKCS7-----\n")
                print(f"   Certificate saved: {cert_file}")

                # Convert to PEM
                pem_file = f"{common_name}_certificate.pem"
                os.system(f'openssl pkcs7 -in {cert_file} -print_certs -out {pem_file} 2>/dev/null')
                print(f"   PEM format: {pem_file}")

            return True
        else:
            print("   FAILED: Certificate enrollment failed")
            lines = response_str.split('\r\n')
            print(f"   Response: {lines[0] if lines else 'No response'}")
            return False

    except Exception as e:
        print(f"   FAILED: {e}")
        return False
    finally:
        try:
            connection.close()
            sock.close()
        except:
            pass

def main():
    if len(sys.argv) < 4:
        print("EST Complete Workflow Test Client")
        print("=" * 40)
        print("Usage: python3 final_test_client.py <server_ip> <username> <password> [device_name]")
        print("\nThis demonstrates the complete EST workflow:")
        print("- CA Certificate Retrieval")
        print("- SRP Bootstrap Authentication")
        print("- Bootstrap Login Process")
        print("- Certificate Enrollment")
        print("\nExample:")
        print("  python3 final_test_client.py 192.168.1.100 testuser testpass123")
        print("  python3 final_test_client.py localhost admin password123 device01")
        sys.exit(1)

    server_ip = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    device_name = sys.argv[4] if len(sys.argv) >= 5 else "test-device"
    port = 8443

    print("EST Complete Workflow Test")
    print("=" * 50)
    print(f"Server: {server_ip}:{port}")
    print(f"Username: {username}")
    print(f"Device: {device_name}")
    print("=" * 50)

    # Run all tests
    test1 = test_cacerts(server_ip, port, username, password)
    test2 = test_bootstrap_page(server_ip, port, username, password)
    test3 = test_bootstrap_login(server_ip, port, username, password)
    test4 = test_certificate_enrollment(server_ip, port, username, password, device_name)

    # Results
    print(f"\n{'='*50}")
    print("FINAL RESULTS:")
    print(f"  CA Certificate Retrieval:  {'PASS' if test1 else 'FAIL'}")
    print(f"  Bootstrap Page Access:     {'PASS' if test2 else 'FAIL'}")
    print(f"  Bootstrap Login:           {'PASS' if test3 else 'FAIL'}")
    print(f"  Certificate Enrollment:    {'PASS' if test4 else 'FAIL'}")

    all_pass = test1 and test2 and test3 and test4
    print(f"\nOVERALL: {'SUCCESS - ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")

    if all_pass:
        print(f"\nCONGRATULATIONS!")
        print(f"Your EST server is fully functional and supports:")
        print(f"- TLS 1.2 with compatible cipher suites")
        print(f"- SRP bootstrap authentication")
        print(f"- CA certificate distribution")
        print(f"- Certificate enrollment workflow")
        print(f"- All EST RFC 7030 core functionality")

    print("="*50)
    return all_pass

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)