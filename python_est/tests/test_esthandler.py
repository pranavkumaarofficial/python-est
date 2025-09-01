#!/usr/bin/python
# -*- coding: utf-8 -*-
""" unittests for esthandler """
# pylint: disable= C0415, E0401, R0904, W0201, W0212
import unittest
import sys
import importlib
import io
from unittest.mock import patch, Mock, mock_open

sys.path.insert(0, '.')
sys.path.insert(1, '..')

class EsthanderTestCases(unittest.TestCase):
    """ test class for cgi_handler """

    def setUp(self):
        """ setup unittest """
        import logging
        logging.basicConfig(level=logging.CRITICAL)
        self.logger = logging.getLogger('test_est')
        from est_proxy.est_handler import ESTSrvHandler
        self.esthandler = ESTSrvHandler.__new__(ESTSrvHandler)
        self.esthandler.logger = logging.getLogger('test_est')

    def test_001__cacerts_split(self):
        """ _cacerts_split() two certs """
        ca_certs = """
foo
-----END CERTIFICATE-----
bar
-----END CERTIFICATE-----
"""
        result = ['\nfoo\n-----END CERTIFICATE-----\n', 'bar\n-----END CERTIFICATE-----\n']
        self.assertEqual(result, self.esthandler._cacerts_split(ca_certs))

    def test_002__cacerts_split(self):
        """ _cacerts_split() one cert """
        ca_certs = """
foo
-----END CERTIFICATE-----
"""
        result = ['\nfoo\n-----END CERTIFICATE-----\n']
        self.assertEqual(result, self.esthandler._cacerts_split(ca_certs))

    def test_003__cacerts_split(self):
        """ _cacerts_split() certs none """
        ca_certs = None
        result = []
        self.assertEqual(result, self.esthandler._cacerts_split(ca_certs))

    def test_004__cacerts_split(self):
        """ _cacerts_split() certs is a bogus string """
        ca_certs = 'string'
        result = []
        self.assertEqual(result, self.esthandler._cacerts_split(ca_certs))

    @patch('tempfile.NamedTemporaryFile')
    def test_005__cacerts_dump(self, mock_nf):
        """ _cacerts_dump() two certs """
        obj1 = Mock()
        obj1.name = 'foo_ret'
        obj2 = Mock()
        obj2.name = 'bar_ret'
        mock_nf.side_effect = [obj1, obj2]
        result = ['foo_ret', 'bar_ret']
        self.assertEqual(result, self.esthandler._cacerts_dump(['foo', 'bar']))

    @patch('tempfile.NamedTemporaryFile')
    def test_006_cacerts_dump(self, mock_nf):
        """ _cacerts_dump() two certs """
        obj1 = Mock()
        obj1.name = 'foo_ret'
        mock_nf.side_effect = [obj1]
        result = ['foo_ret']
        self.assertEqual(result, self.esthandler._cacerts_dump(['foo']))

    @patch('tempfile.NamedTemporaryFile')
    def test_007_cacerts_dump(self, mock_nf):
        """ _cacerts_dump() empty list   """
        obj1 = Mock()
        obj1.name = 'foo_ret'
        mock_nf.side_effect = [obj1]
        self.assertFalse(self.esthandler._cacerts_dump([]))

    @patch('tempfile.NamedTemporaryFile')
    def test_008_cacerts_dump(self, mock_nf):
        """ _cacerts_dump() empty list   """
        obj1 = Mock()
        obj1.name = 'foo_ret'
        mock_nf.side_effect = [obj1]
        self.assertFalse(self.esthandler._cacerts_dump('foo'))

    def test_009__opensslcmd_build(self):
        """ _opensslcmd_build two certs """
        self.esthandler.openssl_bin = 'openssl'
        file_name_list = ['foo', 'bar']
        pkcs7_file = 'pkcs7_file'
        result = ['openssl', 'crl2pkcs7', '-nocrl', '-out', 'pkcs7_file', '--certfile', 'foo', '--certfile', 'bar']
        self.assertEqual(result, self.esthandler._opensslcmd_build(file_name_list, pkcs7_file))

    def test_010__opensslcmd_build(self):
        """ _opensslcmd_build one certs """
        self.esthandler.openssl_bin = 'openssl'
        file_name_list = ['foo']
        pkcs7_file = 'pkcs7_file'
        result = ['openssl', 'crl2pkcs7', '-nocrl', '-out', 'pkcs7_file', '--certfile', 'foo']
        self.assertEqual(result, self.esthandler._opensslcmd_build(file_name_list, pkcs7_file))

    def test_011__opensslcmd_build(self):
        """ _opensslcmd_build two certs """
        self.esthandler.openssl_bin = 'openssl'
        file_name_list = ['foo1', 'foo2', 'foo3']
        pkcs7_file = 'pkcs7_file'
        result = ['openssl', 'crl2pkcs7', '-nocrl', '-out', 'pkcs7_file', '--certfile', 'foo1', '--certfile', 'foo2', '--certfile', 'foo3']
        self.assertEqual(result, self.esthandler._opensslcmd_build(file_name_list, pkcs7_file))

    def test_012__opensslcmd_build(self):
        """ _opensslcmd_build one certs in list as string """
        self.esthandler.openssl_bin = 'openssl'
        file_name_list = 'foo'
        pkcs7_file = 'pkcs7_file'
        result = ['openssl', 'crl2pkcs7', '-nocrl', '-out', 'pkcs7_file', '--certfile', 'foo']
        self.assertEqual(result, self.esthandler._opensslcmd_build(file_name_list, pkcs7_file))

    def test_013__opensslcmd_build(self):
        """ _opensslcmd_build one certs in list as string """
        self.esthandler.openssl_bin = 'openssl'
        file_name_list = b'foo'
        pkcs7_file = 'pkcs7_file'
        result = ['openssl', 'crl2pkcs7', '-nocrl', '-out', 'pkcs7_file', '--certfile', 'foo']
        self.assertEqual(result, self.esthandler._opensslcmd_build(file_name_list, pkcs7_file))

    def test_014___pkcs7_clean(self):
        """ _pkcs7_clean() certs ok """
        pkcs7 = '-----BEGIN PKCS7-----\nfoo-----END PKCS7-----'
        result = 'foo'
        self.assertEqual(result, self.esthandler._pkcs7_clean(pkcs7))

    def test_015___pkcs7_clean(self):
        """ _pkcs7_clean() hast just END tag """
        pkcs7 = 'foo-----END PKCS7-----'
        result = 'foo'
        self.assertEqual(result, self.esthandler._pkcs7_clean(pkcs7))

    def test_016___pkcs7_clean(self):
        """ _pkcs7_clean() just BEGIN tag """
        pkcs7 = '-----BEGIN PKCS7-----\nfoo'
        result = 'foo'
        self.assertEqual(result, self.esthandler._pkcs7_clean(pkcs7))

    def test_017___pkcs7_clean(self):
        """ _pkcs7_clean() pcs#7 None """
        pkcs7 = None
        self.assertFalse(self.esthandler._pkcs7_clean(pkcs7))

    def test_018___pkcs7_clean(self):
        """ _pkcs7_clean() pcs#7 int """
        pkcs7 = 8
        self.assertEqual(8, self.esthandler._pkcs7_clean(pkcs7))

    def test_019___pkcs7_clean(self):
        """ _pkcs7_clean() pcs#7 byte """
        pkcs7 = b'-----BEGIN PKCS7-----\nfoo-----END PKCS7-----'
        result = 'foo'
        self.assertEqual(result, self.esthandler._pkcs7_clean(pkcs7))

    @patch('est_proxy.est_handler.ESTSrvHandler._tmpfiles_clean')
    @patch('est_proxy.est_handler.ESTSrvHandler._cacerts_dump')
    @patch('est_proxy.est_handler.ESTSrvHandler._cacerts_split')
    @patch('builtins.open', mock_open(read_data="pkcs7_struc"))
    @patch('subprocess.call')
    def test_020__pkcs7_convert(self, mock_call, mock_split, mock_dmp, mock_clean):
        """ _pkcs7_convert() all ok """
        self.esthandler.openssl_bin = 'openssl'
        mock_call.return_value = 0
        mock_split.return_value = ['foo', 'bar']
        mock_dmp.return_value = ['foo_name', 'bar_name']
        mock_clean.return_value = 0
        self.assertEqual('pkcs7_struc', self.esthandler._pkcs7_convert('cacertss'))

    @patch('tempfile.NamedTemporaryFile')
    @patch('builtins.open', mock_open(read_data="pkcs7_struc"))
    @patch('est_proxy.est_handler.ESTSrvHandler._tmpfiles_clean')
    @patch('est_proxy.est_handler.ESTSrvHandler._cacerts_dump')
    @patch('est_proxy.est_handler.ESTSrvHandler._cacerts_split')
    @patch('subprocess.call')
    def test_021__pkcs7_convert(self, mock_call, mock_split, mock_dmp, mock_clean, mock_nf):
        """ _pkcs7_convert() all ok """
        obj1 = Mock()
        obj1.name = 'mock_nf_ret'
        mock_nf.side_effect = [obj1]
        self.esthandler.openssl_bin = 'openssl'
        mock_call.return_value = 0
        mock_split.return_value = ['foo', 'bar']
        mock_dmp.return_value = ['foo_name', 'bar_name']
        mock_clean.return_value = 0
        self.assertEqual('pkcs7_struc', self.esthandler._pkcs7_convert('cacertss'))

    def test_022__pkcs7_convert(self):
        """ _pkcs7_convert() all no cacerts """
        self.esthandler.openssl_bin = 'openssl'
        self.assertFalse(self.esthandler._pkcs7_convert(None))

    @patch('est_proxy.est_handler.ESTSrvHandler._cacerts_dump')
    @patch('est_proxy.est_handler.ESTSrvHandler._cacerts_split')
    def test_023__pkcs7_convert(self, mock_split, mock_dmp):
        """ _pkcs7_convert() no openssl command defined """
        self.esthandler.openssl_bin = None
        mock_split.return_value = ['foo', 'bar']
        mock_dmp.return_value = ['foo_name', 'bar_name']
        self.assertFalse(self.esthandler._pkcs7_convert('cacertss'))

    @patch('est_proxy.est_handler.ESTSrvHandler._cacerts_dump')
    @patch('est_proxy.est_handler.ESTSrvHandler._cacerts_split')
    def test_024__pkcs7_convert(self, mock_split, mock_dmp):
        """ _pkcs7_convert() cert dump run into an error """
        self.esthandler.openssl_bin = 'openssl'
        mock_split.return_value = ['foo', 'bar']
        mock_dmp.return_value = []
        self.assertFalse(self.esthandler._pkcs7_convert('cacertss'))

    @patch('tempfile.NamedTemporaryFile')
    @patch('builtins.open', mock_open(read_data="pkcs7_struc"))
    @patch('est_proxy.est_handler.ESTSrvHandler._tmpfiles_clean')
    @patch('est_proxy.est_handler.ESTSrvHandler._cacerts_dump')
    @patch('est_proxy.est_handler.ESTSrvHandler._cacerts_split')
    @patch('subprocess.call')
    def test_025__pkcs7_convert(self, mock_call, mock_split, mock_dmp, mock_clean, mock_nf):
        """ _pkcs7_convert() all ok """
        obj1 = Mock()
        obj1.name = 'mock_nf_ret'
        mock_nf.side_effect = [obj1]
        self.esthandler.openssl_bin = 'openssl'
        mock_call.return_value = 1
        mock_split.return_value = ['foo', 'bar']
        mock_dmp.return_value = ['foo_name', 'bar_name']
        mock_clean.return_value = 0
        self.assertFalse(self.esthandler._pkcs7_convert('cacertss'))

    def test_026__get_process(self):
        """ _get_process() - root path """
        self.esthandler.path = '/'
        self.assertEqual((400, 'text/html', 29, None, b'An unknown error has occured.'), self.esthandler._get_process())

    def test_027__get_process(self):
        """ _get_process() - None as path """
        self.esthandler.path = None
        self.assertEqual((400, 'text/html', 29, None, b'An unknown error has occured.'), self.esthandler._get_process())

    def test_028__get_process(self):
        """ _get_process() - int as path """
        self.esthandler.path = 13
        self.assertEqual((400, 'text/html', 29, None, b'An unknown error has occured.'), self.esthandler._get_process())

    def test_029__get_process(self):
        """ _get_process() - string as path """
        self.esthandler.path = 13
        self.assertEqual((400, 'text/html', 29, None, b'An unknown error has occured.'), self.esthandler._get_process())

    def test_030__get_process(self):
        """ _get_process() - unknown path """
        self.esthandler.path = '/notallowedpath'
        self.assertEqual((400, 'text/html', 29, None, b'An unknown error has occured.'), self.esthandler._get_process())

    @patch('est_proxy.est_handler.ESTSrvHandler._cacerts_get')
    def test_031__get_process(self, mock_caget):
        """ _get_process() - ca certs """
        self.esthandler.path = '/.well-known/est/cacerts'
        mock_caget.return_value = 'foobar'
        self.assertEqual((200, 'application/pkcs7-mime', 6, 'base64', b'foobar'), self.esthandler._get_process())

    @patch('est_proxy.est_handler.ESTSrvHandler._cacerts_get')
    def test_032__get_process(self, mock_caget):
        """ _get_process() - ca certs """
        self.esthandler.path = '/.well-known/est/cacerts'
        mock_caget.return_value = None
        self.assertEqual((500, 'text/html', 0, None, None), self.esthandler._get_process())

    def test_033_set_response(self):
        """ _set_response() - all ok """
        def dummy_func(*args):
            self.input = args[0].decode('utf-8')
        mock_wfile = Mock()
        mock_wfile.write = dummy_func
        self.esthandler.requestline = 'requestline'
        self.esthandler.client_address = ('127.0.0.1', 12345)
        self.esthandler.request_version = 'request_version'
        self.esthandler.wfile = mock_wfile
        self.esthandler._set_response(code=200, content_type='text/html', clength=100, encoding='utf-8')
        self.assertIn('HTTP/1.1 200 OK', self.input)
        self.assertIn('Content-Type: text/html', self.input)
        self.assertIn('Content-Transfer-Encoding: utf-8', self.input)
        self.assertIn('Content-Length: 100', self.input)
        self.assertIn('Connection: close', self.input)

    def test_034_set_response(self):
        """ _set_response() - no content length code 500 """
        def dummy_func(*args):
            self.input = args[0].decode('utf-8')
        mock_wfile = Mock()
        mock_wfile.write = dummy_func
        self.esthandler.requestline = 'requestline'
        self.esthandler.client_address = ('127.0.0.1', 12345)
        self.esthandler.request_version = 'request_version'
        self.esthandler.wfile = mock_wfile
        self.esthandler._set_response(code=500, content_type='text/html', clength=0, encoding='utf-8')
        self.assertIn('HTTP/1.1 500 Internal Server Error', self.input)
        self.assertIn('Content-Type: text/html', self.input)
        self.assertIn('Content-Transfer-Encoding: utf-8', self.input)
        self.assertIn('Connection: close', self.input)

    def test_035_set_response(self):
        """ _set_response() - code 404 """
        def dummy_func(*args):
            self.input = args[0].decode('utf-8')
        mock_wfile = Mock()
        mock_wfile.write = dummy_func
        self.esthandler.requestline = 'requestline'
        self.esthandler.client_address = ('127.0.0.1', 12345)
        self.esthandler.request_version = 'request_version'
        self.esthandler.wfile = mock_wfile
        self.esthandler._set_response(code=404, content_type='text/html', clength=5, encoding='utf-8')
        self.assertIn('HTTP/1.1 404 Not Found', self.input)
        self.assertIn('Content-Type: text/html', self.input)
        self.assertIn('Content-Transfer-Encoding: utf-8', self.input)
        self.assertIn('Connection: close', self.input)

    def test_036_set_response(self):
        """ _set_response() -  different content length """
        def dummy_func(*args):
            self.input = args[0].decode('utf-8')
        mock_wfile = Mock()
        mock_wfile.write = dummy_func
        self.esthandler.requestline = 'requestline'
        self.esthandler.client_address = ('127.0.0.1', 12345)
        self.esthandler.request_version = 'request_version'
        self.esthandler.wfile = mock_wfile
        self.esthandler._set_response(code=200, content_type='foo', clength=5, encoding='utf-8')
        self.assertIn('HTTP/1.1 200 OK', self.input)
        self.assertIn('Content-Type: foo', self.input)
        self.assertIn('Content-Transfer-Encoding: utf-8', self.input)
        self.assertIn('Connection: close', self.input)

    def test_037_set_response(self):
        """ _set_response() -  different encoding, no content-type """
        def dummy_func(*args):
            self.input = args[0].decode('utf-8')
        mock_wfile = Mock()
        mock_wfile.write = dummy_func
        self.esthandler.requestline = 'requestline'
        self.esthandler.client_address = ('127.0.0.1', 12345)
        self.esthandler.request_version = 'request_version'
        self.esthandler.wfile = mock_wfile
        self.esthandler._set_response(code=200, clength=5, encoding='encoding')
        self.assertIn('HTTP/1.1 200 OK', self.input)
        self.assertIn('Content-Type: text/html', self.input)
        self.assertIn('Content-Transfer-Encoding: encoding', self.input)
        self.assertIn('Connection: close', self.input)

    @patch('est_proxy.est_handler.config_load')
    def test_038_config_load(self, mock_load_cfg):
        """ test _config_load empty dictionary """
        mock_load_cfg.return_value = {}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.esthandler._config_load()
        self.assertFalse(self.esthandler.cahandler)
        self.assertEqual('openssl', self.esthandler.openssl_bin)
        self.assertIn('ERROR:test_est:ESTSrvHandler._config_load(): CAhandler configuration missing in config file', lcm.output)

    @patch('est_proxy.est_handler.config_load')
    def test_039_config_load(self, mock_load_cfg):
        """ test _config_load customized openssl command """
        mock_load_cfg.return_value = {'DEFAULT': {'openssl_bin': 'openssl_bin'}}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.esthandler._config_load()
        self.assertFalse(self.esthandler.cahandler)
        self.assertEqual('openssl_bin', self.esthandler.openssl_bin)
        self.assertIn('ERROR:test_est:ESTSrvHandler._config_load(): CAhandler configuration missing in config file', lcm.output)

    @patch('est_proxy.est_handler.config_load')
    def test_040_config_load(self, mock_load_cfg):
        """ test _config_load ca handler config without handler file """
        mock_load_cfg.return_value = {'CAhandler': {'foo': 'bar'}}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.esthandler._config_load()
        self.assertFalse(self.esthandler.cahandler)
        self.assertEqual('openssl', self.esthandler.openssl_bin)
        self.assertIn("ERROR:test_est:ESTSrvHandler._config_load(): default CAhandler could not get loaded. err: No module named 'est_proxy.ca_handler'", lcm.output)

    @patch('importlib.import_module')
    @patch('est_proxy.est_handler.config_load')
    def test_041_config_load(self, mock_load_cfg, mock_import):
        """ test _config_load ca handler config without handler file """
        mock_load_cfg.return_value = {'CAhandler': {'foo': 'bar'}}
        mock_import.return_value = importlib.import_module('examples.ca_handler.skeleton_ca_handler')
        self.esthandler._config_load()
        self.assertTrue(self.esthandler.cahandler)
        self.assertEqual('openssl', self.esthandler.openssl_bin)

    @patch('est_proxy.est_handler.config_load')
    def test_042_config_load(self, mock_load_cfg):
        """ test _config_load ca handler handler file configured but both handle_file and default handler failed """
        mock_load_cfg.return_value = {'CAhandler': {'handler_file': 'handler_file', 'foo': 'bar'}}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.esthandler._config_load()
        self.assertFalse(self.esthandler.cahandler)
        self.assertEqual('openssl', self.esthandler.openssl_bin)
        self.assertIn("ERROR:test_est:ESTSrvHandler._config_load(): CAhandler handler_file could not get loaded. with error: No module named 'handler_file'\nLoading default hander...", lcm.output)
        self.assertIn("ERROR:test_est:ESTSrvHandler._config_load():  Loading default handler failed.", lcm.output)

    @patch('importlib.import_module')
    @patch('est_proxy.est_handler.config_load')
    def test_043_config_load(self, mock_load_cfg, mock_import):
        """ test _config_load ca handler config without handler file """
        mock_load_cfg.return_value = {'CAhandler': {'handler_file': 'handler_file', 'foo': 'bar'}}
        mockresponse1 = Exception('exc_cahandlerconfigload')
        mockresponse2 = importlib.import_module('examples.ca_handler.skeleton_ca_handler')
        mock_import.side_effect = [mockresponse1, mockresponse2]
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.esthandler._config_load()
        self.assertTrue(self.esthandler.cahandler)
        self.assertEqual('openssl', self.esthandler.openssl_bin)
        self.assertIn("ERROR:test_est:ESTSrvHandler._config_load(): CAhandler handler_file could not get loaded. with error: exc_cahandlerconfigload\nLoading default hander...", lcm.output)

    @patch('importlib.import_module')
    @patch('est_proxy.est_handler.config_load')
    def test_044_config_load(self, mock_load_cfg, mock_import):
        """ test _config_load ca handler confighandler file could get successfully loaded """
        mock_load_cfg.return_value = {'CAhandler': {'handler_file': 'handler_file', 'foo': 'bar'}}
        mock_import.return_value = importlib.import_module('examples.ca_handler.skeleton_ca_handler')
        self.esthandler._config_load()
        self.assertTrue(self.esthandler.cahandler)
        self.assertEqual('openssl', self.esthandler.openssl_bin)

    @patch('est_proxy.est_handler.ESTSrvHandler._auth_check')
    def test_045__post_process(self, mock_auth):
        """ _post_process() - root path """
        self.esthandler.path = '/'
        mock_auth.return_value = False
        self.assertEqual((401, None, 48, None, b'The server was unable to authorize the request.\n'), self.esthandler._post_process('data'))

    @patch('est_proxy.est_handler.ESTSrvHandler._auth_check')
    def test_046__post_process(self, mock_auth):
        """ _post_process() - root path """
        self.esthandler.path = '/'
        mock_auth.return_value = True
        self.assertEqual((400, None, 30, None, b'An unknown error has occured.\n'), self.esthandler._post_process('data'))

    @patch('est_proxy.est_handler.ESTSrvHandler._auth_check')
    def test_047__post_process(self, mock_auth):
        """ _post_process() - enroll but no data """
        self.esthandler.path = '/.well-known/est/simpleenroll'
        mock_auth.return_value = True
        self.assertEqual((400, None, 23, None, b'No data had been send.\n'), self.esthandler._post_process(None))

    @patch('est_proxy.est_handler.ESTSrvHandler._auth_check')
    def test_048__post_process(self, mock_auth):
        """ _post_process() - enroll but data to a wrong url """
        self.esthandler.path = '/foobadoo'
        mock_auth.return_value = True
        self.assertEqual((400, None, 30, None, b'An unknown error has occured.\n'), self.esthandler._post_process('data'))

    @patch('est_proxy.est_handler.ESTSrvHandler._auth_check')
    @patch('est_proxy.est_handler.ESTSrvHandler._cert_enroll')
    def test_049__post_process(self, mock_enroll, mock_auth):
        """ _post_process() - enroll but no data """
        self.esthandler.path = '/.well-known/est/simplereenroll'
        mock_auth.return_value = True
        mock_enroll.return_value = ('error', 'cert')
        self.assertEqual((500, None, 0, None, None), self.esthandler._post_process('data'))

    @patch('est_proxy.est_handler.ESTSrvHandler._auth_check')
    @patch('est_proxy.est_handler.ESTSrvHandler._cert_enroll')
    def test_050__post_process(self, mock_enroll, mock_auth):
        """ _post_process() - enroll but no data """
        self.esthandler.path = '/.well-known/est/simplereenroll'
        mock_auth.return_value = True
        mock_enroll.return_value = (None, 'cert')
        self.assertEqual((200, 'application/pkcs7-mime; smime-type=certs-only', 4, 'base64', b'cert'), self.esthandler._post_process('data'))

    def test_051__cert_enroll(self):
        """ _cert_enroll() without csr """
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertEqual(('no CSR submittted', None), self.esthandler._cert_enroll(None))
        self.assertIn('ERROR:test_est:ESTSrvHandler._cert_enroll(): no csr submitted', lcm.output)

    def test_052__cert_enroll(self):
        """ _cert_enroll() error returned """
        ca_handler_module = importlib.import_module('examples.ca_handler.skeleton_ca_handler')
        self.esthandler.cahandler = ca_handler_module.CAhandler
        self.esthandler.cahandler._config_load = Mock()
        self.esthandler.cahandler.enroll = Mock(return_value=['error', 'cert', 'poll_identifier'])
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertEqual(('error', None), self.esthandler._cert_enroll('data'))
        self.assertIn('ERROR:test_est:ESTSrvHandler._cert_enroll(): error', lcm.output)

    def test_053__cert_enroll(self):
        """ _cert_enroll() error returned """
        ca_handler_module = importlib.import_module('examples.ca_handler.skeleton_ca_handler')
        self.esthandler.cahandler = ca_handler_module.CAhandler
        self.esthandler.cahandler._config_load = Mock()
        self.esthandler.cahandler.enroll = Mock(return_value=[None, None, 'poll_identifier'])
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertEqual(('No error but no cert returned', None), self.esthandler._cert_enroll('data'))
        self.assertIn('ERROR:test_est:ESTSrvHandler._cert_enroll(): No error but no cert returned', lcm.output)

    @patch('est_proxy.est_handler.ESTSrvHandler._pkcs7_convert')
    def test_054__cert_enroll(self, mock_convert):
        """ _cert_enroll() all ok """
        ca_handler_module = importlib.import_module('examples.ca_handler.skeleton_ca_handler')
        self.esthandler.cahandler = ca_handler_module.CAhandler
        self.esthandler.cahandler._config_load = Mock()
        self.esthandler.cahandler.enroll = Mock(return_value=[None, 'cert', 'poll_identifier'])
        mock_convert.return_value = 'pkcs7'
        self.assertEqual((None, 'pkcs7'), self.esthandler._cert_enroll('data'))

    def test_055__cacerts_get(self):
        """ _cert_enroll() error returned """
        ca_handler_module = importlib.import_module('examples.ca_handler.skeleton_ca_handler')
        self.esthandler.cahandler = ca_handler_module.CAhandler
        self.esthandler.cahandler._config_load = Mock()
        self.esthandler.cahandler.ca_certs_get = Mock(return_value=None)
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertEqual(None, self.esthandler._cacerts_get())
        self.assertIn('ERROR:test_est:ESTSrvHandler._cacerts_get(): no cacerts returned from handler', lcm.output)

    @patch('est_proxy.est_handler.ESTSrvHandler._pkcs7_convert')
    def test_056__cacerts_get(self, mock_convert):
        """ _cert_enroll() error returned """
        ca_handler_module = importlib.import_module('examples.ca_handler.skeleton_ca_handler')
        self.esthandler.cahandler = ca_handler_module.CAhandler
        self.esthandler.cahandler._config_load = Mock()
        self.esthandler.cahandler.ca_certs_get = Mock(return_value='cacert')
        mock_convert.return_value = 'pkcs7'
        self.assertEqual('pkcs7', self.esthandler._cacerts_get())

    def test_057__auth_check(self):
        """ _auth_check() neither clientauth nor srp auth """
        obj = Mock()
        obj.session = Mock()
        obj.session.clientCertChain = None
        obj.session.srpUsername = None
        self.esthandler.connection = obj
        self.assertFalse(self.esthandler._auth_check())

    def test_058__auth_check(self):
        """ _auth_check() clientauth """
        obj = Mock()
        obj.session = Mock()
        obj.session.clientCertChain = Mock()
        obj.session.clientCertChain.getFingerprint = Mock(return_value='clientCertChain')
        obj.session.srpUsername = None
        self.esthandler.connection = obj
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertTrue(self.esthandler._auth_check())
        self.assertIn('INFO:test_est:Client X.509 SHA1 fingerprint: clientCertChain', lcm.output)

    def test_059__auth_check(self):
        """ _auth_check() clientauth """
        obj = Mock()
        obj.session = Mock()
        obj.session.clientCertChain = None
        obj.session.srpUsername = 'srpUsername'
        self.esthandler.connection = obj
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertTrue(self.esthandler._auth_check())
        self.assertIn('INFO:test_est:Client SRP username: srpUsername', lcm.output)

    def test_060__auth_check(self):
        """ _auth_check() clientauth """
        obj = Mock()
        obj.session = Mock()
        obj.session.clientCertChain = Mock()
        obj.session.clientCertChain.getFingerprint = Mock(return_value='clientCertChain')
        obj.session.srpUsername = 'srpUsername'
        self.esthandler.connection = obj
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertTrue(self.esthandler._auth_check())
        self.assertIn('INFO:test_est:Client X.509 SHA1 fingerprint: clientCertChain', lcm.output)

    @patch('os.remove')
    def test_061__tmpfiles_clean(self, mock_remove):
        """ __tmpfiles_clean """
        file_list = ['foo', 'bar']
        mock_remove.return_value = True
        self.esthandler._tmpfiles_clean(file_list)

    @patch('os.remove')
    def test_062_tmpfiles_clean(self, mock_remove):
        """ __tmpfiles_clean exception for all files """
        file_list = ['foo', 'bar']
        mock_remove.side_effect = Exception('_tmpfiles_clean')
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.esthandler._tmpfiles_clean(file_list)
        self.assertIn('ERROR:test_est:ESTSrvHandler._tmpfiles_clean() failed for foo with error: _tmpfiles_clean', lcm.output)
        self.assertIn('ERROR:test_est:ESTSrvHandler._tmpfiles_clean() failed for bar with error: _tmpfiles_clean', lcm.output)

    @patch('os.remove')
    def test_063_tmpfiles_clean(self, mock_remove):
        """ __tmpfiles_clean exception for last file """
        file_list = ['foo', 'bar']
        mock_remove.side_effect = [True, Exception('_tmpfiles_clean')]
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.esthandler._tmpfiles_clean(file_list)
        self.assertIn('ERROR:test_est:ESTSrvHandler._tmpfiles_clean() failed for bar with error: _tmpfiles_clean', lcm.output)

    @patch('os.remove')
    def test_064_tmpfiles_clean(self, mock_remove):
        """ __tmpfiles_clean exception for last file """
        file_list = ['foo', 'bar']
        mock_remove.side_effect = [Exception('_tmpfiles_clean'), True]
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.esthandler._tmpfiles_clean(file_list)
        self.assertIn('ERROR:test_est:ESTSrvHandler._tmpfiles_clean() failed for foo with error: _tmpfiles_clean', lcm.output)

    @patch('est_proxy.est_handler.ESTSrvHandler._get_process')
    def test_065_do_get(self, mock_process):
        """ test do get """
        mock_process.return_value = ['code', 'content_type', 'content_length', 'encoding', 'content']
        self.esthandler.client_address = ('127.0.0.1', 8080)
        self.esthandler.path = '/'
        self.esthandler.requestline = 'requestline'
        self.esthandler.request_version = 'HTTP/0.9'
        self.esthandler.wfile = Mock()
        self.assertFalse(self.esthandler.do_GET())

    def test_066__init__(self):
        """ test __init__ exception when parsing cfg_file """
        request = Mock()
        request.makefile.return_value = io.BytesIO(b"GET /")
        # request.raw_requestline.return_value = 'fooooo'
        client_address = 'client_address'
        server_address = 'server_address'
        self.esthandler.__init__(request, client_address, server_address)
        self.assertEqual('est_proxy.cfg', self.esthandler.cfg_file)

    def test_067__init__(self):
        """ test __init__ parsing cfg_file """
        request = Mock()
        request.makefile.return_value = io.BytesIO(b"GET /")
        # request.raw_requestline.return_value = 'fooooo'
        client_address = 'client_address'
        server_address = Mock()
        server_address.cfg_file = 'foo.cfg'
        self.esthandler.__init__(request, client_address, server_address)
        self.assertEqual('foo.cfg', self.esthandler.cfg_file)

    def test_068__init__(self):
        """ test __init__ parsing cfg_file """
        request = Mock()
        request.side_effect = Exception('_tmpfiles_clean')
        request.makefile.return_value = io.BytesIO(b"GET /")
        request.raw_requestline.return_value = 'fooooo'
        client_address = 'client_address'
        server_address = Mock()
        self.esthandler.__init__()
        self.assertEqual('est_proxy.cfg', self.esthandler.cfg_file)

    @patch('est_proxy.est_handler.ESTSrvHandler._post_process')
    def test_069_do_post(self, mock_process):
        """ test do get """
        mock_process.return_value = ['code', 'content_type', 'content_length', 'encoding', 'content']
        self.esthandler.client_address = ('127.0.0.1', 8080)
        self.esthandler.path = '/'
        self.esthandler.requestline = 'requestline'
        self.esthandler.request_version = 'HTTP/0.9'
        self.esthandler.rfile = Mock()
        self.esthandler.wfile = Mock()
        self.esthandler.headers = {'Content-Length': 15}
        self.assertFalse(self.esthandler.do_POST())

    @patch('est_proxy.est_handler.ESTSrvHandler._post_process')
    def test_070_do_post(self, mock_process):
        """ test do get """
        mock_process.return_value = ['code', 'content_type', 'content_length', 'encoding', 'content']
        self.esthandler.client_address = ('127.0.0.1', 8080)
        self.esthandler.path = '/'
        self.esthandler.requestline = 'requestline'
        self.esthandler.request_version = 'HTTP/0.9'
        self.esthandler.rfile = Mock()
        self.esthandler.wfile = Mock()
        self.esthandler.headers = {'Content-Length': 0}
        self.assertFalse(self.esthandler.do_POST())

    @patch('est_proxy.est_handler.ESTSrvHandler._post_process')
    def test_071_do_post(self, mock_process):
        """ test do get """
        mock_process.return_value = ['code', 'content_type', 'content_length', 'encoding', 'content']
        self.esthandler.client_address = ('127.0.0.1', 8080)
        self.esthandler.path = '/'
        self.esthandler.requestline = 'requestline'
        self.esthandler.request_version = 'HTTP/0.9'
        self.esthandler.rfile = Mock()
        self.esthandler.rfile.readline = Mock()
        self.esthandler.rfile.readline.side_effect = [b'11', b'12345678901234567', b'', b'0', b'']
        self.esthandler.wfile = Mock()
        self.esthandler.headers = {'Transfer-Encoding': 'chunked'}
        self.assertFalse(self.esthandler.do_POST())


if __name__ == '__main__':
    unittest.main()
