#!/usr/bin/python
# -*- coding: utf-8 -*-
""" unittests for secureserver.py """
# pylint: disable= C0415, W0212
import unittest
import configparser
import sys
import os
from unittest.mock import patch, Mock, mock_open
import warnings
import logging
import tlslite

sys.path.insert(0, '.')
sys.path.insert(1, '..')

def fake_log(logger, text):
    """ fake funktion just sending a text log """
    logger.error(text)

class SecureserverTestCases(unittest.TestCase):
    """ test class for cgi_handler """

    def setUp(self):
        """ setup unittest """
        import logging
        logging.basicConfig(level=logging.CRITICAL)
        self.logger = logging.getLogger('test_est')
        from est_proxy.secureserver import SecureServer
        self.secureserver = SecureServer.__new__(SecureServer)

    #def tearDown(self):
    #    warnings.simplefilter("default", ResourceWarning)

    @patch('est_proxy.secureserver.config_load')
    @patch('est_proxy.secureserver.logger_setup')
    def test_001_config_load(self, mock_logger, mock_load_cfg):
        """ test _config_load empty dictionary """
        mock_logger.return_value = None
        mock_load_cfg.return_value = {}
        self.secureserver._config_load()
        self.assertFalse(self.secureserver.config_dic['connection_log'])
        self.assertFalse(self.secureserver.debug)

    @patch('est_proxy.secureserver.config_load')
    @patch('est_proxy.secureserver.logger_setup')
    def test_002_config_load(self, mock_logger, mock_load_cfg):
        """ test _config_load empty dictionary """
        mock_logger.return_value = None
        parser = configparser.ConfigParser()
        parser['DEFAULT'] = {'foo': 'bar'}
        mock_load_cfg.return_value = parser
        self.secureserver._config_load()
        self.assertFalse(self.secureserver.config_dic['connection_log'])
        self.assertFalse(self.secureserver.debug)

    @patch('est_proxy.secureserver.config_load')
    @patch('est_proxy.secureserver.logger_setup')
    def test_003_config_load(self, mock_logger, mock_load_cfg):
        """ test _config_load debug False """
        mock_logger.return_value = None
        parser = configparser.ConfigParser()
        parser['DEFAULT'] = {'foo': 'bar', 'debug': False}
        mock_load_cfg.return_value = parser
        self.secureserver._config_load()
        self.assertFalse(self.secureserver.config_dic['connection_log'])
        self.assertFalse(self.secureserver.debug)

    @patch('est_proxy.secureserver.config_load')
    @patch('est_proxy.secureserver.logger_setup')
    def test_004_config_load(self, mock_logger, mock_load_cfg):
        """ test _config_load debug False """
        mock_logger.return_value = None
        parser = configparser.ConfigParser()
        parser['DEFAULT'] = {'foo': 'bar', 'debug': True}
        mock_load_cfg.return_value = parser
        self.secureserver._config_load()
        self.assertFalse(self.secureserver.config_dic['connection_log'])
        self.assertTrue(self.secureserver.debug)

    @patch('est_proxy.secureserver.config_load')
    @patch('est_proxy.secureserver.logger_setup')
    def test_005_config_load(self, mock_logger, mock_load_cfg):
        """ test _config_load debug False """
        mock_logger.return_value = None
        parser = configparser.ConfigParser()
        parser['DEFAULT'] = {'foo': 'bar', 'connection_log': False}
        mock_load_cfg.return_value = parser
        self.secureserver._config_load()
        self.assertFalse(self.secureserver.config_dic['connection_log'])
        self.assertFalse(self.secureserver.debug)

    @patch('est_proxy.secureserver.config_load')
    @patch('est_proxy.secureserver.logger_setup')
    def test_006_config_load(self, mock_logger, mock_load_cfg):
        """ test _config_load debug False """
        mock_logger.return_value = None
        parser = configparser.ConfigParser()
        parser['DEFAULT'] = {'foo': 'bar', 'connection_log': True}
        mock_load_cfg.return_value = parser
        self.secureserver._config_load()
        self.assertTrue(self.secureserver.config_dic['connection_log'])
        self.assertFalse(self.secureserver.debug)

    @patch('est_proxy.secureserver.logger_setup')
    @patch('est_proxy.secureserver.config_load')
    def test_007_config_load(self, mock_load_cfg, mock_logger):
        """ test _config_load  daemon section without key_file and cert_file """
        mock_logger.return_value = self.logger
        parser = configparser.ConfigParser()
        parser['Daemon'] = {'foo': 'bar'}
        mock_load_cfg.return_value = parser
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.secureserver._config_load()
        self.assertIn('ERROR:test_est:Secureserver._load_config() Daemon configured but no key_file specified.', lcm.output)
        self.assertIn('ERROR:test_est:Secureserver._load_config() Daemon configured but no cert_file specified.', lcm.output)

    @patch('est_proxy.secureserver.logger_setup')
    @patch('est_proxy.secureserver.config_load')
    def test_008_config_load(self, mock_load_cfg, mock_logger):
        """ test _config_load  daemon section with invalid key_file """
        mock_logger.return_value = self.logger
        parser = configparser.ConfigParser()
        parser['Daemon'] = {'key_file': 'foo'}
        mock_load_cfg.return_value = parser
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.secureserver._config_load()
        self.assertIn('ERROR:test_est:Secureserver._load_config() key_file foo could not be loaded.', lcm.output)

    pkey = b"""-----BEGIN RSA PRIVATE KEY-----
 MIICXQIBAAKBgQDYscuoMzsGmW0pAYsmyHltxB2TdwHS0dImfjCMfaSDkfLdZY5+
 dOWORVns9etWnr194mSGA1F0Pls/VJW8+cX9+3vtJV8zSdANPYUoQf0TP7VlJxkH
 dSRkUbEoz5bAAs/+970uos7n7iXQIni+3erUTdYEk2iWnMBjTljfgbK/dQIDAQAB
 AoGAJHoJZk75aKr7DSQNYIHuruOMdv5ZeDuJvKERWxTrVJqE32/xBKh42/IgqRrc
 esBN9ZregRCd7YtxoL+EVUNWaJNVx2mNmezEznrc9zhcYUrgeaVdFO2yBF1889zO
 gCOVwrO8uDgeyj6IKa25H6c1N13ih/o7ZzEgWbGG+ylU1yECQQDv4ZSJ4EjSh/Fl
 aHdz3wbBa/HKGTjC8iRy476Cyg2Fm8MZUe9Yy3udOrb5ZnS2MTpIXt5AF3h2TfYV
 VoFXIorjAkEA50FcJmzT8sNMrPaV8vn+9W2Lu4U7C+K/O2g1iXMaZms5PC5zV5aV
 CKXZWUX1fq2RaOzlbQrpgiolhXpeh8FjxwJBAOFHzSQfSsTNfttp3KUpU0LbiVvv
 i+spVSnA0O4rq79KpVNmK44Mq67hsW1P11QzrzTAQ6GVaUBRv0YS061td1kCQHnP
 wtN2tboFR6lABkJDjxoGRvlSt4SOPr7zKGgrWjeiuTZLHXSAnCY+/hr5L9Q3ZwXG
 6x6iBdgLjVIe4BZQNtcCQQDXGv/gWinCNTN3MPWfTW/RGzuMYVmyBFais0/VrgdH
 h1dLpztmpQqfyH/zrBXQ9qL/zR4ojS6XYneO/U18WpEe
 -----END RSA PRIVATE KEY-----"""
    @patch('builtins.open', new_callable=mock_open, read_data=pkey)
    @patch('est_proxy.secureserver.logger_setup')
    @patch('est_proxy.secureserver.config_load')
    def test_009_config_load(self, mock_load_cfg, mock_logger, mock_file):
        """ test _config_load  daemon section with correct key_file """
        mock_logger.return_value = self.logger
        parser = configparser.ConfigParser()
        parser['Daemon'] = {'key_file': 'foo'}
        mock_load_cfg.return_value = parser

        with self.assertLogs('test_est', level='INFO') as lcm:
            self.secureserver._config_load()
        # self.assertIn('foo.', lcm.output)
        self.assertTrue(self.secureserver.config_dic['Daemon']['key_file'])

    @patch('est_proxy.secureserver.logger_setup')
    @patch('est_proxy.secureserver.config_load')
    def test_010_config_load(self, mock_load_cfg, mock_logger):
        """ test _config_load  daemon section with invalid key_file """
        mock_logger.return_value = self.logger
        parser = configparser.ConfigParser()
        parser['Daemon'] = {'cert_file': 'foo'}
        mock_load_cfg.return_value = parser
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.secureserver._config_load()
        self.assertIn('ERROR:test_est:Secureserver._load_config() cert_file foo could not be loaded.', lcm.output)

    pkey = b"""-----BEGIN CERTIFICATE-----
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
-----END CERTIFICATE-----"""
    @patch('builtins.open', new_callable=mock_open, read_data=pkey)
    @patch('est_proxy.secureserver.logger_setup')
    @patch('est_proxy.secureserver.config_load')
    def test_011_config_load(self, mock_load_cfg, mock_logger, mock_file):
        """ test _config_load  daemon section with correct key_file """
        mock_logger.return_value = self.logger
        parser = configparser.ConfigParser()
        parser['Daemon'] = {'cert_file': 'foo'}
        mock_load_cfg.return_value = parser

        with self.assertLogs('test_est', level='INFO') as lcm:
            self.secureserver._config_load()
        # self.assertIn('foo.', lcm.output)
        self.assertTrue(self.secureserver.config_dic['Daemon']['cert_file'])

    @patch('est_proxy.secureserver.logger_setup')
    @patch('est_proxy.secureserver.config_load')
    def test_012_config_load(self, mock_load_cfg, mock_logger):
        """ test _config_load  daemon section without key_file and cert_file """
        mock_logger.return_value = self.logger
        parser = configparser.ConfigParser()
        parser['SRP'] = {'foo': 'bar'}
        mock_load_cfg.return_value = parser
        self.secureserver._config_load()
        self.assertEqual({}, self.secureserver.config_dic['SRP'])

    @patch('est_proxy.secureserver.logger_setup')
    @patch('est_proxy.secureserver.config_load')
    def test_013_config_load(self, mock_load_cfg, mock_logger):
        """ test _config_load  daemon section without key_file and cert_file """
        mock_logger.return_value = self.logger
        parser = configparser.ConfigParser()
        parser['SRP'] = {'userdb': 'foo'}
        mock_load_cfg.return_value = parser
        self.secureserver._config_load()
        self.assertEqual({'userdb': 'foo'}, self.secureserver.config_dic['SRP'])

    def test_014_init(self):
        """ test init """
        warnings.simplefilter("ignore", ResourceWarning)
        server_address = ('127.0.0.1', 1234)
        handler_class = 'handlerclass'
        self.secureserver.__init__(server_address, handler_class, cfg_file='cfg_file')
        self.assertEqual('cfg_file', self.secureserver.cfg_file)

    def test_015_handshake(self):
        """ test handshake """
        connection = Mock()
        connection.request_post_handshake_auth = Mock(return_value=['foo', 'bar'])
        self.secureserver.logger = self.logger
        self.assertTrue(self.secureserver.handshake(connection))

    def test_016_handshake(self):
        """ test handshake """
        connection = Mock()
        connection.request_post_handshake_auth = 'bsbas'
        self.secureserver.logger = self.logger

        with self.assertLogs('test_est', level='DEBUG') as lcm:
            self.assertTrue(self.secureserver.handshake(connection))
        self.assertIn("DEBUG:test_est:'str' object is not callable", lcm.output)

    @patch('est_proxy.secureserver.connection_log')
    def test_017_handshake(self, mock_log):
        """ test handshake """
        connection = Mock()
        connection.request_post_handshake_auth = Mock(return_value=['foo', 'bar'])
        self.secureserver.logger = self.logger
        self.secureserver.config_dic = {'connection_log': True}
        with self.assertLogs('test_est', level='INFO') as lcm:
            mock_log = Mock(return_value=fake_log(self.logger, 'test_017_handshake'))
            self.assertTrue(self.secureserver.handshake(connection))
        self.assertIn('ERROR:test_est:test_017_handshake', lcm.output)

    @patch('est_proxy.secureserver.connection_log')
    def test_018_handshake(self, mock_log):
        """ test handshake unknown exception """
        connection = Mock()
        connection.request_post_handshake_auth = Mock(return_value=['foo', 'bar'])
        connection.handshakeServer.side_effect = Exception('unkn')
        self.secureserver.logger = self.logger
        self.secureserver.config_dic = {'connection_log': True}
        with self.assertLogs('test_est', level='INFO') as lcm:
            mock_log = Mock(return_value=fake_log(self.logger, 'test_017_handshake'))
            self.assertFalse(self.secureserver.handshake(connection))
        self.assertIn('ERROR:test_est:Error: unkn', lcm.output)

    @patch('est_proxy.secureserver.connection_log')
    def test_019_handshake(self, mock_log):
        """ test handshake TLSLocalAlert handshake_failure """
        alert = Mock()
        alert.description = tlslite.constants.AlertDescription.handshake_failure

        connection = Mock()
        connection.request_post_handshake_auth = Mock(return_value=['foo', 'bar'])
        connection.handshakeServer.side_effect = tlslite.errors.TLSLocalAlert(alert)
        self.secureserver.logger = self.logger
        self.secureserver.config_dic = {'connection_log': True}
        with self.assertLogs('test_est', level='INFO') as lcm:
            mock_log = Mock(return_value=fake_log(self.logger, 'test_017_handshake'))
            self.assertFalse(self.secureserver.handshake(connection))
        self.assertIn('ERROR:test_est:TLSLocalAlert: Unable to negotiate mutually acceptable parameters', lcm.output)

    @patch('est_proxy.secureserver.connection_log')
    def test_020_handshake(self, mock_log):
        """ test handshake TLSLocalAlert other failure """
        alert = Mock()
        alert.description = 'other failure'

        connection = Mock()
        connection.request_post_handshake_auth = Mock(return_value=['foo', 'bar'])
        connection.handshakeServer.side_effect = tlslite.errors.TLSLocalAlert(alert)
        self.secureserver.logger = self.logger
        self.secureserver.config_dic = {'connection_log': True}
        with self.assertLogs('test_est', level='INFO') as lcm:
            mock_log = Mock(return_value=fake_log(self.logger, 'test_017_handshake'))
            self.assertFalse(self.secureserver.handshake(connection))
        self.assertIn('ERROR:test_est:TLSLocalAlert: other failure', lcm.output)

    @patch('est_proxy.secureserver.connection_log')
    def test_021_handshake(self, mock_log):
        """ test handshake TLSRemoteAlert user canceled """
        alert = Mock()
        alert.description = tlslite.constants.AlertDescription.user_canceled

        connection = Mock()
        connection.request_post_handshake_auth = Mock(return_value=['foo', 'bar'])
        connection.handshakeServer.side_effect = tlslite.errors.TLSRemoteAlert(alert)
        self.secureserver.logger = self.logger
        self.secureserver.config_dic = {'connection_log': True}
        with self.assertLogs('test_est', level='INFO') as lcm:
            mock_log = Mock(return_value=fake_log(self.logger, 'test_017_handshake'))
            self.assertFalse(self.secureserver.handshake(connection))
        self.assertIn('ERROR:test_est:TLSRemoteAlert: user_canceled', lcm.output)

    @patch('est_proxy.secureserver.connection_log')
    def test_022_handshake(self, mock_log):
        """ test handshake TLSRemoteAlert opther message """
        alert = Mock()
        alert.description = tlslite.constants.AlertDescription.handshake_failure

        connection = Mock()
        connection.request_post_handshake_auth = Mock(return_value=['foo', 'bar'])
        connection.handshakeServer.side_effect = tlslite.errors.TLSRemoteAlert(alert)
        self.secureserver.logger = self.logger
        self.secureserver.config_dic = {'connection_log': True}
        with self.assertLogs('test_est', level='INFO') as lcm:
            mock_log = Mock(return_value=fake_log(self.logger, 'test_017_handshake'))
            self.assertFalse(self.secureserver.handshake(connection))
        self.assertIn('ERROR:test_est:TLSRemoteAlert: handshake_failure', lcm.output)

    @patch('est_proxy.secureserver.connection_log')
    def test_023_handshake(self, mock_log):
        """ test handshake TLSError opther message """

        connection = Mock()
        connection.request_post_handshake_auth = Mock(return_value=['foo', 'bar'])
        connection.handshakeServer.side_effect = tlslite.errors.TLSError()
        self.secureserver.logger = self.logger
        self.secureserver.config_dic = {'connection_log': True}
        with self.assertLogs('test_est', level='INFO') as lcm:
            mock_log = Mock(return_value=fake_log(self.logger, 'test_017_handshake'))
            self.assertFalse(self.secureserver.handshake(connection))
        self.assertIn("ERROR:test_est:TLSError: TLSError()", lcm.output)

if __name__ == '__main__':
    unittest.main()
