# TLS Handshake Error Fixes
## Resolving "insufficient_security" and "unable to negotiate mutually acceptable parameters"

These errors occur when the TLS client and server cannot agree on compatible cipher suites, TLS versions, or key exchange methods.

## Root Cause Analysis

The errors indicate:
1. **insufficient_security**: Client/server cipher suites don't meet security requirements
2. **missing_extension**: Required TLS extensions (like supported_groups) are missing
3. **unable to negotiate mutually acceptable parameters**: No common cipher suites found

## Fix 1: Update HandshakeSettings in helper.py

Edit `python_est/core/helper.py` to configure more compatible TLS settings:

```python
def hssrv_options_get(logger, config_dic):
    """ get parameters for handshake server """
    logger.debug('hssrv_options_get()')

    hs_settings = HandshakeSettings()

    # Configure TLS versions for better compatibility
    hs_settings.minVersion = (3, 1)  # TLS 1.0
    hs_settings.maxVersion = (3, 3)  # TLS 1.2 (avoid TLS 1.3 compatibility issues)

    # Enable more cipher suites for compatibility
    hs_settings.cipherNames = [
        "aes128", "aes256", "3des",
        "sha", "sha256",
        "rsa", "srp_sha", "srp_sha_rsa"
    ]

    # Configure key exchange methods
    hs_settings.keyExchangeNames = ["rsa", "dhe_rsa", "srp_sha", "srp_sha_rsa"]

    # Enable more certificate types
    hs_settings.certificateTypes = ["x509"]

    # Configure DH parameters for better compatibility
    hs_settings.dhParams = None  # Use default

    # Enable backward compatibility
    hs_settings.useExperimentalTackExtension = False
    hs_settings.sendFallbackSCSV = False

    option_dic = {}
    if 'Daemon' in config_dic:
        if 'cert_file' in config_dic['Daemon'] and 'key_file' in config_dic['Daemon']:
            option_dic['certChain'] = config_dic['Daemon']['cert_file']
            option_dic['privateKey'] = config_dic['Daemon']['key_file']
            option_dic['sessionCache'] = SessionCache()
            option_dic['alpn'] = [bytearray(b'http/1.1')]
            option_dic['settings'] = hs_settings
            option_dic['reqCert'] = False  # Allow bootstrap without client cert
            option_dic['sni'] = None
        else:
            logger.error('Helper.hssrv_options_get(): incomplete Daemon configuration in config file')
    else:
        logger.error('Helper.hssrv_options_get(): Daemon specified but not configured in config file')

    if 'SRP' in config_dic:
        if 'userdb' in config_dic['SRP']:
            try:
                srp_db = VerifierDB(config_dic['SRP']['userdb'])
                srp_db.open()
                option_dic['verifierDB'] = srp_db
            except BaseException as err:
                logger.error('Helper.hssrv_options_get(): SRP database {0} could not get loaded.'.format(config_dic['SRP']['userdb']))
                logger.error('Helper.hssrv_options_get(): Error: {0}'.format(err))

    logger.debug('hssrv_options_get() ended')
    return option_dic
```

## Fix 2: Enhanced Client Configuration

Create an improved client that handles TLS compatibility better:

