# RA Certificate Deployment Checklist

## Phase 1: Pre-Deployment (Done on Windows Dev Machine)

- [x] Generate CA certificate and key
- [x] Generate server certificate for EST server
- [x] Generate RA certificate and key for IQE
- [x] Create bootstrap user (iqe-gateway / iqe-secure-password-2024)
- [x] Implement base64 CSR support in server
- [x] Test base64 CSR decoding locally
- [ ] Test RA certificate authentication locally
  - Run: `python test_ra_cert_auth.py`
  - Requires: `python test_server.py` running

## Phase 2: Deploy to Ubuntu VM

- [ ] Push code to `deploy_v1` branch
  ```bash
  git add .
  git commit -m "feat: Add RA certificate support and base64 CSR handling"
  git push origin deploy_v1
  ```

- [ ] Pull on Ubuntu VM
  ```bash
  cd /path/to/python-est
  git fetch origin
  git checkout deploy_v1
  git pull origin deploy_v1
  ```

- [ ] Copy certificates to VM
  ```bash
  # On Windows, use WinSCP or scp to copy:
  certs/ca-cert.pem
  certs/ca-key.pem
  certs/server.crt
  certs/server.key
  certs/srp_users.db
  certs/iqe-ra-cert.pem
  certs/iqe-ra-key.pem
  ```

- [ ] Install dependencies on VM
  ```bash
  pip install -r requirements.txt
  pip install -e .
  ```

- [ ] Start server on VM
  ```bash
  # If using Docker:
  docker-compose up -d

  # Or directly:
  python test_server.py
  # Should show: Server running on https://0.0.0.0:8445
  ```

- [ ] Test server is accessible
  ```bash
  curl -vk https://10.42.56.101:8445/.well-known/est/cacerts
  ```

## Phase 3: Share Files with IQE Team

- [ ] Create secure package for IQE team
  - File 1: `certs/ca-cert.pem` (for their trust store)
  - File 2: `certs/iqe-ra-cert.pem` (for UI upload)
  - File 3: `certs/iqe-ra-key.pem` (for UI upload - SECURE!)
  - Document: `RA_CERTIFICATE_GUIDE.md`
  - Document: `QUESTIONS_FOR_IQE_TEAM.md`

- [ ] Send files via secure channel
  - Options: Encrypted email, secure file share, in-person USB, etc.
  - DO NOT send via Slack/Teams plain text
  - DO NOT commit iqe-ra-key.pem to git

- [ ] Send questions from `QUESTIONS_FOR_IQE_TEAM.md`

## Phase 4: IQE Team Actions

- [ ] IQE imports CA certificate into trust store
  - File: `ca-cert.pem`
  - Purpose: Trust EST server's TLS certificate

- [ ] IQE uploads RA certificate to UI
  - RA Certificate File: `iqe-ra-cert.pem`
  - RA Key File: `iqe-ra-key.pem`

- [ ] IQE configures EST endpoints in UI
  - CA Certs: `https://10.42.56.101:8445/.well-known/est/cacerts`
  - Enrollment: `https://10.42.56.101:8445/.well-known/est/simpleenroll`
  - (Note: Use `/simpleenroll`, NOT `/bootstrap` when using RA cert)

- [ ] IQE runs manual curl tests (from `QUESTIONS_FOR_IQE_TEAM.md`)
  - Test 1: /cacerts (no auth)
  - Test 2: /bootstrap with password + base64 CSR
  - Test 3: /simpleenroll with RA cert

- [ ] IQE provides test results and logs

## Phase 5: Testing with IQE UI

- [ ] IQE tests enrollment through UI (with RA cert)

- [ ] Check EST server logs for requests
  ```bash
  # On VM, check logs:
  docker logs python-est-server  # if using Docker
  # OR check console output if running directly
  ```

- [ ] If errors occur:
  - [ ] Get exact error message from IQE logs
  - [ ] Check EST server logs for corresponding error
  - [ ] Check if it's TLS handshake failure
  - [ ] Check if it's CSR parsing failure
  - [ ] Check if it's certificate validation failure

## Phase 6: Troubleshooting (If Needed)

### If TLS Connection Fails
- [ ] Verify CA cert was imported into IQE trust store
- [ ] Test with curl from IQE server: `curl -vk https://10.42.56.101:8445/.well-known/est/cacerts`
- [ ] Check firewall rules (port 8445 open?)
- [ ] Check server is listening: `netstat -tulpn | grep 8445`

### If Authentication Fails
- [ ] Verify RA cert was uploaded correctly in IQE UI
- [ ] Check RA cert is valid: `openssl x509 -in iqe-ra-cert.pem -text -noout`
- [ ] Check RA cert is signed by CA: `openssl verify -CAfile ca-cert.pem iqe-ra-cert.pem`
- [ ] Check server logs for "Client certificate validation failed"

### If CSR Parsing Fails
- [ ] Check if IQE is sending base64-encoded CSR
- [ ] Verify `Content-Transfer-Encoding: base64` header is present
- [ ] Check server logs for "Decoded base64-encoded CSR"
- [ ] Test with curl using base64 CSR (Test 2 from questions doc)

### If Still Getting 500 Errors
- [ ] Get full error stack trace from IQE logs
- [ ] Get full error stack trace from EST server logs
- [ ] Compare manual curl success vs UI failure
- [ ] Check if UI is sending different headers/format than curl
- [ ] Consider adding more detailed logging to server

## Phase 7: Success Criteria

- [ ] IQE UI can successfully enroll test pump
- [ ] Pump receives client certificate from EST server
- [ ] Certificate is valid and signed by CA
- [ ] Pump can use certificate for EAP-TLS authentication
- [ ] No errors in IQE or EST server logs

## Phase 8: Documentation & Handoff

- [ ] Document the successful configuration
- [ ] Create runbook for certificate renewal (RA cert expires in 2 years)
- [ ] Share success metrics with team
- [ ] Update your profile/portfolio with this achievement
- [ ] Request LOR from higher ops (after successful deployment)

## Important Notes

### Security Reminders
- ⚠️  `iqe-ra-key.pem` is sensitive - handle like a password
- ⚠️  `ca-key.pem` is VERY sensitive - keep on secure server only
- ⚠️  DO NOT commit private keys to git
- ⚠️  Use secure channels for file transfer

### RA Certificate vs Password
You now have TWO ways IQE can authenticate:

**Method 1: Password (Bootstrap)**
- Endpoint: `/bootstrap`
- Auth: `iqe-gateway` / `iqe-secure-password-2024`
- Status: Implemented, getting 500 errors (might be fixed with base64 support)

**Method 2: RA Certificate** (RECOMMENDED)
- Endpoint: `/simpleenroll`
- Auth: Client certificate (iqe-ra-cert.pem + iqe-ra-key.pem)
- Status: Generated, ready to test
- Advantages: More secure, bypasses SRP auth, proper EST gateway pattern

Try BOTH methods and see which works better!

## Current Status

**Date**: 2025-11-03
**Branch**: deploy_v1
**Server**: Not yet deployed to Ubuntu VM
**IQE Team**: Awaiting responses to questions

**Next Immediate Steps**:
1. Test RA cert authentication locally (run `test_ra_cert_auth.py`)
2. Push to `deploy_v1` branch
3. Deploy to Ubuntu VM
4. Send files + questions to IQE team
5. Wait for their CA cert import and testing

Good luck! 🚀
