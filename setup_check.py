#!/usr/bin/env python3
"""
Setup verification script for Python-EST server
Verifies all dependencies and configuration are ready.
"""

import sys
import importlib
from pathlib import Path

def check_python_version():
    """Check Python version compatibility."""
    print("Python Checking Python version...")
    if sys.version_info < (3, 8):
        print("X Python 3.8+ required")
        return False
    print(f"[OK] Python {sys.version.split()[0]} detected")
    return True

def check_dependencies():
    """Check required dependencies."""
    print("\nPackage Checking dependencies...")
    required = [
        'fastapi', 'uvicorn', 'cryptography', 'pydantic',
        'aiohttp', 'requests', 'yaml', 'click', 'rich', 'pytz'
    ]

    missing = []
    for dep in required:
        try:
            importlib.import_module(dep)
            print(f"[OK] {dep}")
        except ImportError:
            print(f"[MISSING] {dep}")
            missing.append(dep)

    if missing:
        print(f"\nWarning: Install missing dependencies: pip install {' '.join(missing)}")
        return False
    return True

def check_files():
    """Check required files exist."""
    print("\nFile Checking required files...")
    required_files = [
        'config.example.yaml',
        'requirements.txt',
        'test_server.py',
        'src/python_est/__init__.py',
        'src/python_est/server.py',
        'certs/ca-cert.pem',
        'certs/ca-key.pem'
    ]

    missing = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"[OK] {file_path}")
        else:
            print(f"[MISSING] {file_path}")
            missing.append(file_path)

    if missing:
        print(f"\nWarning: Missing files detected. Some features may not work.")
        return False
    return True

def main():
    """Run all checks."""
    print("Python-EST Setup Verification\n")

    checks = [
        check_python_version(),
        check_dependencies(),
        check_files()
    ]

    if all(checks):
        print("\nSuccess: All checks passed! Ready to run:")
        print("   python test_server.py")
        print("\nAccess points:")
        print("   * Bootstrap: https://localhost:8445/.well-known/est/bootstrap")
        print("   * Stats: https://localhost:8445/")
        print("   * Credentials: estuser / estpass123")
    else:
        print("\nWarning: Some checks failed. Please resolve issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()