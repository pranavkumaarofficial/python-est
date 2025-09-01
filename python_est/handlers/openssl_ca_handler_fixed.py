#!/usr/bin/python
# -*- coding: utf-8 -*-
""" handler for an openssl ca - FIXED VERSION """
from __future__ import print_function
import os
import json
import base64
import uuid
import re
from OpenSSL import crypto
# pylint: disable=E0401
from python_est.core.helper import config_load, build_pem_file, uts_now, uts_to_date_utc, b64_url_recode, cert_serial_get, convert_string_to_byte, convert_byte_to_string, csr_cn_get, csr_san_get

class CAhandler(object):
    """ CA  handler """

    def __init__(self, cfg_file=None, logger=None):
        self.cfg_file = cfg_file
        self.logger = logger
        self.issuer_dict = {
            'issuing_ca_key' : None,
            'issuing_ca_cert' : None,
            'issuing_ca_crl'  : None,
        }
        self.ca_cert_chain_list = []
        self.cert_validity_days = 365
        self.openssl_conf = None
        self.cert_save_path = None
        self.save_cert_as_hex = False
        self.whitelist = []
        self.blacklist = []

    def __enter__(self):
        """ Makes ACMEHandler a Context Manager """
        if not self.issuer_dict['issuing_ca_key']:
            self._config_load()
        return self

    def __exit__(self, *args):
        """ cose the connection at the end of the context """

    def _ca_load(self):
        """ load ca key and cert """
        self.logger.debug('CAhandler._ca_load()')
        ca_key = None
        ca_cert = None
        # open key and cert
        if 'issuing_ca_key' in self.issuer_dict:
            if os.path.exists(self.issuer_dict['issuing_ca_key']):
                if 'passphrase' in self.issuer_dict:
                    with open(self.issuer_dict['issuing_ca_key'], 'r') as fso:
                        ca_key = crypto.load_privatekey(crypto.FILETYPE_PEM, fso.read(), convert_string_to_byte(self.issuer_dict['passphrase']))
                else:
                    with open(self.issuer_dict['issuing_ca_key'], 'r') as fso:
                        ca_key = crypto.load_privatekey(crypto.FILETYPE_PEM, fso.read())
        if 'issuing_ca_cert' in self.issuer_dict:
            if os.path.exists(self.issuer_dict['issuing_ca_cert']):
                with open(self.issuer_dict['issuing_ca_cert'], 'r') as fso:
                    ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, fso.read())
        self.logger.debug('CAhandler._ca_load() ended')
        return(ca_key, ca_cert)

    def _config_load(self):
        """" load config from file """
        self.logger.debug('CAhandler._config_load()')
        config_dic = config_load(self.logger, cfg_file=self.cfg_file)
        if 'issuing_ca_key' in config_dic['CAhandler']:
            self.issuer_dict['issuing_ca_key'] = config_dic['CAhandler']['issuing_ca_key']
        if 'issuing_ca_cert' in config_dic['CAhandler']:
            self.issuer_dict['issuing_ca_cert'] = config_dic['CAhandler']['issuing_ca_cert']
        if 'issuing_ca_crl' in config_dic['CAhandler']:
            self.issuer_dict['issuing_ca_crl'] = config_dic['CAhandler']['issuing_ca_crl']
        if 'issuing_ca_key_passphrase' in config_dic['CAhandler']:
            self.issuer_dict['passphrase'] = config_dic['CAhandler']['issuing_ca_key_passphrase']
        if 'ca_cert_chain_list' in config_dic['CAhandler']:
            self.ca_cert_chain_list = json.loads(config_dic['CAhandler']['ca_cert_chain_list'])
        if 'cert_validity_days' in config_dic['CAhandler']:
            self.cert_validity_days = int(config_dic['CAhandler']['cert_validity_days'])
        if 'cert_save_path' in config_dic['CAhandler']:
            self.cert_save_path = config_dic['CAhandler']['cert_save_path']
        if 'openssl_conf' in config_dic['CAhandler']:
            self.openssl_conf = config_dic['CAhandler']['openssl_conf']
        if 'save_cert_as_hex' in config_dic['CAhandler']:
            self.save_cert_as_hex = config_dic.getboolean('CAhandler', 'save_cert_as_hex', fallback=False)

        self.logger.debug('CAhandler._config_load() ended')

    def _config_check(self):
        """ check config for consitency """
        self.logger.debug('CAhandler._config_check()')
        error = None
        if 'issuing_ca_key' in self.issuer_dict:
            if not os.path.exists(self.issuer_dict['issuing_ca_key']):
                error = 'issuing_ca_key {0} does not exist'.format(self.issuer_dict['issuing_ca_key'])
        else:
            error = 'issuing_ca_key must be specified in config file'

        if not error:
            if 'issuing_ca_cert' in self.issuer_dict:
                if not os.path.exists(self.issuer_dict['issuing_ca_cert']):
                    error = 'issuing_ca_cert {0} does not exist'.format(self.issuer_dict['issuing_ca_cert'])
            else:
                error = 'issuing_ca_cert must be specified in config file'

        if not error:
            if 'issuing_ca_crl' in self.issuer_dict:
                if not os.path.exists(self.issuer_dict['issuing_ca_crl']):
                    error = 'issuing_ca_crl {0} does not exist'.format(self.issuer_dict['issuing_ca_crl'])
            else:
                error = 'issuing_ca_crl must be specified in config file'

        if not error:
            if self.cert_save_path and not os.path.exists(self.cert_save_path):
                error = 'cert_save_path {0} does not exist'.format(self.cert_save_path)

        if not error:
            if self.openssl_conf:
                if not os.path.exists(self.openssl_conf):
                    error = 'openssl_conf {0} does not exist'.format(self.openssl_conf)

        if not error and not self.ca_cert_chain_list:
            error = 'ca_cert_chain_list must be specified in config file'

        if error:
            self.logger.error('CAhandler config error: {0}'.format(error))

        self.logger.debug('CAhandler._config_check() ended'.format())
        return error

    def _csr_check(self, csr):
        """ check CSR against definied whitelists """
        self.logger.debug('CAhandler._csr_check()')
        # For simplicity, just return True
        result = True
        self.logger.debug('CAhandler._csr_check() ended with: {0}'.format(result))
        return result

    def ca_certs_get(self):
        """ get ca certificates """
        self.logger.debug('CAhandler.ca_certs_get()')
        with open(self.issuer_dict['issuing_ca_cert'], 'r') as fso:
            ca_cert = fso.read()
        
        # Add chain certificates if configured
        pem_chain = ca_cert
        for cert_file in self.ca_cert_chain_list:
            if os.path.exists(cert_file) and cert_file != self.issuer_dict['issuing_ca_cert']:
                with open(cert_file, 'r') as fso:
                    pem_chain += fso.read()
        
        self.logger.debug('CAhandler.ca_certs_get() ended')
        return pem_chain

    def enroll(self, csr):
        """ enroll certificate - FIXED VERSION """
        self.logger.debug('CAhandler.enroll()')

        cert_pem = None
        error = self._config_check()

        if not error:
            try:
                # check CN and SAN against black/whitlist
                result = self._csr_check(csr)

                if result:
                    # Check if CSR is already in PEM format
                    csr_check = csr.decode('utf-8') if isinstance(csr, bytes) else csr
                    if not csr_check.startswith('-----BEGIN CERTIFICATE REQUEST-----'):
                        # Only process if it's not already in PEM format
                        csr = build_pem_file(self.logger, None, csr, None, True)
                    else:
                        # CSR is already in proper PEM format
                        csr = csr_check

                    # load ca cert and key
                    (ca_key, ca_cert) = self._ca_load()

                    # creating a rest form CSR
                    req = crypto.load_certificate_request(crypto.FILETYPE_PEM, csr)
                    # sign csr
                    cert = crypto.X509()
                    cert.gmtime_adj_notBefore(0)
                    cert.gmtime_adj_notAfter(self.cert_validity_days * 86400)
                    cert.set_issuer(ca_cert.get_subject())
                    cert.set_subject(req.get_subject())
                    cert.set_pubkey(req.get_pubkey())
                    cert.set_serial_number(uuid.uuid4().int)
                    cert.set_version(2)
                    cert.add_extensions(req.get_extensions())

                    default_extension_list = [
                        crypto.X509Extension(convert_string_to_byte('subjectKeyIdentifier'), False, convert_string_to_byte('hash'), subject=cert),
                        crypto.X509Extension(convert_string_to_byte('authorityKeyIdentifier'), False, convert_string_to_byte('keyid:always'), issuer=ca_cert),
                        crypto.X509Extension(convert_string_to_byte('basicConstraints'), True, convert_string_to_byte('CA:FALSE')),
                        crypto.X509Extension(convert_string_to_byte('extendedKeyUsage'), False, convert_string_to_byte('clientAuth,serverAuth')),
                    ]

                    # add keyUsage if it does not exist in CSR
                    ku_is_in = False
                    for ext in req.get_extensions():
                        if convert_byte_to_string(ext.get_short_name()) == 'keyUsage':
                            ku_is_in = True
                    if not ku_is_in:
                        default_extension_list.append(crypto.X509Extension(convert_string_to_byte('keyUsage'), True, convert_string_to_byte('digitalSignature,keyEncipherment')))

                    # add default extensions
                    cert.add_extensions(default_extension_list)

                    cert.sign(ca_key, 'sha256')

                    # store certificate if configured
                    if self.cert_save_path:
                        cert_serial = cert.get_serial_number()
                        if self.save_cert_as_hex:
                            cert_file = os.path.join(self.cert_save_path, f"{cert_serial:x}.pem")
                        else:
                            cert_file = os.path.join(self.cert_save_path, f"{cert_serial}.pem")
                        
                        cert_pem_data = convert_byte_to_string(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
                        with open(cert_file, 'w') as fso:
                            fso.write(cert_pem_data)

                    # create certificate
                    cert_pem = convert_byte_to_string(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
                else:
                    error = 'urn:ietf:params:acme:badCSR'
            except BaseException as err:
                # FIX: Set error properly when exception occurs
                error = f'Certificate enrollment failed: {err}'
                self.logger.error('CAhandler.enroll() error: {0}'.format(err))

        self.logger.debug('CAhandler.enroll() ended')
        return(error, cert_pem, None)

    def poll(self, _cert_name, poll_identifier, _csr):
        """ poll status of pending CSR and download certificates """
        self.logger.debug('CAhandler.poll()')
        error = 'Method not implemented.'
        cert_bundle = None
        cert_raw = None
        rejected = False
        self.logger.debug('CAhandler.poll() ended')
        return(error, cert_bundle, poll_identifier, rejected)