✅ Directory Cleanup Complete
📂 New Structure:
python-est/
├── README.md                    ← Comprehensive overview
├── QUICKSTART.md                ← Same-VM deployment guide (NEW)
│
├── docker-compose-nginx.yml     ← EST server (your current setup)
├── docker-compose-radius.yml    ← RADIUS server (NEW, decoupled)
├── docker-compose-full.yml      ← Legacy (not recommended)
│
├── docker/                      ← All Dockerfiles
│   ├── Dockerfile
│   ├── Dockerfile.radius
│   └── entrypoint.sh
│
├── scripts/                     ← All utility scripts
│   ├── generate_certificates_python.py
│   ├── generate_ra_certificate.py
│   ├── create_iqe_user.py
│   └── test_ra_auth_windows.py
│
├── docs/                        ← All documentation
│   ├── ARCHITECTURE_DECOUPLED.md
│   ├── DEPLOY_DECOUPLED.md
│   ├── COMMANDS_DECOUPLED.md
│   ├── CISCO_WLC_CONFIG.md
│   ├── DEPLOY_COMPLETE_STACK.md
│   └── COMMANDS.md
│
├── radius/                      ← RADIUS configuration
│   ├── generate_radius_certs.sh
│   ├── clients.conf
│   ├── eap
│   └── radiusd.conf
│
└── [certs, nginx, src, config files...]
🎯 Answers to Your Questions:
1. Can RADIUS run on same VM as EST?
YES! And it's completely decoupled:
# Same VM (10.42.56.101)
# Your EST server - NO CHANGES NEEDED
docker-compose -f docker-compose-nginx.yml up -d

# Add RADIUS - completely independent
docker-compose -f docker-compose-radius.yml up -d
Why this works:
✅ Different compose files = independent deployments
✅ Different ports = EST (8445/tcp), RADIUS (1812/udp)
✅ RADIUS uses network_mode: host = no Docker network overlap
✅ Can restart one without affecting the other
✅ Can migrate RADIUS to different VM later (just update WLC IP)
2. Directory Cleanup Done
✅ Moved all docs to /docs
✅ Moved all scripts to /scripts
✅ Moved Dockerfiles to /docker
✅ Updated all compose files to reference docker/Dockerfile*
✅ Removed temp files (test.der, device-cert.p7, nul)
✅ Created clean README.md
✅ Created QUICKSTART.md for same-VM deployment
🚀 Next Steps:
Follow QUICKSTART.md - it has the 5-minute setup for adding RADIUS to your existing EST VM!
# Quick setup (on 10.42.56.101)
bash radius/generate_radius_certs.sh
mkdir -p radius-certs && cp certs/ca-cert.pem radius-certs/
nano radius/clients.conf  # Update WLC IP & secret
docker-compose -f docker-compose-radius.yml up -d --build
Your EST server stays untouched! RADIUS runs alongside it completely independently.