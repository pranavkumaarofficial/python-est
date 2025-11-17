#!/usr/bin/env python3
"""
IQE Workflow Simulation Script
This simulates the complete IQE process for requesting and installing pump certificates.

Usage:
    python simulate_iqe_workflow.py --serial NPPBBB5 --est-url https://10.42.56.101:8445
"""

import argparse
import os
import sys
import subprocess
import requests
import urllib3
from pathlib import Path

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class IQESimulator:
    def __init__(self, pump_serial, est_url, ra_cert_path, ra_key_path):
        self.pump_serial = pump_serial
        self.est_url = est_url.rstrip('/')
        self.ra_cert_path = ra_cert_path
        self.ra_key_path = ra_key_path
        self.output_dir = Path(f"usb-pump-{pump_serial}")

    def step1_generate_csr(self):
        """Generate CSR for pump"""
        print(f"\n{'='*60}")
        print("STEP 1: Generate Pump CSR (Certificate Signing Request)")
        print(f"{'='*60}")

        # Create output directory
        self.output_dir.mkdir(exist_ok=True)

        csr_file = self.output_dir / f"{self.pump_serial}-csr.der"
        key_file = self.output_dir / f"{self.pump_serial}-key.pem"

        # Generate private key and CSR
        cmd = [
            'openssl', 'req', '-new', '-newkey', 'rsa:2048', '-nodes',
            '-keyout', str(key_file),
            '-out', str(csr_file),
            '-outform', 'DER',
            '-subj', f'/CN={self.pump_serial}/O=Ferrari Medical Inc'
        ]

        print(f"Generating CSR for pump: {self.pump_serial}")
        print(f"Command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return False

        print(f"✅ CSR generated: {csr_file}")
        print(f"✅ Private key generated: {key_file}")

        self.csr_file = csr_file
        self.key_file = key_file
        return True

    def step2_request_certificate(self):
        """Request certificate from EST server"""
        print(f"\n{'='*60}")
        print("STEP 2: Request Certificate from EST Server")
        print(f"{'='*60}")

        # Read CSR
        with open(self.csr_file, 'rb') as f:
            csr_data = f.read()

        # EST simpleenroll endpoint
        est_endpoint = f"{self.est_url}/.well-known/est/simpleenroll"

        print(f"EST URL: {est_endpoint}")
        print(f"RA Certificate: {self.ra_cert_path}")
        print(f"CSR Size: {len(csr_data)} bytes")
        print("Sending request with RA authentication...")

        # Make request with RA cert authentication
        try:
            response = requests.post(
                est_endpoint,
                data=csr_data,
                headers={'Content-Type': 'application/pkcs10'},
                cert=(self.ra_cert_path, self.ra_key_path),
                verify=False,  # Self-signed cert
                timeout=30
            )

            print(f"Response Status: {response.status_code}")
            print(f"Response Length: {len(response.content)} bytes")

            if response.status_code == 200:
                # Save PKCS#7 response
                p7_file = self.output_dir / f"{self.pump_serial}-cert.p7"
                with open(p7_file, 'wb') as f:
                    f.write(response.content)

                print(f"✅ Certificate received: {p7_file}")
                self.p7_file = p7_file
                return True
            else:
                print(f"❌ EST server returned error: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error connecting to EST server: {e}")
            return False

    def step3_extract_certificate(self):
        """Extract certificate from PKCS#7 response"""
        print(f"\n{'='*60}")
        print("STEP 3: Extract Certificate from PKCS#7")
        print(f"{'='*60}")

        cert_file = self.output_dir / f"{self.pump_serial}-cert.pem"

        # Decode base64 PKCS#7
        p7_decoded = self.output_dir / f"{self.pump_serial}-cert-decoded.p7"

        # Check if already DER or base64
        with open(self.p7_file, 'rb') as f:
            content = f.read()
            if content.startswith(b'-----BEGIN'):
                # Already PEM, convert to DER
                print("Converting PEM to DER...")
                cmd = ['openssl', 'base64', '-d', '-in', str(self.p7_file), '-out', str(p7_decoded)]
            else:
                # Already DER or base64 encoded
                print("Decoding base64...")
                with open(p7_decoded, 'wb') as out:
                    import base64
                    try:
                        out.write(base64.b64decode(content))
                    except:
                        # Already decoded
                        out.write(content)

        # Extract certificate from PKCS#7
        cmd = [
            'openssl', 'pkcs7', '-print_certs',
            '-in', str(p7_decoded),
            '-inform', 'DER',
            '-out', str(cert_file)
        ]

        print(f"Extracting certificate...")
        print(f"Command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return False

        print(f"✅ Certificate extracted: {cert_file}")
        self.cert_file = cert_file
        return True

    def step4_verify_certificate(self):
        """Verify certificate details"""
        print(f"\n{'='*60}")
        print("STEP 4: Verify Certificate Details")
        print(f"{'='*60}")

        # Show certificate details
        cmd = ['openssl', 'x509', '-in', str(self.cert_file), '-noout', '-subject', '-issuer', '-dates']
        result = subprocess.run(cmd, capture_output=True, text=True)

        print("Certificate Details:")
        print(result.stdout)

        # Verify signature (if CA cert available)
        ca_cert = Path('certs/ca-cert.pem')
        if ca_cert.exists():
            cmd = ['openssl', 'verify', '-CAfile', str(ca_cert), str(self.cert_file)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(f"Signature Verification: {result.stdout.strip()}")

            if 'OK' in result.stdout:
                print("✅ Certificate signature is valid!")
                return True
            else:
                print("❌ Certificate signature verification failed!")
                return False
        else:
            print("⚠️  CA certificate not found, skipping signature verification")
            return True

    def step5_prepare_usb_package(self):
        """Prepare USB installation package"""
        print(f"\n{'='*60}")
        print("STEP 5: Prepare USB Installation Package")
        print(f"{'='*60}")

        # Copy and rename files for pump
        wifi_cert = self.output_dir / 'wifi_cert.pem'
        wifi_key = self.output_dir / 'wifi_private_key.prv'
        wifi_ca = self.output_dir / 'wifi_root_cert.pem'

        # Copy certificate
        print(f"Copying {self.cert_file} -> {wifi_cert}")
        with open(self.cert_file, 'r') as src, open(wifi_cert, 'w') as dst:
            dst.write(src.read())

        # Copy private key (rename to .prv)
        print(f"Copying {self.key_file} -> {wifi_key}")
        with open(self.key_file, 'r') as src, open(wifi_key, 'w') as dst:
            dst.write(src.read())

        # Copy EST CA certificate
        ca_cert = Path('certs/ca-cert.pem')
        if ca_cert.exists():
            print(f"Copying {ca_cert} -> {wifi_ca}")
            with open(ca_cert, 'r') as src, open(wifi_ca, 'w') as dst:
                dst.write(src.read())
        else:
            print(f"⚠️  CA certificate not found at {ca_cert}")
            print("   You'll need to copy this manually!")

        print(f"\n✅ USB Package Ready: {self.output_dir}/")
        print("\nFiles created:")
        for file in [wifi_cert, wifi_key, wifi_ca]:
            if file.exists():
                size = file.stat().st_size
                print(f"  - {file.name} ({size} bytes)")

        return True

    def step6_generate_pump_config(self):
        """Generate wpa_supplicant configuration for pump"""
        print(f"\n{'='*60}")
        print("STEP 6: Generate Pump WiFi Configuration")
        print(f"{'='*60}")

        config_file = self.output_dir / 'wpa_supplicant.conf'

        config_content = f"""# WPA Supplicant Configuration for Pump {self.pump_serial}
# This file should be copied to /etc/wpa_supplicant/wpa_supplicant.conf on the pump

ctrl_interface=/var/run/wpa_supplicant
ctrl_interface_group=0
update_config=1

# WPA2/WPA3 Enterprise with EAP-TLS (Certificate-based Authentication)
network={{
    ssid="INTEROP_RADIUS_WLAN"                     # WiFi SSID
    scan_ssid=1                                    # Scan for hidden SSIDs
    key_mgmt=WPA-EAP                               # WPA2/WPA3 Enterprise
    eap=TLS                                        # EAP-TLS (certificate auth)
    identity="{self.pump_serial}"                  # Pump serial number

    # Certificate paths (adjust if pump uses different paths)
    ca_cert="/etc/cert/wifi_root_cert.pem"         # EST CA certificate
    client_cert="/etc/cert/wifi_cert.pem"          # Pump certificate
    private_key="/etc/cert/wifi_private_key.prv"   # Pump private key

    # Security settings
    proto=RSN                                      # WPA2
    pairwise=CCMP                                  # AES encryption
    group=CCMP

    # Optional: If private key is encrypted, uncomment and add password
    # private_key_passwd="password"
}}
"""

        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)

        print(f"✅ WiFi configuration generated: {config_file}")
        return True

    def step7_generate_install_script(self):
        """Generate installation script for pump"""
        print(f"\n{'='*60}")
        print("STEP 7: Generate Installation Script")
        print(f"{'='*60}")

        install_script = self.output_dir / 'install_on_pump.sh'

        script_content = f"""#!/bin/bash
# Installation script for pump {self.pump_serial}
# Run this script on the pump after mounting USB drive

set -e  # Exit on error

echo "=== Installing WiFi Certificates for Pump {self.pump_serial} ==="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
   echo "❌ Please run as root (sudo ./install_on_pump.sh)"
   exit 1
fi

# Find USB mount point (adjust if needed)
USB_MOUNT="/mnt/usb"
if [ ! -d "$USB_MOUNT" ]; then
    echo "Mounting USB drive..."
    mkdir -p $USB_MOUNT
    mount /dev/sda1 $USB_MOUNT || {{
        echo "❌ Failed to mount USB. Please mount manually and update USB_MOUNT variable."
        exit 1
    }}
fi

echo "USB mounted at: $USB_MOUNT"
echo

# Create certificate directory
CERT_DIR="/etc/cert"
echo "Creating certificate directory: $CERT_DIR"
mkdir -p $CERT_DIR

# Copy certificates
echo "Copying certificates..."
cp $USB_MOUNT/wifi_cert.pem $CERT_DIR/
cp $USB_MOUNT/wifi_private_key.prv $CERT_DIR/
cp $USB_MOUNT/wifi_root_cert.pem $CERT_DIR/

# Set proper permissions
echo "Setting permissions..."
chmod 644 $CERT_DIR/wifi_cert.pem
chmod 600 $CERT_DIR/wifi_private_key.prv  # Private key must be protected!
chmod 644 $CERT_DIR/wifi_root_cert.pem
chown root:root $CERT_DIR/*

echo "✅ Certificates installed!"
echo

# Verify installation
echo "Verifying certificates..."
ls -la $CERT_DIR/

echo
echo "Certificate details:"
openssl x509 -in $CERT_DIR/wifi_cert.pem -noout -subject -issuer -dates

# Verify signature
echo
echo "Verifying certificate signature..."
openssl verify -CAfile $CERT_DIR/wifi_root_cert.pem $CERT_DIR/wifi_cert.pem

# Copy WiFi configuration (optional)
if [ -f "$USB_MOUNT/wpa_supplicant.conf" ]; then
    echo
    echo "Installing WiFi configuration..."
    cp $USB_MOUNT/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf
    chmod 600 /etc/wpa_supplicant/wpa_supplicant.conf
    echo "✅ WiFi configuration installed!"

    # Restart wpa_supplicant
    echo "Restarting wpa_supplicant..."
    systemctl restart wpa_supplicant || {{
        echo "⚠️  Failed to restart wpa_supplicant. You may need to restart manually."
    }}
fi

echo
echo "=== Installation Complete ==="
echo
echo "Next steps:"
echo "1. Verify pump can see WiFi: iwlist wlan0 scan | grep Ferrari2"
echo "2. Check WiFi connection status: wpa_cli status"
echo "3. Monitor RADIUS logs on server for authentication attempts"
echo
"""

        with open(install_script, 'w', encoding='utf-8') as f:
            f.write(script_content)

        # Make executable
        os.chmod(install_script, 0o755)

        print(f"✅ Installation script generated: {install_script}")
        return True

    def step8_generate_readme(self):
        """Generate README with instructions"""
        print(f"\n{'='*60}")
        print("STEP 8: Generate README")
        print(f"{'='*60}")

        readme_file = self.output_dir / 'README.md'

        readme_content = f"""# Pump WiFi Certificate Installation Package

**Pump Serial:** {self.pump_serial}
**Generated:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**EST Server:** {self.est_url}

## 📁 Package Contents

```
usb-pump-{self.pump_serial}/
├── wifi_cert.pem              # Pump certificate (public)
├── wifi_private_key.prv       # Pump private key (KEEP SECRET!)
├── wifi_root_cert.pem         # EST CA certificate (public)
├── wpa_supplicant.conf        # WiFi configuration
├── install_on_pump.sh         # Installation script
└── README.md                  # This file
```

## 🚀 Installation Instructions

### Method 1: Using Installation Script (Recommended)

1. **Copy entire folder to USB drive**
   ```bash
   # On IQE or Windows machine
   cp -r usb-pump-{self.pump_serial} /media/usb/
   ```

2. **On pump, mount USB and run script**
   ```bash
   # Mount USB
   sudo mkdir -p /mnt/usb
   sudo mount /dev/sda1 /mnt/usb

   # Run installation script
   cd /mnt/usb/usb-pump-{self.pump_serial}
   sudo ./install_on_pump.sh
   ```

3. **Verify installation**
   ```bash
   # Check certificates
   ls -la /etc/cert/

   # Check WiFi status
   wpa_cli status

   # Should show: wpa_state=COMPLETED when connected
   ```

### Method 2: Manual Installation

If the script doesn't work, install manually:

```bash
# 1. Create certificate directory
sudo mkdir -p /etc/cert

# 2. Copy certificates from USB
sudo cp /mnt/usb/usb-pump-{self.pump_serial}/wifi_cert.pem /etc/cert/
sudo cp /mnt/usb/usb-pump-{self.pump_serial}/wifi_private_key.prv /etc/cert/
sudo cp /mnt/usb/usb-pump-{self.pump_serial}/wifi_root_cert.pem /etc/cert/

# 3. Set permissions
sudo chmod 644 /etc/cert/wifi_cert.pem
sudo chmod 600 /etc/cert/wifi_private_key.prv
sudo chmod 644 /etc/cert/wifi_root_cert.pem

# 4. Copy WiFi config
sudo cp /mnt/usb/usb-pump-{self.pump_serial}/wpa_supplicant.conf /etc/wpa_supplicant/
sudo chmod 600 /etc/wpa_supplicant/wpa_supplicant.conf

# 5. Restart WiFi
sudo systemctl restart wpa_supplicant
```

## 🔍 Verification

### Check Certificate Details
```bash
openssl x509 -in /etc/cert/wifi_cert.pem -noout -subject -issuer -dates
```

Expected output:
```
subject=CN = {self.pump_serial}, O = Ferrari Medical Inc
issuer=C = US, ST = CA, L = Test, O = Test CA, CN = Python-EST Root CA
notBefore=...
notAfter=...
```

### Verify Signature
```bash
openssl verify -CAfile /etc/cert/wifi_root_cert.pem /etc/cert/wifi_cert.pem
```

Expected: `/etc/cert/wifi_cert.pem: OK`

### Check WiFi Connection
```bash
# See WiFi status
wpa_cli status

# Scan for WiFi
iwlist wlan0 scan | grep Ferrari2

# Check IP address (when connected)
ip addr show wlan0
```

## 🌐 Network Information

**WiFi SSID:** Ferrari2
**Authentication:** WPA2/WPA3 Enterprise (EAP-TLS)
**RADIUS Server:** 10.42.56.101:1812
**WLC IP:** 10.40.88.26

## 🐛 Troubleshooting

### Pump can't see WiFi
```bash
# Check WiFi interface
iwconfig wlan0

# Scan for networks
iwlist wlan0 scan | grep ESSID
```

### WPA supplicant errors
```bash
# Check logs
journalctl -u wpa_supplicant -f

# Restart service
sudo systemctl restart wpa_supplicant
```

### Certificate issues
```bash
# Verify certificate is valid
openssl x509 -in /etc/cert/wifi_cert.pem -noout -text

# Check private key matches certificate
openssl x509 -in /etc/cert/wifi_cert.pem -noout -modulus | openssl md5
openssl rsa -in /etc/cert/wifi_private_key.prv -noout -modulus | openssl md5
# These two outputs should match!
```

## 📞 Support

For issues, check:
- RADIUS server logs: `docker logs -f freeradius-server` (on 10.42.56.101)
- WLC logs for authentication attempts
- Pump system logs: `journalctl -xe`

## ⚠️ Security Notes

- **NEVER share `wifi_private_key.prv`** - This is secret!
- Certificate is valid for 1 year - plan for renewal
- Keep USB drive secure after installation
- Certificate is tied to pump serial number {self.pump_serial}
"""

        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)

        print(f"✅ README generated: {readme_file}")
        return True

    def run_complete_workflow(self):
        """Run complete IQE workflow"""
        print("\n" + "="*60)
        print("IQE COMPLETE WORKFLOW SIMULATION")
        print(f"Pump Serial: {self.pump_serial}")
        print(f"EST Server: {self.est_url}")
        print("="*60)

        steps = [
            ("Generate CSR", self.step1_generate_csr),
            ("Request Certificate from EST", self.step2_request_certificate),
            ("Extract Certificate", self.step3_extract_certificate),
            ("Verify Certificate", self.step4_verify_certificate),
            ("Prepare USB Package", self.step5_prepare_usb_package),
            ("Generate Pump Config", self.step6_generate_pump_config),
            ("Generate Install Script", self.step7_generate_install_script),
            ("Generate README", self.step8_generate_readme),
        ]

        for step_name, step_func in steps:
            if not step_func():
                print(f"\n❌ Workflow failed at: {step_name}")
                return False

        print("\n" + "="*60)
        print("✅ COMPLETE WORKFLOW SUCCESS!")
        print("="*60)
        print(f"\n📦 USB Package Location: {self.output_dir.absolute()}/")
        print("\nPackage contains:")
        print("  - wifi_cert.pem              (Pump certificate)")
        print("  - wifi_private_key.prv       (Pump private key)")
        print("  - wifi_root_cert.pem         (EST CA certificate)")
        print("  - wpa_supplicant.conf        (WiFi configuration)")
        print("  - install_on_pump.sh         (Installation script)")
        print("  - README.md                  (Complete instructions)")
        print("\n📋 Next Steps:")
        print("1. Copy this folder to USB drive")
        print("2. Insert USB into pump")
        print("3. Run: sudo ./install_on_pump.sh")
        print("4. Monitor RADIUS logs for authentication")
        print("\n" + "="*60)

        return True


def main():
    parser = argparse.ArgumentParser(description='Simulate IQE workflow for pump certificate provisioning')
    parser.add_argument('--serial', default='NPPBBB5', help='Pump serial number')
    parser.add_argument('--est-url', default='https://localhost:8445', help='EST server URL')
    parser.add_argument('--ra-cert', default='certs/iqe-ra-cert.pem', help='RA certificate path')
    parser.add_argument('--ra-key', default='certs/iqe-ra-key.pem', help='RA private key path')

    args = parser.parse_args()

    # Verify RA credentials exist
    if not os.path.exists(args.ra_cert):
        print(f"❌ RA certificate not found: {args.ra_cert}")
        print("   Please generate RA certificates first!")
        sys.exit(1)

    if not os.path.exists(args.ra_key):
        print(f"❌ RA private key not found: {args.ra_key}")
        sys.exit(1)

    # Run simulation
    simulator = IQESimulator(args.serial, args.est_url, args.ra_cert, args.ra_key)
    success = simulator.run_complete_workflow()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
