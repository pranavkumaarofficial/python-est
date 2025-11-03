#!/bin/bash
# Cisco libest Quick Setup Script
# Run this on your Ubuntu VM

set -e  # Exit on error

echo "=========================================="
echo "Cisco libest Quick Setup for IQE Demo"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}[1/10] Installing dependencies...${NC}"
sudo apt-get update
sudo apt-get install -y build-essential libssl-dev git autoconf automake libtool

echo -e "${GREEN}[OK] Dependencies installed${NC}"

echo -e "${YELLOW}[2/10] Creating directory...${NC}"
mkdir -p ~/libest-server
cd ~/libest-server

echo -e "${YELLOW}[3/10] Cloning libest repository...${NC}"
if [ -d "libest" ]; then
    echo "libest directory exists, pulling latest..."
    cd libest
    git pull
    cd ..
else
    git clone https://github.com/cisco/libest.git
fi

echo -e "${GREEN}[OK] Repository cloned${NC}"

echo -e "${YELLOW}[4/10] Building libest (this may take 5-10 minutes)...${NC}"
cd libest
./configure --prefix=/usr/local
make
sudo make install

echo -e "${GREEN}[OK] libest built and installed${NC}"

echo -e "${YELLOW}[5/10] Setting up server directory...${NC}"
cd example/server

echo -e "${YELLOW}[6/10] Generating CA certificate...${NC}"
./mfgCAs.sh

echo -e "${GREEN}[OK] CA certificate generated${NC}"

echo -e "${YELLOW}[7/10] Configuring certificate with IP address...${NC}"

# Backup original config
cp estExampleCA.cnf estExampleCA.cnf.backup

# Add IP address to alt_names section
# Find the [alt_names] section and add IP addresses
cat >> estExampleCA.cnf << 'EOF'

# Added for IQE compatibility
[alt_names]
DNS.1 = localhost
DNS.2 = estserver
IP.1 = 127.0.0.1
IP.2 = 10.42.56.101
EOF

echo -e "${GREEN}[OK] Certificate config updated with IP address${NC}"

echo -e "${YELLOW}[8/10] Generating server certificate...${NC}"
./mfgCerts.sh

echo -e "${GREEN}[OK] Server certificate generated${NC}"

echo -e "${YELLOW}[9/10] Creating user credentials...${NC}"
# Create htdigest file with default user
echo "Creating user: iqe-gateway"
htdigest -c .htdigest estrealm iqe-gateway
# You'll be prompted to enter password: iqe-secure-password-2024

echo -e "${GREEN}[OK] User created${NC}"

echo -e "${YELLOW}[10/10] Configuring server startup script...${NC}"

# Backup original runserver.sh
cp runserver.sh runserver.sh.backup

# Create new runserver.sh with correct settings
cat > runserver.sh << 'EOF'
#!/bin/bash
# EST server startup script for IQE compatibility

# Kill any existing estserver
pkill estserver 2>/dev/null || true

# Start EST server
./estserver \
  -c estCA/cacert.crt \
  -k estCA/private/cakey.pem \
  -r estrealm \
  -p 8446 \
  -o \
  -v \
  --http-auth-required

echo "EST server started on port 8446"
echo "Press Ctrl+C to stop"

# Keep script running
tail -f /dev/null
EOF

chmod +x runserver.sh

echo -e "${GREEN}[OK] Server configured${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}Installation Complete!${NC}"
echo "=========================================="
echo ""
echo "Server location: ~/libest-server/libest/example/server"
echo "CA Certificate: ~/libest-server/libest/example/server/estCA/cacert.crt"
echo ""
echo "Next steps:"
echo "  1. Open firewall: sudo ufw allow 8446/tcp"
echo "  2. Start server: cd ~/libest-server/libest/example/server && ./runserver.sh"
echo "  3. Test: curl -vk https://localhost:8446/.well-known/est/cacerts"
echo "  4. Copy CA cert to share with IQE team"
echo ""
echo "IQE UI Configuration:"
echo "  URL: https://10.42.56.101:8446/.well-known/est/simpleenroll"
echo "  Username: iqe-gateway"
echo "  Password: iqe-secure-password-2024"
echo ""
echo "Good luck with your demo! 🚀"
