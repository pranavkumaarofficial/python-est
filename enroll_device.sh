#!/bin/bash
#
# EST Device Enrollment Script for Linux VMs
#
# Usage: ./enroll_device.sh <device_id> [est_server_url]
#

set -e

# Configuration
DEFAULT_EST_SERVER="https://localhost:8445"
USERNAME="estuser"
PASSWORD="estpass123"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_dependencies() {
    print_info "Checking dependencies..."

    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi

    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is required but not installed"
        exit 1
    fi

    print_success "Dependencies check passed"
}

# Install Python dependencies
install_python_deps() {
    print_info "Installing Python dependencies..."

    pip3 install --user requests cryptography urllib3 2>/dev/null || {
        print_warning "Failed to install some dependencies, continuing..."
    }

    print_success "Python dependencies installed"
}

# Download EST client if not present
download_est_client() {
    if [[ ! -f "est_client.py" ]]; then
        print_info "EST client not found, downloading..."

        # In a real scenario, download from your repository
        print_warning "Please ensure est_client.py is in the current directory"
        print_warning "You can download it from your repository or copy it manually"
        return 1
    fi

    print_success "EST client found"
}

# Main enrollment function
enroll_device() {
    local device_id="$1"
    local server_url="$2"

    print_info "Starting EST enrollment for device: $device_id"
    print_info "EST Server: $server_url"
    print_info "Username: $USERNAME"

    # Run EST client
    if python3 est_client.py "$server_url" "$device_id" "$USERNAME" "$PASSWORD"; then
        print_success "EST enrollment completed successfully!"

        # Display generated files
        if [[ -d "device_$device_id" ]]; then
            print_info "Generated certificate files:"
            ls -la "device_$device_id/"

            print_info "Certificate bundle location: device_$device_id/"
            print_info "You can now use these certificates for authentication"
        fi

        return 0
    else
        print_error "EST enrollment failed!"
        return 1
    fi
}

# Show usage
show_usage() {
    echo "EST Device Enrollment Script"
    echo "============================"
    echo ""
    echo "Usage: $0 <device_id> [est_server_url]"
    echo ""
    echo "Parameters:"
    echo "  device_id        Unique identifier for this device (required)"
    echo "  est_server_url   EST server URL (optional, default: $DEFAULT_EST_SERVER)"
    echo ""
    echo "Examples:"
    echo "  $0 vm-redhat-001"
    echo "  $0 vm-ubuntu-002 https://est.company.com:8445"
    echo "  $0 iot-device-123 https://192.168.1.100:8445"
    echo ""
    echo "Credentials:"
    echo "  Username: $USERNAME"
    echo "  Password: $PASSWORD"
    echo ""
}

# Main script
main() {
    echo "EST Device Enrollment for Linux VMs"
    echo "===================================="
    echo ""

    # Check arguments
    if [[ $# -lt 1 ]]; then
        show_usage
        exit 1
    fi

    local device_id="$1"
    local server_url="${2:-$DEFAULT_EST_SERVER}"

    # Validate device ID
    if [[ ! "$device_id" =~ ^[a-zA-Z0-9_-]+$ ]]; then
        print_error "Invalid device ID. Use only letters, numbers, underscore, and dash."
        exit 1
    fi

    # Run enrollment process
    check_dependencies
    install_python_deps
    download_est_client
    enroll_device "$device_id" "$server_url"

    if [[ $? -eq 0 ]]; then
        print_success "Device enrollment completed successfully!"
        echo ""
        echo "Next steps:"
        echo "1. Copy certificate files to appropriate locations"
        echo "2. Configure applications to use the certificate"
        echo "3. Test certificate-based authentication"
        echo ""
        echo "Certificate files are located in: device_$device_id/"
    else
        print_error "Device enrollment failed!"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"