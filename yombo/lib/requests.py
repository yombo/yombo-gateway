#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://yombo.net
"""

.. note::

  * For library documentation, see: `Requests @ Library Documentation <https://yombo.net/docs/libraries/requests>`_


A friendly HTTP helper. Uses treq to process requests. Also provides various helper functions to massage data
even if this library wasn't used to make the request.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.22.0

:copyright: Copyright 2018-2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/requests.html>`_
"""
# Import python libraries
import json
import msgpack
import traceback
import treq

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet.error import ConnectionRefusedError, ConnectError

# Import Yombo libraries
from yombo.constants import VERSION
from yombo.constants.requests import HEADER_AUTHORIZATION, HEADER_CONTENT_TYPE, HEADER_USER_AGENT, HEADER_X_API_KEY
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import bytes_to_unicode
from yombo.classes.caseinsensitivedict import CaseInsensitiveDict

from yombo.constants import CONTENT_TYPE_MSGPACK

logger = get_logger("library.requests")


class Requests(YomboLibrary):

    def make_headers(self, session, session_type):
        headers = {
            HEADER_CONTENT_TYPE: self.contentType,
            HEADER_AUTHORIZATION: f"Yombo-Gateway-{VERSION}",
            HEADER_X_API_KEY: self.api_key,
            HEADER_USER_AGENT: f"yombo-gateway-{VERSION}",
        }
        if session is not None:
            headers["Authorization"] = f"{session_type} {session}"

        return headers

    def errorHandler(self,result):
        raise YomboWarning(f"Problem with request: {result}")

    @inlineCallbacks
    def request(self, method, url, **kwargs):
        """
        Make an HTTP request using treq. This basically uses treq, but parses the response
        and attempts to decode the data if it's json or msgpack.

        This must be called with "yield".

        It returns a dictionary with these keys:
           * content - The processed content. Convert JSON and msgpack to a dictionary.
           * content_raw - The raw content from server, only passed through bytes to unicode.
           * response - Raw treq response, with "all_headers" injected; which is a cleaned up headers version of
             response.headers.
           * content_type - NOT related to HTTP headers. This will be either "dict" if it's a dictionary, or "string".
           * request - The original request object. Contains attributes such as: method, uri, and headers,

        First two arguments:

        * method (str) – HTTP method. Example: "GET", "HEAD". "PUT", "POST".
        * url (str) – http or https URL, which may include query arguments.

        Keyword arguments for fine tuning:

        * headers (Headers or None) – Optional HTTP Headers to send with this request.
        * params (dict w/ str or list/tuple of str values, list of 2-tuples, or None.) – Optional parameters to be append as the query string to the URL, any query string parameters in the URL already will be preserved.
        * data (str, file-like, IBodyProducer, or None) – Optional request body.
        * json (dict, list/tuple, int, string/unicode, bool, or None) – Optional JSON-serializable content to pass in body.
        * persistent (bool) – Use persistent HTTP connections. Default: True
        * allow_redirects (bool) – Follow HTTP redirects. Default: True
        * auth (tuple of ("username", "password").) – HTTP Basic Authentication information.
        * cookies (dict or CookieJar) – Cookies to send with this request. The HTTP kind, not the tasty kind.
        * timeout (int) – Request timeout seconds. If a response is not received within this timeframe, a connection is aborted with CancelledError.
        * browser_like_redirects (bool) – Use browser like redirects (i.e. Ignore RFC2616 section 10.3 and follow redirects from POST requests). Default: False
        * unbuffered (bool) – Pass True to to disable response buffering. By default treq buffers the entire response body in memory.

        :return:
        """
        logger.debug("Request receive: {method} : {url}", method=method, url=url)
        method = method.upper()
        try:
            treq_response = yield treq.request(method, url, **kwargs)
        except ConnectionRefusedError as e:
            raise YomboWarning(f"Connection was refused to '{url}': {e}")
        except ConnectError as e:
            raise YomboWarning(f"Error connecting to '{url}': {e}")
        except Exception as e:
            logger.info("Requests error: {error}", error=e)
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{method} {url}", method=method, url=url)
            logger.error("{trace}", trace=traceback.format_exc())
            logger.error("--------------------------------------------------------")
            logger.warn("An exception of type {etype} occurred in yombo.lib.yomboapi:import_component. Message: {msg}",
                        etype=type(e), msg=e)
            logger.error("--------------------------------------------------------")
            raise e

        response = WebResponse(self)
        yield response.process_response(treq_response)
        return response


class WebResponse(object):
    def __init__(self, parent):
        self._Parent = parent
        self.request = None
        self.content = None
        self.content_raw = None
        self.response = None
        self.content_type = None
        self.response_phrase = None
        self.response_code = None
        self.headers = None

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
        content = raw_content
        headers = self.clean_headers(response, True)

        if HEADER_CONTENT_TYPE in headers:
            content_type = headers[HEADER_CONTENT_TYPE][0]
        else:
            content_type = None
        if content_type == HEADER_CONTENT_TYPE:
            try:
                content = yield treq.json_content(response)
                content_type = "dict"
            except Exception as e:
                raise YomboWarning(f"Receive response reported json, but found an error: {e}")
        elif content_type == CONTENT_TYPE_MSGPACK:
            try:
                content = msgpack.loads(raw_content)
            except Exception:
                if len(content) == 0:
                    return "dict", {}
                raise YomboWarning(f"Receive response reported msgpack, but isn't: {content}")
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
                    content = raw_content

        content = bytes_to_unicode(content)
        # return {
        #     "content_type": content_type,
        #     "headers": response.all_headers,
        # }

        self.content = bytes_to_unicode(content)
        self.content_raw = raw_content
        self.request = response.request.original
        self.response = response
        self.content_type = content_type
        self.response_phrase = bytes_to_unicode(response.phrase)
        self.response_code = response.code
        self.headers = headers

    def clean_headers(self, response, update_response=None):
        """
        Take a treq response and get friendly headers.

        :param response:
        :return:
        """
        all_headers = CaseInsensitiveDict()
        raw_headers = bytes_to_unicode(response.headers._rawHeaders)
        for key, value in raw_headers.items():
            all_headers[key.lower()] = value[0]
        if update_response is not False:
            response.all_headers = all_headers
        return all_headers
