#!/usr/bin/python
# -*- coding: utf-8 -*-
""" unittests for helper """
# pylint: disable=C0302, C0415, E0401, R0902, R0904, R0913, R0914, R0915, W0212
import unittest
import configparser
import sys
from unittest.mock import patch, MagicMock, Mock

sys.path.insert(0, '.')
sys.path.insert(1, '..')

class HelperTestCases(unittest.TestCase):
    """ test class for helper """
    def setUp(self):
        """ setup """
        import logging
        logging.basicConfig(level=logging.CRITICAL)
        from est_proxy.helper import config_load, hssrv_options_get, connection_log, b64decode_pad, b64_encode, b64_decode, b64_url_recode, build_pem_file, cert_pem2der, ca_handler_get, cert_serial_get, cert_eku_get, cert_extensions_get, cert_san_get, convert_byte_to_string, convert_string_to_byte, csr_cn_get, csr_san_get, uts_to_date_utc, logger_setup
        self.b64_decode = b64_decode
        self.b64_encode = b64_encode
        self.b64_url_recode = b64_url_recode
        self.b64decode_pad = b64decode_pad
        self.build_pem_file = build_pem_file
        self.ca_handler_get = ca_handler_get
        self.cert_eku_get = cert_eku_get
        self.cert_extensions_get = cert_extensions_get
        self.cert_san_get = cert_san_get
        self.cert_serial_get = cert_serial_get
        self.cert_pem2der = cert_pem2der
        self.config_load = config_load
        self.connection_log = connection_log
        self.convert_byte_to_string = convert_byte_to_string
        self.convert_string_to_byte = convert_string_to_byte
        self.csr_cn_get = csr_cn_get
        self.csr_san_get = csr_san_get
        self.logger_setup = logger_setup
        self.logger = logging.getLogger('test_est')
        self.hssrv_options_get = hssrv_options_get
        self.uts_to_date_utc = uts_to_date_utc

    def tearDown(self):
        """ teardown test environment """
        # Clean up run after every test method.

    def test_001_allways_ok(self):
        """ a test that never failes """
        self.assertEqual('foo', 'foo')

    def test_002_hssrv_options_get(self):
        """ test handshake options empty config dic and wrong task"""
        config_dic = {}
        task = 'wrong task'
        self.assertEqual({}, self.hssrv_options_get(self.logger, config_dic))

    def test_003_hssrv_options_get(self):
        """ test handshake options empty config dic Daemon task """
        config_dic = {}
        expected_log = 'ERROR:test_est:Helper.hssrv_options_get(): Daemon specified but not configured in config file'
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertEqual({}, self.hssrv_options_get(self.logger, config_dic))
        self.assertIn(expected_log, lcm.output)

    def test_004_hssrv_options_get(self):
        """ test handshake options empty config dic Daemon task """
        config_dic = {'Daemon': {'foo': 'bar'}}
        expected_log = 'ERROR:test_est:Helper.hssrv_options_get(): incomplete Daemon configuration in config file'
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertEqual({}, self.hssrv_options_get(self.logger, config_dic))
        self.assertIn(expected_log, lcm.output)

    def test_005_hssrv_options_get(self):
        """ test handshake options empty config dic Daemon task """
        config_dic = {'Daemon': {'cert_file': 'cert_file', 'foo': 'bar'}}
        expected_log = 'ERROR:test_est:Helper.hssrv_options_get(): incomplete Daemon configuration in config file'
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertEqual({}, self.hssrv_options_get(self.logger, config_dic))
        self.assertIn(expected_log, lcm.output)

    def test_006_hssrv_options_get(self):
        """ test handshake options empty config dic Daemon task """
        config_dic = {'Daemon': {'cert_file': 'cert_file', 'key_file': 'key_file'}}
        foo_ = {'reqCert': True, 'sni': None, 'privateKey': 'key_file', 'certChain': 'cert_file', 'alpn': [bytearray(b'http/1.1')]}
        self.assertTrue(foo_.items() <= self.hssrv_options_get(self.logger, config_dic).items())

    def test_007_hssrv_options_get(self):
        """ test handshake options SRP in with bogus parameters """
        config_dic = {'Daemon': {'cert_file': 'cert_file', 'key_file': 'key_file'}, 'SRP': {'foo': 'bar'}}
        foo_ = {'reqCert': True, 'sni': None, 'privateKey': 'key_file', 'certChain': 'cert_file', 'alpn': [bytearray(b'http/1.1')]}
        self.assertTrue(foo_.items() <= self.hssrv_options_get(self.logger, config_dic).items())

    def test_008_hssrv_options_get(self):
        """ test handshake options SRP included but database load failed """
        config_dic = {'Daemon': {'cert_file': 'cert_file', 'key_file': 'key_file'}, 'SRP': {'userdb': 'foo.db'}}
        foo_ = {'reqCert': True, 'sni': None, 'privateKey': 'key_file', 'certChain': 'cert_file', 'alpn': [bytearray(b'http/1.1')]}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertTrue(foo_.items() <= self.hssrv_options_get(self.logger, config_dic).items())
        error_message = "ERROR:test_est:Helper.hssrv_options_get(): SRP database foo.db could not get loaded."
        self.assertIn(error_message, lcm.output)

    def test_007_helper_b64_decode(self):
        """ test bas64 decoder for string value"""
        self.assertEqual('test', self.b64_decode(self.logger, 'dGVzdA=='))

    def test_008_helper_b64_decode(self):
        """ test bas64 decoder for byte value """
        self.assertEqual('test', self.b64_decode(self.logger, b'dGVzdA=='))

    def test_009_helper_b64_encode(self):
        """ test bas64 decoder for string value """
        self.assertEqual(b'dGVzdA==', self.b64_encode(self.logger, 'test'))

    def test_010_helper_b64_encode(self):
        """ test bas64 decoder for byte value """
        self.assertEqual(b'dGVzdA==', self.b64_encode(self.logger, b'test'))

    def test_011_helper_b64_url_recode(self):
        """ test base64url recode to base64 - add padding for 2 char"""
        self.assertEqual('fafafa==', self.b64_url_recode(self.logger, 'fafafa'))

    def test_012_helper_b64_url_recode(self):
        """ test base64url recode to base64 - add padding for 3 char"""
        self.assertEqual('fafaf===', self.b64_url_recode(self.logger, 'fafaf'))

    def test_013_helper_b64_url_recode(self):
        """ test base64url recode to base64 - no padding"""
        self.assertEqual('fafafafa', self.b64_url_recode(self.logger, 'fafafafa'))

    def test_014_helper_b64_url_recode(self):
        """ test base64url replace - with + and pad"""
        self.assertEqual('fafa+f==', self.b64_url_recode(self.logger, 'fafa-f'))

    def test_015_helper_b64_url_recode(self):
        """ test base64url replace _ with / and pad"""
        self.assertEqual('fafa/f==', self.b64_url_recode(self.logger, 'fafa_f'))

    def test_016_helper_b64_url_recode(self):
        """ test base64url recode to base64 - add padding for 1 char"""
        self.assertEqual('fafafaf=', self.b64_url_recode(self.logger, b'fafafaf'))

    def test_017_helper_b64_url_recode(self):
        """ test base64url recode to base64 - add padding for 2 char"""
        self.assertEqual('fafafa==', self.b64_url_recode(self.logger, b'fafafa'))

    def test_018_helper_b64_url_recode(self):
        """ test base64url recode to base64 - add padding for 3 char"""
        self.assertEqual('fafaf===', self.b64_url_recode(self.logger, b'fafaf'))

    def test_019_helper_b64_url_recode(self):
        """ test base64url recode to base64 - no padding"""
        self.assertEqual('fafafafa', self.b64_url_recode(self.logger, b'fafafafa'))

    def test_020_helper_b64_url_recode(self):
        """ test base64url replace - with + and pad"""
        self.assertEqual('fafa+f==', self.b64_url_recode(self.logger, b'fafa-f'))

    def test_021_helper_b64_url_recode(self):
        """ test base64url replace _ with / and pad"""
        self.assertEqual('fafa/f==', self.b64_url_recode(self.logger, b'fafa_f'))

    def test_022_helper_build_pem_file(self):
        """ test build_pem_file without exsting content """
        existing = None
        cert = 'cert'
        self.assertEqual('-----BEGIN CERTIFICATE-----\ncert\n-----END CERTIFICATE-----\n', self.build_pem_file(self.logger, existing, cert, True))

    def test_023_helper_build_pem_file(self):
        """ test build_pem_file with exsting content """
        existing = 'existing'
        cert = 'cert'
        self.assertEqual('existing-----BEGIN CERTIFICATE-----\ncert\n-----END CERTIFICATE-----\n', self.build_pem_file(self.logger, existing, cert, True))

    def test_024_helper_build_pem_file(self):
        """ test build_pem_file with long cert (to test wrap) """
        existing = None
        cert = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        self.assertEqual('-----BEGIN CERTIFICATE-----\naaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\naaaaaaaaa\n-----END CERTIFICATE-----\n', self.build_pem_file(self.logger, existing, cert, True))

    def test_025_helper_build_pem_file(self):
        """ test build_pem_file with long cert (to test wrap) """
        existing = None
        cert = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        self.assertEqual('-----BEGIN CERTIFICATE-----\naaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n-----END CERTIFICATE-----\n', self.build_pem_file(self.logger, existing, cert, False))

    def test_026_helper_build_pem_file(self):
        """ test build_pem_file for CSR """
        existing = None
        csr = 'MIIClzCCAX8CAQAwGTEXMBUGA1UEAwwOZm9vMS5iYXIubG9jYWwwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDBvH7P73CwR7AF/WGeTfIDLlMWD6VZV3CTZBF0AwNMTFU/zbdAX8r63pzElX/5C5ZVsc36XHqdAJcioJlI33uE3RhOSvDyOcDgWlnPK9gj2soQ7enizGqd1u7hf6C3IwFtc4uGNOU3Z/tnTzVdYiCSKS+5lTZfMxn4FtEUN+w90NHBvC+AlTo3Gl0gqbYOZgg/UwWj60u7S2gBzSeb2/w62Z7bz+SknGZbeI4ySo30ET6oCSCAUN42jE+1dHI/Y+tGBtqP3h7W7OezKeLsJjD9r07U0+uMoVCY9oKTyT0gK8+gsde0tpt6QKa93HJGUPAP9ehrKCl335QcJESFw67/AgMBAAGgOTA3BgkqhkiG9w0BCQ4xKjAoMAsGA1UdDwQEAwIF4DAZBgNVHREEEjAQgg5mb28xLmJhci5sb2NhbDANBgkqhkiG9w0BAQsFAAOCAQEAf4cdGpYHLqX+06BFF7+NqXLmKvc7n66vAfevLN75eu/pCXhhRSdpXvcYm+mAVEXJCPaG2kFGt6wfBvVWoVX/91d+OuAtiUHmhY95Oi7g3RF3ThCrvT2mR4zsNiKgC34jXbl9489iIiFRBQXkq2fLwN5JwBYutUENwkDIeApRRbmUzTDbar1xoBAQ3GjVtOAEjHc/3S1yyKkCpM6Qkg8uWOJAXw9INJqH6x55nMZrvTUuXkURc/mvhV+bp2vdKoigGvfa3VVfoAI0BZLQMohQ9QLKoNQsKxEs3JidvpZrl3o23LMGEPoJs3zIuowTa217PHwdBw4UwtD7KxJK/+344A=='
        result = """-----BEGIN CERTIFICATE REQUEST-----
MIIClzCCAX8CAQAwGTEXMBUGA1UEAwwOZm9vMS5iYXIubG9jYWwwggEiMA0GCSqG
SIb3DQEBAQUAA4IBDwAwggEKAoIBAQDBvH7P73CwR7AF/WGeTfIDLlMWD6VZV3CT
ZBF0AwNMTFU/zbdAX8r63pzElX/5C5ZVsc36XHqdAJcioJlI33uE3RhOSvDyOcDg
WlnPK9gj2soQ7enizGqd1u7hf6C3IwFtc4uGNOU3Z/tnTzVdYiCSKS+5lTZfMxn4
FtEUN+w90NHBvC+AlTo3Gl0gqbYOZgg/UwWj60u7S2gBzSeb2/w62Z7bz+SknGZb
eI4ySo30ET6oCSCAUN42jE+1dHI/Y+tGBtqP3h7W7OezKeLsJjD9r07U0+uMoVCY
9oKTyT0gK8+gsde0tpt6QKa93HJGUPAP9ehrKCl335QcJESFw67/AgMBAAGgOTA3
BgkqhkiG9w0BCQ4xKjAoMAsGA1UdDwQEAwIF4DAZBgNVHREEEjAQgg5mb28xLmJh
ci5sb2NhbDANBgkqhkiG9w0BAQsFAAOCAQEAf4cdGpYHLqX+06BFF7+NqXLmKvc7
n66vAfevLN75eu/pCXhhRSdpXvcYm+mAVEXJCPaG2kFGt6wfBvVWoVX/91d+OuAt
iUHmhY95Oi7g3RF3ThCrvT2mR4zsNiKgC34jXbl9489iIiFRBQXkq2fLwN5JwBYu
tUENwkDIeApRRbmUzTDbar1xoBAQ3GjVtOAEjHc/3S1yyKkCpM6Qkg8uWOJAXw9I
NJqH6x55nMZrvTUuXkURc/mvhV+bp2vdKoigGvfa3VVfoAI0BZLQMohQ9QLKoNQs
KxEs3JidvpZrl3o23LMGEPoJs3zIuowTa217PHwdBw4UwtD7KxJK/+344A==
-----END CERTIFICATE REQUEST-----
"""
        self.assertEqual(result, self.build_pem_file(self.logger, existing, csr, False, True))

    def test_027_helper_build_pem_file(self):
        """ test build_pem_file with long cert (to test wrap) """
        existing = 'existing'
        cert = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        self.assertEqual('existing-----BEGIN CERTIFICATE-----\naaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n-----END CERTIFICATE-----\n', self.build_pem_file(self.logger, existing, cert, False))

    def test_027_helper_ca_handler_get(self):
        """ identifier check none input"""
        file_name = 'foo'
        self.assertEqual('foo', self.ca_handler_get(self.logger, file_name))

    def test_028_helper_ca_handler_get(self):
        """ identifier check none input"""
        file_name = 'foo.py'
        self.assertEqual('foo', self.ca_handler_get(self.logger, file_name))

    def test_029_helper_ca_handler_get(self):
        """ identifier check none input"""
        file_name = 'foo/foo.py'
        self.assertEqual('foo.foo', self.ca_handler_get(self.logger, file_name))

    def test_030_helper_ca_handler_get(self):
        """ identifier check none input"""
        file_name = 'foo\\foo.py'
        self.assertEqual('foo.foo', self.ca_handler_get(self.logger, file_name))

    def test_031_helper_cert_serial_get(self):
        """ test cert_serial_get """
        cert = """MIIDDTCCAfWgAwIBAgIBCjANBgkqhkiG9w0BAQsFADAaMRgwFgYDVQQDEw9mb28u
                ZXhhbXBsZS5jb20wHhcNMTkwMTIwMTY1OTIwWhcNMTkwMjE5MTY1OTIwWjAaMRgw
                FgYDVQQDEw9mb28uZXhhbXBsZS5jb20wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAw
                ggEKAoIBAQCqUeNzDyBVugUKZq597ishYAdMPgus5Nw5pWE/Jw7PP0koeFE2wODq
                HVb+XNFFEX4IOyiE2Pi4ilzfXYGKchhP3wHgnkxGNIwt/cDNZgyTiUpITV/ciFaC
                7avkvQS6ScCYUYrhby7QnvcU02mAyhNcSVGI5TW7HhFdtWrEAK3N8H6yhxHLSi2y
                dpQ3kCJyJylqt/Rv3uKNjCvTv867K6A1QSsXoAxtPK9P0UOTRvgHkFf8T32Bn/Er
                1bjkX9Ms8rqDQmicCWJk260lUHzN6vxaeiEg7Kz3TA8Ik3DMIcvwJrE168G1APo+
                FyOIKyx+t78HWOlNINIqZMj5e2DpulV7AgMBAAGjXjBcMB8GA1UdIwQYMBaAFK1Z
                zuGt0Pe+NLerCXqQBYmVV7suMB0GA1UdDgQWBBStWc7hrdD3vjS3qwl6kAWJlVe7
                LjAaBgNVHREEEzARgg9mb28uZXhhbXBsZS5jb20wDQYJKoZIhvcNAQELBQADggEB
                AANW0DD4Xp7LH/Rzf2jVLwiFlbtR6iazyn9S/pH2Gwqjkscv/27/dqJb7CfPdD02
                5ItQcYkZPJhDOsj63kvUaD89QU31RnYQrXrbXFqYOIAq6kxfZUoQmpfEBxbB4Wxm
                TW0OWS+FMqNw/SuGs6EQjTRA+gBOeGzj4H9yOFOg0PpadBayZ7UT4lm1LOiFHh8h
                bta75ocePrurdNxsxKJhLlXbnKD6lurCb4khRhrmLmpK8JxhuaevEVklSQX0gqlR
                fxAH4XQsaqcaedPNI+W5OUITMz40ezDCbUqxS9KEMCGPoOTXNRAjbr72sc4Vkw7H
                t+eRUDECE+0UnjyeCjTn3EU="""
        self.assertEqual(10, self.cert_serial_get(self.logger, cert))

    def test_032_helper_convert_byte_to_string(self):
        """ convert byte2string for a string value """
        self.assertEqual('foo', self.convert_byte_to_string('foo'))

    def test_033_helper_convert_byte_to_string(self):
        """ convert byte2string for a string value """
        self.assertEqual('foo', self.convert_byte_to_string('foo'))

    def test_034_helper_convert_byte_to_string(self):
        """ convert byte2string for a string value """
        self.assertNotEqual('foo', self.convert_byte_to_string('foobar'))

    def test_035_helper_convert_byte_to_string(self):
        """ convert byte2string for a string value """
        self.assertNotEqual('foo', self.convert_byte_to_string(b'foobar'))

    def test_036_helper_convert_string_to_byte(self):
        """ convert string value to byte """
        value = 'foo.bar'
        self.assertEqual(b'foo.bar', self.convert_string_to_byte(value))

    def test_037_helper_convert_string_to_byte(self):
        """ convert string value to byte """
        value = b'foo.bar'
        self.assertEqual(b'foo.bar', self.convert_string_to_byte(value))

    def test_038_helper_convert_string_to_byte(self):
        """ convert string value to byte """
        value = b''
        self.assertEqual(b'', self.convert_string_to_byte(value))

    def test_039_helper_convert_string_to_byte(self):
        """ convert string value to byte """
        value = ''
        self.assertEqual(b'', self.convert_string_to_byte(value))

    def test_040_helper_convert_string_to_byte(self):
        """ convert string value to byte """
        value = None
        self.assertFalse(self.convert_string_to_byte(value))

    def test_041_helper_csr_cn_get(self):
        """ get cn of csr """
        csr = 'MIIClzCCAX8CAQAwGTEXMBUGA1UEAwwOZm9vMS5iYXIubG9jYWwwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC0lk4lyEIa0VL/u5ic01Zo/o+gyYqFpU7xe+nbFgiKA+R1rqrzP/sR6xjHqS0Rkv/BcBXf81sp/+iDmwIQLVlBTkKdimqVHCJMAbTL8ZNpcLDaRUce4liyX1cmczPTSqI/kcyEr8tKpYN+KzvKZZsNx2Pbgu7y7/70P2uSywiW+sqYZ+X28KGFxq6wwENzJtweDVsbWql9LLtw6daF41UQg10auNlRL1nhW0SlWZh1zPPW/0sa6C3xX28jjVh843b4ekkRNLXSEYQMTi0qYR2LomQ5aTlQ/hellf17UknfN2aA2RH5D7Ek+mndj/rH21bxQg26KRmHlaJld9K1IfvJAgMBAAGgOTA3BgkqhkiG9w0BCQ4xKjAoMAsGA1UdDwQEAwIF4DAZBgNVHREEEjAQgg5mb28xLmJhci5sb2NhbDANBgkqhkiG9w0BAQsFAAOCAQEAl3egrkO3I94IpxxfSJmVetd7s9uW3lSBqh9OiypFevQO7ZgUxau+k05NKTUNpSq3W9H/lRr5AG5x3/VX8XZVbcLKXQ0d6e38uXBAUFQQJmjBVYqd8KcMfqLeFFUBsLcG04yek2tNIbhXZfBtw9UYO27Y5ktMgWjAz2VskIXl3E2L0b8tGnSKDoMB07IVpYB9bHfHX4o+ccIgq1HxyYT1d+eVIQuSHHxR7j7Wkgb8RG9bCWpVWaYWKWU0Inh3gMnP06kPBJ9nOB4adgC3Hz37ab/0KpmBuQBEgmMfINwV/OpJVv2Su1FYK+uX7E1qUGae6QDsfg0Yor9uP0Vkv4b1NA=='
        self.assertEqual('foo1.bar.local', self.csr_cn_get(self.logger, csr))

    def test_042_helper_csr_cn_get(self):
        """ get cn of csr """
        csr = b'MIIClzCCAX8CAQAwGTEXMBUGA1UEAwwOZm9vMS5iYXIubG9jYWwwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC0lk4lyEIa0VL/u5ic01Zo/o+gyYqFpU7xe+nbFgiKA+R1rqrzP/sR6xjHqS0Rkv/BcBXf81sp/+iDmwIQLVlBTkKdimqVHCJMAbTL8ZNpcLDaRUce4liyX1cmczPTSqI/kcyEr8tKpYN+KzvKZZsNx2Pbgu7y7/70P2uSywiW+sqYZ+X28KGFxq6wwENzJtweDVsbWql9LLtw6daF41UQg10auNlRL1nhW0SlWZh1zPPW/0sa6C3xX28jjVh843b4ekkRNLXSEYQMTi0qYR2LomQ5aTlQ/hellf17UknfN2aA2RH5D7Ek+mndj/rH21bxQg26KRmHlaJld9K1IfvJAgMBAAGgOTA3BgkqhkiG9w0BCQ4xKjAoMAsGA1UdDwQEAwIF4DAZBgNVHREEEjAQgg5mb28xLmJhci5sb2NhbDANBgkqhkiG9w0BAQsFAAOCAQEAl3egrkO3I94IpxxfSJmVetd7s9uW3lSBqh9OiypFevQO7ZgUxau+k05NKTUNpSq3W9H/lRr5AG5x3/VX8XZVbcLKXQ0d6e38uXBAUFQQJmjBVYqd8KcMfqLeFFUBsLcG04yek2tNIbhXZfBtw9UYO27Y5ktMgWjAz2VskIXl3E2L0b8tGnSKDoMB07IVpYB9bHfHX4o+ccIgq1HxyYT1d+eVIQuSHHxR7j7Wkgb8RG9bCWpVWaYWKWU0Inh3gMnP06kPBJ9nOB4adgC3Hz37ab/0KpmBuQBEgmMfINwV/OpJVv2Su1FYK+uX7E1qUGae6QDsfg0Yor9uP0Vkv4b1NA=='
        self.assertEqual('foo1.bar.local', self.csr_cn_get(self.logger, csr))

    @patch('OpenSSL.crypto.load_certificate_request')
    def test_043_helper_csr_cn_get(self, mock_csrload):
        """ get cn of csr """
        csr = 'csr'
        obj1 = Mock()
        obj1.get_components = Mock(return_value={'CN': 'foo'})
        obj2 = Mock()
        obj2.get_subject = Mock(return_value=obj1)
        mock_csrload.return_value = obj2
        self.assertEqual('foo', self.csr_cn_get(self.logger, csr))

    @patch('OpenSSL.crypto.load_certificate_request')
    def test_044_helper_csr_cn_get(self, mock_csrload):
        """ get cn of csr """
        csr = 'csr'
        obj1 = Mock()
        obj1.get_components = Mock(return_value={b'CN': 'foo'})
        obj2 = Mock()
        obj2.get_subject = Mock(return_value=obj1)
        mock_csrload.return_value = obj2
        self.assertEqual('foo', self.csr_cn_get(self.logger, csr))

    @patch('OpenSSL.crypto.load_certificate_request')
    def test_045_helper_csr_cn_get(self, mock_csrload):
        """ get cn of csr """
        csr = 'csr'
        obj1 = Mock()
        obj1.get_components = Mock(return_value={b'CN': b'foo'})
        obj2 = Mock()
        obj2.get_subject = Mock(return_value=obj1)
        mock_csrload.return_value = obj2
        self.assertEqual('foo', self.csr_cn_get(self.logger, csr))

    def test_043_helper_csr_san_get(self):
        """ get sans but no csr """
        csr = None
        self.assertEqual([], self.csr_san_get(self.logger, csr))

    def test_044_helper_csr_san_get(self):
        """ get sans but one san with == """
        csr = 'MIIClzCCAX8CAQAwGTEXMBUGA1UEAwwOZm9vMS5iYXIubG9jYWwwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDMwfxxbCCTsZY8mTFZkoQ5cAJyQZLUiz34sDDRvEpI9ZzdNNm2AEZR7AgKNuBkLwzUzY5iQ182huNzYJYZZEvYX++ocF2ngapTMQgfB+bWS5bpWIdjnAcz1/86jmJgTciwL25dSnEWL17Yn3pAWweoewr730rq/PMyIbviQrasksnSo7abe2mctxkHjHb5sZ+Z1yRTN6ir/bObXmxr+vHeeD2vLRv4Hd5XaA1d+k31J2FVMnrn5OpWbxGHo49zd0xdy2mgTdZ9UraLaQnyGlkjYzV0rqHIAIm8HOUjGN5U75/rlOPF0x62FCICZU/z1AgRvugaA5eO8zTSQJiMiBe3AgMBAAGgOTA3BgkqhkiG9w0BCQ4xKjAoMAsGA1UdDwQEAwIF4DAZBgNVHREEEjAQgg5mb28xLmJhci5sb2NhbDANBgkqhkiG9w0BAQsFAAOCAQEANAXOIkv0CovmdzyoAv1dsiK0TK2XHBdBTEPFDsrT7MnrIXOFS4FnDrg8zpn7QBzBRTl3HaKN8fnpIHkA/6ZRDqaEJq0AeskjxIg9LKDBBx5TEdgPh1CwruRWLlXtrqU7XXQmk0wLIo/kfaDRcTjyJ3yHTEK06mCAaws0sTKlTw2D4pIiDRp8zbLHeSEUX5UKOSGbLSSUY/F2XwgPB8nC2BCD/gkvHRR+dMQSdOCiS9GLwZdYAAyESw6WhmGPjmVbeTRgSt/9//yx3JKQgkFYmpSMLKR2G525M+l1qfku/4b0iMOa4vQjFRj5AXZH0SBpAKtvnFxUpP6P9mTE7+akOQ=='
        self.assertEqual(['DNS:foo1.bar.local'], self.csr_san_get(self.logger, csr))

    def test_045_helper_csr_san_get(self):
        """ get sans but one san without == """
        csr = 'MIIClzCCAX8CAQAwGTEXMBUGA1UEAwwOZm9vMS5iYXIubG9jYWwwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDMwfxxbCCTsZY8mTFZkoQ5cAJyQZLUiz34sDDRvEpI9ZzdNNm2AEZR7AgKNuBkLwzUzY5iQ182huNzYJYZZEvYX++ocF2ngapTMQgfB+bWS5bpWIdjnAcz1/86jmJgTciwL25dSnEWL17Yn3pAWweoewr730rq/PMyIbviQrasksnSo7abe2mctxkHjHb5sZ+Z1yRTN6ir/bObXmxr+vHeeD2vLRv4Hd5XaA1d+k31J2FVMnrn5OpWbxGHo49zd0xdy2mgTdZ9UraLaQnyGlkjYzV0rqHIAIm8HOUjGN5U75/rlOPF0x62FCICZU/z1AgRvugaA5eO8zTSQJiMiBe3AgMBAAGgOTA3BgkqhkiG9w0BCQ4xKjAoMAsGA1UdDwQEAwIF4DAZBgNVHREEEjAQgg5mb28xLmJhci5sb2NhbDANBgkqhkiG9w0BAQsFAAOCAQEANAXOIkv0CovmdzyoAv1dsiK0TK2XHBdBTEPFDsrT7MnrIXOFS4FnDrg8zpn7QBzBRTl3HaKN8fnpIHkA/6ZRDqaEJq0AeskjxIg9LKDBBx5TEdgPh1CwruRWLlXtrqU7XXQmk0wLIo/kfaDRcTjyJ3yHTEK06mCAaws0sTKlTw2D4pIiDRp8zbLHeSEUX5UKOSGbLSSUY/F2XwgPB8nC2BCD/gkvHRR+dMQSdOCiS9GLwZdYAAyESw6WhmGPjmVbeTRgSt/9//yx3JKQgkFYmpSMLKR2G525M+l1qfku/4b0iMOa4vQjFRj5AXZH0SBpAKtvnFxUpP6P9mTE7+akOQ'
        self.assertEqual(['DNS:foo1.bar.local'], self.csr_san_get(self.logger, csr))

    def test_046_helper_csr_san_get(self):
        """ get sans but two sans """
        csr = 'MIICpzCCAY8CAQAwGTEXMBUGA1UEAwwOZm9vMS5iYXIubG9jYWwwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDMwfxxbCCTsZY8mTFZkoQ5cAJyQZLUiz34sDDRvEpI9ZzdNNm2AEZR7AgKNuBkLwzUzY5iQ182huNzYJYZZEvYX++ocF2ngapTMQgfB+bWS5bpWIdjnAcz1/86jmJgTciwL25dSnEWL17Yn3pAWweoewr730rq/PMyIbviQrasksnSo7abe2mctxkHjHb5sZ+Z1yRTN6ir/bObXmxr+vHeeD2vLRv4Hd5XaA1d+k31J2FVMnrn5OpWbxGHo49zd0xdy2mgTdZ9UraLaQnyGlkjYzV0rqHIAIm8HOUjGN5U75/rlOPF0x62FCICZU/z1AgRvugaA5eO8zTSQJiMiBe3AgMBAAGgSTBHBgkqhkiG9w0BCQ4xOjA4MAsGA1UdDwQEAwIF4DApBgNVHREEIjAggg5mb28xLmJhci5sb2NhbIIOZm9vMi5iYXIubG9jYWwwDQYJKoZIhvcNAQELBQADggEBADeuf4J8Xziw2OuvLNnLOSgHQl2HdMFtRdgJoun7zPobsP3L3qyXLvvhJcQsIJggu5ZepnHGrCxroSbtRSO65GtLQA0Rq3DCGcPIC1fe9AYrqoynx8bWt2Hd+PyDrBppHVoQzj6yNCt6XNSDs04BMtjs9Pu4DD6DDHmxFMVNdHXea2Rms7C5nLQvXgw7yOF3Zk1vEu7Kue7d3zZMhN+HwwrNEA7RGAEzHHlCv5LL4Mw+kf6OJ8nf/WDiLDKEQIh6bnOuB42Y2wUMpzui8Uur0VJO+twY46MvjiVMMBZE3aPJU33eNPAQVC7GinStn+zQIJA5AADdcO8Lk1qdtaDiGp8'
        self.assertEqual(['DNS:foo1.bar.local', 'DNS:foo2.bar.local'], self.csr_san_get(self.logger, csr))

    def test_047_helper_csr_san_get(self):
        """ get sans but three sans """
        csr = 'MIICtzCCAZ8CAQAwGTEXMBUGA1UEAwwOZm9vMS5iYXIubG9jYWwwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDMwfxxbCCTsZY8mTFZkoQ5cAJyQZLUiz34sDDRvEpI9ZzdNNm2AEZR7AgKNuBkLwzUzY5iQ182huNzYJYZZEvYX++ocF2ngapTMQgfB+bWS5bpWIdjnAcz1/86jmJgTciwL25dSnEWL17Yn3pAWweoewr730rq/PMyIbviQrasksnSo7abe2mctxkHjHb5sZ+Z1yRTN6ir/bObXmxr+vHeeD2vLRv4Hd5XaA1d+k31J2FVMnrn5OpWbxGHo49zd0xdy2mgTdZ9UraLaQnyGlkjYzV0rqHIAIm8HOUjGN5U75/rlOPF0x62FCICZU/z1AgRvugaA5eO8zTSQJiMiBe3AgMBAAGgWTBXBgkqhkiG9w0BCQ4xSjBIMAsGA1UdDwQEAwIF4DA5BgNVHREEMjAwgg5mb28xLmJhci5sb2NhbIIOZm9vMi5iYXIubG9jYWyCDmZvbzMuYmFyLmxvY2FsMA0GCSqGSIb3DQEBCwUAA4IBAQAQRkub6G4uijaXOYpCkoz40I+SVRsbRDgnMNjsooZz1+7DVglFjrr6Pb0PPTOvOxtmbHP2KK0WokDn4LqOD2t0heuI+KPQy7m/ROpOB/YZOzTWEB8yS4vjkf/RFiJ7fnCAc8vA+3K/mBVb+89F8w/KlyPmpg1GK7UNgjEa5bnznTox8q12CocCJVykPEiC8AT/VPWUOPfg6gs+V6LO8R73VRPMVy0ttYKGX80ob+KczDTMUhoxXg8OG+G+bXXU+4Tu4l+nQWf2lFejECi/vNKzUT90IbcGJwyk7rc4Q7BJ/t/5nMo+vuV9f+2HI7qakHcw6u9RGylL4OYDf1CrqF1R'
        self.assertEqual(['DNS:foo1.bar.local', 'DNS:foo2.bar.local', 'DNS:foo3.bar.local'], self.csr_san_get(self.logger, csr))

    def test_048_helper_uts_to_date_utc(self):
        """ test uts_to_date_utc for a given format """
        self.assertEqual('2018-12-01', self.uts_to_date_utc(1543640400, '%Y-%m-%d'))

    def test_049_helper_uts_to_date_utc(self):
        """ test uts_to_date_utc without format """
        self.assertEqual('2018-12-01T05:00:00Z', self.uts_to_date_utc(1543640400))

    def test_050_helper_b64decode_pad(self):
        """ test b64decode_pad() method with a regular base64 encoded string """
        self.assertEqual('this-is-foo-correctly-padded', self.b64decode_pad(self.logger, 'dGhpcy1pcy1mb28tY29ycmVjdGx5LXBhZGRlZA=='))

    def test_051_helper_b64decode_pad(self):
        """ test b64decode_pad() method with a regular base64 encoded string """
        self.assertEqual('this-is-foo-with-incorrect-padding', self.b64decode_pad(self.logger, 'dGhpcy1pcy1mb28td2l0aC1pbmNvcnJlY3QtcGFkZGluZw'))

    def test_052_helper_b64decode_pad(self):
        """ test b64 decoding failure """
        self.assertEqual('ERR: b64 decoding error', self.b64decode_pad(self.logger, 'b'))

    def test_053_helper_cert_pem2der(self):
        """ test cert2pem """
        pem_file = '''-----BEGIN CERTIFICATE-----
MIIEGDCCAgCgAwIBAgIJALL8aztMPfV2MA0GCSqGSIb3DQEBCwUAMEgxCzAJBgNV
BAYTAkRFMQ8wDQYDVQQIDAZCZXJsaW4xFzAVBgNVBAoMDkFjbWUyQ2VydGlmaWVy
MQ8wDQYDVQQDDAZzdWItY2EwHhcNMTkwNjI1MDEyNTAwWhcNMjAwNjI1MDEyNTAw
WjBPMQswCQYDVQQGEwJERTEPMA0GA1UEBxMGQmVybGluMRcwFQYDVQQKEw5BY21l
MkNlcnRpZmllcjEWMBQGA1UEAwwNY2xpZW50X3N1Yi1jYTCCASIwDQYJKoZIhvcN
AQEBBQADggEPADCCAQoCggEBALvoKKg3ciBVWZtquiWyMogWU6ydEfmLbXktK6T+
owxzxHVaoePVGH9DZvTZD2pHS8xJ6fpFr3pZYiuqiUHuxdMpj9gVxik5ivBrSJIk
ZXLxwvNJWpMa1o1Hxz1By3Hrlm3ebKIzfQPqRRcdjWtJgCFbcTpalwhE1RQFMp4I
cb08aAE9uEaZQ4uZ8Ls30J6IHC4PG63lGI1tkAtLIoUWupRAmnWDx0ysXzXeN7m+
Lff9ols9MZNgzRMgY/zGUq0LzZfi+L+Iev3sztCdoIOBA/K63jv0hOPyYg331L05
XIwbLeUoUG41J4pZzafx6MAFp4Zam1w+aafCzEw7ZPHQvn0CAwEAATANBgkqhkiG
9w0BAQsFAAOCAgEABPgWo4KAXJNXNfEBbixDuCxtwO1JuphSOTcpIlEp+uNOSDzg
NEbrhUXTNM8SPshzFjBpudc29okiyC62CfLD/X+EvIeKo/oa477kN6MuNfqLGZ42
a935ES3S00Wy8rbwyIoPCsKWT/6VsHRHUn8XhFNFUBKZ8FGxwXcAVpPanyikURqV
H1MgAk62hJQdYjSxdga/GKS1dS39fyxQz7uBPt5WIQZPzL6dr2Yn/4lQUvTUVus2
e1cTh3z02yB5EDlEAcMMvMNpfYvNdU5H6QEPwysbkW9E/Ep84aq21zwuPxICh0Kd
jHWKkHtCqDoEYIADDl1AD5UdJTMQ9LIzUjsBvtB5I6yT7jgsx/iqTDrkJVK/zRf4
NeKRa3AW57jsPUIcUstUFnVJbg+MM4fYmapx8Hqm/Aq+II9ip80AM6hXvierTQn4
MNQivL0ZJfj0Ro9KEIDAHN3IAfIlFovbkBPLMi9PtfyhuVmXpthE9OaDlgUguWb4
5LAKwgfu1TFGPPpf5jTw2qVx0F+iCiUwK8ZgnakkXOKE5+KIb8ejL+3pPd5Wt+45
w/7gEFOjT6XAzZGnUtcMH/lpxmgbl3/SKkyrW4h7PnF2FEEVC4XnZuQm+ZwD/PpX
fmAA52ygKHBzUr9V33CkW0FhvjqkAUya5x9CqWlHoal0RVvFavnw+4ImqbE=
-----END CERTIFICATE-----'''
        result = b'MIIEGDCCAgCgAwIBAgIJALL8aztMPfV2MA0GCSqGSIb3DQEBCwUAMEgxCzAJBgNVBAYTAkRFMQ8wDQYDVQQIDAZCZXJsaW4xFzAVBgNVBAoMDkFjbWUyQ2VydGlmaWVyMQ8wDQYDVQQDDAZzdWItY2EwHhcNMTkwNjI1MDEyNTAwWhcNMjAwNjI1MDEyNTAwWjBPMQswCQYDVQQGEwJERTEPMA0GA1UEBxMGQmVybGluMRcwFQYDVQQKEw5BY21lMkNlcnRpZmllcjEWMBQGA1UEAwwNY2xpZW50X3N1Yi1jYTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALvoKKg3ciBVWZtquiWyMogWU6ydEfmLbXktK6T+owxzxHVaoePVGH9DZvTZD2pHS8xJ6fpFr3pZYiuqiUHuxdMpj9gVxik5ivBrSJIkZXLxwvNJWpMa1o1Hxz1By3Hrlm3ebKIzfQPqRRcdjWtJgCFbcTpalwhE1RQFMp4Icb08aAE9uEaZQ4uZ8Ls30J6IHC4PG63lGI1tkAtLIoUWupRAmnWDx0ysXzXeN7m+Lff9ols9MZNgzRMgY/zGUq0LzZfi+L+Iev3sztCdoIOBA/K63jv0hOPyYg331L05XIwbLeUoUG41J4pZzafx6MAFp4Zam1w+aafCzEw7ZPHQvn0CAwEAATANBgkqhkiG9w0BAQsFAAOCAgEABPgWo4KAXJNXNfEBbixDuCxtwO1JuphSOTcpIlEp+uNOSDzgNEbrhUXTNM8SPshzFjBpudc29okiyC62CfLD/X+EvIeKo/oa477kN6MuNfqLGZ42a935ES3S00Wy8rbwyIoPCsKWT/6VsHRHUn8XhFNFUBKZ8FGxwXcAVpPanyikURqVH1MgAk62hJQdYjSxdga/GKS1dS39fyxQz7uBPt5WIQZPzL6dr2Yn/4lQUvTUVus2e1cTh3z02yB5EDlEAcMMvMNpfYvNdU5H6QEPwysbkW9E/Ep84aq21zwuPxICh0KdjHWKkHtCqDoEYIADDl1AD5UdJTMQ9LIzUjsBvtB5I6yT7jgsx/iqTDrkJVK/zRf4NeKRa3AW57jsPUIcUstUFnVJbg+MM4fYmapx8Hqm/Aq+II9ip80AM6hXvierTQn4MNQivL0ZJfj0Ro9KEIDAHN3IAfIlFovbkBPLMi9PtfyhuVmXpthE9OaDlgUguWb45LAKwgfu1TFGPPpf5jTw2qVx0F+iCiUwK8ZgnakkXOKE5+KIb8ejL+3pPd5Wt+45w/7gEFOjT6XAzZGnUtcMH/lpxmgbl3/SKkyrW4h7PnF2FEEVC4XnZuQm+ZwD/PpXfmAA52ygKHBzUr9V33CkW0FhvjqkAUya5x9CqWlHoal0RVvFavnw+4ImqbE='
        self.assertEqual(result, self.b64_encode(self.logger, self.cert_pem2der(pem_file)))

    def test_054_helper_cert_san_get(self):
        """ test cert_san_get for a single SAN and recode = True"""
        cert = """MIIDDTCCAfWgAwIBAgIBCjANBgkqhkiG9w0BAQsFADAaMRgwFgYDVQQDEw9mb28u
                ZXhhbXBsZS5jb20wHhcNMTkwMTIwMTY1OTIwWhcNMTkwMjE5MTY1OTIwWjAaMRgw
                FgYDVQQDEw9mb28uZXhhbXBsZS5jb20wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAw
                ggEKAoIBAQCqUeNzDyBVugUKZq597ishYAdMPgus5Nw5pWE/Jw7PP0koeFE2wODq
                HVb+XNFFEX4IOyiE2Pi4ilzfXYGKchhP3wHgnkxGNIwt/cDNZgyTiUpITV/ciFaC
                7avkvQS6ScCYUYrhby7QnvcU02mAyhNcSVGI5TW7HhFdtWrEAK3N8H6yhxHLSi2y
                dpQ3kCJyJylqt/Rv3uKNjCvTv867K6A1QSsXoAxtPK9P0UOTRvgHkFf8T32Bn/Er
                1bjkX9Ms8rqDQmicCWJk260lUHzN6vxaeiEg7Kz3TA8Ik3DMIcvwJrE168G1APo+
                FyOIKyx+t78HWOlNINIqZMj5e2DpulV7AgMBAAGjXjBcMB8GA1UdIwQYMBaAFK1Z
                zuGt0Pe+NLerCXqQBYmVV7suMB0GA1UdDgQWBBStWc7hrdD3vjS3qwl6kAWJlVe7
                LjAaBgNVHREEEzARgg9mb28uZXhhbXBsZS5jb20wDQYJKoZIhvcNAQELBQADggEB
                AANW0DD4Xp7LH/Rzf2jVLwiFlbtR6iazyn9S/pH2Gwqjkscv/27/dqJb7CfPdD02
                5ItQcYkZPJhDOsj63kvUaD89QU31RnYQrXrbXFqYOIAq6kxfZUoQmpfEBxbB4Wxm
                TW0OWS+FMqNw/SuGs6EQjTRA+gBOeGzj4H9yOFOg0PpadBayZ7UT4lm1LOiFHh8h
                bta75ocePrurdNxsxKJhLlXbnKD6lurCb4khRhrmLmpK8JxhuaevEVklSQX0gqlR
                fxAH4XQsaqcaedPNI+W5OUITMz40ezDCbUqxS9KEMCGPoOTXNRAjbr72sc4Vkw7H
                t+eRUDECE+0UnjyeCjTn3EU="""
        self.assertEqual(['DNS:foo.example.com'], self.cert_san_get(self.logger, cert, recode=True))

    def test_055_helper_cert_san_get(self):
        """ test cert_san_get for a single SAN and recode = False"""
        cert = """-----BEGIN CERTIFICATE-----\nMIIDDTCCAfWgAwIBAgIBCjANBgkqhkiG9w0BAQsFADAaMRgwFgYDVQQDEw9mb28u
                ZXhhbXBsZS5jb20wHhcNMTkwMTIwMTY1OTIwWhcNMTkwMjE5MTY1OTIwWjAaMRgw
                FgYDVQQDEw9mb28uZXhhbXBsZS5jb20wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAw
                ggEKAoIBAQCqUeNzDyBVugUKZq597ishYAdMPgus5Nw5pWE/Jw7PP0koeFE2wODq
                HVb+XNFFEX4IOyiE2Pi4ilzfXYGKchhP3wHgnkxGNIwt/cDNZgyTiUpITV/ciFaC
                7avkvQS6ScCYUYrhby7QnvcU02mAyhNcSVGI5TW7HhFdtWrEAK3N8H6yhxHLSi2y
                dpQ3kCJyJylqt/Rv3uKNjCvTv867K6A1QSsXoAxtPK9P0UOTRvgHkFf8T32Bn/Er
                1bjkX9Ms8rqDQmicCWJk260lUHzN6vxaeiEg7Kz3TA8Ik3DMIcvwJrE168G1APo+
                FyOIKyx+t78HWOlNINIqZMj5e2DpulV7AgMBAAGjXjBcMB8GA1UdIwQYMBaAFK1Z
                zuGt0Pe+NLerCXqQBYmVV7suMB0GA1UdDgQWBBStWc7hrdD3vjS3qwl6kAWJlVe7
                LjAaBgNVHREEEzARgg9mb28uZXhhbXBsZS5jb20wDQYJKoZIhvcNAQELBQADggEB
                AANW0DD4Xp7LH/Rzf2jVLwiFlbtR6iazyn9S/pH2Gwqjkscv/27/dqJb7CfPdD02
                5ItQcYkZPJhDOsj63kvUaD89QU31RnYQrXrbXFqYOIAq6kxfZUoQmpfEBxbB4Wxm
                TW0OWS+FMqNw/SuGs6EQjTRA+gBOeGzj4H9yOFOg0PpadBayZ7UT4lm1LOiFHh8h
                bta75ocePrurdNxsxKJhLlXbnKD6lurCb4khRhrmLmpK8JxhuaevEVklSQX0gqlR
                fxAH4XQsaqcaedPNI+W5OUITMz40ezDCbUqxS9KEMCGPoOTXNRAjbr72sc4Vkw7H
                t+eRUDECE+0UnjyeCjTn3EU=\n-----END CERTIFICATE-----"""

        self.assertEqual(['DNS:foo.example.com'], self.cert_san_get(self.logger, cert, recode=False))

    def test_056_helper_cert_san_get(self):
        """ test cert_san_get for a single SAN and recode = False"""
        cert = """-----BEGIN CERTIFICATE-----
MIIEZDCCAkygAwIBAgIIe941mx0FQtAwDQYJKoZIhvcNAQELBQAwKjEXMBUGA1UE
CxMOYWNtZTJjZXJ0aWZpZXIxDzANBgNVBAMTBnN1Yi1jYTAeFw0yMTA0MDkxNTUy
MDBaFw0yNjA0MDkxNTUyMDBaMBgxFjAUBgNVBAMTDWVzdGNsaWVudC5lc3QwggEi
MA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDAn6IqwTE1RvZUm3gelpu4tmrd
Fj8Ub98J1YeQz7qrew5iA81NeH9tR484edjcY0ieOt3e1MfxJoziWtaeqxpsfytm
VB/i+850kVZmvRCR1jhW/4AzidkVBMQiCR5erPmmheeCxbKkto0rHb7ziRA+F8/f
ZLKfLNsahEQPxDuMItyQFCOQFHh8Hfuend2NgsQKeZ1r5Czf3n5Q6NFff7HG+MDe
NDNdPB3ShgcvvNCFUS1z615/GIItfSqcWTAVaJ7436cA7yy5y4+0SvjfXYtHYfyt
hBj/5UqlUmjni8Irj5K8uEtb1YUujmvlTTbzPkhYqIkSoyr7t21Dz+gcYn49AgMB
AAGjgZ8wgZwwDAYDVR0TAQH/BAIwADAdBgNVHQ4EFgQUN3Z0iLv1FE17DCDBfpxW
2P+5+kIwCwYDVR0PBAQDAgO4MBMGA1UdJQQMMAoGCCsGAQUFBwMCMBgGA1UdEQQR
MA+CDWVzdGNsaWVudC5lc3QwEQYJYIZIAYb4QgEBBAQDAgWgMB4GCWCGSAGG+EIB
DQQRFg94Y2EgY2VydGlmaWNhdGUwDQYJKoZIhvcNAQELBQADggIBACMAHHH4/0eA
XbS/uKsIjLN1QPnnzgjxC0xoUon8UVM0PUMH+FMg6rs21Xyl5tn5iItmvKI9c3ak
AZ00RUQKVdmJVFRUKywmfF7n5epBpXtWJrSH817NT9GOp+PO5VUTDV5VkvpVLoy7
WzThrheLKz1nC1dWowRz86tcBLAsC1zT17fsNZXQDuv4LiQQXs7QKhUU75r1Ixrd
BPeBQSP5skGpWxm8sapQSfOALoXu1pSoGIr6tqvNGuEoZGvUuWeQHG/G8c2ufL+6
lEzZBBCd6e2tErkqD/vqfCRzbLcGgSPX0HVWdkjH09nHWXI5UhNr2YgGF7YvSTKW
JfbDVlTql1BuSn2yTQtDk4E8k9BLr8WfqFSZvYrivT9Ax1n3BD9jvQL5+QRdioH1
kqNGMme0Pb43pHciX4hu9L5rGenZRmxeGXZ78uSOR+n2bGxAMw1OY7Rx/lsNSKWD
SN+7xIrwjjXO5Uthev1ecrLAK2+EpjITa6Y85ms39V4ypCEdujkKEBeVxuN8DdMJ
2GaFGluSRZeYZ0LAPfYr5sp6G6904WF+PcT0WjGenH4PJLXrAttbhhvQxXU0Q8s2
CUwUHy5OT/DW3POq7WETc+zmFGwZqiP3W9gmN0hHXsKqkNmz2RYgoH57lPS1PJb0
klGUNHG98CtsmlhrivhSTJWqSIOfyKGF
-----END CERTIFICATE-----"""
        self.assertEqual(b'MAoGCCsGAQUFBwMC', self.b64_encode(self.logger, self.cert_eku_get(self.logger, cert, recode=False)))

    def test_057_helper_cert_san_get(self):
        """ test cert_san_get for a single SAN and recode = True"""
        cert = "MIIEZDCCAkygAwIBAgIIe941mx0FQtAwDQYJKoZIhvcNAQELBQAwKjEXMBUGA1UECxMOYWNtZTJjZXJ0aWZpZXIxDzANBgNVBAMTBnN1Yi1jYTAeFw0yMTA0MDkxNTUyMDBaFw0yNjA0MDkxNTUyMDBaMBgxFjAUBgNVBAMTDWVzdGNsaWVudC5lc3QwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDAn6IqwTE1RvZUm3gelpu4tmrdFj8Ub98J1YeQz7qrew5iA81NeH9tR484edjcY0ieOt3e1MfxJoziWtaeqxpsfytmVB/i+850kVZmvRCR1jhW/4AzidkVBMQiCR5erPmmheeCxbKkto0rHb7ziRA+F8/fZLKfLNsahEQPxDuMItyQFCOQFHh8Hfuend2NgsQKeZ1r5Czf3n5Q6NFff7HG+MDeNDNdPB3ShgcvvNCFUS1z615/GIItfSqcWTAVaJ7436cA7yy5y4+0SvjfXYtHYfythBj/5UqlUmjni8Irj5K8uEtb1YUujmvlTTbzPkhYqIkSoyr7t21Dz+gcYn49AgMBAAGjgZ8wgZwwDAYDVR0TAQH/BAIwADAdBgNVHQ4EFgQUN3Z0iLv1FE17DCDBfpxW2P+5+kIwCwYDVR0PBAQDAgO4MBMGA1UdJQQMMAoGCCsGAQUFBwMCMBgGA1UdEQQRMA+CDWVzdGNsaWVudC5lc3QwEQYJYIZIAYb4QgEBBAQDAgWgMB4GCWCGSAGG+EIBDQQRFg94Y2EgY2VydGlmaWNhdGUwDQYJKoZIhvcNAQELBQADggIBACMAHHH4/0eAXbS/uKsIjLN1QPnnzgjxC0xoUon8UVM0PUMH+FMg6rs21Xyl5tn5iItmvKI9c3akAZ00RUQKVdmJVFRUKywmfF7n5epBpXtWJrSH817NT9GOp+PO5VUTDV5VkvpVLoy7WzThrheLKz1nC1dWowRz86tcBLAsC1zT17fsNZXQDuv4LiQQXs7QKhUU75r1IxrdBPeBQSP5skGpWxm8sapQSfOALoXu1pSoGIr6tqvNGuEoZGvUuWeQHG/G8c2ufL+6lEzZBBCd6e2tErkqD/vqfCRzbLcGgSPX0HVWdkjH09nHWXI5UhNr2YgGF7YvSTKWJfbDVlTql1BuSn2yTQtDk4E8k9BLr8WfqFSZvYrivT9Ax1n3BD9jvQL5+QRdioH1kqNGMme0Pb43pHciX4hu9L5rGenZRmxeGXZ78uSOR+n2bGxAMw1OY7Rx/lsNSKWDSN+7xIrwjjXO5Uthev1ecrLAK2+EpjITa6Y85ms39V4ypCEdujkKEBeVxuN8DdMJ2GaFGluSRZeYZ0LAPfYr5sp6G6904WF+PcT0WjGenH4PJLXrAttbhhvQxXU0Q8s2CUwUHy5OT/DW3POq7WETc+zmFGwZqiP3W9gmN0hHXsKqkNmz2RYgoH57lPS1PJb0klGUNHG98CtsmlhrivhSTJWqSIOfyKGF"
        self.assertEqual(b'MAoGCCsGAQUFBwMC', self.b64_encode(self.logger, self.cert_eku_get(self.logger, cert, recode=True)))

    def test_058_helper_cert_extensions_get(self):
        """ test cert_san_get for a single SAN and recode = False"""
        cert = """-----BEGIN CERTIFICATE-----
MIIEZDCCAkygAwIBAgIIe941mx0FQtAwDQYJKoZIhvcNAQELBQAwKjEXMBUGA1UE
CxMOYWNtZTJjZXJ0aWZpZXIxDzANBgNVBAMTBnN1Yi1jYTAeFw0yMTA0MDkxNTUy
MDBaFw0yNjA0MDkxNTUyMDBaMBgxFjAUBgNVBAMTDWVzdGNsaWVudC5lc3QwggEi
MA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDAn6IqwTE1RvZUm3gelpu4tmrd
Fj8Ub98J1YeQz7qrew5iA81NeH9tR484edjcY0ieOt3e1MfxJoziWtaeqxpsfytm
VB/i+850kVZmvRCR1jhW/4AzidkVBMQiCR5erPmmheeCxbKkto0rHb7ziRA+F8/f
ZLKfLNsahEQPxDuMItyQFCOQFHh8Hfuend2NgsQKeZ1r5Czf3n5Q6NFff7HG+MDe
NDNdPB3ShgcvvNCFUS1z615/GIItfSqcWTAVaJ7436cA7yy5y4+0SvjfXYtHYfyt
hBj/5UqlUmjni8Irj5K8uEtb1YUujmvlTTbzPkhYqIkSoyr7t21Dz+gcYn49AgMB
AAGjgZ8wgZwwDAYDVR0TAQH/BAIwADAdBgNVHQ4EFgQUN3Z0iLv1FE17DCDBfpxW
2P+5+kIwCwYDVR0PBAQDAgO4MBMGA1UdJQQMMAoGCCsGAQUFBwMCMBgGA1UdEQQR
MA+CDWVzdGNsaWVudC5lc3QwEQYJYIZIAYb4QgEBBAQDAgWgMB4GCWCGSAGG+EIB
DQQRFg94Y2EgY2VydGlmaWNhdGUwDQYJKoZIhvcNAQELBQADggIBACMAHHH4/0eA
XbS/uKsIjLN1QPnnzgjxC0xoUon8UVM0PUMH+FMg6rs21Xyl5tn5iItmvKI9c3ak
AZ00RUQKVdmJVFRUKywmfF7n5epBpXtWJrSH817NT9GOp+PO5VUTDV5VkvpVLoy7
WzThrheLKz1nC1dWowRz86tcBLAsC1zT17fsNZXQDuv4LiQQXs7QKhUU75r1Ixrd
BPeBQSP5skGpWxm8sapQSfOALoXu1pSoGIr6tqvNGuEoZGvUuWeQHG/G8c2ufL+6
lEzZBBCd6e2tErkqD/vqfCRzbLcGgSPX0HVWdkjH09nHWXI5UhNr2YgGF7YvSTKW
JfbDVlTql1BuSn2yTQtDk4E8k9BLr8WfqFSZvYrivT9Ax1n3BD9jvQL5+QRdioH1
kqNGMme0Pb43pHciX4hu9L5rGenZRmxeGXZ78uSOR+n2bGxAMw1OY7Rx/lsNSKWD
SN+7xIrwjjXO5Uthev1ecrLAK2+EpjITa6Y85ms39V4ypCEdujkKEBeVxuN8DdMJ
2GaFGluSRZeYZ0LAPfYr5sp6G6904WF+PcT0WjGenH4PJLXrAttbhhvQxXU0Q8s2
CUwUHy5OT/DW3POq7WETc+zmFGwZqiP3W9gmN0hHXsKqkNmz2RYgoH57lPS1PJb0
klGUNHG98CtsmlhrivhSTJWqSIOfyKGF
-----END CERTIFICATE-----"""
        self.assertEqual(['MAA=', 'BBQ3dnSIu/UUTXsMIMF+nFbY/7n6Qg==', 'AwIDuA==', 'MAoGCCsGAQUFBwMC', 'MA+CDWVzdGNsaWVudC5lc3Q=', 'AwIFoA==', 'Fg94Y2EgY2VydGlmaWNhdGU='], self.cert_extensions_get(self.logger, cert, recode=False))

    def test_059_helper_cert_extensions_get(self):
        """ test cert_san_get for a single SAN and recode = True"""
        cert = "MIIEZDCCAkygAwIBAgIIe941mx0FQtAwDQYJKoZIhvcNAQELBQAwKjEXMBUGA1UECxMOYWNtZTJjZXJ0aWZpZXIxDzANBgNVBAMTBnN1Yi1jYTAeFw0yMTA0MDkxNTUyMDBaFw0yNjA0MDkxNTUyMDBaMBgxFjAUBgNVBAMTDWVzdGNsaWVudC5lc3QwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDAn6IqwTE1RvZUm3gelpu4tmrdFj8Ub98J1YeQz7qrew5iA81NeH9tR484edjcY0ieOt3e1MfxJoziWtaeqxpsfytmVB/i+850kVZmvRCR1jhW/4AzidkVBMQiCR5erPmmheeCxbKkto0rHb7ziRA+F8/fZLKfLNsahEQPxDuMItyQFCOQFHh8Hfuend2NgsQKeZ1r5Czf3n5Q6NFff7HG+MDeNDNdPB3ShgcvvNCFUS1z615/GIItfSqcWTAVaJ7436cA7yy5y4+0SvjfXYtHYfythBj/5UqlUmjni8Irj5K8uEtb1YUujmvlTTbzPkhYqIkSoyr7t21Dz+gcYn49AgMBAAGjgZ8wgZwwDAYDVR0TAQH/BAIwADAdBgNVHQ4EFgQUN3Z0iLv1FE17DCDBfpxW2P+5+kIwCwYDVR0PBAQDAgO4MBMGA1UdJQQMMAoGCCsGAQUFBwMCMBgGA1UdEQQRMA+CDWVzdGNsaWVudC5lc3QwEQYJYIZIAYb4QgEBBAQDAgWgMB4GCWCGSAGG+EIBDQQRFg94Y2EgY2VydGlmaWNhdGUwDQYJKoZIhvcNAQELBQADggIBACMAHHH4/0eAXbS/uKsIjLN1QPnnzgjxC0xoUon8UVM0PUMH+FMg6rs21Xyl5tn5iItmvKI9c3akAZ00RUQKVdmJVFRUKywmfF7n5epBpXtWJrSH817NT9GOp+PO5VUTDV5VkvpVLoy7WzThrheLKz1nC1dWowRz86tcBLAsC1zT17fsNZXQDuv4LiQQXs7QKhUU75r1IxrdBPeBQSP5skGpWxm8sapQSfOALoXu1pSoGIr6tqvNGuEoZGvUuWeQHG/G8c2ufL+6lEzZBBCd6e2tErkqD/vqfCRzbLcGgSPX0HVWdkjH09nHWXI5UhNr2YgGF7YvSTKWJfbDVlTql1BuSn2yTQtDk4E8k9BLr8WfqFSZvYrivT9Ax1n3BD9jvQL5+QRdioH1kqNGMme0Pb43pHciX4hu9L5rGenZRmxeGXZ78uSOR+n2bGxAMw1OY7Rx/lsNSKWDSN+7xIrwjjXO5Uthev1ecrLAK2+EpjITa6Y85ms39V4ypCEdujkKEBeVxuN8DdMJ2GaFGluSRZeYZ0LAPfYr5sp6G6904WF+PcT0WjGenH4PJLXrAttbhhvQxXU0Q8s2CUwUHy5OT/DW3POq7WETc+zmFGwZqiP3W9gmN0hHXsKqkNmz2RYgoH57lPS1PJb0klGUNHG98CtsmlhrivhSTJWqSIOfyKGF"
        self.assertEqual(['MAA=', 'BBQ3dnSIu/UUTXsMIMF+nFbY/7n6Qg==', 'AwIDuA==', 'MAoGCCsGAQUFBwMC', 'MA+CDWVzdGNsaWVudC5lc3Q=', 'AwIFoA==', 'Fg94Y2EgY2VydGlmaWNhdGU='], self.cert_extensions_get(self.logger, cert, recode=True))

    def test_060_logger_setup(self):
        """ stupid logger setup """
        debug = False
        cfg_file =None
        self.assertTrue(self.logger_setup(debug, cfg_file))

    def test_061_logger_setup(self):
        """ stupid logger setup """
        debug = True
        cfg_file =None
        self.assertTrue(self.logger_setup(debug, cfg_file))

    def test_062_logger_setup(self):
        """ stupid logger setup """
        debug = False
        cfg_file = 'cfg_file'
        self.assertTrue(self.logger_setup(debug, cfg_file))

    @patch('tlslite.constants.CipherSuite.ietfNames')
    def test_063__connection_log(self, mockcs):
        """ stupid connection logger """
        seconds = 10
        mockcs.return_value = 'foo'
        msession = Mock()
        msession.cipherSuite = Mock(return_value='cipherSuite')
        connection = Mock()
        connection.getpeername = Mock(return_value='getpeername')
        connection.getVersionName = Mock(return_value='getVersionName')
        connection.getCipherName = Mock(return_value='getCipherName')
        connection.getCipherImplementation = Mock(return_value='getCipherImplementation')
        connection.version = (2, 1)
        connection.dhGroupSize = 'dhGroupSize'
        connection.next_proto = 'next_proto'
        connection.encryptThenMAC = 'encryptThenMAC'
        connection.extendedMasterSecret = 'extendedMasterSecret'
        connection.session = Mock(return_value=msession)
        with self.assertLogs('test_est', level='DEBUG') as lcm:
            self.connection_log(self.logger, connection, seconds)
        self.assertIn('DEBUG:test_est:Remote end: getpeername', lcm.output)
        self.assertIn('DEBUG:test_est: Handshake time: 10.000 seconds', lcm.output)
        self.assertIn('DEBUG:test_est: Version: getVersionName', lcm.output)
        self.assertIn('DEBUG:test_est: Cipher: getCipherName getCipherImplementation', lcm.output)
        self.assertIn('DEBUG:test_est: DH group size: dhGroupSize bits', lcm.output)
        self.assertIn('DEBUG:test_est: Next-Protocol Negotiated: next_proto', lcm.output)
        self.assertIn('DEBUG:test_est: Encrypt-then-MAC: encryptThenMAC', lcm.output)
        self.assertIn('DEBUG:test_est: Extended Master Secret: extendedMasterSecret', lcm.output)

    


if __name__ == '__main__':
    unittest.main()
