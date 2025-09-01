#!/usr/bin/python
# -*- coding: utf-8 -*-
""" helper functions for est_proxy """
from __future__ import print_function
import calendar
from datetime import datetime
import os
import logging
import configparser
import base64
import textwrap
import OpenSSL
import pytz
from tlslite import SessionCache, HandshakeSettings, VerifierDB
from tlslite.constants import CipherSuite, HashAlgorithm, SignatureAlgorithm, GroupName, SignatureScheme

def b64decode_pad(logger, string):
    """ b64 decoding and padding of missing "=" """
    logger.debug('b64decode_pad()')
    try:
        b64dec = base64.urlsafe_b64decode(string + '=' * (4 - len(string) % 4))
    except BaseException:
        b64dec = b'ERR: b64 decoding error'
    return b64dec.decode('utf-8')

def b64_decode(logger, string):
    """ b64 decoding """
    logger.debug('b64decode()')
    return convert_byte_to_string(base64.b64decode(string))

def b64_encode(logger, string):
    """ encode a bytestream in base64 """
    logger.debug('b64_encode()')
    return base64.b64encode(convert_string_to_byte(string))

def b64_url_recode(logger, string):
    """ recode base64_url to base64 """
    logger.debug('b64_url_recode()')
    padding_factor = (4 - len(string) % 4) % 4
    string = convert_byte_to_string(string)
    string += "="*padding_factor
    result = str(string).translate(dict(zip(map(ord, u'-_'), u'+/')))
    return result

def build_pem_file(logger, existing, certificate, wrap, csr=False):
    """ construct pem_file """
    logger.debug('build_pem_file()')
    if csr:
        pem_file = '-----BEGIN CERTIFICATE REQUEST-----\n{0}\n-----END CERTIFICATE REQUEST-----\n'.format(textwrap.fill(convert_byte_to_string(certificate), 64))
        # req = OpenSSL.crypto.load_certificate_request(OpenSSL.crypto.FILETYPE_ASN1, base64.b64decode(certificate))
        # pem_file = convert_byte_to_string(OpenSSL.crypto.dump_certificate_request(OpenSSL.crypto.FILETYPE_PEM,req))
    else:
        if existing:
            if wrap:
                pem_file = '{0}-----BEGIN CERTIFICATE-----\n{1}\n-----END CERTIFICATE-----\n'.format(convert_byte_to_string(existing), textwrap.fill(convert_byte_to_string(certificate), 64))
            else:
                pem_file = '{0}-----BEGIN CERTIFICATE-----\n{1}\n-----END CERTIFICATE-----\n'.format(convert_byte_to_string(existing), convert_byte_to_string(certificate))
        else:
            if wrap:
                pem_file = '-----BEGIN CERTIFICATE-----\n{0}\n-----END CERTIFICATE-----\n'.format(textwrap.fill(convert_byte_to_string(certificate), 64))
            else:
                pem_file = '-----BEGIN CERTIFICATE-----\n{0}\n-----END CERTIFICATE-----\n'.format(convert_byte_to_string(certificate))
    return pem_file

def ca_handler_get(logger, ca_handler_name):
    """ turn handler-filename into a python path """
    logger.debug('ca_handler_get({0})'.format(ca_handler_name))
    ca_handler_name = ca_handler_name.rstrip('.py')
    ca_handler_name = ca_handler_name.replace('/', '.')
    ca_handler_name = ca_handler_name.replace('\\', '.')
    logger.debug('ca_handler_get() ended with: {0}'.format(ca_handler_name))
    return ca_handler_name

def cert_pem2der(pem_file):
    """ convert certificate pem to der """
    certobj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, pem_file)
    return OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_ASN1, certobj)

def cert_san_get(logger, certificate, recode=True):
    """ get subject alternate names from certificate """
    logger.debug('cert_san_get()')
    if recode:
        pem_file = build_pem_file(logger, None, b64_url_recode(logger, certificate), True)
    else:
        pem_file = certificate

    cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, pem_file)
    san = []
    ext_count = cert.get_extension_count()
    for i in range(0, ext_count):
        ext = cert.get_extension(i)
        if 'subjectAltName' in str(ext.get_short_name()):
            san_list = ext.__str__().split(',')
            for san_name in san_list:
                san_name = san_name.rstrip()
                san_name = san_name.lstrip()
                san.append(san_name)
    logger.debug('cert_san_get() ended')
    return san

