#!/usr/bin/env python3
"""
Simple test client for EST endpoints
"""
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_cacerts():
    """Test /cacerts endpoint"""
    print("Testing /cacerts endpoint (no authentication required)...")
    try:
        response = requests.get('https://localhost:8443/.well-known/est/cacerts',
                              verify=False, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"Content-Length: {len(response.content)}")
        if response.status_code == 200:
            print("✅ /cacerts endpoint working!")
            return True
        else:
            print(f"❌ /cacerts failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error testing /cacerts: {e}")
        return False

def test_bootstrap_page():
    """Test bootstrap login page"""
    print("\nTesting bootstrap login page...")
    try:
        response = requests.get('https://localhost:8443/.well-known/est/bootstrap',
                              verify=False, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200 and 'EST Bootstrap Login' in response.text:
            print("✅ Bootstrap page accessible!")
            return True
        else:
            print(f"❌ Bootstrap page failed with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing bootstrap page: {e}")
        return False

if __name__ == '__main__':
    print("EST Server Test Client")
    print("=" * 50)

    # Test endpoints
    cacerts_ok = test_cacerts()
    bootstrap_ok = test_bootstrap_page()

    print(f"\n{'=' * 50}")
    print("Test Results:")
    print(f"  /cacerts endpoint: {'✅ PASS' if cacerts_ok else '❌ FAIL'}")
    print(f"  /bootstrap page:   {'✅ PASS' if bootstrap_ok else '❌ FAIL'}")