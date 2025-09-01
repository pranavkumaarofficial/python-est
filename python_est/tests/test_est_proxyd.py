#!/usr/bin/python
# -*- coding: utf-8 -*-
""" unittests for helper """
# pylint: disable=C0302, C0415, E0401, R0902, R0904, R0913, R0914, R0915, W0212
import unittest
import configparser
import sys
from unittest.mock import patch, Mock

sys.path.insert(0, '.')
sys.path.insert(1, '..')

class HelperTestCases(unittest.TestCase):
    """ test class for helper """
    def setUp(self):
        """ setup """
        import logging
        logging.basicConfig(level=logging.CRITICAL)
        self.logger = logging.getLogger('test_est')
        from est_proxyd import _arg_parse, _config_load, srv_run
        self._arg_parse = _arg_parse
        self._config_load = _config_load
        self.srv_run = srv_run

    def tearDown(self):
        """ teardown test environment """
        # Clean up run after every test method.

    def test_001_allways_ok(self):
        """ a test that never failes """
        self.assertEqual('foo', 'foo')

    @patch('os.path.isfile')
    def test_002__arg_parse(self, mock_file):
        """ a test that never failes """
        sys.argv = ['foo', '-c', 'foo.cfg']
        mock_file.return_value = True
        self._arg_parse()

    @patch('os.path.isfile')
    def test_003__arg_parse(self, mock_file):
        """ a test that never failes """
        sys.argv = ['foo', '-c', 'foo.cfg']
        mock_file.return_value = False
        self._arg_parse()

    @patch('est_proxyd.config_load')
    def test_002_config_load(self, mock_load_cfg):
        """ test _config_load """
        mock_load_cfg.return_value = 'foo'
        self.assertEqual((False, {}), self._config_load())

    @patch('est_proxyd.config_load')
    def test_003_config_load(self, mock_load_cfg):
        """ test _config_load """
        parser = configparser.ConfigParser()
        parser['DEFAULT'] = {'foo': 'bar'}
        mock_load_cfg.return_value = parser
        self.assertEqual((False, {}), self._config_load())

    @patch('est_proxyd.config_load')
    def test_004_config_load(self, mock_load_cfg):
        """ test _config_load debug false """
        parser = configparser.ConfigParser()
        parser['DEFAULT'] = {'debug': False}
        mock_load_cfg.return_value = parser
        self.assertEqual((False, {}), self._config_load())

    @patch('est_proxyd.config_load')
    def test_005_config_load(self, mock_load_cfg):
        """ test _config_load debug true """
        parser = configparser.ConfigParser()
        parser['DEFAULT'] = {'debug': True}
        mock_load_cfg.return_value = parser
        self.assertEqual((True, {}), self._config_load())

    @patch('est_proxyd.config_load')
    def test_006_config_load(self, mock_load_cfg):
        """ test _config_load address and port int """
        parser = configparser.ConfigParser()
        parser['DEFAULT'] = {'debug': True}
        parser['Daemon'] = {'address': 'address', 'port': 1234}
        mock_load_cfg.return_value = parser
        self.assertEqual((True, {'Daemon': {'address': 'address', 'port': 1234}}), self._config_load())

    @patch('est_proxyd.config_load')
    def test_007_config_load(self, mock_load_cfg):
        """ test _config_load address and port string """
        parser = configparser.ConfigParser()
        parser['DEFAULT'] = {'debug': True}
        parser['Daemon'] = {'address': 'address', 'port': '1235'}
        mock_load_cfg.return_value = parser
        self.assertEqual((True, {'Daemon': {'address': 'address', 'port': 1235}}), self._config_load())

    @patch('est_proxyd.config_load')
    def test_008_config_load(self, mock_load_cfg):
        """ test _config_load address and port string """
        parser = configparser.ConfigParser()
        parser['DEFAULT'] = {'debug': True}
        parser['Daemon'] = {'address': 'address', 'port': 'aaa'}
        mock_load_cfg.return_value = parser
        self.assertEqual((True, {'Daemon': {'address': 'address', 'port': 1443}}), self._config_load())

    def test_009_srv_run(self):
        """ test srv_run """
        server_class = Mock()
        handler_class = Mock()
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.srv_run(self.logger, server_class, handler_class)
        self.assertIn('INFO:test_est:starting est_proxy 0.1.0 on 127.0.0.1:8080', lcm.output)
        self.assertIn('INFO:test_est:stopping est_proxy on 127.0.0.1:8080', lcm.output)

if __name__ == '__main__':
    unittest.main()
