#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://yombo.net
"""

.. note::

  For more information see: `YomboAPI @ Module Development <https://yombo.net/docs/libraries/yomboapi>`_


Manages interactions with api.yombo.net

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.11.0

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/yomboapi.html>`_
"""
# Import python libraries
import msgpack
try:
    from hashlib import sha3_224 as sha224
except ImportError:
    from hashlib import sha224
import treq

try: import simplejson as json
except ImportError: import json

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.web.client import Agent
from twisted.internet import reactor

# Import Yombo libraries
from yombo.constants import VERSION
from yombo.ext.expiringdict import ExpiringDict
from yombo.core.exceptions import YomboWarning, YomboWarningCredentails
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import bytes_to_unicode, unicode_to_bytes

logger = get_logger('library.yomboapi')

class YomboAPI(YomboLibrary):
    @property
    def valid_api_auth(self):
        try:
            return self._States.get('yomboapi.valid_api_auth')
        except KeyError:
            return None

    @valid_api_auth.setter
    def valid_api_auth(self, val):
        return self._States.set('yomboapi.valid_api_key', val)

    @property
    def api_auth(self):
        return self._api_auth

    @api_auth.setter
    def api_auth(self, val):
        self._api_auth = val
        self._Configs.set('core', 'api_auth', val)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo Yombo API library"

    def _init_(self, **kwargs):
        self.init_defer = None
        self.session_validation_cache = ExpiringDict()
        self.custom_agent = Agent(reactor, connectTimeout=20)
        self.contentType = self._Configs.get('yomboapi', 'contenttype', 'application/json', False)  # TODO: Msgpack later
        self.base_url = self._Configs.get('yomboapi', 'baseurl', "https://api.yombo.net/api", False)

        self.gateway_id = self._Configs.get2('core', 'gwid', 'local', False)
        self.gateway_hash = self._Configs.get2('core', 'gwhash', None, False)

        self.api_key = self._Configs.get('yomboapi', 'api_key', 'gd9mDxJlLdEwhKwxwyPfFksTEnRE5k', False)
        self._api_auth = self._Configs.get('core', 'api_auth', None, False)  # to be encrypted with gpg later
        self.valid_api_auth = False

        if self._Loader.operating_mode == 'run':
            self.init_defer = Deferred()
            self.validate_api_auth()
            return self.init_defer

    def clear_session_cache(self, session=None):
        if session is None:
            self.session_validation_cache.clear()
        else:
            hashed = sha224(session)
            if hashed in self.session_validation_cache:
                del self.session_validation_cache[hashed]  # None works too...

    @inlineCallbacks
    def validate_api_auth(self):
        """
        Validates that the system has a valid api auth key.

        If the system session is invalid or expired, it will attempt to request a new api_auth key using
        gateway credentials.

        If the system is unable to complete this, the system will exit.

        :return:
        """
        logger.debug("About to validate api auth: %s" % self.api_auth)

        if self.valid_api_auth is not True:
            if self.api_auth is not None:
                results = yield self.do_validate_api_auth()
                logger.debug("Do Validate Session results: {results}", results=results)
            else:
                results = False

            if results is True:
                logger.debug("System has a valid api auth token.")
                self.valid_api_auth = True
            else:
                logger.debug("System doesn't have a valid api auth token, will attempt to get one.")
                results = yield self.new_gateway_api_auth()
                logger.debug("Gateway login wit h key full results: {results}", results=results)
                if results is False:
                    self.valid_api_auth = False
                    logger.warn("System has an invalid api auth token.")
                else:
                    new_session = results['response']['gateway_api_auth']
                    logger.debug("System now has a valid auth token.")
                    self.api_auth = new_session
                    self.valid_api_auth = True

        if self.init_defer is not None:
            self.init_defer.callback(10)

    @inlineCallbacks
    def do_validate_api_auth(self):
        gateway_id = self.gateway_id()
        gateway_hash = self.gateway_hash()
        try:
            results = yield self.request("POST", "/v1/gateway/%s/check_api_auth" % gateway_id,
                                         {'gw_hash': gateway_hash,
                                          'api_auth': self.api_auth})
        except Exception as e:
            logger.debug("do_validate_api_auth API Error: {error}", error=e)
            return False

        if (results['content']['code'] != 200):
            return False
        else:
            return results['content']['response']['gateway_api_auth']

    @inlineCallbacks
    def new_gateway_api_auth(self):
        gateway_id = self.gateway_id()
        gateway_hash = self.gateway_hash()
        try:
            results = yield self.request("POST", "/v1/gateway/%s/new_api_auth" % gateway_id,
                                         {'gw_hash': gateway_hash})
        except Exception as e:
            logger.debug("$$$1 API Errror: {error}", error=e)
            return False

        logger.info("new_gateway_api_auth Results from API for login w key: {results}", results=results)

        if results['content']['code'] != 200:
            return False
        else:
            return results['content']

    @inlineCallbacks
    def do_validate_login_key(self, login_key):
        try:
            results = yield self.request("POST", "/v1/user/login_key/validate", {'login_key': login_key})
        except Exception as e:
            logger.debug("do_validate_login_key API Errror: {error}", error=e)
            return False

        # logger.debug("Login key results: REsults from API: {results}", results=results['content'])
        # waiting on final API.yombo.com to complete this.  If we get something, we are good for now.

        if (results['content']['code'] != 200):
            return False
        else:
            return results['data']

    @inlineCallbacks
    def do_validate_session(self, session):
        try:
            results = yield self.request("POST", "/v1/user/session/validate", {'session': session})
            # results = yield self.request("GET", "/v1/user/session/validate", None, session=session)
        except Exception as e:
            logger.debug("$$$1 API Errror: {error}", error=e)
            return False

        # logger.debug("do_validate_session full results: {results}", results=results['content'])
        # waiting on final API.yombo.com to complete this.  If we get something, we are good for now.

        if (results['content']['code'] != 200):
            return False
        else:
            return results['content']['response']['login']

    @inlineCallbacks
    def user_login_with_key(self, login_key):
        try:
            results = yield self.request("POST", "/v1/user/login", {'login_key': login_key}, False)
        except Exception as e:
            logger.debug("$$$2 API Errror: {error}", error=e)
            return False

        # logger.info("user_login_with_key Results from API for login w key: {results}", results=results['content'])
        # waiting on final API.yombo.com to complete this.  If we get something, we are good for now.

        if results['content']['code'] != 200:
            return False
        elif results['content']['message'] != 'Logged in':
            return False
        else:
            return results['content']

    @inlineCallbacks
    def user_login_with_credentials(self, username, password, g_recaptcha_response):
        results = yield self.request(
            "POST",
            "/v1/user/login",
            {
                'username': username,
                'password':password,
                'g-recaptcha-response': g_recaptcha_response
            },
            False
        )

        if results['content']['code'] != 200:
            return False
        elif results['content']['message'] != 'Logged in':
            return False
        else:
            return results['content']

    @inlineCallbacks
    def gateways(self, session_info=None):
        results = yield self.request("GET", "/v1/gateway")
        logger.debug("$$$4 REsults from API: {results}", results=results)

        if results['Code'] == 200:  # life is good!
            return results['Response']['Gateway']
        else:
            return False

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
    def request(self, method, path, data=None, session=None):
        path = self.base_url + path

        logger.debug("{method}: {path}: {data}", method=method, path=path, data=data)
        session_type = None
        if session is None:
            if self.api_auth is None:
                if self.valid_api_auth is False:
                    raise YomboWarningCredentails("Yombo API::request has no valid API credentials.")
            session = "%s:%s" % (self.gateway_id(), self.api_auth)
            session_type = 'Gateway'
        elif session is False:
            session = None
        else:
            session_type = 'Bearer'


        logger.debug("session: {session_type} - {session}", session_type=session_type, session=session)
        headers = self.make_headers(session, session_type)
        logger.debug("headers: {headers}", headers=headers)
        if data is not None:
            data = json.dumps(data).encode()
        logger.debug("yombo api request headers: {headers}", headers=headers)
        logger.debug("yombo api request data: {data}", data=data)

        if method == 'GET':
            results = yield self._get(path, headers, data)
        elif method == 'POST':
            results = yield self._post(path, headers, data)
        elif method == 'PATCH':
            results = yield self._patch(path, headers, data)
        elif method == 'PUT':
            results = yield self._put(path, headers, data)
        elif method == 'DELETE':
            results = yield self._delete(path, headers, data)
        else:
            raise Exception("Bad request type?? %s: %s" % (method, path) )

        return results

    @inlineCallbacks
    def _get(self, path, headers, args=None):
        path = path
        # response = yield treq.get(path, params=args, agent=self.custom_agent, headers=headers)
        response = yield treq.get(path, headers=headers, params=args)
        content = yield treq.content(response)
        # logger.debug("getting URL: {path}  headers: {headers}", path=path, agent=self.custom_agent, headers=headers)
        final_response = self.decode_results(content, self.response_headers(response), response.code, response.phrase)
        return final_response

    @inlineCallbacks
    def _patch(self, path, headers, data):
        # print("yapi patch called. path: %s... headers: %s... data: %s" % (path, headers, data))
        response = yield treq.patch(path, data=data, agent=self.custom_agent, headers=headers)
        content = yield treq.content(response)
        final_response = self.decode_results(content, self.response_headers(response), response.code, response.phrase)
        return final_response

    @inlineCallbacks
    def _post(self, path, headers, data):
        # print("yapi post called. path: %s... headers: %s... data: %s" % (path, headers, data))

        response = yield treq.post(path, data=data, agent=self.custom_agent, headers=headers)
        content = yield treq.content(response)
        final_response = self.decode_results(content, self.response_headers(response), response.code, response.phrase)
        # print("dddd: %s" % final_response)
        return final_response

    @inlineCallbacks
    def _put(self, path, headers, data):
        response = yield treq.put(path, data=data, agent=self.custom_agent, headers=headers)
        content = yield treq.content(response)
        final_response = self.decode_results(content, self.response_headers(response), response.code, response.phrase)
        return final_response

    @inlineCallbacks
    def _delete(self, path, headers, args={}):
        response = yield treq.delete(path, params=args, agent=self.custom_agent, headers=headers)
        content = yield treq.content(response)
        final_response = self.decode_results(content, self.response_headers(response), response.code, response.phrase)
        return final_response

    def response_headers(self, response):
        data = {}
        raw_headers = bytes_to_unicode(response.headers._rawHeaders)
        for key, value in raw_headers.items():
            data[key.lower()] = value
        return data

    def decode_results(self, content, headers, code, phrase):
        # print("decode_results headers: %s" % headers)

        # print(content)
        content_type = headers['content-type'][0]
        phrase = bytes_to_unicode(phrase)

        # print( "######  content: %s" % content)
        if content_type == 'application/json':
            try:
                content = json.loads(content)
                content_type = "dict"
            except Exception:
                raise YomboWarning("Receive yombo api response reported json, but isn't: %s" % content)
        elif content_type == 'application/msgpack':
            try:
                content = msgpack.loads(content)
                content_type = "dict"
            except Exception:
                raise YomboWarning("Receive yombo api response reported msgpack, but isn't.")
        else:
            try:
                content = json.loads(content)
                content_type = "dict"
            except Exception:
                try:
                    content = msgpack.loads(content)
                    content_type = "dict"
                except Exception:
                    content_type = "string"
        # print("decode content: %s" % content)
        content = bytes_to_unicode(content)

        if code >= 300:
            logger.warn("error with request: {content}", content=content)
            if 'message' in content:
                message = content['message']
            else:
                message = phrase
            if 'html_message' in content:
                html_message = content['html_message']
            else:
                html_message = phrase

            raise YomboWarning(message, code, 'decode_results', 'Yomboapi', html_message=html_message)
        results = {
            'status': 'ok',
            'content': content,
            'content_type': content_type,
            'code': code,
            'phrase': phrase,
            'headers': headers,
        }

        if content_type == "string":
            logger.warn("Error content: {content}", content=content)
            raise YomboWarning('Unknown api error', content['code'], html_message='Unknown api error')
        else:
            if 'response' in content:
                if 'locator' in content['response']:
                    results['data'] = content['response'][content['response']['locator']]
                else:
                    results['data'] = []

            # Check if there was any errors, if so, raise something.
            return results
