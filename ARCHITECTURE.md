# Architecture

## Overview

Python-EST is a modular EST (RFC 7030) protocol server with pluggable CA backend support.

## Directory Structure

```
python-est/
├── python_est/           # Main package
│   ├── core/            # EST protocol implementation
│   │   ├── est_handler.py    # HTTP request handler (+ bootstrap)
│   │   ├── secureserver.py   # HTTPS/TLS server (+ SRP support)
│   │   └── helper.py         # Utility functions (+ SRP config)
│   ├── handlers/        # CA integration modules
│   │   ├── openssl_ca_handler_fixed.py  # OpenSSL CA
│   │   ├── mscertsrv_ca_handler.py      # Microsoft ADCS
│   │   └── xca_ca_handler.py            # XCA database
│   ├── config/          # Configuration templates
│   └── tests/           # Test suite
├── main.py              # Server entry point
├── python_est.cfg       # Configuration file (+ SRP/Bootstrap)
├── setup_certs.py       # Certificate generator
├── create_srp_users.py  # SRP user management utility
├── test_bootstrap_client.py  # SRP authentication test client
└── BOOTSTRAP_README.md  # Bootstrap implementation guide
```

## Core Components

### EST Handler (`est_handler.py`)
- Implements EST protocol endpoints
- Handles HTTP requests and responses
- Performs dual authentication (certificates + SRP)
- Bootstrap login page and form processing
- Converts certificates to PKCS#7 format

### Secure Server (`secureserver.py`)
- HTTPS/TLS server with flexible authentication
- Supports TLS 1.2/1.3
- Configurable client certificate requirements
- SRP authentication support

### CA Handlers
- **OpenSSL Handler**: File-based certificate authority
- **ADCS Handler**: Microsoft Certificate Services integration
- **XCA Handler**: XCA database integration

## Data Flow

### Standard EST Flow
```
Client Request → TLS + Client Cert → EST Handler → CA Handler → Certificate Response
```

### Bootstrap Authentication Flow (New!)
```
Client → SRP Handshake → Bootstrap Login → EST Handler → Success Page
```

### Detailed Process
1. **Bootstrap Path**: Client uses SRP authentication → HTML login form → credentials verification
2. **Standard Path**: Client sends HTTPS request with client certificate → certificate validation
3. EST handler routes request to appropriate CA handler based on authentication method
4. CA handler processes certificate request
5. Response returned as PKCS#7 encoded certificate or HTML success page

## Configuration

Configuration is loaded from `python_est.cfg`:

- **Daemon**: Server settings (port, certificates)
- **CAhandler**: CA backend configuration
- **SRP**: Bootstrap authentication database
- **Bootstrap**: Bootstrap endpoint configuration
- **Handler-specific**: Parameters for each CA type

### New Configuration Sections
```ini
[SRP]
userdb = certs/srp_users.db

[Bootstrap]
enabled = true
endpoint = /.well-known/est/bootstrap
```

## Extensibility

New CA handlers can be added by:
1. Implementing the base CA handler interface
2. Adding handler-specific configuration
3. Registering in main configuration file