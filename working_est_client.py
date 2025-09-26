#!/usr/bin/env python3
"""
Working EST Client - Demonstrates Full EST Workflow
This resolves all TLS handshake issues and demonstrates the complete process:
1. CA Certificate Retrieval (/cacerts)
2. SRP Bootstrap Authentication
3. Bootstrap Login Form Submission
4. Certificate Enrollment
"""
import sys
import socket
import base64
import os
from tlslite.api import TLSConnection, HandshakeSettings

class WorkingESTClient:
    def __init__(self, server_ip, port=8443):
        self.server_ip = server_ip
        self.port = port

    def create_connection(self, use_srp=False, username=None, password=None):
        """Create TLS connection with working settings"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((self.server_ip, self.port))

        connection = TLSConnection(sock)
        settings = HandshakeSettings()
        settings.minVersion = (3, 1)  # TLS 1.0
        settings.maxVersion = (3, 3)  # TLS 1.2

        if use_srp and username and password:
            connection.handshakeClientSRP(username, password, settings=settings)
        else:
            # This will fail for /cacerts without SRP, but that's expected
            # /cacerts works with SRP authentication in this implementation
            pass

        return connection, sock

    def test_cacerts_with_srp(self, username, password):
        """Test /cacerts endpoint with SRP authentication (this works!)"""
        print(f"1. Testing CA Certificate Retrieval (/.well-known/est/cacerts)")
        print("   Using SRP authentication...")

        try:
            connection, sock = self.create_connection(use_srp=True, username=username, password=password)

            request = f"GET /.well-known/est/cacerts HTTP/1.1\r\nHost: {self.server_ip}:{self.port}\r\nConnection: close\r\n\r\n"
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
                print("   ✅ SUCCESS: CA certificates retrieved!")

                # Extract and save CA certificates
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
                    print(f"   📁 CA certificates saved to: ca_certificates.p7b")
                return True
            else:
                print("   ❌ FAILED: Unexpected response")
                return False

        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            return False
        finally:
            try:
                connection.close()
                sock.close()
            except:
                pass

    def test_bootstrap_page(self, username, password):
        """Test bootstrap page access"""
        print(f"\n2. Testing Bootstrap Page Access (/.well-known/est/bootstrap)")

        try:
            connection, sock = self.create_connection(use_srp=True, username=username, password=password)

            request = f"GET /.well-known/est/bootstrap HTTP/1.1\r\nHost: {self.server_ip}:{self.port}\r\nConnection: close\r\n\r\n"
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

            if "EST Bootstrap Login" in response_str and "form" in response_str:
                print("   ✅ SUCCESS: Bootstrap login page accessible!")
                print("   📋 HTML form with username/password fields received")
                return True
            else:
                print("   ❌ FAILED: Bootstrap page not accessible")
                return False

        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            return False
        finally:
            try:
                connection.close()
                sock.close()
            except:
                pass

    def test_bootstrap_login(self, username, password):
        """Test bootstrap login form submission"""
        print(f"\n3. Testing Bootstrap Login Form Submission")

        try:
            connection, sock = self.create_connection(use_srp=True, username=username, password=password)

            # Prepare form data
            form_data = f"username={username}&password={password}"
            content_length = len(form_data)

            post_request = f"""POST /bootstrap/login HTTP/1.1\r
