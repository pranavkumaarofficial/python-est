#!/usr/bin/python
# -*- coding: utf-8 -*-
""" skeleton for customized CA handler """
from __future__ import print_function
# pylint: disable=E0401
from est_proxy.helper import config_load

class CAhandler(object):
    """ EST CA  handler """

    def __init__(self, _debug=None, logger=None):
        self.logger = logger
        self.parameter = None

    def __enter__(self):
        """ Makes CAhandler a Context Manager """
        if not self.parameter:
            self._config_load()
        return self

    def __exit__(self, *args):
        """ cose the connection at the end of the context """

    def _config_load(self):
        """" load config from file """
        self.logger.debug('CAhandler._config_load()')

        config_dic = config_load(self.logger, 'CAhandler')
        if 'parameter' in config_dic['CAhandler']:
            self.parameter = config_dic['CAhandler']['parameter']

        self.logger.debug('CAhandler._config_load() ended')

    def _stub_func(self, parameter):
        """" load config from file """
        self.logger.debug('CAhandler._stub_func({0})'.format(parameter))

        self.logger.debug('CAhandler._stub_func() ended')

    def ca_certs_get(self):
        """ get ca certificates """
        self.logger.debug('CAhandler.ca_certs_get()')

        pem_chain = None

        return pem_chain

    def enroll(self, csr):
        """ enroll certificate  """
        self.logger.debug('CAhandler.enroll()')

        cert_bundle = None
        error = None
        cert_raw = None
        poll_indentifier = None
        self._stub_func(csr)

        self.logger.debug('Certificate.enroll() ended')

        return(error, certificate, poll_indentifier)

    def poll(self, poll_identifier, _csr):
        """ poll status of pending CSR and download certificates """
        self.logger.debug('CAhandler.poll()')

        error = None
        certificate = None
        rejected = False
        self._stub_func(cert_name)

        self.logger.debug('CAhandler.poll() ended')
        return(error, certificate, poll_identifier, rejected)