def cert_eku_get(logger, certificate, recode=True):
    """ get extended key usage from certificate """
    logger.debug('cert_eku_get()')
    if recode:
        pem_file = build_pem_file(logger, None, b64_url_recode(logger, certificate), True)
    else:
        pem_file = certificate

    cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, pem_file)
    eku = None
    ext_count = cert.get_extension_count()
    for i in range(0, ext_count):
        ext = cert.get_extension(i)
        if 'extendedKeyUsage' in str(ext.get_short_name()):
            eku = cert.get_extension(i).get_data()
    logger.debug('cert_eku_get() ended')
    return eku

def cert_extensions_get(logger, certificate, recode=True):
    """ get extenstions from certificate certificate """
    logger.debug('cert_extensions_get()')
    if recode:
        pem_file = build_pem_file(logger, None, b64_url_recode(logger, certificate), True)
    else:
        pem_file = certificate

    cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, pem_file)
    extension_list = []
    ext_count = cert.get_extension_count()
    for i in range(0, ext_count):
        ext = cert.get_extension(i)
        extension_list.append(convert_byte_to_string(base64.b64encode(ext.get_data())))

    logger.debug('cert_extensions_get() ended with: {0}'.format(extension_list))
    return extension_list

def cert_serial_get(logger, certificate):
    """ get serial number form certificate """
    logger.debug('cert_serial_get()')
    pem_file = build_pem_file(logger, None, b64_url_recode(logger, certificate), True)
    cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, pem_file)
    logger.debug('cert_serial_get() ended with: {0}'.format(cert.get_serial_number()))
    return cert.get_serial_number()

def config_load(logger=None, mfilter=None, cfg_file=os.path.dirname(__file__)+'/'+'est_proxy.cfg'):
    """ small configparser wrappter to load a config file """
    if logger:
        logger.debug('load_config({1}:{0})'.format(mfilter, cfg_file))
    config = configparser.RawConfigParser()
    config.optionxform = str
    try:
        config.read(cfg_file)
    except BaseException:
        config = {}

    return config

def connection_log(logger, connection, seconds):
    """ a really ugly function i need to replace at a later stage """
    logger.debug('Remote end: %s', connection.getpeername())
    logger.debug(' Handshake time: %.3f seconds', seconds)
    logger.debug(" Version: %s", connection.getVersionName())
    logger.debug(" Cipher: %s %s", connection.getCipherName(), connection.getCipherImplementation())
    logger.debug(" Ciphersuite: %s", CipherSuite.ietfNames[connection.session.cipherSuite])

    if connection.session.clientCertChain:
        logger.debug(" Client X.509 SHA1 fingerprint: %s", connection.session.clientCertChain.getFingerprint())
    else:
        logger.debug(" No client certificate provided by peer")
    if connection.session.serverCertChain:
        logger.debug(" Server X.509 SHA1 fingerprint: %s", connection.session.serverCertChain.getFingerprint())
    if connection.session.srpUsername:
        logger.debug(" Client SRP username: %s", connection.session.srpUsername)
    if connection.version >= (3, 3) and connection.serverSigAlg is not None:
        scheme = SignatureScheme.toRepr(connection.serverSigAlg)
        if scheme is None:
            scheme = "{1}+{0}".format(HashAlgorithm.toStr(connection.serverSigAlg[0]), SignatureAlgorithm.toStr(connection.serverSigAlg[1]))
        logger.debug(" Key exchange signature: %s", scheme)
    if connection.ecdhCurve is not None:
        logger.debug(" Group used for key exchange: %s", GroupName.toStr(connection.ecdhCurve))
    if connection.dhGroupSize is not None:
        logger.debug(" DH group size: %s bits", connection.dhGroupSize)
    if connection.session.serverName:
        logger.debug(" SNI: %s", connection.session.serverName)
    if connection.session.appProto:
        logger.debug(" Application Layer Protocol negotiated: %s", connection.session.appProto.decode('utf-8'))
    logger.debug(" Next-Protocol Negotiated: %s", connection.next_proto)
    logger.debug(" Encrypt-then-MAC: %s", connection.encryptThenMAC)
    logger.debug(" Extended Master Secret: %s", connection.extendedMasterSecret)

