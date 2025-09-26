# EST Client Setup and Testing Guide
## Testing Bootstrap and Enrollment from Network Client

This guide covers setting up clients to test the bootstrap and certificate enrollment process with your Python-EST server.

## Client Setup

### Prerequisites on Client Machine
```bash
# Install Python 3 and required packages
sudo apt install python3 python3-pip git -y  # Ubuntu/Debian
# OR
sudo yum install python3 python3-pip git -y  # CentOS/RHEL

# Install OpenSSL for certificate operations
sudo apt install openssl curl -y
```

### Method 1: Using Python TLS Client (Recommended)

#### 1. Setup Client Environment
```bash
# Clone the same repository on client
git clone https://github.com/pranavkumaarofficial/python-est.git
cd python-est

# Create virtual environment
python3 -m venv est-client-env
source est-client-env/bin/activate

# Install dependencies
pip install tlslite-ng requests cryptography
```

#### 2. Create Enhanced Test Client
```bash
# Create comprehensive test client
cat > est_client_test.py << 'EOF'
#!/usr/bin/env python3
"""
Comprehensive EST Client Test Tool
Tests bootstrap authentication and certificate enrollment
"""
import sys
import socket
import argparse
from tlslite.api import TLSConnection
import base64
import os

class ESTClient:
    def __init__(self, server_ip, port=8443):
        self.server_ip = server_ip
        self.port = port

    def test_cacerts(self):
        """Test /cacerts endpoint (no authentication required)"""
        print(f"Testing /cacerts endpoint on {self.server_ip}:{self.port}")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.server_ip, self.port))

            connection = TLSConnection(sock)
            connection.handshakeClientCert()

            request = f"GET /.well-known/est/cacerts HTTP/1.1\r\nHost: {self.server_ip}:{self.port}\r\nConnection: close\r\n\r\n"
            connection.write(request.encode())

            response = connection.read(max=8192)
            response_str = response.decode('utf-8', errors='ignore')

            if "HTTP/1.1 200" in response_str and "application/pkcs7-mime" in response_str:
                print("✅ /cacerts endpoint working - CA certificates retrieved!")
                # Extract and save CA certificates
                lines = response_str.split('\r\n')
                content_start = False
                ca_cert_data = ""
                for line in lines:
                    if content_start:
                        ca_cert_data += line
                    if line == "":
                        content_start = True

                if ca_cert_data:
                    with open('ca_certs.p7b', 'w') as f:
                        f.write("-----BEGIN PKCS7-----\n")
                        f.write(ca_cert_data)
                        f.write("-----END PKCS7-----\n")
                    print("📁 CA certificates saved to ca_certs.p7b")
                return True
            else:
                print("❌ /cacerts failed")
                print(f"Response: {response_str[:300]}")
                return False

        except Exception as e:
            print(f"❌ /cacerts test failed: {e}")
            return False
        finally:
            try:
                connection.close()
                sock.close()
            except:
                pass

    def test_bootstrap_authentication(self, username, password):
        """Test SRP bootstrap authentication"""
        print(f"\nTesting SRP bootstrap authentication for user: {username}")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.server_ip, self.port))

            connection = TLSConnection(sock)

            print("Performing SRP handshake...")
            connection.handshakeClientSRP(username, password)

            print("✅ SRP authentication successful!")
            print(f"Connected with cipher: {connection.getCipherName()}")
            print(f"SRP username: {connection.session.srpUsername}")

            # Test bootstrap page access
            request = f"GET /.well-known/est/bootstrap HTTP/1.1\r\nHost: {self.server_ip}:{self.port}\r\nConnection: close\r\n\r\n"
            connection.write(request.encode())

            response = connection.read(max=8192)
            response_str = response.decode('utf-8', errors='ignore')

            if "EST Bootstrap Login" in response_str:
                print("✅ Bootstrap page accessible with SRP authentication!")
                return connection, True
            else:
                print("❌ Bootstrap page access failed")
                return None, False

        except Exception as e:
            print(f"❌ SRP authentication failed: {e}")
            return None, False

    def test_bootstrap_login_form(self, username, password):
        """Test bootstrap login form submission"""
        print(f"\nTesting bootstrap login form submission...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.server_ip, self.port))

            connection = TLSConnection(sock)
            connection.handshakeClientSRP(username, password)

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

            response = connection.read(max=8192)
            response_str = response.decode('utf-8', errors='ignore')

            if "Bootstrap Authentication Successful" in response_str:
                print("✅ Bootstrap login form submission successful!")
                print("🔐 Ready for certificate enrollment!")
                return True
            else:
                print("❌ Bootstrap login failed")
                print(f"Response: {response_str[:500]}")
                return False

        except Exception as e:
            print(f"❌ Bootstrap login test failed: {e}")
            return False
        finally:
            try:
                connection.close()
                sock.close()
            except:
                pass

    def generate_csr(self, common_name):
        """Generate a simple CSR for testing"""
        print(f"\n🔧 Generating CSR for {common_name}...")

        key_file = f"{common_name}.key"
        csr_file = f"{common_name}.csr"

        # Generate private key
        os.system(f'openssl genrsa -out {key_file} 2048')

        # Generate CSR
        subject = f"/C=US/ST=State/L=City/O=Organization/CN={common_name}"
        os.system(f'openssl req -new -key {key_file} -out {csr_file} -subj "{subject}"')

        if os.path.exists(csr_file):
            with open(csr_file, 'rb') as f:
                csr_data = f.read()
            print(f"✅ CSR generated: {csr_file}")
            return csr_data
        else:
            print("❌ CSR generation failed")
            return None

    def test_certificate_enrollment(self, username, password, common_name):
        """Test certificate enrollment via /simpleenroll"""
        print(f"\nTesting certificate enrollment for {common_name}...")

        # Generate CSR
        csr_data = self.generate_csr(common_name)
        if not csr_data:
            return False

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.server_ip, self.port))

            connection = TLSConnection(sock)
            connection.handshakeClientSRP(username, password)

            # Convert CSR to base64 for EST
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

            response = connection.read(max=8192)
            response_str = response.decode('utf-8', errors='ignore')

            if "HTTP/1.1 200" in response_str and "application/pkcs7-mime" in response_str:
                print("✅ Certificate enrollment successful!")

                # Extract certificate
                lines = response_str.split('\r\n')
                content_start = False
                cert_data = ""
                for line in lines:
                    if content_start:
                        cert_data += line
                    if line == "":
                        content_start = True

                if cert_data:
                    cert_file = f"{common_name}_cert.p7b"
                    with open(cert_file, 'w') as f:
                        f.write("-----BEGIN PKCS7-----\n")
                        f.write(cert_data)
                        f.write("-----END PKCS7-----\n")
                    print(f"📁 Certificate saved to {cert_file}")

                    # Extract PEM certificate
                    os.system(f'openssl pkcs7 -in {cert_file} -print_certs -out {common_name}_cert.pem')
                    print(f"📁 PEM certificate saved to {common_name}_cert.pem")

                return True
            else:
                print("❌ Certificate enrollment failed")
                print(f"Response: {response_str[:500]}")
                return False

        except Exception as e:
            print(f"❌ Certificate enrollment failed: {e}")
            return False
        finally:
            try:
                connection.close()
                sock.close()
            except:
                pass

def main():
    parser = argparse.ArgumentParser(description='EST Client Test Tool')
    parser.add_argument('server_ip', help='EST server IP address')
    parser.add_argument('-p', '--port', type=int, default=8443, help='EST server port (default: 8443)')
    parser.add_argument('-u', '--username', default='testuser', help='SRP username (default: testuser)')
    parser.add_argument('-P', '--password', default='testpass123', help='SRP password (default: testpass123)')
    parser.add_argument('-c', '--common-name', default='test-device', help='Common name for certificate (default: test-device)')
    parser.add_argument('--cacerts-only', action='store_true', help='Test only /cacerts endpoint')

    args = parser.parse_args()

    client = ESTClient(args.server_ip, args.port)

    print("EST Client Test Tool")
    print("=" * 50)
    print(f"Server: {args.server_ip}:{args.port}")
    print(f"Username: {args.username}")
    print("=" * 50)

    # Test /cacerts (no auth required)
    cacerts_ok = client.test_cacerts()

    if args.cacerts_only:
        sys.exit(0 if cacerts_ok else 1)

    # Test SRP authentication and bootstrap
    conn, srp_ok = client.test_bootstrap_authentication(args.username, args.password)
    if conn:
        conn.close()

    # Test bootstrap login form
    login_ok = client.test_bootstrap_login_form(args.username, args.password)

    # Test certificate enrollment
    enroll_ok = client.test_certificate_enrollment(args.username, args.password, args.common_name)

    print("\n" + "=" * 50)
    print("TEST RESULTS:")
    print(f"  CA Certificates:     {'✅ PASS' if cacerts_ok else '❌ FAIL'}")
    print(f"  SRP Authentication:  {'✅ PASS' if srp_ok else '❌ FAIL'}")
    print(f"  Bootstrap Login:     {'✅ PASS' if login_ok else '❌ FAIL'}")
    print(f"  Certificate Enroll:  {'✅ PASS' if enroll_ok else '❌ FAIL'}")

    all_pass = cacerts_ok and srp_ok and login_ok and enroll_ok
    print(f"\nOVERALL: {'✅ ALL TESTS PASSED' if all_pass else '❌ SOME TESTS FAILED'}")

    sys.exit(0 if all_pass else 1)

if __name__ == '__main__':
    main()
EOF

chmod +x est_client_test.py
```

