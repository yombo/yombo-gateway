#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://yombo.net
"""

.. note::

  * For library documentation, see: `Requests @ Library Documentation <https://yombo.net/docs/libraries/requests>`_


A friendly HTTP helper. Usese treq to process requests. Also provides various helper functions to massage data
even if this library wasn't used to make the request.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.22.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/requests.html>`_
"""
# Import python libraries
import msgpack
try:
    from hashlib import sha3_224 as sha224
except ImportError:
    from hashlib import sha224
import treq

try:
    import simplejson as json
except ImportError:
    import json

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import VERSION
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import bytes_to_unicode
from yombo.constants import CONTENT_TYPE_JSON, CONTENT_TYPE_MSGPACK

logger = get_logger('library.requests')

class Requests(YomboLibrary):

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo Requests library"

    def make_headers(self, session, session_type):
        headers = {
            'Content-Type': self.contentType,
            'Authorization': "Yombo-Gateway-%s" % VERSION,
            'x-api-key': self.api_key,
            'User-Agent': "yombo-gateway-%s" % VERSION,
        }
        if session is not None:
            headers['Authorization'] = '%s %s' % (session_type, session)

        return headers

    def errorHandler(self,result):
        raise YomboWarning("Problem with request: %s" % result)

    @inlineCallbacks
    def request(self, method, url, **kwargs):
        """
        Make an HTTP request using treq. This basically uses treq, but parses the response
        and attempts to decode the data if it's json or msgpack.

        This must be called with 'yield'.

        It returns a dictionary with 3 keys: content and response.
           * content - The processed content. Convert JSON and msgpack to a dictionary.
           * raw_content - The raw content from server, only passed through bytes to unicode.
           * response - Raw treq response, with 'all_headers' injected; which is a cleaned up headers version of
             response.headers.
           * content_type - NOT related to HTTP headers. This will be either 'dict' if it's a dictionary, or 'string'.
           * request - The original request object. Contains attributes such as: method, uri, and headers,

        First two arguments:

        * method (str) – HTTP method. Example: 'GET', 'HEAD'. 'PUT', 'POST'.
        * url (str) – http or https URL, which may include query arguments.

        Keyword arguments for fine tuning:

        * headers (Headers or None) – Optional HTTP Headers to send with this request.
        * params (dict w/ str or list/tuple of str values, list of 2-tuples, or None.) – Optional parameters to be append as the query string to the URL, any query string parameters in the URL already will be preserved.
        * data (str, file-like, IBodyProducer, or None) – Optional request body.
        * json (dict, list/tuple, int, string/unicode, bool, or None) – Optional JSON-serializable content to pass in body.
        * persistent (bool) – Use persistent HTTP connections. Default: True
        * allow_redirects (bool) – Follow HTTP redirects. Default: True
        * auth (tuple of ('username', 'password').) – HTTP Basic Authentication information.
        * cookies (dict or CookieJar) – Cookies to send with this request. The HTTP kind, not the tasty kind.
        * timeout (int) – Request timeout seconds. If a response is not received within this timeframe, a connection is aborted with CancelledError.
        * browser_like_redirects (bool) – Use browser like redirects (i.e. Ignore RFC2616 section 10.3 and follow redirects from POST requests). Default: False
        * unbuffered (bool) – Pass True to to disable response buffering. By default treq buffers the entire response body in memory.

        :return:
        """
        logger.debug("Request receive: {method} : {url}", method=method, url=url)
        response = yield treq.request(method, url, **kwargs)
        content_type, content = yield self.process_response(response)
        return {
            'content': content,
            'response': response,
            'content_type': content_type,
            'request': response.request.original,
        }

    def clean_headers(self, response, update_response=None):
        """
        Take a treq response and get friendly headers.

        :param response:
        :return:
        """
        all_headers = {}
        raw_headers = bytes_to_unicode(response.headers._rawHeaders)
        for key, value in raw_headers.items():
            all_headers[key.lower()] = value
        if update_response is not False:
            response.all_headers = all_headers
        return all_headers

    @inlineCallbacks
    def process_response(self, response):
        """
        Receives a treq response, collects the content, and attempts to smartly decode
        the content based on the response headers.

        If headers don't match, a YomboWarning will be raised.

        :param response:
        :param headers:
        :return:
        """
        raw_content = yield treq.content(response)
        headers = self.clean_headers(response, True)
        content_type = headers['content-type'][0]
        # print("PR: content_type: %s, %s" % (content_type, raw_content))
        if content_type == CONTENT_TYPE_JSON:
            try:
                content = yield treq.json_content(response)
                content_type = "dict"
            except Exception:
                raise YomboWarning("Receive response reported json, but isn't: %s" % content)
        elif content_type == CONTENT_TYPE_MSGPACK:
            try:
                content = msgpack.loads(raw_content)
            except Exception:
                if len(content) == 0:
                    return 'dict', {}
                raise YomboWarning("Receive response reported msgpack, but isn't: %s" % content)
        else:
            content_type = "string"
            try:
                content = json.loads(raw_content)
                content_type = "dict"
            except Exception:
                try:
                    content = msgpack.loads(raw_content)
                    content_type = "dict"
                except Exception:
                    pass
        return content_type, bytes_to_unicode(content)
