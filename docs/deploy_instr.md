Then on your Ubuntu VM, you can deploy:
cd ~/Desktop/python-est
git pull origin deploy_v1

# Generate certificates (edit line 167 for your IP first if needed)
python3 generate_certificates_python.py
python3 generate_ra_certificate.py

# Deploy
docker-compose -f docker-compose-nginx.yml up -d --build

# Check status
docker-compose -f docker-compose-nginx.yml ps
docker-compose -f docker-compose-nginx.yml logs -f

# Test (from Ubuntu)
curl -k https://localhost:8445/health
curl -k https://localhost:8445/.well-known/est/cacerts

# Test RA authentication (this will work on Linux)
curl -vk https://localhost:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @test.der
Summary of what we accomplished: ✅ Cleaned repository - removed 50+ unnecessary files ✅ Fixed critical bugs - missing dependencies, config issues, Docker build errors
✅ Working deployment - server starts, health checks pass, endpoints respond ✅ Production ready - Nginx reverse proxy, RA cert authentication, clean structure The server is now ready for your IQE integration on Ubuntu!





































# SSH to Ubuntu VM first
cd ~/Desktop/python-est

# Pull latest code
git pull origin deploy_v1

# Stop any old containers
docker-compose -f docker-compose-nginx.yml down

# Clean up old data
rm -rf certs/* data/*

# Generate certificates (IMPORTANT: Edit line 167 first if your IP isn't 10.42.56.101)
python3 generate_certificates_python.py

# Generate RA certificate for IQE
python3 generate_ra_certificate.py

# Optional: Create SRP user for testing
python3 create_iqe_user.py

# Build and deploy
docker-compose -f docker-compose-nginx.yml up -d --build

# Check status
docker-compose -f docker-compose-nginx.yml ps

# View logs
docker-compose -f docker-compose-nginx.yml logs -f

# Test health endpoint
curl -k https://localhost:8445/health

# Test CA certs
curl -k https://localhost:8445/.well-known/est/cacerts
3. IQE Integration Steps
A. Package files for IQE team
# Create package directory
mkdir -p ~/iqe_deployment_package

# Copy required files
cp certs/ca-cert.pem ~/iqe_deployment_package/
cp certs/iqe-ra-cert.pem ~/iqe_deployment_package/
cp certs/iqe-ra-key.pem ~/iqe_deployment_package/

# List files
ls -la ~/iqe_deployment_package/
B. Send to IQE Team
Files to upload to IQE UI:
ca-cert.pem - EST server CA certificate (for validation)
iqe-ra-cert.pem - RA certificate (for authentication)
iqe-ra-key.pem - RA private key (keep secure!)
IQE Configuration (provide to IQE team):
EST Server Settings:
  URL: https://10.42.56.101:8445
  CA Certificate: ca-cert.pem
  Client Certificate: iqe-ra-cert.pem
  Client Key: iqe-ra-key.pem
  
EST Endpoints:
  CA Certs: /.well-known/est/cacerts
  Simple Enroll: /.well-known/est/simpleenroll
  Simple Re-enroll: /.well-known/est/simplereenroll
C. Verify on Ubuntu VM
# Test RA authentication with real certificates
# First create a test CSR
python3 << 'EOF'
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, 'US'),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'Hospital'),
    x509.NameAttribute(NameOID.COMMON_NAME, 'test-device-ubuntu'),
])).sign(key, hashes.SHA256())

with open('/tmp/test.der', 'wb') as f:
    f.write(csr.public_bytes(serialization.Encoding.DER))
print("CSR created at /tmp/test.der")
EOF

# Test RA enrollment
curl -vk https://localhost:8445/.well-known/est/simpleenroll \
  --cert certs/iqe-ra-cert.pem \
  --key certs/iqe-ra-key.pem \
  -H "Content-Type: application/pkcs10" \
  --data-binary @/tmp/test.der \
  -o device-cert.p7

# Check if it worked
ls -lh device-cert.p7

# View server logs for RA authentication
docker-compose -f docker-compose-nginx.yml logs python-est-server | grep "RA Certificate"
Expected Success Output
Health check:
{"status":"healthy","service":"Python-EST Server"}
RA authentication logs:
✅ Client certificate validated by nginx: CN=IQE Registration Authority...
🔐 RA certificate authentication (nginx validated)
✅ RA Certificate authentication successful for: IQE Registration Authority
Enrolled certificate for requester: IQE Registration Authority
Container status:
NAME                    STATUS
python-est-server       Up (healthy)
est-nginx               Up (healthy)
Summary for IQE Team
What IQE needs to do:
Upload the 3 certificate files to their EST client configuration
Configure EST server URL: https://10.42.56.101:8445
Test enrollment using the RA certificate authentication
What should work:
IQE gateway authenticates using RA certificate (no username/password needed)
IQE can enroll devices and get certificates in base64 PKCS#7 format
All EST endpoints available: /cacerts, /simpleenroll, /simplereenroll
That's it! Everything is ready for production IQE integration! 🚀