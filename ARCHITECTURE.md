# Architecture

## Overview

Python-EST is a modular EST (RFC 7030) protocol server with pluggable CA backend support.

## Directory Structure

```
python-est/
├── python_est/           # Main package
│   ├── core/            # EST protocol implementation
│   │   ├── est_handler.py    # HTTP request handler
│   │   ├── secureserver.py   # HTTPS/TLS server
│   │   └── helper.py         # Utility functions
│   ├── handlers/        # CA integration modules
│   │   ├── openssl_ca_handler_fixed.py  # OpenSSL CA
│   │   ├── mscertsrv_ca_handler.py      # Microsoft ADCS
│   │   └── xca_ca_handler.py            # XCA database
│   ├── config/          # Configuration templates
│   └── tests/           # Test suite
├── main.py              # Server entry point
├── python_est.cfg       # Configuration file
└── setup_certs.py       # Certificate generator
```

## Core Components

### EST Handler (`est_handler.py`)
- Implements EST protocol endpoints
- Handles HTTP requests and responses
- Performs client certificate authentication
- Converts certificates to PKCS#7 format

### Secure Server (`secureserver.py`) 
- HTTPS/TLS server with client certificate validation
- Supports TLS 1.2/1.3
- Enforces mutual TLS authentication

### CA Handlers
- **OpenSSL Handler**: File-based certificate authority
- **ADCS Handler**: Microsoft Certificate Services integration
- **XCA Handler**: XCA database integration

## Data Flow

```
Client Request → TLS Auth → EST Handler → CA Handler → Certificate Response
```

1. Client sends HTTPS request with client certificate
2. Server validates client certificate
3. EST handler routes request to appropriate CA handler
4. CA handler processes certificate request
5. Response returned as PKCS#7 encoded certificate

## Configuration

Configuration is loaded from `python_est.cfg`:

- **Daemon**: Server settings (port, certificates)
- **CAhandler**: CA backend configuration
- **Handler-specific**: Parameters for each CA type

## Extensibility

New CA handlers can be added by:
1. Implementing the base CA handler interface
2. Adding handler-specific configuration
3. Registering in main configuration file