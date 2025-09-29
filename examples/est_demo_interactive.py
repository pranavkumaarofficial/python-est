#!/usr/bin/env python3
"""
Complete EST Demo with Authentication and Enrollment Flow
"""

import asyncio
import base64
import secrets
from datetime import datetime, timedelta
from typing import Optional

import uvicorn
from fastapi import FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

app = FastAPI(title="Complete EST Demo", version="1.0.0")

# Simple in-memory session store
sessions = {}

# Fixed credentials for demo
DEMO_USERNAME = "admin"
DEMO_PASSWORD = "est123"

def generate_demo_certificate(common_name: str = "demo-device") -> tuple[str, str]:
    """Generate a demo certificate for enrollment"""
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Create certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Demo City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Python-EST Demo CA"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName(common_name),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())

    # Convert to PEM format
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()

    return cert_pem, key_pem

@app.get("/", response_class=HTMLResponse)
async def server_info():
    """Server information and statistics page"""
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python-EST Server Demo</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0; padding: 20px; min-height: 100vh;
            display: flex; align-items: center; justify-content: center;
        }
        .container {
            background: white; padding: 40px; border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); max-width: 500px; width: 100%;
        }
        .logo { text-align: center; margin-bottom: 30px; }
        .logo h1 { color: #333; margin: 0; font-size: 28px; }
        .logo p { color: #666; margin: 5px 0 0 0; font-size: 14px; }
        .status {
            background: #e8f5e8; border: 1px solid #4caf50; color: #2e7d32;
            padding: 15px; border-radius: 6px; margin: 20px 0; font-size: 14px;
        }
        .features {
            background: #e8f4fd; border: 1px solid #0066cc; color: #004499;
            padding: 15px; border-radius: 6px; margin: 20px 0; font-size: 14px;
        }
        .nav-buttons {
            display: flex; gap: 10px; margin-top: 20px;
        }
        .btn {
            flex: 1; padding: 12px; text-align: center; text-decoration: none;
            border-radius: 6px; font-weight: bold; transition: all 0.3s;
        }
        .btn-primary { background: #007bff; color: white; }
        .btn-primary:hover { background: #0056b3; }
        .btn-secondary { background: #6c757d; color: white; }
        .btn-secondary:hover { background: #545b62; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>Python-EST Server</h1>
            <p>Complete Demo with Authentication</p>
        </div>

        <div class="status">
            <strong>[OK] Server Status:</strong> Running Successfully<br>
            <strong>[ARCH] Architecture:</strong> FastAPI + Async<br>
            <strong>[AUTH] Authentication:</strong> Username/Password Ready
        </div>

        <div class="features">
            <strong>[FEATURES] Available Operations:</strong><br>
            • [OK] Server information and statistics<br>
            • [OK] CA certificate distribution<br>
            • [OK] Bootstrap authentication with credentials<br>
            • [OK] Certificate enrollment and issuance<br>
            • [OK] Complete end-to-end EST workflow
        </div>

        <div style="text-align: center;">
            <h3>[SUCCESS] EST Protocol Implementation Ready!</h3>
            <p>This server demonstrates a complete EST workflow with authentication.</p>
            <p><strong>Ready for device bootstrap and enrollment!</strong></p>
        </div>

        <div class="nav-buttons">
            <a href="/.well-known/est/bootstrap" class="btn btn-primary">Start Bootstrap</a>
            <a href="/.well-known/est/cacerts" class="btn btn-secondary">Get CA Certs</a>
        </div>
    </div>
</body>
</html>'''
    return HTMLResponse(content=html_content)

@app.get("/.well-known/est/cacerts")
async def get_ca_certificates():
    """Get CA certificates endpoint"""
    # Demo CA certificate in base64 PKCS#7 format
    demo_ca_cert = """LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tDQpNSUlEeXpDQ0FyT2dBd0lCQWdJVU1Ea3k="""

    return Response(
        content=demo_ca_cert,
        media_type="application/pkcs7-mime",
        headers={
            "Content-Transfer-Encoding": "base64",
            "Content-Disposition": "attachment; filename=cacerts.p7c"
        }
    )

@app.get("/.well-known/est/bootstrap", response_class=HTMLResponse)
async def bootstrap_page():
    """Bootstrap authentication page with login form"""
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EST Bootstrap Authentication</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0; padding: 20px; min-height: 100vh;
            display: flex; align-items: center; justify-content: center;
        }
        .container {
            background: white; padding: 40px; border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); max-width: 400px; width: 100%;
        }
        .logo { text-align: center; margin-bottom: 30px; }
        .logo h1 { color: #333; margin: 0; font-size: 24px; }
        .logo p { color: #666; margin: 5px 0 0 0; font-size: 14px; }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block; margin-bottom: 5px; font-weight: bold; color: #333;
        }
        input[type="text"], input[type="password"] {
            width: 100%; padding: 12px; border: 1px solid #ddd;
            border-radius: 6px; box-sizing: border-box; font-size: 14px;
        }
        input[type="text"]:focus, input[type="password"]:focus {
            outline: none; border-color: #007bff; box-shadow: 0 0 0 2px rgba(0,123,255,0.25);
        }
        .btn {
            width: 100%; padding: 12px; background: #007bff; color: white;
            border: none; border-radius: 6px; font-size: 16px; font-weight: bold;
            cursor: pointer; transition: background-color 0.3s;
        }
        .btn:hover { background: #0056b3; }
        .info {
            background: #e8f4fd; border: 1px solid #0066cc; color: #004499;
            padding: 15px; border-radius: 6px; margin-bottom: 20px; font-size: 13px;
        }
        .demo-creds {
            background: #fff3cd; border: 1px solid #ffeaa7; color: #856404;
            padding: 10px; border-radius: 6px; margin-bottom: 20px; font-size: 12px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>EST Bootstrap</h1>
            <p>Device Authentication</p>
        </div>

        <div class="demo-creds">
            <strong>Demo Credentials:</strong><br>
            Username: <code>admin</code> | Password: <code>est123</code>
        </div>

        <div class="info">
            <strong>Bootstrap Process:</strong><br>
            1. Enter your device credentials<br>
            2. Authenticate with the EST server<br>
            3. Receive temporary certificate<br>
            4. Proceed to certificate enrollment
        </div>

        <form method="post" action="/.well-known/est/bootstrap">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required placeholder="Enter username">
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required placeholder="Enter password">
            </div>
            <button type="submit" class="btn">Authenticate & Bootstrap</button>
        </form>

        <div style="text-align: center; margin-top: 20px;">
            <a href="/" style="color: #666; text-decoration: none; font-size: 14px;">← Back to Server Info</a>
        </div>
    </div>
</body>
</html>'''
    return HTMLResponse(content=html_content)

@app.post("/.well-known/est/bootstrap")
async def bootstrap_authenticate(username: str = Form(...), password: str = Form(...)):
    """Handle bootstrap authentication"""
    if username == DEMO_USERNAME and password == DEMO_PASSWORD:
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        sessions[session_token] = {
            "username": username,
            "authenticated": True,
            "created": datetime.utcnow()
        }

        # Redirect to enrollment page with session
        response = RedirectResponse(url=f"/enrollment?session={session_token}", status_code=302)
        return response
    else:
        # Return to bootstrap page with error
        html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EST Bootstrap - Authentication Failed</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0; padding: 20px; min-height: 100vh;
            display: flex; align-items: center; justify-content: center;
        }
        .container {
            background: white; padding: 40px; border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); max-width: 400px; width: 100%;
            text-align: center;
        }
        .error {
            background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24;
            padding: 15px; border-radius: 6px; margin-bottom: 20px;
        }
        .btn {
            padding: 12px 24px; background: #007bff; color: white;
            border: none; border-radius: 6px; text-decoration: none;
            display: inline-block; margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Authentication Failed</h1>
        <div class="error">
            <strong>Invalid credentials!</strong><br>
            Please check your username and password.
        </div>
        <p>Demo credentials: <code>admin</code> / <code>est123</code></p>
        <a href="/.well-known/est/bootstrap" class="btn">Try Again</a>
    </div>
</body>
</html>'''
        return HTMLResponse(content=html_content, status_code=401)

@app.get("/enrollment", response_class=HTMLResponse)
async def enrollment_page(session: str):
    """Certificate enrollment page"""
    if session not in sessions or not sessions[session]["authenticated"]:
        return RedirectResponse(url="/.well-known/est/bootstrap")

    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EST Certificate Enrollment</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0; padding: 20px; min-height: 100vh;
            display: flex; align-items: center; justify-content: center;
        }
        .container {
            background: white; padding: 40px; border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); max-width: 500px; width: 100%;
        }
        .logo { text-align: center; margin-bottom: 30px; }
        .logo h1 { color: #333; margin: 0; font-size: 24px; }
        .success {
            background: #d4edda; border: 1px solid #c3e6cb; color: #155724;
            padding: 15px; border-radius: 6px; margin-bottom: 20px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block; margin-bottom: 5px; font-weight: bold; color: #333;
        }
        input[type="text"] {
            width: 100%; padding: 12px; border: 1px solid #ddd;
            border-radius: 6px; box-sizing: border-box; font-size: 14px;
        }
        .btn {
            width: 100%; padding: 12px; background: #28a745; color: white;
            border: none; border-radius: 6px; font-size: 16px; font-weight: bold;
            cursor: pointer; margin-top: 10px;
        }
        .btn:hover { background: #218838; }
        .step {
            background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 10px 0;
            border-left: 4px solid #007bff;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>Certificate Enrollment</h1>
            <p>Bootstrap Authentication Successful</p>
        </div>

        <div class="success">
            <strong>[SUCCESS] Bootstrap Complete!</strong><br>
            You have been successfully authenticated. You can now request a certificate.
        </div>

        <div class="step">
            <strong>Step 1:</strong> Bootstrap authentication ✅<br>
            <strong>Step 2:</strong> Certificate enrollment ⏳<br>
            <strong>Step 3:</strong> Certificate issuance (pending)
        </div>

        <form method="post" action="/enroll">
            <input type="hidden" name="session" value="''' + session + '''">
            <div class="form-group">
                <label for="device_name">Device Name:</label>
                <input type="text" id="device_name" name="device_name" required
                       placeholder="Enter device name (e.g., my-iot-device)" value="demo-device">
            </div>
            <button type="submit" class="btn">Request Certificate</button>
        </form>

        <div style="text-align: center; margin-top: 20px;">
            <a href="/" style="color: #666; text-decoration: none; font-size: 14px;">← Back to Server Info</a>
        </div>
    </div>
</body>
</html>'''
    return HTMLResponse(content=html_content)

@app.post("/enroll")
async def enroll_certificate(session: str = Form(...), device_name: str = Form(...)):
    """Handle certificate enrollment"""
    if session not in sessions or not sessions[session]["authenticated"]:
        return RedirectResponse(url="/.well-known/est/bootstrap")

    # Generate certificate for the device
    cert_pem, key_pem = generate_demo_certificate(device_name)

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EST Certificate Issued</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0; padding: 20px; min-height: 100vh;
        }}
        .container {{
            background: white; padding: 40px; border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); max-width: 700px;
            margin: 0 auto;
        }}
        .logo {{ text-align: center; margin-bottom: 30px; }}
        .logo h1 {{ color: #333; margin: 0; font-size: 24px; }}
        .success {{
            background: #d4edda; border: 1px solid #c3e6cb; color: #155724;
            padding: 15px; border-radius: 6px; margin-bottom: 20px;
        }}
        .cert-box {{
            background: #f8f9fa; border: 1px solid #dee2e6;
            padding: 15px; border-radius: 6px; margin: 15px 0;
            font-family: monospace; font-size: 12px;
            max-height: 200px; overflow-y: auto;
            white-space: pre-wrap;
        }}
        .step {{
            background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 10px 0;
            border-left: 4px solid #28a745;
        }}
        .btn {{
            padding: 12px 24px; background: #007bff; color: white;
            border: none; border-radius: 6px; text-decoration: none;
            display: inline-block; margin: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>Certificate Issued Successfully!</h1>
            <p>EST Enrollment Complete</p>
        </div>

        <div class="success">
            <strong>[SUCCESS] Certificate Enrollment Complete!</strong><br>
            Your device certificate has been generated and issued successfully.
        </div>

        <div class="step">
            <strong>✅ Step 1:</strong> Bootstrap authentication - Complete<br>
            <strong>✅ Step 2:</strong> Certificate enrollment - Complete<br>
            <strong>✅ Step 3:</strong> Certificate issuance - Complete
        </div>

        <h3>Certificate Details:</h3>
        <p><strong>Device Name:</strong> {device_name}</p>
        <p><strong>Valid From:</strong> {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC</p>
        <p><strong>Valid To:</strong> {(datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")} UTC</p>

        <h3>Certificate (PEM Format):</h3>
        <div class="cert-box">{cert_pem}</div>

        <h3>Private Key (PEM Format):</h3>
        <div class="cert-box">{key_pem}</div>

        <div style="text-align: center; margin-top: 30px;">
            <h3>🎉 EST Protocol Workflow Complete!</h3>
            <p>Your device can now use this certificate for secure communication.</p>

            <a href="/" class="btn">Return to Server</a>
            <a href="/.well-known/est/bootstrap" class="btn">New Bootstrap</a>
        </div>
    </div>
</body>
</html>'''

    return HTMLResponse(content=html_content)

@app.post("/.well-known/est/simpleenroll")
async def simple_enrollment():
    """EST simple enrollment endpoint (for API clients)"""
    return {
        "message": "Certificate enrollment successful",
        "status": "success",
        "note": "Use the web interface for complete workflow demo"
    }

if __name__ == "__main__":
    print("Starting Complete EST Demo Server...")
    print("Server Info: https://localhost:8444/")
    print("Bootstrap URL: https://localhost:8444/.well-known/est/bootstrap")
    print("Demo Credentials: admin / est123")
    print()
    print("Complete workflow:")
    print("1. Visit https://localhost:8444/ for server information")
    print("2. Click 'Start Bootstrap' to begin authentication")
    print("3. Login with demo credentials")
    print("4. Complete certificate enrollment")
    print("5. Receive issued certificate")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8444,
        ssl_keyfile="certs/server.key",
        ssl_certfile="certs/server.crt",
        log_level="info"
    )