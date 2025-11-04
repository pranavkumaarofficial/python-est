# SOLUTION: RA Authentication in Docker

## Problem Confirmed

Your logs prove that **uvicorn's transport is None in Docker**, which prevents direct client certificate extraction:

```
INFO: 🔍 Transport: None
INFO: ℹ️  No client certificate present, falling back to password authentication
INFO: 401 Unauthorized
```

This is a **known limitation** of uvicorn in containerized environments.

## Industry-Standard Solution: Nginx Reverse Proxy

The proper solution is to use **nginx as a TLS termination proxy** that:
1. Handles the TLS handshake and extracts client certificates
2. Forwards the certificate to the Python app via HTTP headers
3. Python app reads the certificate from headers

This is how **production EST servers** handle client certificates in Docker/Kubernetes.

## Architecture

```
┌─────────────┐
│ IQE Gateway │
│ (with RA    │
│  cert)      │
└──────┬──────┘
       │ HTTPS + Client Cert
       │
       ▼
┌──────────────────────────────────┐
│ Nginx (Port 8445)                │
│ - TLS termination                │
│ - Extract client cert            │
│ - Add X-SSL-Client-Cert header   │
└──────┬───────────────────────────┘
       │ HTTP + Headers
       │
       ▼
┌──────────────────────────────────┐
│ Python EST Server (Port 8000)    │
│ - Read cert from header          │
│ - Validate & authenticate        │
└──────────────────────────────────┘
```

## Implementation

### Step 1: Create Nginx Configuration

Create `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream est_backend {
        server python-est-server:8000;
    }

    server {
        listen 8445 ssl;
        server_name _;

        # Server TLS certificate
        ssl_certificate /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;

        # Client certificate settings
        ssl_client_certificate /etc/nginx/certs/ca-cert.pem;
        ssl_verify_client optional;  # Allow both RA cert and no cert
        ssl_verify_depth 2;

        # TLS settings
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers on;

        location /.well-known/est/ {
            proxy_pass http://est_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Forward client certificate (if present)
            proxy_set_header X-SSL-Client-Verify $ssl_client_verify;
            proxy_set_header X-SSL-Client-S-DN $ssl_client_s_dn;
            proxy_set_header X-SSL-Client-Cert $ssl_client_cert;

            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Health check
        location /health {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }
    }
}
```

### Step 2: Update Python Middleware

Update `src/python_est/server.py` middleware to read cert from nginx headers:

```python
@self.app.middleware("http")
async def extract_client_cert(request: Request, call_next):
    """Extract client certificate from nginx headers."""

    # Get client cert from nginx header
    ssl_client_cert = request.headers.get('X-SSL-Client-Cert')
    ssl_client_verify = request.headers.get('X-SSL-Client-Verify')

    if ssl_client_cert and ssl_client_verify == 'SUCCESS':
        try:
            # nginx sends cert with spaces instead of newlines
            cert_pem = ssl_client_cert.replace(' ', '\n')
            cert_pem = f"-----BEGIN CERTIFICATE-----\n{cert_pem}\n-----END CERTIFICATE-----"

            cert = x509.load_pem_x509_certificate(cert_pem.encode())
            request.state.client_cert = cert
            logger.info(f"✅ Client cert found: {cert.subject.rfc4514_string()}")
        except Exception as e:
            logger.warning(f"Failed to parse client cert: {e}")
    else:
        logger.info(f"ℹ️  No client certificate (verify={ssl_client_verify})")

    response = await call_next(request)
    return response
```

### Step 3: Update Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  python-est-server:
    build: .
    container_name: python-est-server
    expose:
      - "8000"
    volumes:
      - ./certs:/app/certs
      - ./data:/app/data
      - ./config-iqe.yaml:/app/config.yaml
    environment:
      - PORT=8000
    networks:
      - est_network

  nginx:
    image: nginx:alpine
    container_name: est-nginx
    ports:
      - "8445:8445"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - python-est-server
    networks:
      - est_network

networks:
  est_network:
    driver: bridge
```

### Step 4: Update Python Server Config

Modify the EST server to listen on HTTP (nginx handles HTTPS):

```python
# In server.py start() method:
config = uvicorn.Config(
    app=self.app,
    host="0.0.0.0",
    port=8000,  # HTTP port (nginx forwards to this)
    # Remove SSL config - nginx handles it
    # ssl_keyfile=...  # REMOVE
    # ssl_certfile=... # REMOVE
    # ssl_ca_certs=... # REMOVE
)
```

### Step 5: Deploy

```bash
# Build and start
docker-compose up -d --build

# Check logs
docker-compose logs -f

# Test
curl -vk https://localhost:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @test-csr.der
```

## Why This Works

1. **Nginx handles TLS**: Nginx is battle-tested for TLS termination
2. **Reliable cert extraction**: Nginx reliably extracts client certs
3. **Standard approach**: This is how Kubernetes ingress controllers work
4. **Platform-independent**: Works on Windows, Linux, Docker, K8s

## Alternative: Simpler Approach (Keep Trying Different Methods)

If you don't want to add nginx, we can try **mod_ssl extension** or **custom SSL handler**, but the nginx solution is the most reliable and production-ready.

Let me know which approach you prefer!
