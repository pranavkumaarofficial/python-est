# Python EST Server with RA Authentication

EST (Enrollment over Secure Transport) server implementation with RA certificate authentication support.

## Quick Deploy

```bash
# Deploy with nginx (RA authentication)
docker-compose -f docker-compose-nginx.yml up -d --build

# Check status
docker-compose -f docker-compose-nginx.yml ps
docker-compose -f docker-compose-nginx.yml logs -f
```

## Architecture

```
IQE Gateway → nginx:8445 (TLS + RA cert) → python-est:8000 (HTTP)
```

- **nginx**: TLS termination, extracts client certificate, forwards via HTTP headers
- **python-est**: Validates RA certificate, issues device certificates

## Generate Certificates

```bash
# Generate CA and server certificates
python3 generate_certificates_python.py

# Generate RA certificate for IQE gateway
python3 generate_ra_certificate.py

# Create bootstrap user (optional)
python3 create_iqe_user.py
```

**Note**: `generate_certificates_python.py` includes `10.42.56.101` in the server certificate SAN. Edit line 167 to match your server IP if different.

## Testing

```bash
# Health check
curl -k https://localhost:8445/health

# CA certs
curl -k https://localhost:8445/.well-known/est/cacerts

# RA enrollment (with RA cert)
curl -vk https://localhost:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @test.der
```

## Configuration

**Nginx mode** (use `config-nginx.yaml`):
- Backend listens on HTTP port 8000
- Nginx handles TLS on port 8445
- Set `NGINX_MODE=true` environment variable

**Standalone mode** (use `config-iqe.yaml`):
- Backend listens on HTTPS port 8445
- No nginx proxy

## Troubleshooting

```bash
# View logs
docker-compose -f docker-compose-nginx.yml logs -f

# Check RA authentication
docker-compose -f docker-compose-nginx.yml logs python-est-server | grep "Client certificate"

# Restart
docker-compose -f docker-compose-nginx.yml down
docker-compose -f docker-compose-nginx.yml up -d --build
```

## Files

- `src/python_est/server.py` - EST server implementation
- `nginx/nginx.conf` - Nginx TLS termination config
- `docker-compose-nginx.yml` - Docker Compose for nginx mode
- `config-nginx.yaml` - Config for nginx mode (port 8000)
- `config-iqe.yaml` - Config for standalone mode (port 8445)
- `Dockerfile` - Container image definition