#### 3. Run Client Tests
```bash
# Replace YOUR_SERVER_IP with your EST server's IP address
# Test all functionality
python est_client_test.py YOUR_SERVER_IP -u testuser -P testpass123

# Test only CA certificates (no auth required)
python est_client_test.py YOUR_SERVER_IP --cacerts-only

# Test with custom user
python est_client_test.py YOUR_SERVER_IP -u your_username -P your_password -c my-device-01
```

### Method 2: Using cURL for Basic Testing

#### Test CA Certificates (No Auth Required)
```bash
# Replace YOUR_SERVER_IP with your server's IP
curl -k https://YOUR_SERVER_IP:8443/.well-known/est/cacerts

# Save CA certificates
curl -k https://YOUR_SERVER_IP:8443/.well-known/est/cacerts -o ca_certs.p7b
```

#### Test Bootstrap Page Access
```bash
# This will fail without proper SRP authentication
curl -k https://YOUR_SERVER_IP:8443/.well-known/est/bootstrap
```

### Method 3: Browser Testing

#### Access Bootstrap Page
1. Open browser and navigate to: `https://YOUR_SERVER_IP:8443/bootstrap`
2. Accept security warning (self-signed certificate)
3. **Note**: This will fail with "handshake failure" because browsers don't support SRP authentication

### Expected Results

#### Successful CA Certificates Test
- HTTP 200 response
- Content-Type: application/pkcs7-mime
- Base64-encoded PKCS#7 certificate data

#### Successful SRP Authentication
- TLS handshake completes with SRP cipher
- Bootstrap page returns HTML form
- Form submission returns success message

#### Successful Certificate Enrollment
- HTTP 200 response
- Content-Type: application/pkcs7-mime; smime-type=certs-only
- Base64-encoded PKCS#7 certificate response

## Troubleshooting Client Issues

### TLS Handshake Failures
```bash
# Check server logs
sudo journalctl -u python-est -f

# Check network connectivity
telnet YOUR_SERVER_IP 8443

# Verify firewall rules on server
sudo ufw status  # Ubuntu
sudo firewall-cmd --list-ports  # CentOS
```

### SRP Authentication Issues
- Verify username/password are correct
- Check SRP user database on server
- Ensure SRP is enabled in server config

### Certificate Enrollment Issues
- Verify SRP authentication works first
- Check CSR format (must be valid PKCS#10)
- Verify CA handler is properly configured

## Security Notes
- Use strong passwords for SRP users
- Test in isolated network environment first
- Monitor server logs during testing
- Clean up test certificates after validation