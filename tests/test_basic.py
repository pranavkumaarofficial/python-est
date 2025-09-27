#!/usr/bin/env python3
"""
Basic tests for Python-EST
"""

import pytest
import requests
import urllib3

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@pytest.fixture
def est_server_url():
    """EST server URL for testing"""
    return "https://localhost:8443"

@pytest.fixture
def demo_server_url():
    """Demo server URL for testing"""
    return "https://localhost:8444"

def test_server_info(demo_server_url):
    """Test server info endpoint"""
    response = requests.get(f"{demo_server_url}/", verify=False)
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "status" in data

def test_bootstrap_endpoint(demo_server_url):
    """Test bootstrap endpoint"""
    response = requests.get(f"{demo_server_url}/.well-known/est/bootstrap", verify=False)
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")

def test_ca_certificates_endpoint(demo_server_url):
    """Test CA certificates endpoint"""
    response = requests.get(f"{demo_server_url}/.well-known/est/cacerts", verify=False)
    assert response.status_code == 200
    assert response.headers.get("content-type") == "application/pkcs7-mime"
    assert response.headers.get("content-transfer-encoding") == "base64"

def test_enrollment_endpoint(demo_server_url):
    """Test enrollment endpoint"""
    response = requests.post(
        f"{demo_server_url}/.well-known/est/simpleenroll",
        data="test-csr-data",
        headers={"Content-Type": "application/pkcs10"},
        verify=False
    )
    assert response.status_code == 200