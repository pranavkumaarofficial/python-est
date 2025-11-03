baa@brdinterop6331:~$ curl -vk https://10.42.56.101:8445/.well-known/est/cacerts -o /tmp/test.p7
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
} [5 bytes data]
* TLSv1.3 (OUT), TLS app data, [no content] (0):
} [1 bytes data]
> GET /.well-known/est/cacerts HTTP/1.1
> Host: 10.42.56.101:8445
> User-Agent: curl/7.61.1
> Accept: */*
>
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
< date: Mon, 03 Nov 2025 12:45:07 GMT
< server: uvicorn
< content-transfer-encoding: base64
< content-disposition: attachment; filename=cacerts.p7c
< content-length: 1948
< content-type: application/pkcs7-mime
<
{ [5 bytes data]
* TLSv1.3 (IN), TLS app data, [no content] (0):
{ [1 bytes data]
100  1948  100  1948    0     0   190k      0 --:--:-- --:--:-- --:--:--  190k
* Connection #0 to host 10.42.56.101 left intact
baa@brdinterop6331:~$ curl -vk https://10.42.56.101:8445/.well-known/est/cacerts 2>&1 | grep -i "content-transfer"
< content-transfer-encoding: base64
baa@brdinterop6331:~$ head -1 /tmp/test.p7
MIIFrwYJKoZIhvcNAQcCoIIFoDCCBZwCAQExADALBgkqhkiG9w0BBwGgggWEMIIFgDCCA2igAwIBAgIUY4Ol2QrBpTh2C6z+CaAPJpi5DowwDQYJKoZIhvcNAQELBQAwWDELMAkGA1UEBhMCVVMxCzAJBgNVBAgMAkNBMQ0wCwYDVQQHDARUZXN0MRAwDgYDVQQKDAdUZXN0IENBMRswGQYDVQQDDBJQeXRob24tRVNUIFJvb3QgQ0EwHhcNMjUxMTAzMDcwMjA5WhcNMzUxMTAxMDcwMjA5WjBYMQswCQYDVQQGEwJVUzELMAkGA1UECAwCQ0ExDTALBgNVBAcMBFRlc3QxEDAOBgNVBAoMB1Rlc3QgQ0ExGzAZBgNVBAMMElB5dGhvbi1FU1QgUm9vdCBDQTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAOGIXym4/FjeGEeyWHisxtR0jN/y+GsDb8fXWhfh0IduiEmlF9TWr1Ujl6rfG2ALrujpoJGQyKL3Sq4qo95Z+v8IsN9ohBKs7v8uBlkkzHMD1M9V4nGU6HzWrRBgQOUL2uwNkIwQWSvVGleIP+VL1IQLtxjkIGIIcHTJiAgfdaizAX4vl0reOmwU+Nw4OnRhVX0Pwh/W9EBzc2TxSdbMs1zk7VzGs8m+I8g43kLcSwHlmrtBjC8VLai0INYvDQARxceTtZ9o+/ORZ1IH1sEk1Qd5ClDY+fWUJ4rSnxcGmTC4lab1HmxxzSUmrlqcs/HjLyWQAl7rOTNi4xGbQ1ZM7WOCi5SqblIg8h3XS9sStliu0d/4rHhJn22kjqzm46pXUZJVZ7YkBIPXhnwD4A3HboFxpPkbws/Jqeba0vspxrPasIoyniFmxj+pY4yXcjQV1CnBHm8P4wuBbOU6Br5qFewYCCQajTZu3VUX2IpjNEQGBnFzZ9i7ZiBizaKdpHlt3hW2hgN9ML04DrzCOOcFskBgrFGiy3wHSLhLjHg6ouAim+A0APcLFaMxke4ieEMJr3Lyj9m9KDckmeHKBeQEG4l9nfankQjpHlU4wKA06cjyBO9voaJKqzr6IY9yjLLmFtADSVM7joNmfhNrrkMA5enTSOabXHE73oX2/jUYcRhdAgMBAAGjQjBAMA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgGGMB0GA1UdDgQWBBTAR7WCg2p4Tt97ze+1lcdAwtUOtzANBgkqhkiG9w0BAQsFAAOCAgEAlheP++dhCnux4J7/WUQW349EH8jEYv0Xdhe7/vtM2bqSgYXp1X5sAX+AGAZT9U8C8QK74LnPjDYal1PIPI1K+4pzzvDLCen8LqYHK+bhEXo7NGg8Uz64wEnyuRRJh66zLYj4hXK6rbGSXRHCZYS8ISno71VeNqNi50/IuuzfUlr2nGrDZ1RqGkrKRu/rsfY4TLrVY+KBkxJb34PYea554DCEu5rYHDaaj1l3E6BCrikGxEDIL1VHdQ1cn7D7w3WU6oxJaR9YGwbzOKOKrGsI71WY8yb+3ecY3aD/AC1XT4ut2mUqWrhJLzSlgPJbzv9TFyoe7NiTyrGaGF8yJbDtm5wAKLP8v1S6ho9J+gVdWf8xBPfh5cUgm/Mce9AGydsEcgqAwvUM5ESrXizXo51WadA2lu/DHQ4m25s/7neF36HXI+i8QUHTH3FhHxyVHUfBghMbg5m0a1M1IYJHgiBEtumOyiSCv/OhiG4PkMuk7kIiz+HXqnyiL8aXFALjHkbTzm+gi5uGXW27Y5TyBryxrYnB1JWgdYog6XM7QeXwAPKiyzcl8cxUUdtZ2dJDb7YVNwyFh6vWK+lkKOdJBE5Bw3jr44VDziqDybHasv30deGGe+W/KX29Vbsn8uQ+N1Ki/TC1DizE82OceG8J3jOOtdlG2LbI0/9bSNJokq/t3E4xAA==baa@brdinterop6331:~$ base64 -d /tmp/test.p7 > /tmp/test.der
baa@brdinterop6331:~$ openssl pkcs7 -inform DER -in /tmp/test.der -print_certs -text
Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number:
            63:83:a5:d9:0a:c1:a5:38:76:0b:ac:fe:09:a0:0f:26:98:b9:0e:8c
        Signature Algorithm: sha256WithRSAEncryption
        Issuer: C=US, ST=CA, L=Test, O=Test CA, CN=Python-EST Root CA
        Validity
            Not Before: Nov  3 07:02:09 2025 GMT
            Not After : Nov  1 07:02:09 2035 GMT
        Subject: C=US, ST=CA, L=Test, O=Test CA, CN=Python-EST Root CA
        Subject Public Key Info:
            Public Key Algorithm: rsaEncryption
                RSA Public-Key: (4096 bit)
                Modulus:
                    00:e1:88:5f:29:b8:fc:58:de:18:47:b2:58:78:ac:
                    c6:d4:74:8c:df:f2:f8:6b:03:6f:c7:d7:5a:17:e1:
                    d0:87:6e:88:49:a5:17:d4:d6:af:55:23:97:aa:df:
                    1b:60:0b:ae:e8:e9:a0:91:90:c8:a2:f7:4a:ae:2a:
                    a3:de:59:fa:ff:08:b0:df:68:84:12:ac:ee:ff:2e:
                    06:59:24:cc:73:03:d4:cf:55:e2:71:94:e8:7c:d6:
                    ad:10:60:40:e5:0b:da:ec:0d:90:8c:10:59:2b:d5:
                    1a:57:88:3f:e5:4b:d4:84:0b:b7:18:e4:20:62:08:
                    70:74:c9:88:08:1f:75:a8:b3:01:7e:2f:97:4a:de:
                    3a:6c:14:f8:dc:38:3a:74:61:55:7d:0f:c2:1f:d6:
                    f4:40:73:73:64:f1:49:d6:cc:b3:5c:e4:ed:5c:c6:
                    b3:c9:be:23:c8:38:de:42:dc:4b:01:e5:9a:bb:41:
                    8c:2f:15:2d:a8:b4:20:d6:2f:0d:00:11:c5:c7:93:
                    b5:9f:68:fb:f3:91:67:52:07:d6:c1:24:d5:07:79:
                    0a:50:d8:f9:f5:94:27:8a:d2:9f:17:06:99:30:b8:
                    95:a6:f5:1e:6c:71:cd:25:26:ae:5a:9c:b3:f1:e3:
                    2f:25:90:02:5e:eb:39:33:62:e3:11:9b:43:56:4c:
                    ed:63:82:8b:94:aa:6e:52:20:f2:1d:d7:4b:db:12:
                    b6:58:ae:d1:df:f8:ac:78:49:9f:6d:a4:8e:ac:e6:
                    e3:aa:57:51:92:55:67:b6:24:04:83:d7:86:7c:03:
                    e0:0d:c7:6e:81:71:a4:f9:1b:c2:cf:c9:a9:e6:da:
                    d2:fb:29:c6:b3:da:b0:8a:32:9e:21:66:c6:3f:a9:
                    63:8c:97:72:34:15:d4:29:c1:1e:6f:0f:e3:0b:81:
                    6c:e5:3a:06:be:6a:15:ec:18:08:24:1a:8d:36:6e:
                    dd:55:17:d8:8a:63:34:44:06:06:71:73:67:d8:bb:
                    66:20:62:cd:a2:9d:a4:79:6d:de:15:b6:86:03:7d:
                    30:bd:38:0e:bc:c2:38:e7:05:b2:40:60:ac:51:a2:
                    cb:7c:07:48:b8:4b:8c:78:3a:a2:e0:22:9b:e0:34:
                    00:f7:0b:15:a3:31:91:ee:22:78:43:09:af:72:f2:
                    8f:d9:bd:28:37:24:99:e1:ca:05:e4:04:1b:89:7d:
                    9d:f6:a7:91:08:e9:1e:55:38:c0:a0:34:e9:c8:f2:
                    04:ef:6f:a1:a2:4a:ab:3a:fa:21:8f:72:8c:b2:e6:
                    16:d0:03:49:53:3b:8e:83:66:7e:13:6b:ae:43:00:
                    e5:e9:d3:48:e6:9b:5c:71:3b:de:85:f6:fe:35:18:
                    71:18:5d
                Exponent: 65537 (0x10001)
        X509v3 extensions:
            X509v3 Basic Constraints: critical
                CA:TRUE
            X509v3 Key Usage: critical
                Digital Signature, Certificate Sign, CRL Sign
            X509v3 Subject Key Identifier:
                C0:47:B5:82:83:6A:78:4E:DF:7B:CD:EF:B5:95:C7:40:C2:D5:0E:B7
    Signature Algorithm: sha256WithRSAEncryption
         96:17:8f:fb:e7:61:0a:7b:b1:e0:9e:ff:59:44:16:df:8f:44:
         1f:c8:c4:62:fd:17:76:17:bb:fe:fb:4c:d9:ba:92:81:85:e9:
         d5:7e:6c:01:7f:80:18:06:53:f5:4f:02:f1:02:bb:e0:b9:cf:
         8c:36:1a:97:53:c8:3c:8d:4a:fb:8a:73:ce:f0:cb:09:e9:fc:
         2e:a6:07:2b:e6:e1:11:7a:3b:34:68:3c:53:3e:b8:c0:49:f2:
         b9:14:49:87:ae:b3:2d:88:f8:85:72:ba:ad:b1:92:5d:11:c2:
         65:84:bc:21:29:e8:ef:55:5e:36:a3:62:e7:4f:c8:ba:ec:df:
         52:5a:f6:9c:6a:c3:67:54:6a:1a:4a:ca:46:ef:eb:b1:f6:38:
         4c:ba:d5:63:e2:81:93:12:5b:df:83:d8:79:ae:79:e0:30:84:
         bb:9a:d8:1c:36:9a:8f:59:77:13:a0:42:ae:29:06:c4:40:c8:
         2f:55:47:75:0d:5c:9f:b0:fb:c3:75:94:ea:8c:49:69:1f:58:
         1b:06:f3:38:a3:8a:ac:6b:08:ef:55:98:f3:26:fe:dd:e7:18:
         dd:a0:ff:00:2d:57:4f:8b:ad:da:65:2a:5a:b8:49:2f:34:a5:
         80:f2:5b:ce:ff:53:17:2a:1e:ec:d8:93:ca:b1:9a:18:5f:32:
         25:b0:ed:9b:9c:00:28:b3:fc:bf:54:ba:86:8f:49:fa:05:5d:
         59:ff:31:04:f7:e1:e5:c5:20:9b:f3:1c:7b:d0:06:c9:db:04:
         72:0a:80:c2:f5:0c:e4:44:ab:5e:2c:d7:a3:9d:56:69:d0:36:
         96:ef:c3:1d:0e:26:db:9b:3f:ee:77:85:df:a1:d7:23:e8:bc:
         41:41:d3:1f:71:61:1f:1c:95:1d:47:c1:82:13:1b:83:99:b4:
         6b:53:35:21:82:47:82:20:44:b6:e9:8e:ca:24:82:bf:f3:a1:
         88:6e:0f:90:cb:a4:ee:42:22:cf:e1:d7:aa:7c:a2:2f:c6:97:
         14:02:e3:1e:46:d3:ce:6f:a0:8b:9b:86:5d:6d:bb:63:94:f2:
         06:bc:b1:ad:89:c1:d4:95:a0:75:8a:20:e9:73:3b:41:e5:f0:
         00:f2:a2:cb:37:25:f1:cc:54:51:db:59:d9:d2:43:6f:b6:15:
         37:0c:85:87:ab:d6:2b:e9:64:28:e7:49:04:4e:41:c3:78:eb:
         e3:85:43:ce:2a:83:c9:b1:da:b2:fd:f4:75:e1:86:7b:e5:bf:
         29:7d:bd:55:bb:27:f2:e4:3e:37:52:a2:fd:30:b5:0e:2c:c4:
         f3:63:9c:78:6f:09:de:33:8e:b5:d9:46:d8:b6:c8:d3:ff:5b:
         48:d2:68:92:af:ed:dc:4e
-----BEGIN CERTIFICATE-----
MIIFgDCCA2igAwIBAgIUY4Ol2QrBpTh2C6z+CaAPJpi5DowwDQYJKoZIhvcNAQEL
BQAwWDELMAkGA1UEBhMCVVMxCzAJBgNVBAgMAkNBMQ0wCwYDVQQHDARUZXN0MRAw
DgYDVQQKDAdUZXN0IENBMRswGQYDVQQDDBJQeXRob24tRVNUIFJvb3QgQ0EwHhcN
MjUxMTAzMDcwMjA5WhcNMzUxMTAxMDcwMjA5WjBYMQswCQYDVQQGEwJVUzELMAkG
A1UECAwCQ0ExDTALBgNVBAcMBFRlc3QxEDAOBgNVBAoMB1Rlc3QgQ0ExGzAZBgNV
BAMMElB5dGhvbi1FU1QgUm9vdCBDQTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCC
AgoCggIBAOGIXym4/FjeGEeyWHisxtR0jN/y+GsDb8fXWhfh0IduiEmlF9TWr1Uj
l6rfG2ALrujpoJGQyKL3Sq4qo95Z+v8IsN9ohBKs7v8uBlkkzHMD1M9V4nGU6HzW
rRBgQOUL2uwNkIwQWSvVGleIP+VL1IQLtxjkIGIIcHTJiAgfdaizAX4vl0reOmwU
+Nw4OnRhVX0Pwh/W9EBzc2TxSdbMs1zk7VzGs8m+I8g43kLcSwHlmrtBjC8VLai0
INYvDQARxceTtZ9o+/ORZ1IH1sEk1Qd5ClDY+fWUJ4rSnxcGmTC4lab1HmxxzSUm
rlqcs/HjLyWQAl7rOTNi4xGbQ1ZM7WOCi5SqblIg8h3XS9sStliu0d/4rHhJn22k
jqzm46pXUZJVZ7YkBIPXhnwD4A3HboFxpPkbws/Jqeba0vspxrPasIoyniFmxj+p
Y4yXcjQV1CnBHm8P4wuBbOU6Br5qFewYCCQajTZu3VUX2IpjNEQGBnFzZ9i7ZiBi
zaKdpHlt3hW2hgN9ML04DrzCOOcFskBgrFGiy3wHSLhLjHg6ouAim+A0APcLFaMx
ke4ieEMJr3Lyj9m9KDckmeHKBeQEG4l9nfankQjpHlU4wKA06cjyBO9voaJKqzr6
IY9yjLLmFtADSVM7joNmfhNrrkMA5enTSOabXHE73oX2/jUYcRhdAgMBAAGjQjBA
MA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgGGMB0GA1UdDgQWBBTAR7WC
g2p4Tt97ze+1lcdAwtUOtzANBgkqhkiG9w0BAQsFAAOCAgEAlheP++dhCnux4J7/
WUQW349EH8jEYv0Xdhe7/vtM2bqSgYXp1X5sAX+AGAZT9U8C8QK74LnPjDYal1PI
PI1K+4pzzvDLCen8LqYHK+bhEXo7NGg8Uz64wEnyuRRJh66zLYj4hXK6rbGSXRHC
ZYS8ISno71VeNqNi50/IuuzfUlr2nGrDZ1RqGkrKRu/rsfY4TLrVY+KBkxJb34PY
ea554DCEu5rYHDaaj1l3E6BCrikGxEDIL1VHdQ1cn7D7w3WU6oxJaR9YGwbzOKOK
rGsI71WY8yb+3ecY3aD/AC1XT4ut2mUqWrhJLzSlgPJbzv9TFyoe7NiTyrGaGF8y
JbDtm5wAKLP8v1S6ho9J+gVdWf8xBPfh5cUgm/Mce9AGydsEcgqAwvUM5ESrXizX
o51WadA2lu/DHQ4m25s/7neF36HXI+i8QUHTH3FhHxyVHUfBghMbg5m0a1M1IYJH
giBEtumOyiSCv/OhiG4PkMuk7kIiz+HXqnyiL8aXFALjHkbTzm+gi5uGXW27Y5Ty
BryxrYnB1JWgdYog6XM7QeXwAPKiyzcl8cxUUdtZ2dJDb7YVNwyFh6vWK+lkKOdJ
BE5Bw3jr44VDziqDybHasv30deGGe+W/KX29Vbsn8uQ+N1Ki/TC1DizE82OceG8J
3jOOtdlG2LbI0/9bSNJokq/t3E4=
-----END CERTIFICATE-----