```python
#!/usr/bin/env python3
"""
Enhanced EST Client with TLS Compatibility Fixes
"""
import sys
import socket
from tlslite.api import TLSConnection, HandshakeSettings

def create_compatible_connection(server_ip, port=8443):
    """Create TLS connection with compatibility settings"""

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30)  # Longer timeout
    sock.connect((server_ip, port))

    connection = TLSConnection(sock)

    # Configure client handshake settings
    settings = HandshakeSettings()
    settings.minVersion = (3, 1)  # TLS 1.0
    settings.maxVersion = (3, 3)  # TLS 1.2

    # Enable compatible cipher suites
    settings.cipherNames = [
        "aes128", "aes256", "3des",
        "sha", "sha256",
        "rsa", "srp_sha", "srp_sha_rsa"
    ]

    # Configure key exchange
    settings.keyExchangeNames = ["rsa", "dhe_rsa", "srp_sha", "srp_sha_rsa"]

    return connection, settings

def test_basic_tls_connection(server_ip, port=8443):
    """Test basic TLS connection without SRP"""
    print(f"Testing basic TLS connection to {server_ip}:{port}")

    try:
        connection, settings = create_compatible_connection(server_ip, port)

        print("Attempting TLS handshake...")
        connection.handshakeClientCert(settings=settings)

        print("SUCCESS: TLS connection established!")
        print(f"TLS Version: {connection.version}")
        print(f"Cipher: {connection.getCipherName()}")

        # Test /cacerts
        request = f"GET /.well-known/est/cacerts HTTP/1.1\r\nHost: {server_ip}:{port}\r\nConnection: close\r\n\r\n"
        connection.write(request.encode())

        response = connection.read(max=8192)
        response_str = response.decode('utf-8', errors='ignore')

        if "HTTP/1.1 200" in response_str:
            print("SUCCESS: /cacerts endpoint working!")
            return True
        else:
            print("FAILED: /cacerts returned error")
            print(f"Response: {response_str[:300]}")
            return False

    except Exception as e:
        print(f"FAILED: {e}")
        return False
    finally:
        try:
            connection.close()
            sock.close()
        except:
            pass

def test_srp_connection(server_ip, username, password, port=8443):
    """Test SRP connection with compatibility fixes"""
    print(f"\nTesting SRP connection to {server_ip}:{port}")

    try:
        connection, settings = create_compatible_connection(server_ip, port)

        print("Attempting SRP handshake...")
        connection.handshakeClientSRP(username, password, settings=settings)

        print("SUCCESS: SRP authentication!")
        print(f"Cipher: {connection.getCipherName()}")
        print(f"SRP Username: {connection.session.srpUsername}")

        # Test bootstrap page
        request = f"GET /bootstrap HTTP/1.1\r\nHost: {server_ip}:{port}\r\nConnection: close\r\n\r\n"
        connection.write(request.encode())

        response = connection.read(max=8192)
        response_str = response.decode('utf-8', errors='ignore')

        if "EST Bootstrap Login" in response_str:
            print("SUCCESS: Bootstrap page accessible!")
            return True
        else:
            print("FAILED: Bootstrap page not accessible")
            return False

    except Exception as e:
        print(f"FAILED: {e}")
        return False
    finally:
        try:
            connection.close()
            sock.close()
        except:
            pass

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 tls_test_client.py <server_ip> [username] [password]")
        sys.exit(1)

    server_ip = sys.argv[1]

    # Test basic TLS first
    basic_ok = test_basic_tls_connection(server_ip)

    # Test SRP if credentials provided
    if len(sys.argv) >= 4:
        username = sys.argv[2]
        password = sys.argv[3]
        srp_ok = test_srp_connection(server_ip, username, password)
    else:
        srp_ok = None

    print(f"\n{'='*50}")
    print("TLS TEST RESULTS:")
    print(f"  Basic TLS:      {'PASS' if basic_ok else 'FAIL'}")
    if srp_ok is not None:
        print(f"  SRP Auth:       {'PASS' if srp_ok else 'FAIL'}")

    print(f"\nOVERALL: {'SUCCESS' if basic_ok else 'FAILED'}")
```

## Fix 3: Alternative TLS Configuration

If the above doesn't work, try this more permissive configuration:

```python
# In helper.py - Ultra-compatible settings
hs_settings = HandshakeSettings()
hs_settings.minVersion = (3, 0)  # SSL 3.0 (very permissive)
hs_settings.maxVersion = (3, 4)  # Up to TLS 1.3
hs_settings.cipherNames = ["aes128", "aes256", "3des", "rc4", "null"]
hs_settings.macNames = ["sha", "sha256", "md5"]
hs_settings.keyExchangeNames = ["rsa", "dhe_rsa", "srp_sha", "srp_sha_rsa", "ecdhe_rsa"]
hs_settings.sendFallbackSCSV = True
```

## Fix 4: OpenSSL Version Compatibility

Check and potentially downgrade OpenSSL for compatibility:

```bash
# Check current OpenSSL version
openssl version

# If using OpenSSL 3.x, you might need compatibility mode
export OPENSSL_CONF=/dev/null

# Or create compatibility config
cat > /tmp/openssl_compat.conf << EOF
openssl_conf = openssl_init

[openssl_init]
providers = provider_sect

[provider_sect]
default = default_sect
legacy = legacy_sect

[default_sect]
activate = 1

[legacy_sect]
activate = 1
EOF

export OPENSSL_CONF=/tmp/openssl_compat.conf
```

## Fix 5: Use Specific TLS Library Versions

Install specific compatible versions:

```bash
# Uninstall current version
pip uninstall tlslite-ng

# Install specific compatible version
pip install tlslite-ng==0.8.0a40

# Or try alternative version
pip install tlslite-ng==0.7.6
```

## Testing the Fixes

1. **Apply Fix 1**: Update `helper.py` with the enhanced HandshakeSettings
2. **Restart Server**: Kill and restart the EST server
3. **Test with Enhanced Client**: Use the improved client code
4. **Check Server Logs**: Monitor for different error messages

## Quick Test Commands

```bash
# Test basic connectivity first
telnet YOUR_SERVER_IP 8443

# Test with OpenSSL client
echo "GET / HTTP/1.1\r\n\r\n" | openssl s_client -connect YOUR_SERVER_IP:8443 -cipher 'ALL:!aNULL:!eNULL'

# Test with specific cipher
echo "GET / HTTP/1.1\r\n\r\n" | openssl s_client -connect YOUR_SERVER_IP:8443 -cipher 'AES128-SHA'
```

## Most Common Working Solution

Based on common issues, try this specific fix first:

1. **Update `helper.py`** with the enhanced settings from Fix 1
2. **Set TLS version explicitly** to avoid TLS 1.3 issues
3. **Use the enhanced client** with compatible settings
4. **Ensure OpenSSL compatibility** with legacy providers

This should resolve the "insufficient_security" and "unable to negotiate mutually acceptable parameters" errors.