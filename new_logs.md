baa@brdinterop6331:~$ cd /tmp
baa@brdinterop6331:/tmp$ clear
baa@brdinterop6331:/tmp$ # Generate CSR
baa@brdinterop6331:/tmp$ openssl req -new -newkey rsa:2048 -nodes \
>   -keyout test-key.pem -out test-csr.der -outform DER \
>   -subj "/CN=test-pump-final"
Generating a RSA private key
..+++++
............................................................................+++++
writing new private key to 'test-key.pem'
-----
baa@brdinterop6331:/tmp$
baa@brdinterop6331:/tmp$ # Test enrollment with password
baa@brdinterop6331:/tmp$ curl -vk -u iqe-gateway:iqe-secure-password-2024 \
>   -H "Content-Type: application/pkcs10" \
>   --data-binary @test-csr.der \
>   https://10.42.56.101:8445/.well-known/est/simpleenroll \
>   -o client-cert.p7
*   Trying 10.42.56.101...
* TCP_NODELAY set
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0* Connected to 10.42.56.101 (10.42.56.101) port 8445 (#0)
* ALPN, offering h2
* ALPN, offering http/1.1
* successfully set certificate verify locations:
*   CAfile: /etc/pki/tls/certs/ca-bundle.crt
  CApath: none
} [5 bytes data]
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
} [512 bytes data]
* TLSv1.3 (IN), TLS handshake, Server hello (2):
{ [122 bytes data]
* TLSv1.3 (IN), TLS handshake, [no content] (0):
{ [1 bytes data]
* TLSv1.3 (IN), TLS handshake, Encrypted Extensions (8):
{ [28 bytes data]
* TLSv1.3 (IN), TLS handshake, [no content] (0):
{ [1 bytes data]
* TLSv1.3 (IN), TLS handshake, Certificate (11):
{ [2610 bytes data]
* TLSv1.3 (IN), TLS handshake, [no content] (0):
{ [1 bytes data]
* TLSv1.3 (IN), TLS handshake, CERT verify (15):
{ [264 bytes data]
* TLSv1.3 (IN), TLS handshake, [no content] (0):
{ [1 bytes data]
* TLSv1.3 (IN), TLS handshake, Finished (20):
{ [52 bytes data]
* TLSv1.3 (OUT), TLS change cipher, Change cipher spec (1):
} [1 bytes data]
* TLSv1.3 (OUT), TLS handshake, [no content] (0):
} [1 bytes data]
* TLSv1.3 (OUT), TLS handshake, Finished (20):
} [52 bytes data]
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384
* ALPN, server did not agree to a protocol
* Server certificate:
*  subject: C=US; ST=CA; L=Test; O=Python-EST Server; CN=localhost
*  start date: Nov  3 07:12:52 2025 GMT
*  expire date: Nov  3 07:12:52 2026 GMT
*  issuer: C=US; ST=CA; L=Test; O=Test CA; CN=Python-EST Root CA
*  SSL certificate verify result: self signed certificate in certificate chain (19), continuing anyway.
* Server auth using Basic with user 'iqe-gateway'
} [5 bytes data]
* TLSv1.3 (OUT), TLS app data, [no content] (0):
} [1 bytes data]
> POST /.well-known/est/simpleenroll HTTP/1.1
> Host: 10.42.56.101:8445
> Authorization: Basic aXFlLWdhdGV3YXk6aXFlLXNlY3VyZS1wYXNzd29yZC0yMDI0
> User-Agent: curl/7.61.1
> Accept: */*
> Content-Type: application/pkcs10
> Content-Length: 611
>
} [611 bytes data]
* upload completely sent off: 611 out of 611 bytes
{ [5 bytes data]
* TLSv1.3 (IN), TLS handshake, [no content] (0):
{ [1 bytes data]
* TLSv1.3 (IN), TLS handshake, Newsession Ticket (4):
{ [233 bytes data]
* TLSv1.3 (IN), TLS handshake, [no content] (0):
{ [1 bytes data]
* TLSv1.3 (IN), TLS handshake, Newsession Ticket (4):
{ [233 bytes data]
* TLSv1.3 (IN), TLS app data, [no content] (0):
{ [1 bytes data]
< HTTP/1.1 200 OK
< date: Mon, 03 Nov 2025 12:57:39 GMT
< server: uvicorn
< content-disposition: attachment; filename=cert.p7c
< content-length: 1191
< content-type: application/pkcs7-mime; smime-type=certs-only
<
{ [5 bytes data]
* TLSv1.3 (IN), TLS app data, [no content] (0):
{ [1 bytes data]
100  1802  100  1191  100   611  26466  13577 --:--:-- --:--:-- --:--:-- 40044
* Connection #0 to host 10.42.56.101 left intact
baa@brdinterop6331:/tmp$ openssl pkcs7 -inform DER -in client-cert.p7 -print_certs -out client.pem
baa@brdinterop6331:/tmp$ echo "Enrollment result: $?"
Enrollment result: 0
baa@brdinterop6331:/tmp$ cat client.pem | head -20
subject=CN = test-pump-final

issuer=C = US, ST = CA, L = Test, O = Test CA, CN = Python-EST Root CA

-----BEGIN CERTIFICATE-----
MIIEdDCCAlygAwIBAgIUCqXddU1S1I+CHE8UfAvdrZ22GXUwDQYJKoZIhvcNAQEL
BQAwWDELMAkGA1UEBhMCVVMxCzAJBgNVBAgMAkNBMQ0wCwYDVQQHDARUZXN0MRAw
DgYDVQQKDAdUZXN0IENBMRswGQYDVQQDDBJQeXRob24tRVNUIFJvb3QgQ0EwHhcN
MjUxMTAzMTI1NzM5WhcNMjYxMTAzMTI1NzM5WjAaMRgwFgYDVQQDDA90ZXN0LXB1
bXAtZmluYWwwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDZHY06lQsg
v8B2RCitlgH3IO/PlGnWNaHSukHUXyQ4TXIpgVVmW0yqvKKU9AcsVZrhSAqKjqmx
7Xau5Dh/nv0xGuUQiUy0uK4kd0H8B3qf4Vam35FhGhkg4+ZU8leLhMA3MPi6uKJv
jVcom+PpWgtqnoXzPaXC14m75qqqo0PiVHGWD56bVBW4fcMrhJaw0SvAL/sSRtoV
/LJ31FDUfEXDurx2Bnn/ajWD0hkjRDiNh9xtB9ffHTP4rRxp4ypcOOqsePrPLS6D
Mw1TNGg3giU+4vIABENzxBiI+dOuS+9x7g17Mu3nLen02V26+3hsbX3LY4gYxQbq
wlOTXB0M3yKdAgMBAAGjdDByMB0GA1UdDgQWBBSnoHeABZkL7NCM6/3sAw7AMdn9
6DAfBgNVHSMEGDAWgBTAR7WCg2p4Tt97ze+1lcdAwtUOtzAOBgNVHQ8BAf8EBAMC
BaAwIAYDVR0lAQH/BBYwFAYIKwYBBQUHAwIGCCsGAQUFBwMBMA0GCSqGSIb3DQEB
CwUAA4ICAQBypgDVA4BX2zPxdQlYNjPWNnjDmk88Xx8+0vi1auTnf3LYl5+oG1yw
yiqOlc6HEZUW9yT9Fe9/pdcbL+N1JrAOLThLfp8Uoi4O84wP3PzhQjHFXc3tDbMB
baa@brdinterop6331:/tmp$