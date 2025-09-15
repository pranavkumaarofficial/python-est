# -*- coding: utf-8 -*-
""" http based est protocol handler """
import os
import tempfile
import subprocess
import importlib
from http.server import BaseHTTPRequestHandler
# pylint: disable=E0401
from python_est.core.helper import config_load, ca_handler_get, logger_setup # ,b64_encode, cert_san_get, cert_extensions_get, cert_eku_get
from python_est.core.version import __version__

class ESTSrvHandler(BaseHTTPRequestHandler):
    """ serverside of est protocol handler """
    cahandler = None
    debug = False
    cfg_file = None
    logger = None
    openssl_bin = None
    connection = None
    protocol_version = "HTTP/1.1"
    server_version = 'est_proxy'
    sys_version = __version__

    def __init__(self, *args, **kwargs):
        """ init function """
        # get config and logger file
        try:
            self.cfg_file = args[2].__dict__['cfg_file']
        except BaseException:
            # self.logger.error('ESTSrvHandler.__init__ cfg_file load from args failed')
            self.cfg_file = 'est_proxy.cfg'
        try:
            self.logger = args[2].__dict__['logger']
        except BaseException:
            self.logger = logger_setup(self.debug, cfg_file=self.cfg_file)
        if not self.openssl_bin:
            self._config_load()
        try:
            # store connection settings
            self.connection = args[0]
        except BaseException as err_:
            self.logger.error('ESTSrvHandler.__init__ store connection settings failed: {0}'.format(err_))
        try:
            super().__init__(*args, **kwargs)
        except BaseException as err_:
            self.logger.error('ESTSrvHandler.__init__ superclass init failed: {0}'.format(err_))

    def _cacerts_get(self):
        """ get ca certificates """
        self.logger.debug('ESTSrvHandler._cacerts_get()')
        with self.cahandler(self.cfg_file, self.logger) as ca_handler:
            # get ca_certs
            ca_certs = ca_handler.ca_certs_get()
            # convert pem to pkcs#7
            if ca_certs:
                ca_pkcs7 = self._pkcs7_convert(ca_certs)
            else:
                self.logger.error('ESTSrvHandler._cacerts_get(): no cacerts returned from handler')
                ca_pkcs7 = None
        self.logger.debug('ESTSrvHandler._cacerts_get() ended with: {0}'.format(bool(ca_pkcs7)))
        return ca_pkcs7

    def _auth_check(self):
        """ check authentication - bootstrap allows SRP only """
        self.logger.debug('ESTSrvHandler._auth_check()')
        authenticated = False

        # For bootstrap endpoints, only SRP authentication is required
        if self.path == '/.well-known/est/bootstrap' or self.path.startswith('/bootstrap'):
            if self.connection.session.srpUsername:
                self.logger.info('Bootstrap: Client SRP username: {0}'.format(self.connection.session.srpUsername))
                authenticated = True
            else:
                self.logger.debug('Bootstrap: No SRP authentication provided')
        else:
            # For regular EST endpoints, require client certificate or SRP
            if self.connection.session.clientCertChain or self.connection.session.srpUsername:
                if self.connection.session.clientCertChain:
                    self.logger.info('Client X.509 SHA1 fingerprint: {0}'.format(self.connection.session.clientCertChain.getFingerprint()))
                else:
                    self.logger.info('Client SRP username: {0}'.format(self.connection.session.srpUsername))
                authenticated = True

        self.logger.debug('ESTSrvHandler._auth_check() ended with: {0}'.format(authenticated))
        return authenticated

    def _cacerts_split(self, ca_certs):
        """ split ca_certs """
        self.logger.debug('ESTSrvHandler._cacerts_split()')
        ca_certs_list = []
        if ca_certs:
            cert = ""
            for line in ca_certs.splitlines(True):
                cert += line
                if '-----END CERTIFICATE-----' in line:
                    ca_certs_list.append(cert)
                    cert = ""
        self.logger.debug('ESTSrvHandler._cacerts_split() ended with: {0} certs'.format(len(ca_certs_list)))
        return ca_certs_list

    def _cacerts_dump(self, ca_list):
        """ dump certs to file """
        self.logger.debug('ESTSrvHandler._cacerts_dump()')
        ca_file_names = []
        if isinstance(ca_list, list):
            for cert in ca_list:
                fso = tempfile.NamedTemporaryFile(mode='w+', delete=False)
                fso.write(cert)
                fso.close()
                ca_file_names.append(fso.name)
        self.logger.debug('ESTSrvHandler._cacerts_dump() ended with: {0} certs'.format(len(ca_file_names)))
        return ca_file_names

    def _cert_enroll(self, csr):
        """ enroll cert """
        self.logger.debug('ESTSrvHandler._cert_enroll()')
        cert_pkcs7 = None
        if csr:
            with self.cahandler(self.cfg_file, self.logger) as ca_handler:
                # get certs
                (error, cert, _poll_identifier) = ca_handler.enroll(csr)
                if not error and cert:
                    cert_pkcs7 = self._pkcs7_convert(cert, pkcs7_clean=True)
                else:
                    if not cert:
                        error = 'No error but no cert returned'
                    self.logger.error('ESTSrvHandler._cert_enroll(): {0}'.format(error))

        else:
            error = 'no CSR submittted'
            self.logger.error('ESTSrvHandler._cert_enroll(): no csr submitted')

        self.logger.debug('ESTSrvHandler._cacerts_get() ended with: {0}'.format(bool(cert_pkcs7)))
        return (error, cert_pkcs7)

    def _config_load(self):
        """ load config from file """
        self.logger.debug('ESTSrvHandler._config_load()')
        config_dic = config_load(self.logger, cfg_file=self.cfg_file)

        if 'DEFAULT' in config_dic and 'openssl_bin' in config_dic['DEFAULT']:
            self.openssl_bin = config_dic['DEFAULT']['openssl_bin']
        else:
            self.openssl_bin = 'openssl'

        if 'CAhandler' in config_dic and 'handler_file' in config_dic['CAhandler']:
            try:
                ca_handler_module = importlib.import_module(ca_handler_get(self.logger, config_dic['CAhandler']['handler_file']))
            except BaseException as err_:
                self.logger.error('ESTSrvHandler._config_load(): CAhandler {0} could not get loaded. with error: {1}\nLoading default hander...'.format(config_dic['CAhandler']['handler_file'], err_))
                try:
                    ca_handler_module = importlib.import_module('est_proxy.ca_handler')
                except BaseException:
                    self.logger.error('ESTSrvHandler._config_load():  Loading default handler failed.')
                    ca_handler_module = None
        else:
            if 'CAhandler' in config_dic:
                try:
                    ca_handler_module = importlib.import_module('est_proxy.ca_handler')
                except BaseException as err_:
                    self.logger.error('ESTSrvHandler._config_load(): default CAhandler could not get loaded. err: {0}'.format(err_))
                    ca_handler_module = None
            else:
                self.logger.error('ESTSrvHandler._config_load(): CAhandler configuration missing in config file')
                ca_handler_module = None

        if ca_handler_module:
            # store handler in variable
            self.cahandler = ca_handler_module.CAhandler

        self.logger.debug('ca_handler: {0}'.format(ca_handler_module))
        self.logger.debug('ESTSrvHandler._config_load() ended')

    def _pkcs7_clean(self, pkcs7_struc):
        """ remove cert header and footer """
        self.logger.debug('ESTSrvHandler._pkcs7_clean()')
        if isinstance(pkcs7_struc, bytes):
            pkcs7_struc = pkcs7_struc.decode('utf-8')
        if pkcs7_struc and isinstance(pkcs7_struc, str):
            # remove pkcs7 start end end tags
            pkcs7_struc = pkcs7_struc.replace('-----BEGIN PKCS7-----\n', '')
            # do not remove CR from end tag as it must be part of the content
            pkcs7_struc = pkcs7_struc.replace('-----END PKCS7-----', '')
        return pkcs7_struc

    def _pkcs7_convert(self, ca_certs, pkcs7_clean=True):
        """ convert to pkcs#7 """
        self.logger.debug('ESTSrvHandler._pkcs7_convert()')

        pkcs7_struc = None
        if ca_certs:
            # split pem-chain into certs
            ca_list = self._cacerts_split(ca_certs)
            # dump certs into temporary files
            file_names = self._cacerts_dump(ca_list)

            if self.openssl_bin and file_names:
                fso = tempfile.NamedTemporaryFile(mode='w+', delete=False)
                pkcs7_file = fso.name
                fso.close()

                # create command-line to convert
                openssl_cmd = self._opensslcmd_build(file_names, pkcs7_file)

                # run command and capture return code
                rcode = subprocess.call(openssl_cmd)
                if rcode == 0:
                    with open(pkcs7_file, 'r', encoding='utf-8') as fso:
                        pkcs7_struc = fso.read()

                if pkcs7_struc and pkcs7_clean:
                    pkcs7_struc = self._pkcs7_clean(pkcs7_struc)

                # add outfile to list and delete all files
                file_names.append(pkcs7_file)
                self._tmpfiles_clean(file_names)

        return pkcs7_struc

    def _tmpfiles_clean(self, file_name_list):
        """ clean files """
        self.logger.debug('ESTSrvHandler._tmpfiles_clean()')
        for file_name in file_name_list:
            try:
                os.remove(file_name)
            except BaseException as err:
                self.logger.error('ESTSrvHandler._tmpfiles_clean() failed for {0} with error: {1}'.format(file_name, err))

    def _opensslcmd_build(self, file_name_list, pkcs7_file):
        """ build ssl cmd """
        # convert to list if string or byte
        if isinstance(file_name_list, str):
            file_name_list = [file_name_list]
        elif isinstance(file_name_list, bytes):
            file_name_list = [file_name_list.decode('utf-8')]
        # create list of openssl parameters
        cmd_list = [self.openssl_bin, 'crl2pkcs7', '-nocrl', '-out', pkcs7_file]
        for file_name in file_name_list:
            cmd_list.extend(['--certfile', file_name])
        return cmd_list

    def _bootstrap_page_get(self):
        """ return bootstrap login page """
        self.logger.debug('ESTSrvHandler._bootstrap_page_get()')

        html_content = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>EST Bootstrap Authentication</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 400px; margin: 100px auto; padding: 20px; }
        .container { border: 1px solid #ddd; padding: 30px; border-radius: 8px; background: #f9f9f9; }
        h2 { text-align: center; color: #333; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], input[type="password"] {
            width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;
        }
        .btn {
            width: 100%; padding: 12px; background: #007bff; color: white; border: none;
            border-radius: 4px; cursor: pointer; font-size: 16px;
        }
        .btn:hover { background: #0056b3; }
        .info { font-size: 12px; color: #666; margin-top: 15px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h2>EST Bootstrap Login</h2>
        <form method="post" action="/bootstrap/login">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit" class="btn">Login & Enroll Certificate</button>
        </form>
        <div class="info">
            This page is for initial certificate enrollment using SRP authentication.<br>
            After successful enrollment, use certificate-based authentication.
        </div>
    </div>
</body>
</html>'''

        self.logger.debug('ESTSrvHandler._bootstrap_page_get() ended')
        return html_content

    def _bootstrap_login_process(self, post_data):
        """ process bootstrap login form submission """
        self.logger.debug('ESTSrvHandler._bootstrap_login_process()')

        try:
            # Parse form data
            form_data = {}
            if post_data:
                post_str = post_data.decode('utf-8')
                for pair in post_str.split('&'):
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        # Basic URL decoding
                        key = key.replace('+', ' ').replace('%20', ' ')
                        value = value.replace('+', ' ').replace('%20', ' ')
                        form_data[key] = value

            username = form_data.get('username', '')
            password = form_data.get('password', '')

            if not username or not password:
                return (400, 'text/html', 'Username and password required', None)

            # Check if this is an SRP authenticated connection
            if not self.connection.session.srpUsername:
                return (401, 'text/html', 'SRP authentication required for bootstrap', None)

            # Verify the SRP username matches the form username
            if self.connection.session.srpUsername != username:
                self.logger.warning('Bootstrap: SRP username mismatch: {0} vs {1}'.format(
                    self.connection.session.srpUsername, username))
                return (401, 'text/html', 'Authentication failed', None)

            # Generate a simple CSR for the user (in a real implementation, client would provide CSR)
            success_page = '''<!DOCTYPE html>
<html>
<head>
    <title>Bootstrap Success</title>
    <style>body { font-family: Arial, sans-serif; text-align: center; margin-top: 100px; }</style>
</head>
<body>
    <h2>✅ Bootstrap Authentication Successful</h2>
    <p>User: {0}</p>
    <p>SRP Authentication completed successfully.</p>
    <p>Next: Submit your CSR to /.well-known/est/simpleenroll with SRP authentication.</p>
    <a href="/bootstrap">← Back to Bootstrap</a>
</body>
</html>'''.format(username)

            return (200, 'text/html', success_page, None)

        except Exception as e:
            self.logger.error('Bootstrap login processing error: {0}'.format(e))
            return (500, 'text/html', 'Internal server error', None)

    def _set_response(self, code=404, content_type='text/html', clength=0, encoding=None):
        """ set response method """
        self.send_response(code)
        if content_type:
            self.send_header('Content-Type', content_type)
        if encoding:
            self.send_header('Content-Transfer-Encoding', encoding)
        if clength:
            self.send_header('Content-Length', clength)
        self.send_header('Connection', 'close')
        self.end_headers()

    def _get_process(self):
        """ main method to process get requests """
        self.logger.debug('ESTSrvHandler._get_process %s', self.path)
        content = None
        content_length = 0
        encoding = None

        if self.path == '/.well-known/est/cacerts':
            code = 200
            ca_certs = self._cacerts_get()
            if ca_certs:
                code = 200
                content_type = 'application/pkcs7-mime'
                content = ca_certs
                encoding = 'base64'
            else:
                code = 500
                content_type = 'text/html'
        elif self.path == '/.well-known/est/bootstrap' or self.path == '/bootstrap':
            code = 200
            content_type = 'text/html'
            content = self._bootstrap_page_get()
        else:
            code = 400
            content_type = 'text/html'
            content = 'An unknown error has occured.'

        if content:
            content_length = len(str(content))
            content = content.encode('utf8')

        return(code, content_type, content_length, encoding, content)

    def _post_process(self, data):
        """ main method to process post requests """
        self.logger.debug('ESTSrvHandler._post_process %s', self.path)
        content = None
        content_length = 0
        content_type = None
        encoding = None
        code = 400

        # Handle bootstrap login form submission
        if self.path == '/bootstrap/login':
            (code, content_type, content, encoding) = self._bootstrap_login_process(data)
            return (code, content_type, len(content) if content else 0, encoding, content)

        # check if connection is poperly authenticated
        connection_authenticated = self._auth_check()

        if connection_authenticated:
            if data and (self.path == '/.well-known/est/simpleenroll' or self.path == '/.well-known/est/simplereenroll'):
                # enroll certificate
                (error, cert) = self._cert_enroll(data)
                if not error:
                    code = 200
                    content_type = 'application/pkcs7-mime; smime-type=certs-only'
                    content = cert
                    encoding = 'base64'
                else:
                    code = 500
            else:
                code = 400
                if data:
                    content = 'An unknown error has occured.\n'
                else:
                    content = 'No data had been send.\n'
        else:
            code = 401
            content = 'The server was unable to authorize the request.\n'

        if content:
            content_length = len(str(content))
            content = content.encode('utf8')

        return(code, content_type, content_length, encoding, content)

    # pylint: disable=C0103
    def do_GET(self):
        """ this is a http get """
        self.logger.debug('ESTSrvHandler.do_GET %s path: %s', self.client_address, self.path)
        # process request
        (code, content_type, content_length, encoding, content) = self._get_process()
        # write response
        self._set_response(code, content_type, content_length, encoding)
        if content:
            self.wfile.write(content)

    def do_POST(self):
        """ this is a http post """
        self.logger.debug('ESTSrvHandler.do_POST %s path: %s', self.client_address, self.path)

        if "Content-Length" in self.headers:
            #  gets the size of data
            content_length = int(self.headers['Content-Length'])
            if content_length > 0:
                # gets the data itself
                post_data = self.rfile.read(content_length)
            else:
                post_data = None

        elif "chunked" in self.headers.get("Transfer-Encoding", ""):
            self.logger.debug('ESTSrvHandler.do_POST() chunk encoding detected...')
            post_data = b''
            # i had to implement my on chunk method as i had problems to read the data end
            # send by globalsign estclient
            # two loops - outer loop looks for a content lenght 0
            #           - inner loop looks for b'' indicating a chunk end
            while True:
                line = self.rfile.readline().strip()
                # first line in a sequence is usually the content length in hex followed by data
                chunk_length = int(line, 16)
                self.logger.debug('ESTSrvHandler.do_POST() chunk with length of {0} detected.'.format(chunk_length))
                while True:
                    # read data line by line and look for b'' indicateing chunk end
                    line = self.rfile.readline().strip()
                    if line != b'':
                        post_data += line
                    else:
                        self.logger.debug('ESTSrvHandler.do_POST() chunk end detected.')
                        break
                # Finally, a chunk size of 0 is an end indication
                if chunk_length == 0:
                    self.logger.debug('ESTSrvHandler.do_POST() end sequence detected.')
                    break

        (code, content_type, content_length, encoding, content) = self._post_process(post_data)

        # write response
        self._set_response(code, content_type, content_length, encoding)
        if content:
            self.wfile.write(content)

        #self._set_response()
        #self.wfile.write("POST request for {}".format(self.path).encode('utf-8'))