def convert_byte_to_string(value):
    """ convert a variable to string if needed """
    if hasattr(value, 'decode'):
        try:
            return value.decode()
        except BaseException:
            return value
    else:
        return value

def convert_string_to_byte(value):
    """ convert a variable to byte if needed """
    if hasattr(value, 'encode'):
        result = value.encode()
    else:
        result = value
    return result

def csr_cn_get(logger, csr):
    """ get cn from certificate request """
    logger.debug('CAhandler.csr_cn_get()')
    pem_file = build_pem_file(logger, None, csr, True, True)
    req = OpenSSL.crypto.load_certificate_request(OpenSSL.crypto.FILETYPE_PEM, pem_file)
    subject = req.get_subject()
    components = dict(subject.get_components())
    result = None
    if 'CN' in components:
        result = components['CN']
    elif b'CN' in components:
        result = convert_byte_to_string(components[b'CN'])

    logger.debug('CAhandler.csr_cn_get() ended with: {0}'.format(result))
    return result

def csr_san_get(logger, csr):
    """ get subject alternate names from certificate """
    logger.debug('cert_san_get()')
    san = []
    if csr:
        pem_file = build_pem_file(logger, None, b64_url_recode(logger, csr), True, True)
        req = OpenSSL.crypto.load_certificate_request(OpenSSL.crypto.FILETYPE_PEM, pem_file)
        for ext in req.get_extensions():
            if 'subjectAltName' in str(ext.get_short_name()):
                san_list = ext.__str__().split(',')
                for san_name in san_list:
                    san_name = san_name.rstrip()
                    san_name = san_name.lstrip()
                    san.append(san_name)
    logger.debug('cert_san_get() ended with: {0}'.format(str(san)))
    return san

def logger_setup(debug, cfg_file=None):
    """ setup logger """
    if debug:
        log_mode = logging.DEBUG
    else:
        log_mode = logging.INFO

    # define log format
    try:
        config_dic = config_load(cfg_file=cfg_file)
        log_format = config_dic.get('Logging', 'log_format', fallback='%(message)s')
    except BaseException:
        log_format = '%(message)s'

    logging.basicConfig(format=log_format, datefmt="%Y-%m-%d %H:%M:%S", level=log_mode)
    logger = logging.getLogger('est_proxy')
    return logger

def hssrv_options_get(logger, config_dic):
    """ get parameters for handshake server """
    logger.debug('hssrv_options_get()')

    hs_settings = HandshakeSettings()

    #  settings.useExperimentalTackExtension=True
    # settings.dhParams = dhparam
    # if ssl3:
    #    settings.minVersion = (3, 0)
    #
    # if cipherlist:
    #    settings.cipherNames = [item for cipher in cipherlist
    #                            for item in cipher.split(',')]

    option_dic = {}
    if 'Daemon' in config_dic:
        if 'cert_file' in config_dic['Daemon'] and 'key_file' in config_dic['Daemon']:
            option_dic['certChain'] = config_dic['Daemon']['cert_file']
            option_dic['privateKey'] = config_dic['Daemon']['key_file']
            option_dic['sessionCache'] = SessionCache()
            option_dic['alpn'] = [bytearray(b'http/1.1')]
            option_dic['settings'] = hs_settings
            option_dic['reqCert'] = True
            option_dic['sni'] = None
        else:
            logger.error('Helper.hssrv_options_get(): incomplete Daemon configuration in config file')
    else:
        logger.error('Helper.hssrv_options_get(): Daemon specified but not configured in config file')

    if 'SRP' in config_dic:
        if 'userdb' in config_dic['SRP']:
            try:
                srp_db = VerifierDB(config_dic['SRP']['userdb'])
                srp_db.open()
                option_dic['verifierDB'] = srp_db
            except BaseException as err:
                logger.error('Helper.hssrv_options_get(): SRP database {0} could not get loaded.'.format(config_dic['SRP']['userdb']))
                logger.error('Helper.hssrv_options_get(): Error: {0}'.format(err))
    logger.debug('hssrv_options_get() ended')
    return option_dic

def uts_now():
    """ return unixtimestamp in utc """
    return calendar.timegm(datetime.utcnow().utctimetuple())

def uts_to_date_utc(uts, tformat='%Y-%m-%dT%H:%M:%SZ'):
    """ convert unix timestamp to date format """
    return datetime.fromtimestamp(int(uts), tz=pytz.utc).strftime(tformat)
