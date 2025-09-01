#!/usr/bin/python
# -*- coding: utf-8 -*-
""" unittests for openssl_ca_handler """
# pylint: disable=C0302, C0415, R0904, R0913, W0212
import sys
import os
import unittest
from unittest.mock import patch, Mock
# from OpenSSL import crypto
import shutil

sys.path.insert(0, '.')
sys.path.insert(1, '..')

def _prepare(dir_path):
    """ prepare testing """
     # copy clean database
    if os.path.exists(dir_path + '/ca/est_proxy-clean.xdb'):
        shutil.copy(dir_path + '/ca/est_proxy-clean.xdb', dir_path + '/ca/est_proxy.xdb')

def _cleanup(dir_path):
    """ cleanup function """
    # remove old db
    if os.path.exists(dir_path + '/ca/est_proxy.xdb'):
        os.remove(dir_path + '/ca/est_proxy.xdb')

def return_input(*args, **kwargs):
    """ this function just returns input to output """
    _foo = kwargs
    return args


class TestACMEHandler(unittest.TestCase):
    """ test class for cgi_handler """

    def setUp(self):
        """ setup unittest """
        import logging
        from examples.ca_handler.xca_ca_handler import CAhandler
        logging.basicConfig(level=logging.CRITICAL)
        self.logger = logging.getLogger('test_est')
        self.cahandler = CAhandler(False, self.logger)
        self.dir_path = os.path.dirname(os.path.realpath(__file__))
        _prepare(self.dir_path)

    def tearDown(self):
        """ teardown """
        _cleanup(self.dir_path)

    def test_001_default(self):
        """ default test which always passes """
        self.assertEqual('foo', 'foo')

    def test_002_check_config(self):
        """ CAhandler._config_check with an empty config_dict """
        self.assertEqual('xdb_file must be specified in config file', self.cahandler._config_check())

    def test_003_check_config(self):
        """ CAhandler._config_check non existing xdb """
        self.cahandler.xdb_file = 'foo'
        self.assertEqual('xdb_file foo does not exist', self.cahandler._config_check())

    @patch('os.path.exists')
    def test_004_check_config(self, mock_file):
        """ CAhandler._config_check xdb exists but no issuing ca_name """
        self.cahandler.xdb_file = 'foo'
        mock_file.return_value = True
        self.assertEqual('issuing_ca_name must be set in config file', self.cahandler._config_check())

    @patch('os.path.exists')
    def test_005_check_config(self, mock_file):
        """ CAhandler._config_check xdb exists but no issuing ca_name """
        self.cahandler.xdb_file = 'foo'
        self.cahandler.issuing_ca_name = 'foo'
        mock_file.return_value = True
        self.assertFalse(self.cahandler._config_check())

    def test_006_csr_search(self):
        """ CAhandler._config_check non existing request """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.assertFalse(self.cahandler._csr_search('name', 'foo'))

    def test_007_csr_search(self):
        """ CAhandler._config_check existing request """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.assertTrue(self.cahandler._csr_search('name', 'test_request'))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_cert_load')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_key_load')
    def test_008_ca_load(self, mock_key, mock_cert):
        """ CAhandler._ca_load for both cert and key """
        mock_key.return_value = 'key'
        mock_cert.return_value = ('cert', 1)
        self.assertEqual(('key', 'cert', 1), self.cahandler._ca_load())

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_cert_load')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_key_load')
    def test_009_ca_load(self, mock_key, mock_cert):
        """ CAhandler._ca_load for cert only """
        mock_key.return_value = None
        mock_cert.return_value = ('cert', 1)
        self.assertEqual((None, 'cert', 1), self.cahandler._ca_load())

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_cert_load')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_key_load')
    def test_010_ca_load(self, mock_key, mock_cert):
        """ CAhandler._ca_load for cert only """
        mock_key.return_value = 'key'
        mock_cert.return_value = (None, None)
        self.assertEqual(('key', None, None), self.cahandler._ca_load())

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_cert_load')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_key_load')
    def test_011_ca_load(self, mock_key, mock_cert):
        """ CAhandler._ca_load without key and cert """
        mock_key.return_value = None
        mock_cert.return_value = (None, None)
        self.assertEqual((None, None, None), self.cahandler._ca_load())

    def test_012_ca_cert_load(self):
        """ CAhandler._ca_cert_load """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        self.assertTrue(self.cahandler._ca_cert_load())

    def test_013_ca_cert_load(self):
        """ CAhandler._ca_cert_load for non existing cert """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'bar'
        self.assertEqual((None, None), self.cahandler._ca_cert_load())

    @patch('OpenSSL.crypto.load_certificate')
    def test_014_ca_cert_load(self, mock_certload):
        """ CAhandler._ca_cert_load """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        mock_certload.side_effect = Exception('exc_cert_load')
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertEqual((None, None, None), self.cahandler._ca_load())
        self.assertIn('ERROR:test_est:CAhandler._ca_cert_load() failed with error: exc_cert_load', lcm.output)

    def test_015_ca_key_load(self):
        """ CAhandler._ca_key_load """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_key = 'sub-ca'
        self.cahandler.passphrase = 'test1234'
        self.assertTrue(self.cahandler._ca_key_load())

    def test_016_ca_key_load(self):
        """ CAhandler._ca_key_load with wrong passphrase """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        self.cahandler.passphrase = 'wrongpw'
        self.assertFalse(self.cahandler._ca_key_load())

    def test_017_ca_key_load(self):
        """ CAhandler._ca_key_load without passphrase (should fail) """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        # self.cahandler.passphrase = 'wrongpw'
        self.assertFalse(self.cahandler._ca_key_load())

    @patch('OpenSSL.crypto.load_privatekey')
    def test_018_ca_key_load(self, mock_key):
        """ CAhandler._ca_key_load """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_key = 'sub-ca'
        self.cahandler.passphrase = 'test1234'
        mock_key.side_effect = Exception('exc_key_load')
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.cahandler._ca_key_load()
        self.assertIn('ERROR:test_est:CAhandler._ca_key_load() failed with error: exc_key_load', lcm.output)

    def test_019_csr_insert(self):
        """ CAhandler._csr_insert empty item dic """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        csr_dic = {}
        self.assertFalse(self.cahandler._csr_insert(csr_dic))

    def test_020_csr_insert(self):
        """ CAhandler._csr_insert full item dic """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        csr_dic = {'item': 2, 'signed': 0, 'request': 'request'}
        self.assertEqual(2, self.cahandler._csr_insert(csr_dic))

    def test_021_csr_insert(self):
        """ CAhandler._csr_insert full item dic item has wrong datatype """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        csr_dic = {'item': '2', 'signed': 0, 'request': 'request'}
        self.assertFalse(self.cahandler._csr_insert(csr_dic))

    def test_022_csr_insert(self):
        """ CAhandler._csr_insert full item dic item has wrong datatype """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        csr_dic = {'item': 2, 'signed': '0', 'request': 'request'}
        self.assertFalse(self.cahandler._csr_insert(csr_dic))

    def test_023_csr_insert(self):
        """ CAhandler._csr_insert item dic without item """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        csr_dic = {'signed': 0, 'request': 'request'}
        self.assertFalse(self.cahandler._csr_insert(csr_dic))

    def test_024_csr_insert(self):
        """ CAhandler._csr_insert item dic without signed """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        csr_dic = {'item': 2, 'request': 'request'}
        self.assertFalse(self.cahandler._csr_insert(csr_dic))

    def test_025_csr_insert(self):
        """ CAhandler._csr_insert item dic without request """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        csr_dic = {'item': 2, 'signed': 0}
        self.assertFalse(self.cahandler._csr_insert(csr_dic))

    def test_026_item_insert(self):
        """ CAhandler._item_insert empty item dic """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        item_dic = {}
        self.assertFalse(self.cahandler._item_insert(item_dic))

    def test_027_item_insert(self):
        """ CAhandler._item_insert full item dic """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        item_dic = {'name': 'name', 'type': 2, 'source': 0, 'date': 'date', 'comment': 'comment'}
        self.assertEqual(15, self.cahandler._item_insert(item_dic))

    def test_028_item_insert(self):
        """ CAhandler._item_insert no name """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        item_dic = {'type': 2, 'source': 0, 'date': 'date', 'comment': 'comment'}
        self.assertFalse(self.cahandler._item_insert(item_dic))

    def test_029_item_insert(self):
        """ CAhandler._item_insert no type """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        item_dic = {'name': 'name', 'source': 0, 'date': 'date', 'comment': 'comment'}
        self.assertFalse(self.cahandler._item_insert(item_dic))

    def test_030_item_insert(self):
        """ CAhandler._item_insert no siurce """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        item_dic = {'name': 'name', 'item': 2, 'date': 'date', 'comment': 'comment'}
        self.assertFalse(self.cahandler._item_insert(item_dic))

    def test_031_item_insert(self):
        """ CAhandler._item_insert no date  """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        item_dic = {'name': 'name', 'type': 2, 'source': 0, 'comment': 'comment'}
        self.assertFalse(self.cahandler._item_insert(item_dic))

    def test_032_item_insert(self):
        """ CAhandler._item_insert no date  """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        item_dic = {'name': 'name', 'type': 2, 'source': 0, 'date': 'date'}
        self.assertFalse(self.cahandler._item_insert(item_dic))

    def test_033_item_insert(self):
        """ CAhandler._item_insert full item dic type has wrong datatype """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        item_dic = {'name': 'name', 'type': '2', 'source': 0, 'date': 'date', 'comment': 'comment'}
        self.assertFalse(self.cahandler._item_insert(item_dic))

    def test_034_item_insert(self):
        """ CAhandler._item_insert full item dic source has wrong datatype """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.issuing_ca_name = 'sub-ca'
        item_dic = {'name': 'name', 'type': 2, 'source': '0', 'date': 'date', 'comment': 'comment'}
        self.assertFalse(self.cahandler._item_insert(item_dic))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._csr_search')
    def test_035_csr_import(self, mock_search):
        """ CAhandler._csr_import with existing cert_dic """
        mock_search.return_value = {'foo', 'bar'}
        self.assertEqual({'foo', 'bar'}, self.cahandler._csr_import('csr', 'request_name'))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._item_insert')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._csr_insert')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._csr_search')
    def test_036_csr_import(self, mock_search, mock_csr_insert, mock_item_insert):
        """ CAhandler._csr_import with existing cert_dic """
        mock_search.return_value = {}
        mock_csr_insert.return_value = 5
        mock_item_insert.return_value = 10
        self.assertEqual({'item': 10, 'signed': 1, 'request': 'csr'}, self.cahandler._csr_import('csr', 'request_name'))

    def test_037_cert_insert(self):
        """ CAhandler._csr_import with empty cert_dic """
        cert_dic = {}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._cert_insert(cert_dic))
        error = "ERROR:test_est:CAhandler._cert_insert() aborted. dataset empty"
        self.assertIn(error, lcm.output)

    def test_038_cert_insert(self):
        """ CAhandler._csr_import item missing """
        cert_dic = {'serial': 'serial', 'issuer': 'issuer', 'ca': 'ca', 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._cert_insert(cert_dic))
        error = "ERROR:test_est:CAhandler._cert_insert() aborted. dataset incomplete: {'serial': 'serial', 'issuer': 'issuer', 'ca': 'ca', 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}"
        self.assertIn(error, lcm.output)

    def test_039_cert_insert(self):
        """ CAhandler._csr_import serial missing """
        cert_dic = {'item': 'item', 'issuer': 'issuer', 'ca': 'ca', 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._cert_insert(cert_dic))
        error = "ERROR:test_est:CAhandler._cert_insert() aborted. dataset incomplete: {'item': 'item', 'issuer': 'issuer', 'ca': 'ca', 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}"
        self.assertIn(error, lcm.output)

    def test_040_cert_insert(self):
        """ CAhandler._csr_import issuer missing """
        cert_dic = {'item': 'item', 'serial': 'serial', 'ca': 'ca', 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._cert_insert(cert_dic))
        error = "ERROR:test_est:CAhandler._cert_insert() aborted. dataset incomplete: {'item': 'item', 'serial': 'serial', 'ca': 'ca', 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}"
        self.assertIn(error, lcm.output)

    def test_041_cert_insert(self):
        """ CAhandler._csr_import ca missing """
        cert_dic = {'item': 'item', 'serial': 'serial', 'issuer': 'issuer', 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._cert_insert(cert_dic))
        error = "ERROR:test_est:CAhandler._cert_insert() aborted. dataset incomplete: {'item': 'item', 'serial': 'serial', 'issuer': 'issuer', 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}"
        self.assertIn(error, lcm.output)

    def test_042_cert_insert(self):
        """ CAhandler._csr_import cert missing """
        cert_dic = {'item': 'item', 'serial': 'serial', 'issuer': 'issuer', 'ca': 'ca', 'iss_hash': 'iss_hash', 'hash': 'hash'}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._cert_insert(cert_dic))
        error = "ERROR:test_est:CAhandler._cert_insert() aborted. dataset incomplete: {'item': 'item', 'serial': 'serial', 'issuer': 'issuer', 'ca': 'ca', 'iss_hash': 'iss_hash', 'hash': 'hash'}"
        self.assertIn(error, lcm.output)

    def test_043_cert_insert(self):
        """ CAhandler._csr_import iss_hash missing """
        cert_dic = {'item': 'item', 'serial': 'serial', 'issuer': 'issuer', 'ca': 'ca', 'cert': 'cert', 'hash': 'hash'}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._cert_insert(cert_dic))
        error = "ERROR:test_est:CAhandler._cert_insert() aborted. dataset incomplete: {'item': 'item', 'serial': 'serial', 'issuer': 'issuer', 'ca': 'ca', 'cert': 'cert', 'hash': 'hash'}"
        self.assertIn(error, lcm.output)

    def test_044_cert_insert(self):
        """ CAhandler._csr_import hash missing """
        cert_dic = {'item': 'item', 'serial': 'serial', 'issuer': 'issuer', 'ca': 'ca', 'cert': 'cert', 'iss_hash': 'iss_hash'}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._cert_insert(cert_dic))
        error = "ERROR:test_est:CAhandler._cert_insert() aborted. dataset incomplete: {'item': 'item', 'serial': 'serial', 'issuer': 'issuer', 'ca': 'ca', 'cert': 'cert', 'iss_hash': 'iss_hash'}"
        self.assertIn(error, lcm.output)

    def test_045_cert_insert(self):
        """ CAhandler._csr_import with item not int """
        cert_dic = {'item': 'item', 'serial': 'serial', 'issuer': 'issuer', 'ca': 'ca', 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._cert_insert(cert_dic))
        error = "ERROR:test_est:CAhandler._cert_insert() aborted. wrong datatypes: {'item': 'item', 'serial': 'serial', 'issuer': 'issuer', 'ca': 'ca', 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}"
        self.assertIn(error, lcm.output)

    def test_046_cert_insert(self):
        """ CAhandler._csr_import with issuer not int """
        cert_dic = {'item': 1, 'serial': 'serial', 'issuer': 'issuer', 'ca': 'ca', 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._cert_insert(cert_dic))
        error = "ERROR:test_est:CAhandler._cert_insert() aborted. wrong datatypes: {'item': 1, 'serial': 'serial', 'issuer': 'issuer', 'ca': 'ca', 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}"
        self.assertIn(error, lcm.output)

    def test_047_cert_insert(self):
        """ CAhandler._csr_import with ca not int """
        cert_dic = {'item': 1, 'serial': 'serial', 'issuer': 1, 'ca': 'ca', 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._cert_insert(cert_dic))
        error = "ERROR:test_est:CAhandler._cert_insert() aborted. wrong datatypes: {'item': 1, 'serial': 'serial', 'issuer': 1, 'ca': 'ca', 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}"
        self.assertIn(error, lcm.output)

    def test_048_cert_insert(self):
        """ CAhandler._csr_import with iss_hash not int """
        cert_dic = {'item': 1, 'serial': 'serial', 'issuer': 2, 'ca': 3, 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._cert_insert(cert_dic))
        error = "ERROR:test_est:CAhandler._cert_insert() aborted. wrong datatypes: {'item': 1, 'serial': 'serial', 'issuer': 2, 'ca': 3, 'cert': 'cert', 'iss_hash': 'iss_hash', 'hash': 'hash'}"
        self.assertIn(error, lcm.output)

    def test_049_cert_insert(self):
        """ CAhandler._csr_import with hash not int """
        cert_dic = {'item': 1, 'serial': 'serial', 'issuer': 2, 'ca': 3, 'cert': 'cert', 'iss_hash': 4, 'hash': 'hash'}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._cert_insert(cert_dic))
        error = "ERROR:test_est:CAhandler._cert_insert() aborted. wrong datatypes: {'item': 1, 'serial': 'serial', 'issuer': 2, 'ca': 3, 'cert': 'cert', 'iss_hash': 4, 'hash': 'hash'}"
        self.assertIn(error, lcm.output)

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._db_close')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._db_open')
    def test_050_cert_insert(self, mock_open, mock_close):
        """ CAhandler._csr_import with hash not int """
        cert_dic = {'item': 1, 'serial': 'serial', 'issuer': 2, 'ca': 3, 'cert': 'cert', 'iss_hash': 4, 'hash': 5}
        mock_open.return_value = True
        mock_close.return_value = True
        self.cahandler.cursor = Mock()
        self.cahandler.cursor.lastrowid = 5
        self.assertEqual(5, self.cahandler._cert_insert(cert_dic))
        self.assertTrue(mock_open.called)
        self.assertTrue(mock_close.called)

    def test_051_pemcertchain_generate(self):
        """ CAhandler._pemcertchain_generate no certificates """
        ee_cert = None
        issuer_cert = None
        self.cahandler.ca_cert_chain_list = []
        self.assertFalse(self.cahandler._pemcertchain_generate(ee_cert, issuer_cert))

    def test_052_pemcertchain_generate(self):
        """ CAhandler._pemcertchain_generate no issuer """
        ee_cert = 'ee_cert'
        issuer_cert = None
        self.cahandler.ca_cert_chain_list = []
        self.assertEqual('ee_cert', self.cahandler._pemcertchain_generate(ee_cert, issuer_cert))

    def test_053_pemcertchain_generate(self):
        """ CAhandler._pemcertchain_generate no ca chain """
        ee_cert = 'ee_cert'
        issuer_cert = 'issuer_cert'
        self.cahandler.ca_cert_chain_list = []
        self.assertEqual('ee_certissuer_cert', self.cahandler._pemcertchain_generate(ee_cert, issuer_cert))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._cert_search')
    @patch('OpenSSL.crypto.load_certificate')
    def test_054_pemcertchain_generate(self, mock_cert, mock_search):
        """ CAhandler._pemcertchain_generate empty cert dic in ca_chain """
        ee_cert = 'ee_cert'
        issuer_cert = 'issuer_cert'
        self.cahandler.ca_cert_chain_list = ['foo_bar']
        mock_search.return_value = None
        mock_cert.side_effect = ['foo', 'bar']
        self.assertEqual('ee_certissuer_cert', self.cahandler._pemcertchain_generate(ee_cert, issuer_cert))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._cert_search')
    @patch('OpenSSL.crypto.load_certificate')
    def test_055_pemcertchain_generate(self, mock_cert, mock_search):
        """ CAhandler._pemcertchain_generate empty no cert in chain """
        ee_cert = 'ee_cert'
        issuer_cert = 'issuer_cert'
        self.cahandler.ca_cert_chain_list = ['foo_bar']
        mock_search.return_value = {'foo', 'bar'}
        mock_cert.side_effect = ['foo', 'bar']
        self.assertEqual('ee_certissuer_cert', self.cahandler._pemcertchain_generate(ee_cert, issuer_cert))

    @patch('examples.ca_handler.xca_ca_handler.b64_decode')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._cert_search')
    @patch('OpenSSL.crypto.load_certificate')
    @patch('OpenSSL.crypto.dump_certificate')
    def test_056_pemcertchain_generate(self, mock_dump, mock_load, mock_search, mock_b64dec):
        """ CAhandler._pemcertchain_generate one cert in chain """
        ee_cert = 'ee_cert'
        issuer_cert = 'issuer_cert'
        self.cahandler.ca_cert_chain_list = ['foo_bar']
        mock_search.return_value = {'cert': 'foo'}
        mock_load.return_value = 'foo'
        mock_dump.side_effect = ['foo1']
        mock_b64dec.return_value = 'b64dec'
        self.assertEqual('ee_certissuer_certfoo1', self.cahandler._pemcertchain_generate(ee_cert, issuer_cert))

    @patch('examples.ca_handler.xca_ca_handler.b64_decode')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._cert_search')
    @patch('OpenSSL.crypto.load_certificate')
    @patch('OpenSSL.crypto.dump_certificate')
    def test_057_pemcertchain_generate(self, mock_dump, mock_load, mock_search, mock_b64dec):
        """ CAhandler._pemcertchain_generate two certs in chain """
        ee_cert = 'ee_cert'
        issuer_cert = 'issuer_cert'
        self.cahandler.ca_cert_chain_list = ['foo_bar', 'foo_bar']
        mock_search.return_value = {'cert': 'foo'}
        mock_load.return_value = 'foo'
        mock_dump.side_effect = ['foo1', 'foo2']
        mock_b64dec.return_value = 'b64dec'
        self.assertEqual('ee_certissuer_certfoo1foo2', self.cahandler._pemcertchain_generate(ee_cert, issuer_cert))

    @patch('examples.ca_handler.xca_ca_handler.csr_cn_get')
    def test_058_requestname_get(self, mock_cn):
        """ CAhandler._requestname_get from cn """
        mock_cn.return_value = 'foo'
        self.assertEqual('foo', self.cahandler._requestname_get('csr'))

    @patch('examples.ca_handler.xca_ca_handler.csr_san_get')
    @patch('examples.ca_handler.xca_ca_handler.csr_cn_get')
    def test_059_requestname_get(self, mock_cn, mock_san):
        """ CAhandler._requestname_get empty cn empty san"""
        mock_cn.return_value = None
        mock_san.return_value = []
        self.assertFalse(self.cahandler._requestname_get('csr'))

    @patch('examples.ca_handler.xca_ca_handler.csr_san_get')
    @patch('examples.ca_handler.xca_ca_handler.csr_cn_get')
    def test_060_requestname_get(self, mock_cn, mock_san):
        """ CAhandler._requestname_get empty cn empty dsmaged san"""
        mock_cn.return_value = None
        mock_san.return_value = ['foo']
        self.assertFalse(self.cahandler._requestname_get('csr'))

    @patch('examples.ca_handler.xca_ca_handler.csr_san_get')
    @patch('examples.ca_handler.xca_ca_handler.csr_cn_get')
    def test_061_requestname_get(self, mock_cn, mock_san):
        """ CAhandler._requestname_get empty cn empty dsmaged san"""
        mock_cn.return_value = None
        mock_san.return_value = ['dns:foo']
        self.assertEqual('foo', self.cahandler._requestname_get('csr'))

    @patch('examples.ca_handler.xca_ca_handler.csr_san_get')
    @patch('examples.ca_handler.xca_ca_handler.csr_cn_get')
    def test_062_requestname_get(self, mock_cn, mock_san):
        """ CAhandler._requestname_get empty cn empty dsmaged san"""
        mock_cn.return_value = None
        mock_san.return_value = ['dns:foo', 'bar']
        self.assertEqual('foo', self.cahandler._requestname_get('csr'))

    def test_063_cert_insert(self):
        """ CAhandler._revocation_insert with empty rev_dic """
        rev_dic = {}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._revocation_insert(rev_dic))
        error = 'ERROR:test_est:CAhandler._revocation_insert() aborted. dataset empty'
        self.assertIn(error, lcm.output)

    def test_064_cert_insert(self):
        """ CAhandler._revocation_insert no caID """
        rev_dic = {'serial': 'serial', 'date': 'date', 'invaldate': 'invaldate', 'reasonBit': 0}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._revocation_insert(rev_dic))
        error = "ERROR:test_est:CAhandler._revocation_insert() aborted. dataset incomplete: {'serial': 'serial', 'date': 'date', 'invaldate': 'invaldate', 'reasonBit': 0}"
        self.assertIn(error, lcm.output)

    def test_065_cert_insert(self):
        """ CAhandler._revocation_insert no serial """
        rev_dic = {'caID': 4, 'date': 'date', 'invaldate': 'invaldate', 'reasonBit': 0}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._revocation_insert(rev_dic))
        error = "ERROR:test_est:CAhandler._revocation_insert() aborted. dataset incomplete: {'caID': 4, 'date': 'date', 'invaldate': 'invaldate', 'reasonBit': 0}"
        self.assertIn(error, lcm.output)

    def test_066_cert_insert(self):
        """ CAhandler._revocation_insert no date """
        rev_dic = {'caID': 4, 'serial': 'serial', 'invaldate': 'invaldate', 'reasonBit': 0}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._revocation_insert(rev_dic))
        error = "ERROR:test_est:CAhandler._revocation_insert() aborted. dataset incomplete: {'caID': 4, 'serial': 'serial', 'invaldate': 'invaldate', 'reasonBit': 0}"
        self.assertIn(error, lcm.output)

    def test_067_cert_insert(self):
        """ CAhandler._revocation_insert no invaldate """
        rev_dic = {'caID': 4, 'serial': 'serial', 'date': 'date', 'reasonBit': 0}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._revocation_insert(rev_dic))
        error = "ERROR:test_est:CAhandler._revocation_insert() aborted. dataset incomplete: {'caID': 4, 'serial': 'serial', 'date': 'date', 'reasonBit': 0}"
        self.assertIn(error, lcm.output)

    def test_068_cert_insert(self):
        """ CAhandler._revocation_insert no resonBit """
        rev_dic = {'caID': 4, 'serial': 'serial', 'date': 'date', 'invaldate': 'invaldate'}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._revocation_insert(rev_dic))
        error = "ERROR:test_est:CAhandler._revocation_insert() aborted. dataset incomplete: {'caID': 4, 'serial': 'serial', 'date': 'date', 'invaldate': 'invaldate'}"
        self.assertIn(error, lcm.output)

    def test_069_cert_insert(self):
        """ CAhandler._revocation_insert with caID is not int """
        rev_dic = {'caID': 'caID', 'serial': 'serial', 'date': 'date', 'invaldate': 'invaldate', 'reasonBit': 0}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._revocation_insert(rev_dic))
        error = "ERROR:test_est:CAhandler._revocation_insert() aborted. wrong datatypes: {'caID': 'caID', 'serial': 'serial', 'date': 'date', 'invaldate': 'invaldate', 'reasonBit': 0}"
        self.assertIn(error, lcm.output)

    def test_070_cert_insert(self):
        """ CAhandler._revocation_insert with caID is not int """
        rev_dic = {'caID': 0, 'serial': 'serial', 'date': 'date', 'invaldate': 'invaldate', 'reasonBit': '0'}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertFalse(self.cahandler._revocation_insert(rev_dic))
        error = "ERROR:test_est:CAhandler._revocation_insert() aborted. wrong datatypes: {'caID': 0, 'serial': 'serial', 'date': 'date', 'invaldate': 'invaldate', 'reasonBit': '0'}"
        self.assertIn(error, lcm.output)

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._db_close')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._db_open')
    def test_071_rev_insert(self, mock_open, mock_close):
        """ CAhandler._revocation_insert with caID is not inall okt """
        mock_close.return_value = True
        self.cahandler.cursor = Mock()
        self.cahandler.cursor.lastrowid = 5
        rev_dic = {'caID': 0, 'serial': 'serial', 'date': 'date', 'invaldate': 'invaldate', 'reasonBit': 0}
        self.assertEqual(5, self.cahandler._revocation_insert(rev_dic))
        self.assertTrue(mock_open.called)
        self.assertTrue(mock_close.called)

    @patch('examples.ca_handler.xca_ca_handler.uts_to_date_utc')
    def test_072_revoke(self, mock_date):
        """ CAhandler.revocation without xdb file """
        mock_date.return_value = 'foo'
        self.assertEqual((500, 'urn:ietf:params:acme:error:serverInternal', 'configuration error'), self.cahandler.revoke('cert', 'reason', None))

    @patch('examples.ca_handler.xca_ca_handler.cert_serial_get')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_load')
    @patch('examples.ca_handler.xca_ca_handler.uts_to_date_utc')
    def test_073_revoke(self, mock_date, mock_ca, mock_serial):
        """ CAhandler.revocation no CA ID """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        mock_date.return_value = 'foo'
        mock_ca.return_value = ('key', 'cert', None)
        mock_serial.return_value = 1000
        self.assertEqual((500, 'urn:ietf:params:acme:error:serverInternal', 'certificate lookup failed'), self.cahandler.revoke('cert', 'reason', None))

    @patch('examples.ca_handler.xca_ca_handler.cert_serial_get')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_load')
    @patch('examples.ca_handler.xca_ca_handler.uts_to_date_utc')
    def test_074_revoke(self, mock_date, mock_ca, mock_serial):
        """ CAhandler.revocation no serial """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        mock_date.return_value = 'foo'
        mock_ca.return_value = ('key', 'cert', 2)
        mock_serial.return_value = None
        self.assertEqual((500, 'urn:ietf:params:acme:error:serverInternal', 'certificate lookup failed'), self.cahandler.revoke('cert', 'reason', None))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._revocation_search')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._revocation_insert')
    @patch('examples.ca_handler.xca_ca_handler.cert_serial_get')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_load')
    @patch('examples.ca_handler.xca_ca_handler.uts_to_date_utc')
    def test_075_revoke(self, mock_date, mock_ca, mock_serial, mock_rev_insert, mock_search):
        """ CAhandler.revocation no serial """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        mock_date.return_value = 'foo'
        mock_ca.return_value = ('key', 'cert', 2)
        mock_search.return_value = None
        mock_rev_insert.return_value = None
        mock_serial.return_value = 1000
        self.assertEqual((500, 'urn:ietf:params:acme:error:serverInternal', 'database update failed'), self.cahandler.revoke('cert', 'reason', None))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._revocation_search')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._revocation_insert')
    @patch('examples.ca_handler.xca_ca_handler.cert_serial_get')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_load')
    @patch('examples.ca_handler.xca_ca_handler.uts_to_date_utc')
    def test_076_revoke(self, mock_date, mock_ca, mock_serial, mock_rev_insert, mock_search):
        """ CAhandler.revocation no serial """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        mock_date.return_value = 'foo'
        mock_ca.return_value = ('key', 'cert', 2)
        mock_search.return_value = 'foo'
        mock_rev_insert.return_value = 20
        mock_serial.return_value = 1000
        self.assertEqual((400, 'urn:ietf:params:acme:error:alreadyRevoked', 'Certificate has already been revoked'), self.cahandler.revoke('cert', 'reason', None))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._revocation_search')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._revocation_insert')
    @patch('examples.ca_handler.xca_ca_handler.cert_serial_get')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_load')
    @patch('examples.ca_handler.xca_ca_handler.uts_to_date_utc')
    def test_077_revoke(self, mock_date, mock_ca, mock_serial, mock_rev_insert, mock_search):
        """ CAhandler.revocation no serial """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        mock_date.return_value = 'foo'
        mock_ca.return_value = ('key', 'cert', 2)
        mock_search.return_value = None
        mock_rev_insert.return_value = 20
        mock_serial.return_value = 1000
        self.assertEqual((200, None, None), self.cahandler.revoke('cert', 'reason', None))

    def test_078_cert_search(self):
        """ CAhandler._cert_sarch cert can be found """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        search_result = {'item': 6, 'hash': 1675584264, 'iss_hash': 1339028853, 'serial': '0BCC30C544EF26A4', 'issuer': 4, 'ca': 0, 'cert': 'MIIEQTCCAimgAwIBAgIIC8wwxUTvJqQwDQYJKoZIhvcNAQELBQAwETEPMA0GA1UEAxMGc3ViLWNhMB4XDTIwMDYwOTE3MTkwMFoXDTIxMDYwOTE3MTkwMFowGzEZMBcGA1UEAxMQY2xpZW50LmJhci5sb2NhbDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAJps2tk/d5pqv1gSeLnDBFQSzznY/iSBtzRNLlRWm6J7yOAERgGsbMBW7s5AhYRbuHuberlBtsyFyKenWvijo6r7DTOGiv2oBf7iCoCXYbNAqlvnP5inzp6ZmmgmxigLFbdlTfPQBkaytDzLAav1KLCmCof4DpQunsxdDjW0kBm8jRC7HY5bauxeFKQb2NcGmjlB3kQjZNHF52xG/GgkMIH7E0NJUhmsVfItSezkmFUQFhP2VqYYsiPRtvXlZqpzPISxn2InGcUaaBzJFO7RWif0IIsgzcyzqXvt8KEqeoI15gmd1G4lXPeyadXG8kzE8L+8f4J+gGgQSA1eR4VMkOMCAwEAAaOBkjCBjzAMBgNVHRMBAf8EAjAAMB0GA1UdDgQWBBRjovc4aaN6LCIE5E/ZgsLBH+3/WDAOBgNVHQ8BAf8EBAMCA+gwIAYDVR0lAQH/BBYwFAYIKwYBBQUHAwEGCCsGAQUFBwMCMBsGA1UdEQQUMBKCEGNsaWVudC5iYXIubG9jYWwwEQYJYIZIAYb4QgEBBAQDAgZAMA0GCSqGSIb3DQEBCwUAA4ICAQCZm5d3jc9oopD193bGwJFo8NNo1wzYvvqbK/lONy/JsisX1pERxN+EZyTB2CLxQ4yKZU9Xnx0fmcJExqoPLEva6hAMdOiSEsEs52yyL6gjMLHxJJfdXBiqMZetp+BCPf23rc96ONzyjURDCfsN4VMg7090e9yKpuyHKIOHStqMT+ZLvPcd+YiU4jMazoagauEW2mdpqyA8mN92qiphwo8QMCv3XZJWJ1PEwaCTGhBxlzMoaknWKzCD2YQ/yyGE4Ha8vBaymk1eh7txo5B53C0OpO0UT4WGUOZDP1GPySymqQfDO6R9BhBjyggsG5G9FA84tUqZJAKlGhPesQyIQBM4SZlQTJt/hP/cCoZ6BiibBdaZnLzOyH+NTJ9ou0hpmMp2LZiB8G2Igam7wdXySvQe9sxXXDDTKhxwqk7V+by2gS6asfcQjstQQeMN/iMrg3AtZt/Kl5WcHcwSjZAypHugPiwjr48WHvDS2lUKnbbDuiCxvc1TsPGG6Z+b/0aTwrps6yMeTRuDk3A8DYceHftrWZSOgg+5A2ISd58vPOHiamATVLXGJ1vnCP0Sm/Z4QCnIGfOvxltdAnrcA75MnefaOmQv9CrhwyBembugd9fPC/uFi/ESKGPuo6zLYwjFwLqwNe99UgU98iYz9rfdKNqJ6fWRolzz4AXqUHQ4Dc8eZA=='}
        self.assertEqual(search_result, self.cahandler._cert_search('name', 'client'))

    def test_079_cert_search(self):
        """ CAhandler._cert_sarch cert failed """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.assertFalse(self.cahandler._cert_search('name', 'client_failed'))

    def test_080_cert_search(self):
        """ CAhandler._cert_sarch item search succ / cert_search failed """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.assertFalse(self.cahandler._cert_search('name', 'item_no_cert'))

    @patch('examples.ca_handler.xca_ca_handler.config_load')
    def test_081_config_load(self, mock_load_cfg):
        """ test _config_load - ca_chain is not json format """
        mock_load_cfg.return_value = {'CAhandler': {'ca_cert_chain_list': '[foo]'}}
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.cahandler._config_load()
        self.assertFalse(self.cahandler.ca_cert_chain_list)
        self.assertIn('ERROR:test_est:CAhandler._config_load(): parameter "ca_cert_chain_list" cannot be loaded: Expecting value: line 1 column 2 (char 1)', lcm.output)

    @patch('examples.ca_handler.xca_ca_handler.config_load')
    def test_082_config_load(self, mock_load_cfg):
        """ test _config_load - load template """
        mock_load_cfg.return_value = {'CAhandler': {'template_name': 'foo'}}
        self.cahandler._config_load()
        self.assertEqual('foo', self.cahandler.template_name)

    @patch('examples.ca_handler.xca_ca_handler.config_load')
    def test_083_config_load(self, mock_load_cfg):
        """ test _config_load - load template """
        mock_load_cfg.return_value = {'CAhandler': {'xdb_file': 'foo'}}
        self.cahandler._config_load()
        self.assertEqual('foo', self.cahandler.xdb_file)

    @patch('examples.ca_handler.xca_ca_handler.config_load')
    def test_084_config_load(self, mock_load_cfg):
        """ test _config_load - load template """
        mock_load_cfg.return_value = {'CAhandler': {'passphrase': 'foo'}}
        self.cahandler._config_load()
        self.assertEqual('foo', self.cahandler.passphrase)

    @patch('examples.ca_handler.xca_ca_handler.config_load')
    def test_085_config_load(self, mock_load_cfg):
        """ test _config_load - load template """
        mock_load_cfg.return_value = {'CAhandler': {'issuing_ca_name': 'foo'}}
        self.cahandler._config_load()
        self.assertEqual('foo', self.cahandler.issuing_ca_name)

    @patch('examples.ca_handler.xca_ca_handler.config_load')
    def test_086_config_load(self, mock_load_cfg):
        """ test _config_load - load template """
        mock_load_cfg.return_value = {'CAhandler': {'issuing_ca_key': 'foo'}}
        self.cahandler._config_load()
        self.assertEqual('foo', self.cahandler.issuing_ca_key)

    def test_087_stream_split(self):
        """ test stream_split - all ok """
        byte_stream = b'before\x00\x00\x00\x0cafter'
        self.assertEqual((b'before\x00\x00\x00\x0c', b'after'), self.cahandler._stream_split(byte_stream))

    def test_088_stream_split(self):
        """ test stream_split - no bytestream """
        byte_stream = None
        self.assertEqual((None, None), self.cahandler._stream_split(byte_stream))

    def test_089_stream_split(self):
        """ test stream_split - no match """
        byte_stream = b'foofoobar'
        self.assertEqual((None, None), self.cahandler._stream_split(byte_stream))

    def test_090_stream_split(self):
        """ test stream_split - start with match match """
        byte_stream = b'\x00\x00\x00\x0cafter'
        self.assertEqual((b'\x00\x00\x00\x0c', b'after'), self.cahandler._stream_split(byte_stream))

    def test_091__utf_stream_parse(self):
        """ test _utf_stream_parse()  - all ok """
        utf_stream = b'foo\x00\x00\x00bar'
        self.assertEqual(({'foo': 'ar'}), self.cahandler._utf_stream_parse(utf_stream))

    def test_092__utf_stream_parse(self):
        """ test _utf_stream_parse()  - two parameter """
        utf_stream = b'foo1\x00\x00\x00_bar1\x00\x00\x00_foo2\x00\x00\x00_bar2'
        self.assertEqual(({'foo1': 'bar1', 'foo2': 'bar2'}), self.cahandler._utf_stream_parse(utf_stream))

    def test_093__utf_stream_parse(self):
        """ test _utf_stream_parse()  - non even parameter """
        utf_stream = b'foo1\x00\x00\x00_bar1\x00\x00\x00_foo2'
        self.assertEqual(({'foo1': 'bar1'}), self.cahandler._utf_stream_parse(utf_stream))

    def test_094__utf_stream_parse(self):
        """ test _utf_stream_parse()  - replace single \x00 in list key """
        utf_stream = b'f\x00oo1\x00\x00\x00_bar1\x00\x00\x00_foo2'
        self.assertEqual(({'foo1': 'bar1'}), self.cahandler._utf_stream_parse(utf_stream))

    def test_095__utf_stream_parse(self):
        """ test _utf_stream_parse()  - replace multiple \x00 in list key """
        utf_stream = b'f\x00o\x00o\x001\x00\x00\x00_bar1\x00\x00\x00_foo2'
        self.assertEqual(({'foo1': 'bar1'}), self.cahandler._utf_stream_parse(utf_stream))

    def test_096__utf_stream_parse(self):
        """ test _utf_stream_parse()  - replace single \x00 in list value """
        utf_stream = b'foo1\x00\x00\x00_b\x00ar1\x00\x00\x00_foo2'
        self.assertEqual(({'foo1': 'bar1'}), self.cahandler._utf_stream_parse(utf_stream))

    def test_097__utf_stream_parse(self):
        """ test _utf_stream_parse()  - replace multiple \x00 in list value """
        utf_stream = b'foo\x001\x00\x00\x00_b\x00a\x00r1\x00\x00\x00_foo2'
        self.assertEqual(({'foo1': 'bar1'}), self.cahandler._utf_stream_parse(utf_stream))

    def test_098__utf_stream_parse(self):
        """ test _utf_stream_parse()  - no utf_stream """
        utf_stream = None
        self.assertFalse(self.cahandler._utf_stream_parse(utf_stream))

    def test_099__ans1_stream_parse(self):
        """ test _ans1_stream_parse  - with country """
        asn1_stream = b'12345678foo\x06\x03\x55\x04\x06\02fco'
        self.assertEqual(({'countryName': 'co'}), self.cahandler._asn1_stream_parse(asn1_stream))

    def test_100__ans1_stream_parse(self):
        """ test _ans1_stream_parse  - country, loc """
        asn1_stream = b'12345678foo\x06\x03\x55\x04\x06\02fco\x06\x03\x55\x04\x07\03floc'
        self.assertEqual(({'countryName': 'co', 'localityName': 'loc'}), self.cahandler._asn1_stream_parse(asn1_stream))

    def test_101__ans1_stream_parse(self):
        """ test _ans1_stream_parse  - country, lo, state """
        asn1_stream = b'12345678foo\x06\x03\x55\x04\x06\02fco\x06\x03\x55\x04\x07\03floc\x06\x03\x55\x04\x08\05fstate'
        self.assertEqual(({'countryName': 'co', 'localityName': 'loc', 'stateOrProvinceName': 'state'}), self.cahandler._asn1_stream_parse(asn1_stream))

    def test_102__ans1_stream_parse(self):
        """ test _ans1_stream_parse  - country, loc, state, org """
        asn1_stream = b'12345678foo\x06\x03\x55\x04\x06\02fco\x06\x03\x55\x04\x07\03floc\x06\x03\x55\x04\x08\05fstate\x06\x03\x55\x04\x0a\03forg'
        self.assertEqual(({'countryName': 'co', 'localityName': 'loc', 'stateOrProvinceName': 'state', 'organizationName': 'org'}), self.cahandler._asn1_stream_parse(asn1_stream))

    def test_103__ans1_stream_parse(self):
        """ test _ans1_stream_parse  - country, loc, state, org, ou """
        asn1_stream = b'12345678foo\x06\x03\x55\x04\x06\02fco\x06\x03\x55\x04\x07\03floc\x06\x03\x55\x04\x08\05fstate\x06\x03\x55\x04\x0a\03forg\x06\x03\x55\x04\x0b\02fou'
        self.assertEqual(({'countryName': 'co', 'localityName': 'loc', 'stateOrProvinceName': 'state', 'organizationName': 'org', 'organizationalUnitName': 'ou'}), self.cahandler._asn1_stream_parse(asn1_stream))

    def test_104__ans1_stream_parse(self):
        """ test _ans1_stream_parse  - extralong value """
        asn1_stream = b'12345678foo\x06\x03\x55\x04\x07\x11flllllllllllllllll'
        self.assertEqual(({'localityName': 'lllllllllllllllll'}), self.cahandler._asn1_stream_parse(asn1_stream))

    def test_105__ans1_stream_parse(self):
        """ test _ans1_stream_parse - empty stream """
        asn1_stream = None
        self.assertFalse(self.cahandler._asn1_stream_parse(asn1_stream))

    def test_106__ans1_stream_parse(self):
        """ test _ans1_stream_parse - too short """
        asn1_stream = b'123456'
        self.assertFalse(self.cahandler._asn1_stream_parse(asn1_stream))

    def test_107__ans1_stream_parse(self):
        """ test _ans1_stream_parse  - country, non existing value in beteeen """
        asn1_stream = b'12345678foo\x06\x03\x55\x04\x06\02fco\x06\x03\x55\x05\x07\03floc'
        self.assertEqual(({'countryName': 'co'}), self.cahandler._asn1_stream_parse(asn1_stream))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._validity_calculate')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._utf_stream_parse')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._asn1_stream_parse')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._stream_split')
    def test_108__template_parse(self, mock_split, mock_asn, mock_utf, mock_valid):
        """ __template_parse() - all good """
        byte_string = 'foo'
        mock_split.return_value = (b'foo', b'bar')
        mock_asn.return_value = {'foo1': 'bar1'}
        mock_utf.return_value = {'foo2': 'bar2'}
        mock_valid.return_value = 'valid'
        self.assertEqual(({'foo1': 'bar1'}, {'foo2': 'bar2', 'validity': 'valid'}), self.cahandler._template_parse(byte_string))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._validity_calculate')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._utf_stream_parse')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._asn1_stream_parse')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._stream_split')
    def test_109__template_parse(self, mock_split, mock_asn, mock_utf, mock_valid):
        """ __template_parse() - multiple values """
        byte_string = 'foo'
        mock_split.return_value = (b'foo', b'bar')
        mock_asn.return_value = {'foo1': 'bar1', 'foo11': 'bar11'}
        mock_utf.return_value = {'foo2': 'bar2', 'foo21': 'bar21'}
        mock_valid.return_value = 'valid'
        self.assertEqual(({'foo1': 'bar1', 'foo11': 'bar11'}, {'foo2': 'bar2', 'foo21': 'bar21', 'validity': 'valid'}), self.cahandler._template_parse(byte_string))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._validity_calculate')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._utf_stream_parse')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._stream_split')
    def test_110__template_parse(self, mock_split, mock_utf, mock_valid):
        """ __template_parse() - no asn1_stream returned """
        byte_string = 'foo'
        mock_split.return_value = (None, b'bar')
        mock_utf.return_value = {'foo2': 'bar2'}
        mock_valid.return_value = 'valid'
        self.assertEqual(({}, {'foo2': 'bar2', 'validity': 'valid'}), self.cahandler._template_parse(byte_string))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._asn1_stream_parse')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._stream_split')
    def test_111__template_parse(self, mock_split, mock_asn):
        """ __template_parse() - no asn1_stream returned """
        byte_string = 'foo'
        mock_split.return_value = (b'foo', None)
        mock_asn.return_value = {'foo1': 'bar1'}
        self.assertEqual(({'foo1': 'bar1'}, {}), self.cahandler._template_parse(byte_string))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._stream_split')
    def test_112__template_parse(self, mock_split):
        """ __template_parse() - no asn1_stream returned """
        byte_string = 'foo'
        mock_split.return_value = (None, None)
        self.assertEqual(({}, {}), self.cahandler._template_parse(byte_string))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._validity_calculate')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._utf_stream_parse')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._asn1_stream_parse')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._stream_split')
    def test_113__template_parse(self, mock_split, mock_asn, mock_utf, mock_valid):
        """ __template_parse() - multiple values replace blank with None"""
        byte_string = 'foo'
        mock_split.return_value = (b'foo', b'bar')
        mock_asn.return_value = {'foo1': 'bar1', 'foo11': 'bar11'}
        mock_utf.return_value = {'foo2': 'bar2', 'foo21': ''}
        mock_valid.return_value = 'valid'
        self.assertEqual(({'foo1': 'bar1', 'foo11': 'bar11'}, {'foo2': 'bar2', 'foo21': None, 'validity': 'valid'}), self.cahandler._template_parse(byte_string))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._validity_calculate')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._utf_stream_parse')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._asn1_stream_parse')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._stream_split')
    def test_114__template_parse(self, mock_split, mock_asn, mock_utf, mock_valid):
        """ __template_parse() - multiple values replace blanks with None"""
        byte_string = 'foo'
        mock_split.return_value = (b'foo', b'bar')
        mock_asn.return_value = {'foo1': 'bar1', 'foo11': 'bar11'}
        mock_utf.return_value = {'foo2': 'bar2', 'foo21': '', 'foo22': ''}
        mock_valid.return_value = 'valid'
        self.assertEqual(({'foo1': 'bar1', 'foo11': 'bar11'}, {'foo2': 'bar2', 'foo21': None, 'foo22': None, 'validity': 'valid'}), self.cahandler._template_parse(byte_string))

    def test_115__template_load(self):
        """ CAhandler._templatelod - existing template  """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.template_name = 'template'
        dn_dic = {'countryName': 'co', 'stateOrProvinceName': 'prov', 'localityName': 'loc', 'organizationName': 'org', 'organizationalUnitName': 'ou'}
        template_dic = {'validity': 30, 'validN': '30', 'validMidn': '0', 'validM': '0', 'subKey': '0', 'subAltName': None, 'nsSslServerName': None, 'nsRevocationUrl': None, 'nsRenewalUrl': None, 'nsComment': 'xca certificate', 'nsCertType': '0', 'nsCaPolicyUrl': None, 'nsCARevocationUrl': None, 'nsBaseUrl': None, 'noWellDefinedExpDate': '0', 'kuCritical': '1', 'keyUse': '3', 'issAltName': None, 'ekuCritical': '1', 'eKeyUse': 'serverAuth, clientAuth', 'crlDist': None, 'ca': '0', 'bcCritical': '0', 'basicPath': None, 'authKey': '0', 'authInfAcc': None, 'adv_ext': None}
        self.assertEqual((dn_dic, template_dic), self.cahandler._template_load())

    def test_116__template_load(self):
        """ CAhandler._templatelod - not existing template  """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        self.cahandler.template_name = 'notexist'
        self.assertEqual(({}, {}), self.cahandler._template_load())

    def test_117__validity_calculate(self):
        """ CAhandler._validity_calculate() - day value """
        template_dic = {'validM': '0', 'validN': '10'}
        self.assertEqual(10, self.cahandler._validity_calculate(template_dic))

    def test_118__validity_calculate(self):
        """ CAhandler._validity_calculate() - month value """
        template_dic = {'validM': '1', 'validN': '10'}
        self.assertEqual(300, self.cahandler._validity_calculate(template_dic))

    def test_119__validity_calculate(self):
        """ CAhandler._validity_calculate() - year value """
        template_dic = {'validM': '2', 'validN': '2'}
        self.assertEqual(730, self.cahandler._validity_calculate(template_dic))

    def test_120__validity_calculate(self):
        """ CAhandler._validity_calculate() - novalidn """
        template_dic = {'validM': '2', 'novalidN': '2'}
        self.assertEqual(365, self.cahandler._validity_calculate(template_dic))

    def test_121__validity_calculate(self):
        """ CAhandler._validity_calculate() - novalidn """
        template_dic = {'novalidM': '2', 'validN': '2'}
        self.assertEqual(365, self.cahandler._validity_calculate(template_dic))

    def test_122__kue_generate(self):
        """ CAhandler._kue_generate() - digitalSignature """
        kup = 1
        self.assertEqual('digitalSignature', self.cahandler._kue_generate(kup))

    def test_123__kue_generate(self):
        """ CAhandler._kue_generate() - nonRepudiation """
        kup = 2
        self.assertEqual('nonRepudiation', self.cahandler._kue_generate(kup))

    def test_124__kue_generate(self):
        """ CAhandler._kue_generate() - keyEncipherment """
        kup = 4
        self.assertEqual('keyEncipherment', self.cahandler._kue_generate(kup))

    def test_125__kue_generate(self):
        """ CAhandler._kue_generate() - dataEncipherment """
        kup = 8
        self.assertEqual('dataEncipherment', self.cahandler._kue_generate(kup))

    def test_126__kue_generate(self):
        """ CAhandler._kue_generate() - keyAgreement """
        kup = 16
        self.assertEqual('keyAgreement', self.cahandler._kue_generate(kup))

    def test_127__kue_generate(self):
        """ CAhandler._kue_generate() - keyCertSign """
        kup = 32
        self.assertEqual('keyCertSign', self.cahandler._kue_generate(kup))

    def test_128__kue_generate(self):
        """ CAhandler._kue_generate() - cRLSign """
        kup = 64
        self.assertEqual('cRLSign', self.cahandler._kue_generate(kup))

    def test_129__kue_generate(self):
        """ CAhandler._kue_generate() - encipherOnly """
        kup = 128
        self.assertEqual('encipherOnly', self.cahandler._kue_generate(kup))

    def test_130__kue_generate(self):
        """ CAhandler._kue_generate() - encipherOnly """
        kup = 256
        self.assertEqual('decipherOnly', self.cahandler._kue_generate(kup))

    def test_131__kue_generate(self):
        """ CAhandler._kue_generate() - digitalSignature and nonRepudiation """
        kup = 3
        self.assertEqual('digitalSignature,nonRepudiation', self.cahandler._kue_generate(kup))

    def test_132__kue_generate(self):
        """ CAhandler._kue_generate() - all """
        kup = 511
        self.assertEqual('digitalSignature,nonRepudiation,keyEncipherment,dataEncipherment,keyAgreement,keyCertSign,cRLSign,encipherOnly,decipherOnly', self.cahandler._kue_generate(kup))

    def test_133__kue_generate(self):
        """ CAhandler._kue_generate() - all """
        kup = 0
        self.assertEqual('digitalSignature,nonRepudiation,keyEncipherment,keyAgreement', self.cahandler._kue_generate(kup))


    def test_134__subject_modify(self):
        """ CAhandler._subject_modify() empty dn_dic """
        dn_dic = {}
        subject = Mock()
        subject.CN = 'cn'
        subject.countryName = None
        subject.stateOrProvinceName = None
        subject.localityName = None
        subject.organizationName = None
        subject.organizationalUnitName = None
        rc_obj = self.cahandler._subject_modify(subject, dn_dic)
        self.assertEqual('cn', rc_obj.CN)
        self.assertFalse(rc_obj.countryName)
        self.assertFalse(rc_obj.stateOrProvinceName)
        self.assertFalse(rc_obj.localityName)
        self.assertFalse(rc_obj.organizationName)
        self.assertFalse(rc_obj.organizationalUnitName)

    def test_135__subject_modify(self):
        """ CAhandler._subject_modify() wrong dn_dic """
        dn_dic = {'foo': 'bar'}
        subject = Mock()
        subject.CN = 'cn'
        subject.countryName = None
        subject.stateOrProvinceName = None
        subject.localityName = None
        subject.organizationName = None
        subject.organizationalUnitName = None
        rc_obj = self.cahandler._subject_modify(subject, dn_dic)
        self.assertEqual('cn', rc_obj.CN)
        self.assertFalse(rc_obj.countryName)
        self.assertFalse(rc_obj.stateOrProvinceName)
        self.assertFalse(rc_obj.localityName)
        self.assertFalse(rc_obj.organizationName)
        self.assertFalse(rc_obj.organizationalUnitName)

    def test_136__subject_modify(self):
        """ CAhandler._subject_modify() c included """
        dn_dic = {'foo': 'bar', 'countryName': 'co'}
        subject = Mock()
        subject.CN = 'cn'
        subject.countryName = None
        subject.stateOrProvinceName = None
        subject.localityName = None
        subject.organizationName = None
        subject.organizationalUnitName = None
        rc_obj = self.cahandler._subject_modify(subject, dn_dic)
        self.assertEqual('cn', rc_obj.CN)
        self.assertEqual('co', rc_obj.countryName)
        self.assertFalse(rc_obj.stateOrProvinceName)
        self.assertFalse(rc_obj.localityName)
        self.assertFalse(rc_obj.organizationName)
        self.assertFalse(rc_obj.organizationalUnitName)

    def test_137__subject_modify(self):
        """ CAhandler._subject_modify() c, st included """
        dn_dic = {'foo': 'bar', 'countryName': 'co', 'stateOrProvinceName': 'st'}
        subject = Mock()
        subject.CN = 'cn'
        subject.countryName = None
        subject.stateOrProvinceName = None
        subject.localityName = None
        subject.organizationName = None
        subject.organizationalUnitName = None
        rc_obj = self.cahandler._subject_modify(subject, dn_dic)
        self.assertEqual('cn', rc_obj.CN)
        self.assertEqual('co', rc_obj.countryName)
        self.assertEqual('st', rc_obj.stateOrProvinceName)
        self.assertFalse(rc_obj.localityName)
        self.assertFalse(rc_obj.organizationName)
        self.assertFalse(rc_obj.organizationalUnitName)

    def test_138__subject_modify(self):
        """ CAhandler._subject_modify() c, st, l included """
        dn_dic = {'foo': 'bar', 'countryName': 'co', 'stateOrProvinceName': 'st', 'localityName': 'lo'}
        subject = Mock()
        subject.CN = 'cn'
        subject.countryName = None
        subject.stateOrProvinceName = None
        subject.localityName = None
        subject.organizationName = None
        subject.organizationalUnitName = None
        rc_obj = self.cahandler._subject_modify(subject, dn_dic)
        self.assertEqual('cn', rc_obj.CN)
        self.assertEqual('co', rc_obj.countryName)
        self.assertEqual('st', rc_obj.stateOrProvinceName)
        self.assertEqual('lo', rc_obj.localityName)
        self.assertFalse(rc_obj.organizationName)
        self.assertFalse(rc_obj.organizationalUnitName)

    def test_139__subject_modify(self):
        """ CAhandler._subject_modify() c, st, l, o included """
        dn_dic = {'foo': 'bar', 'countryName': 'co', 'stateOrProvinceName': 'st', 'localityName': 'lo', 'organizationName': 'or'}
        subject = Mock()
        subject.CN = 'cn'
        subject.countryName = None
        subject.stateOrProvinceName = None
        subject.localityName = None
        subject.organizationName = None
        subject.organizationalUnitName = None
        rc_obj = self.cahandler._subject_modify(subject, dn_dic)
        self.assertEqual('cn', rc_obj.CN)
        self.assertEqual('co', rc_obj.countryName)
        self.assertEqual('st', rc_obj.stateOrProvinceName)
        self.assertEqual('lo', rc_obj.localityName)
        self.assertEqual('or', rc_obj.organizationName)
        self.assertFalse(rc_obj.organizationalUnitName)

    def test_140__subject_modify(self):
        """ CAhandler._subject_modify() c, st, l, o included """
        dn_dic = {'foo': 'bar', 'countryName': 'co', 'stateOrProvinceName': 'st', 'localityName': 'lo', 'organizationName': 'or', 'organizationalUnitName': 'ou'}
        subject = Mock()
        subject.CN = 'cn'
        subject.countryName = None
        subject.stateOrProvinceName = None
        subject.localityName = None
        subject.organizationName = None
        subject.organizationalUnitName = None
        rc_obj = self.cahandler._subject_modify(subject, dn_dic)
        self.assertEqual('cn', rc_obj.CN)
        self.assertEqual('co', rc_obj.countryName)
        self.assertEqual('st', rc_obj.stateOrProvinceName)
        self.assertEqual('lo', rc_obj.localityName)
        self.assertEqual('or', rc_obj.organizationName)
        self.assertEqual('ou', rc_obj.organizationalUnitName)

    @patch('OpenSSL.crypto.X509Extension')
    def test_141__extension_list_generate(self, mock_crypto):
        """ CAhandler._extension_list_generate() - empty template """
        template_dic = {}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always'), (b'keyUsage', True, b'digitalSignature,keyEncipherment'), (b'basicConstraints', True, b'CA:FALSE'), (b'extendedKeyUsage', False, b'serverAuth')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('OpenSSL.crypto.X509Extension')
    def test_142__extension_list_generate(self, mock_crypto):
        """ CAhandler._extension_list_generate() - wrong template """
        template_dic = {'foo': 'bar'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('OpenSSL.crypto.X509Extension')
    def test_143__extension_list_generate(self, mock_crypto):
        """ CAhandler._extension_list_generate() - eKeyUse without ekuCritical """
        template_dic = {'foo': 'bar', 'eKeyUse': 'eKeyUse'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always'), (b'extendedKeyUsage', False, b'eKeyUse')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('OpenSSL.crypto.X509Extension')
    def test_144__extension_list_generate(self, mock_crypto):
        """ CAhandler._extension_list_generate() - eKeyUse with ekuCritical 0 """
        template_dic = {'foo': 'bar', 'eKeyUse': 'eKeyUse', 'ekuCritical': '0'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always'), (b'extendedKeyUsage', False, b'eKeyUse')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('OpenSSL.crypto.X509Extension')
    def test_145__extension_list_generate(self, mock_crypto):
        """ CAhandler._extension_list_generate() - eKeyUse with ekuCritical 1 """
        template_dic = {'foo': 'bar', 'eKeyUse': 'eKeyUse', 'ekuCritical': '1'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always'), (b'extendedKeyUsage', True, b'eKeyUse')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('OpenSSL.crypto.X509Extension')
    def test_146__extension_list_generate(self, mock_crypto):
        """ CAhandler._extension_list_generate() - eKeyUse with ekuCritical string """
        template_dic = {'foo': 'bar', 'eKeyUse': 'eKeyUse', 'ekuCritical': 'string'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always'), (b'extendedKeyUsage', False, b'eKeyUse')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._kue_generate')
    @patch('OpenSSL.crypto.X509Extension')
    def test_147__extension_list_generate(self, mock_crypto, mock_kue):
        """ CAhandler._extension_list_generate() - KeyUse without kuCritical """
        template_dic = {'foo': 'bar', 'keyUse': 'keyUse'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        mock_kue.return_value = 'kue'
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always'), (b'keyUsage', False, b'kue')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._kue_generate')
    @patch('OpenSSL.crypto.X509Extension')
    def test_148__extension_list_generate(self, mock_crypto, mock_kue):
        """ CAhandler._extension_list_generate() - KeyUse with kuCritical 0 """
        template_dic = {'foo': 'bar', 'keyUse': 'keyUse', 'kuCritical': '0'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        mock_kue.return_value = 'kue'
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always'), (b'keyUsage', False, b'kue')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._kue_generate')
    @patch('OpenSSL.crypto.X509Extension')
    def test_149__extension_list_generate(self, mock_crypto, mock_kue):
        """ CAhandler._extension_list_generate() - KeyUse with kuCritical 1 """
        template_dic = {'foo': 'bar', 'keyUse': 'keyUse', 'kuCritical': '1'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        mock_kue.return_value = 'kue'
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always'), (b'keyUsage', True, b'kue')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._kue_generate')
    @patch('OpenSSL.crypto.X509Extension')
    def test_150__extension_list_generate(self, mock_crypto, mock_kue):
        """ CAhandler._extension_list_generate() - KeyUse with kuCritical string """
        template_dic = {'foo': 'bar', 'keyUse': 'keyUse', 'kuCritical': 'string'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        mock_kue.return_value = 'kue'
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always'), (b'keyUsage', False, b'kue')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('OpenSSL.crypto.X509Extension')
    def test_151__extension_list_generate(self, mock_crypto):
        """ CAhandler._extension_list_generate() - eKeyUse with crlDist """
        template_dic = {'foo': 'bar', 'crlDist': 'crlDist'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always'), (b'crlDistributionPoints', False, b'crlDist')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('OpenSSL.crypto.X509Extension')
    def test_152__extension_list_generate(self, mock_crypto):
        """ CAhandler._extension_list_generate() - eKeyUse with crlDist but no value """
        template_dic = {'foo': 'bar', 'crlDist': None}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('OpenSSL.crypto.X509Extension')
    def test_153__extension_list_generate(self, mock_crypto):
        """ CAhandler._extension_list_generate() - basicConstrains without  bcCritical """
        template_dic = {'foo': 'bar', 'ca': '2'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always'), (b'basicConstraints', False, b'CA:FALSE')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('OpenSSL.crypto.X509Extension')
    def test_154__extension_list_generate(self, mock_crypto):
        """ CAhandler._extension_list_generate() - basicConstrains with  bcCritical 0 """
        template_dic = {'foo': 'bar', 'ca': '2', 'bcCritical': '0'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always'), (b'basicConstraints', False, b'CA:FALSE')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('OpenSSL.crypto.X509Extension')
    def test_155__extension_list_generate(self, mock_crypto):
        """ CAhandler._extension_list_generate() - basicConstrains with  bcCritical 1 """
        template_dic = {'foo': 'bar', 'ca': '2', 'bcCritical': '1'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always'), (b'basicConstraints', True, b'CA:FALSE')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('OpenSSL.crypto.X509Extension')
    def test_156__extension_list_generate(self, mock_crypto):
        """ CAhandler._extension_list_generate() - basicConstrains with  bcCritical string """
        template_dic = {'foo': 'bar', 'ca': '2', 'bcCritical': 'string'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always'), (b'basicConstraints', False, b'CA:FALSE')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('OpenSSL.crypto.X509Extension')
    def test_157__extension_list_generate(self, mock_crypto):
        """ CAhandler._extension_list_generate() - basicConstrains with  ca 1 """
        template_dic = {'foo': 'bar', 'ca': '1', 'bcCritical': '1'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always'), (b'basicConstraints', True, b'CA:TRUE')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('OpenSSL.crypto.X509Extension')
    def test_158__extension_list_generate(self, mock_crypto):
        """ CAhandler._extension_list_generate() - basicConstrains with  ca 0 """
        template_dic = {'foo': 'bar', 'ca': '0', 'bcCritical': '1'}
        cert = 'cert'
        ca_cert = 'cacert'
        mock_crypto.side_effect = return_input
        result = [(b'subjectKeyIdentifier', False, b'hash'), (b'authorityKeyIdentifier', False, b'keyid:always')]
        self.assertEqual(result, self.cahandler._extension_list_generate(template_dic, cert, ca_cert))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._config_load')
    def test_159__enter__(self, mock_cfg):
        """ test enter """
        mock_cfg.return_value = True
        self.cahandler.__enter__()
        self.assertTrue(mock_cfg.called)

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._config_load')
    def test_160__enter__(self, mock_cfg):
        """ test enter """
        self.cahandler.xdb_file = self.dir_path + '/ca/est_proxy.xdb'
        mock_cfg.return_value = True
        self.cahandler.__enter__()
        self.assertFalse(mock_cfg.called)

    def test_161_trigger(self):
        """ test trigger """
        self.assertEqual(('Method not implemented.', None, None), self.cahandler.trigger('payload'))

    def test_162_poll(self):
        """ test poll """
        self.assertEqual(('Method not implemented.', None, None, 'poll_identifier', False), self.cahandler.poll('cert_name', 'poll_identifier','csr'))

    def test_163_stub_func(self):
        """ test stubfunc """
        self.assertEqual('parameter', self.cahandler._stub_func('parameter'))

    @patch('OpenSSL.crypto.dump_certificate')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._pemcertchain_generate')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_load')
    def test_164_ca_certs_get(self, mock_load, mock_gen, mock_dump):
        """ test ca_certs_get """
        mock_load.return_value =  ['ca_key', 'ca_cert', 'ca_id']
        mock_gen.return_value = 'pem_file'
        mock_dump.return_value = 'dump'
        self.assertEqual('pem_file', self.cahandler.ca_certs_get())

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._cert_insert')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._item_insert')
    def test_165__store_cert(self, mock_i_insert, mock_c_insert):
        """ test insert """
        mock_i_insert.return_value = 1
        mock_c_insert.return_value = 2
        self.cahandler._store_cert('ca_id', 'cert_name', 'serial', 'cert', 'name_hash', 'issuer_hash')
        self.assertTrue(mock_i_insert.called)
        self.assertTrue(mock_c_insert.called)

    @patch('examples.ca_handler.xca_ca_handler.dict_from_row')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._db_close')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._db_open')
    def test_166_revocation_search(self, mock_open, mock_close, mock_dicfrow):
        """ revocation search  """
        mock_dicfrow.return_value = {'foo': 'bar'}
        mock_open.return_value = True
        mock_close.return_value = True
        self.cahandler.cursor = Mock()
        self.assertEqual({'foo': 'bar'}, self.cahandler._revocation_search('column', 'value'))
        self.assertTrue(mock_open.called)
        self.assertTrue(mock_close.called)
        self.assertTrue(mock_dicfrow.called)

    @patch('examples.ca_handler.xca_ca_handler.dict_from_row')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._db_close')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._db_open')
    def test_167_revocation_search(self, mock_open, mock_close, mock_dicfrow):
        """ revocation search  dicfromrow throws exception """
        mock_dicfrow.side_effect = Exception('exc_dicfromrow')
        mock_open.return_value = True
        mock_close.return_value = True
        self.cahandler.cursor = Mock()
        self.assertFalse(self.cahandler._revocation_search('column', 'value'))
        self.assertTrue(mock_open.called)
        self.assertTrue(mock_close.called)
        self.assertTrue(mock_dicfrow.called)

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._config_check')
    def test_168_enroll(self, mock_chk):
        """ enroll test error returned from config_check"""
        mock_chk.return_value = 'error'
        self.assertEqual(('error', None, None), self.cahandler.enroll('csr'))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._requestname_get')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._config_check')
    def test_169_enroll(self, mock_chk, mock_nameget):
        """ enroll test error returned no request name returned """
        mock_chk.return_value = None
        mock_nameget.return_value = None
        self.assertEqual(('request_name lookup failed', None, None), self.cahandler.enroll('csr'))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_load')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._csr_import')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._requestname_get')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._config_check')
    def test_170_enroll(self, mock_chk, mock_nameget, mock_csrinfo, mock_ca_load):
        """ enroll test error returned from ca_load failed """
        mock_chk.return_value = None
        mock_nameget.return_value = 'name'
        mock_csrinfo.return_value = {'foo': 'bar'}
        mock_ca_load.return_value = (None, None, None)
        self.assertEqual(('ca lookup failed', None, None), self.cahandler.enroll('csr'))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_load')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._csr_import')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._requestname_get')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._config_check')
    def test_171_enroll(self, mock_chk, mock_nameget, mock_csrinfo, mock_ca_load):
        """ enroll test error returned from ca_load failed """
        mock_chk.return_value = None
        mock_nameget.return_value = 'name'
        mock_csrinfo.return_value = {'foo': 'bar'}
        mock_ca_load.return_value = ('ca_key', None, None)
        self.assertEqual(('ca lookup failed', None, None), self.cahandler.enroll('csr'))

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_load')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._csr_import')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._requestname_get')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._config_check')
    def test_172_enroll(self, mock_chk, mock_nameget, mock_csrinfo, mock_ca_load):
        """ enroll test error returned from ca_load failed """
        mock_chk.return_value = None
        mock_nameget.return_value = 'name'
        mock_csrinfo.return_value = {'foo': 'bar'}
        mock_ca_load.return_value = ('ca_key', 'ca_cert', None)
        self.assertEqual(('ca lookup failed', None, None), self.cahandler.enroll('csr'))

    @patch('OpenSSL.crypto.dump_certificate')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._store_cert')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._extension_list_generate')
    @patch('OpenSSL.crypto.X509')
    @patch('OpenSSL.crypto.load_certificate_request')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_load')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._csr_import')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._requestname_get')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._config_check')
    def test_173_enroll(self, mock_chk, mock_nameget, mock_csrinfo, mock_ca_load, mock_csr_load, mock_509, mock_ext_get, mock_store, mock_dump):
        """ enroll test """
        mock_chk.return_value = None
        mock_nameget.return_value = 'name'
        mock_csrinfo.return_value = {'foo': 'bar'}
        ca_obj = Mock()
        ca_obj.subject_name_hash = Mock(return_value=42)
        mock_ca_load.return_value = ('ca_key', ca_obj, 5)
        dn_obj = Mock()
        dn_obj.CN = 'foo'
        mock_csr_load.return_value = Mock()
        mock_csr_load.return_value.get_subject = Mock(return_value=dn_obj)
        mock_ext_get.return_value = ['ext1', 'ext2']
        mock_509.return_value = Mock()
        mock_509.return_value.get_serial_number = Mock(return_value=42)
        mock_509.return_value.subject_name_hash = Mock(return_value=42)
        mock_store.return_value = 'foo'
        mock_dump.return_value = 'foo'
        self.assertEqual((None, 'foo', None), self.cahandler.enroll('csr'))

    @patch('OpenSSL.crypto.dump_certificate')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._store_cert')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._extension_list_generate')
    @patch('OpenSSL.crypto.X509')
    @patch('OpenSSL.crypto.load_certificate_request')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_load')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._csr_import')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._requestname_get')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._config_check')
    def test_174_enroll(self, mock_chk, mock_nameget, mock_csrinfo, mock_ca_load, mock_csr_load, mock_509, mock_ext_get, mock_store, mock_dump):
        """ enroll test - rewrite CN """
        mock_chk.return_value = None
        mock_nameget.return_value = 'reqname'
        mock_csrinfo.return_value = {'foo': 'bar'}
        ca_obj = Mock()
        ca_obj.subject_name_hash = Mock(return_value=42)
        mock_ca_load.return_value = ('ca_key', ca_obj, 5)
        dn_obj = Mock()
        dn_obj.CN = None
        mock_csr_load.return_value = Mock()
        mock_csr_load.return_value.get_subject = Mock(return_value=dn_obj)
        mock_ext_get.return_value = ['ext1', 'ext2']
        mock_509.return_value = Mock()
        mock_509.return_value.get_serial_number = Mock(return_value=42)
        mock_509.return_value.subject_name_hash = Mock(return_value=42)
        mock_store.return_value = 'foo'
        mock_dump.return_value = 'foo'
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertEqual((None, 'foo', None), self.cahandler.enroll('csr'))
        self.assertIn('INFO:test_est:rewrite CN to reqname', lcm.output)

    @patch('OpenSSL.crypto.dump_certificate')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._store_cert')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._extension_list_generate')
    @patch('OpenSSL.crypto.X509')
    @patch('OpenSSL.crypto.load_certificate_request')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_load')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._csr_import')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._requestname_get')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._config_check')
    def test_175_enroll(self, mock_chk, mock_nameget, mock_csrinfo, mock_ca_load, mock_csr_load, mock_509, mock_ext_get, mock_store, mock_dump):
        """ enroll test - default cert validity """
        mock_chk.return_value = None
        mock_nameget.return_value = 'name'
        mock_csrinfo.return_value = {'foo': 'bar'}
        ca_obj = Mock()
        ca_obj.subject_name_hash = Mock(return_value=42)
        mock_ca_load.return_value = ('ca_key', ca_obj, 5)
        dn_obj = Mock()
        dn_obj.CN = 'foo'
        mock_csr_load.return_value = Mock()
        mock_csr_load.return_value.get_subject = Mock(return_value=dn_obj)
        mock_ext_get.return_value = ['ext1', 'ext2']
        mock_509.return_value = Mock()
        mock_509.return_value.get_serial_number = Mock(return_value=42)
        mock_509.return_value.subject_name_hash = Mock(return_value=42)
        mock_store.return_value = 'foo'
        mock_dump.return_value = 'foo'
        self.assertEqual((None, 'foo', None), self.cahandler.enroll('csr'))
        self.assertEqual(365, self.cahandler.cert_validity_days)

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._template_load')
    @patch('OpenSSL.crypto.dump_certificate')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._store_cert')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._extension_list_generate')
    @patch('OpenSSL.crypto.X509')
    @patch('OpenSSL.crypto.load_certificate_request')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_load')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._csr_import')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._requestname_get')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._config_check')
    def test_176_enroll(self, mock_chk, mock_nameget, mock_csrinfo, mock_ca_load, mock_csr_load, mock_509, mock_ext_get, mock_store, mock_dump, mock_tmp_load):
        """ enroll test - template load validity """
        mock_chk.return_value = None
        mock_nameget.return_value = 'name'
        mock_csrinfo.return_value = {'foo': 'bar'}
        ca_obj = Mock()
        ca_obj.subject_name_hash = Mock(return_value=42)
        mock_ca_load.return_value = ('ca_key', ca_obj, 5)
        dn_obj = Mock()
        dn_obj.CN = 'foo'
        mock_csr_load.return_value = Mock()
        mock_csr_load.return_value.get_subject = Mock(return_value=dn_obj)
        mock_ext_get.return_value = ['ext1', 'ext2']
        mock_509.return_value = Mock()
        mock_509.return_value.get_serial_number = Mock(return_value=42)
        mock_509.return_value.subject_name_hash = Mock(return_value=42)
        mock_store.return_value = 'foo'
        mock_dump.return_value = 'foo'
        dn_dic = {'foo': 'bar'}
        template_dic = {'validity': 500}
        mock_tmp_load.return_value = (dn_dic, template_dic)
        self.cahandler.template_name = 'template'
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertEqual((None, 'foo', None), self.cahandler.enroll('csr'))
        self.assertIn('INFO:test_est:take validity from template: 500', lcm.output)

    @patch('examples.ca_handler.xca_ca_handler.CAhandler._template_load')
    @patch('OpenSSL.crypto.dump_certificate')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._store_cert')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._extension_list_generate')
    @patch('OpenSSL.crypto.X509')
    @patch('OpenSSL.crypto.load_certificate_request')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._ca_load')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._csr_import')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._requestname_get')
    @patch('examples.ca_handler.xca_ca_handler.CAhandler._config_check')
    def test_177_enroll(self, mock_chk, mock_nameget, mock_csrinfo, mock_ca_load, mock_csr_load, mock_509, mock_ext_get, mock_store, mock_dump, mock_tmp_load):
        """ enroll test - template load validity """
        mock_chk.return_value = None
        mock_nameget.return_value = 'name'
        mock_csrinfo.return_value = {'foo': 'bar'}
        ca_obj = Mock()
        ca_obj.subject_name_hash = Mock(return_value=42)
        mock_ca_load.return_value = ('ca_key', ca_obj, 5)
        dn_obj = Mock()
        dn_obj.CN = 'foo'
        mock_csr_load.return_value = Mock()
        mock_csr_load.return_value.get_subject = Mock(return_value=dn_obj)
        mock_ext_get.return_value = ['ext1', 'ext2']
        mock_509.return_value = Mock()
        mock_509.return_value.get_serial_number = Mock(return_value=42)
        mock_509.return_value.subject_name_hash = Mock(return_value=42)
        mock_store.return_value = 'foo'
        mock_dump.return_value = 'foo'
        dn_dic = {'foo': 'bar'}
        template_dic = {}
        mock_tmp_load.return_value = (dn_dic, template_dic)
        self.cahandler.template_name = 'template'
        with self.assertLogs('test_est', level='INFO') as lcm:
            self.assertEqual((None, 'foo', None), self.cahandler.enroll('csr'))
        self.assertIn('INFO:test_est:modify subject with template data', lcm.output)

if __name__ == '__main__':

    unittest.main()