Host: {self.server_ip}:{self.port}\r
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
                print("   ✅ SUCCESS: Bootstrap login successful!")
                print("   🔐 Ready for certificate enrollment operations")
                return True
            else:
                print("   ❌ FAILED: Bootstrap login failed")
                print("   📝 Server response preview:")
                lines = response_str.split('\r\n')
                for line in lines[:3]:
                    print(f"      {line}")
                return False

        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            return False
        finally:
            try:
                connection.close()
                sock.close()
            except:
                pass

    def generate_test_csr(self, common_name):
        """Generate a test CSR"""
        print(f"\n4. Generating Certificate Signing Request")
        print(f"   Common Name: {common_name}")

        try:
            key_file = f"{common_name}.key"
            csr_file = f"{common_name}.csr"

            # Generate private key
            result = os.system(f'openssl genrsa -out {key_file} 2048 2>/dev/null')
            if result != 0:
                print("   ❌ FAILED: Could not generate private key")
                return None

            # Generate CSR
            subject = f"/C=US/ST=Test/L=Test/O=TestOrg/CN={common_name}"
            result = os.system(f'openssl req -new -key {key_file} -out {csr_file} -subj "{subject}" 2>/dev/null')
            if result != 0:
                print("   ❌ FAILED: Could not generate CSR")
                return None

            if os.path.exists(csr_file):
                with open(csr_file, 'rb') as f:
                    csr_data = f.read()
                print(f"   ✅ SUCCESS: CSR generated")
                print(f"   📁 Private key: {key_file}")
                print(f"   📁 CSR file: {csr_file}")
                return csr_data
            else:
                print("   ❌ FAILED: CSR file not created")
                return None

        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            return None

    def test_certificate_enrollment(self, username, password, common_name):
        """Test certificate enrollment"""
        print(f"\n5. Testing Certificate Enrollment (/.well-known/est/simpleenroll)")

        # Generate CSR first
        csr_data = self.generate_test_csr(common_name)
        if not csr_data:
            return False

        try:
            connection, sock = self.create_connection(use_srp=True, username=username, password=password)

            # Convert CSR to base64
            csr_b64 = base64.b64encode(csr_data).decode()
            content_length = len(csr_b64)

            post_request = f"""POST /.well-known/est/simpleenroll HTTP/1.1\r
Host: {self.server_ip}:{self.port}\r
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
                print("   ✅ SUCCESS: Certificate enrollment successful!")

                # Extract certificate
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
                    print(f"   📁 Certificate saved to: {cert_file}")

                    # Convert to PEM format
                    pem_file = f"{common_name}_certificate.pem"
                    result = os.system(f'openssl pkcs7 -in {cert_file} -print_certs -out {pem_file} 2>/dev/null')
                    if result == 0:
                        print(f"   📁 PEM certificate: {pem_file}")

                return True
            else:
                print("   ❌ FAILED: Certificate enrollment failed")
                lines = response_str.split('\r\n')
                print(f"   📝 Server response: {lines[0] if lines else 'No response'}")
                return False

        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            return False
        finally:
            try:
                connection.close()
                sock.close()
            except:
                pass

    def run_complete_test(self, username, password, common_name="test-device"):
        """Run complete EST workflow test"""
        print("EST Complete Workflow Test")
        print("=" * 60)
        print(f"Server: {self.server_ip}:{self.port}")
        print(f"Username: {username}")
        print(f"Device: {common_name}")
        print("=" * 60)

        # Run all tests
        test1 = self.test_cacerts_with_srp(username, password)
        test2 = self.test_bootstrap_page(username, password)
        test3 = self.test_bootstrap_login(username, password)
        test4 = self.test_certificate_enrollment(username, password, common_name)

        # Results
        print(f"\n{'='*60}")
        print("TEST RESULTS:")
        print(f"  1. CA Certificate Retrieval:  {'✅ PASS' if test1 else '❌ FAIL'}")
        print(f"  2. Bootstrap Page Access:     {'✅ PASS' if test2 else '❌ FAIL'}")
        print(f"  3. Bootstrap Login:           {'✅ PASS' if test3 else '❌ FAIL'}")
        print(f"  4. Certificate Enrollment:    {'✅ PASS' if test4 else '❌ FAIL'}")

        all_pass = test1 and test2 and test3 and test4
        print(f"\nOVERALL RESULT: {'✅ ALL TESTS PASSED' if all_pass else '❌ SOME TESTS FAILED'}")

        if all_pass:
            print(f"\n🎉 SUCCESS: EST server is fully functional!")
            print(f"Your EST implementation supports:")
            print(f"  - SRP-based bootstrap authentication")
            print(f"  - CA certificate distribution")
            print(f"  - Certificate enrollment workflow")
            print(f"  - TLS 1.2 with compatible cipher suites")
        else:
            print(f"\n⚠️  Some functionality may need attention")

        print("="*60)
        return all_pass

def main():
    if len(sys.argv) < 4:
        print("Working EST Client - Complete Workflow Test")
        print("=" * 50)
        print("Usage: python3 working_est_client.py <server_ip> <username> <password> [common_name]")
        print("\nThis client demonstrates the complete EST workflow:")
        print("1. CA Certificate Retrieval (no auth required in theory, but uses SRP)")
        print("2. SRP Bootstrap Authentication")
        print("3. Bootstrap Login Process")
        print("4. Certificate Enrollment")
        print("\nExample:")
        print("  python3 working_est_client.py 192.168.1.100 testuser testpass123")
        print("  python3 working_est_client.py localhost admin password123 my-device")
        sys.exit(1)

    server_ip = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    common_name = sys.argv[4] if len(sys.argv) >= 5 else "test-device"

    client = WorkingESTClient(server_ip)
    success = client.run_complete_test(username, password, common_name)

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()