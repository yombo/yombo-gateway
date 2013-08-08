'''This library provides basic webservice client python interfaces.'''

import httplib
import base64
import json
import os

from urllib import urlencode

__author__ = 'Juan Enrique Munoz Zolotoochin'
__email__ = 'juanique@gmail.com'


class HttpResponse(object):

    def __init__(self, http_resp):
        self.parse_response(http_resp)

    def parse_response(self, http_resp):
        self.http_resp = http_resp
        self.content = self.http_resp.read()

        try:
            self.data = json.loads(self.content)
        except ValueError:
            pass

    @property
    def status_code(self):
        return self.http_resp.status


class Connection(object):

    def __init__(self, host, http_conn_class=httplib.HTTPConnection, port=None,
            verbose=False):

        if verbose:
            http_conn_class = self.create_verbose_conn_class(http_conn_class)
        self.http_conn = http_conn_class(host, port=port)

    def create_verbose_conn_class(self, conn_class):

        class VerboseConnection(conn_class):
            response = None

            def _output(self, s):
                print ">%s" % s
                conn_class._output(self, s)

            def request(self, *args, **kwargs):
                conn_class.request(self, *args, **kwargs)
                self.response = conn_class.getresponse(self)

                for name, value in self.response.getheaders():
                    print "<%s : %s" % (name, value)
                print "<status code: %s" % self.response.status

            def getresponse(self):
                return self.response

        return VerboseConnection

    def request(self, method, path, headers={}, body=""):
        if path[0] != '/':
            path = '/' + path

        self.http_conn.request(method, path, headers=headers, body=body)
        return HttpResponse(self.http_conn.getresponse())


class WebClient(object):

    multipart_boundary = '----------bundary------'

    def __init__(self, host, https=False, verbose=False, port=None):
        self.port = port
        self.https = https
        self.verbose = verbose
        self._parse_host(host)
        self.default_headers = {}
        self.multipart_encoding = "utf-8"

        if self.https:
            self.conn_class = httplib.HTTPSConnection
            port = port or 443
        else:
            self.conn_class = httplib.HTTPConnection
            port = port or 80

    def authenticate(self, username, password):
        encoded_credentials = base64.b64encode("%s:%s" % (username, password))
        auth = "Basic " + encoded_credentials
        self.default_headers['Authorization'] = auth

    def _parse_host(self, host):
        https_prefix = "https://"
        http_prefix = "http://"

        if host.startswith(https_prefix):
            self.https = True
            self.host = host.split(https_prefix).pop()
        elif host.startswith(http_prefix):
            self.https = False
            self.host = host.split(http_prefix).pop()
        else:
            self.host = host

    def get_connection(self):
        return Connection(self.host, self.conn_class, self.port, verbose=self.verbose)

    def get(self, path, data={}):
        conn = self.get_connection()
        full_path = self.get_path(path, data)

        headers = dict(self.default_headers)

        return conn.request("GET", full_path, headers)

    def get_path(self, path, data={}):
        return"%s?%s" % (path, urlencode(data))

    def encode_multipart(self, data, files={}):
        CRLF = '\r\n'
        body = []

        for key, value in data.items():
            body.extend([
                "--%s" % self.multipart_boundary,
                'Content-Disposition: form-data; name="%s"' % key,
                '',
                value.encode(self.multipart_encoding),
            ])

        for key, filename in files.items():
            file_name = os.path.basename(filename)
            with open(filename, 'rb') as f:
                file_content = f.read()

            body.extend(
              ['--' + self.multipart_boundary,
               'Content-Disposition: form-data; name="%s"; filename="%s"'
               % (key, file_name),
               'Content-Type: application/octet-stream',
               '',
               file_content,
               ])

        body.extend(['--' + self.multipart_boundary + '--', ''])

        return CRLF.join(body)

    def post(self, path, data={}, content_type='application/json', files={}):
        conn = self.get_connection()

        headers = dict(self.default_headers)

        if content_type == "application/json":
            data = json.dumps(data)
        elif content_type == "multipart/form-data":
            content_type = "%s; boundary=%s" % (content_type, self.multipart_boundary)
            data = self.encode_multipart(data=data, files=files)

        headers['content-type'] = content_type
        return conn.request('POST', path, headers, body=data)


class WebClientException(Exception):
    pass
