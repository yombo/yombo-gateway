#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://yombo.net
"""

.. note::

  * For library documentation, see: `YomboAPI @ Library Documentation <https://yombo.net/docs/libraries/yomboapi>`_


Manages interactions with api.yombo.net

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.11.0

:copyright: Copyright 2016-2018 by Yombo.
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
from twisted.internet.defer import inlineCallbacks
from twisted.web.client import Agent
from twisted.internet import reactor

# Import Yombo libraries
from yombo.constants import VERSION
# from yombo.ext.expiringdict import ExpiringDict
from yombo.core.exceptions import YomboWarning, YomboAPICredentials, YomboRestart
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import bytes_to_unicode, unicode_to_bytes
from yombo.constants import CONTENT_TYPE_JSON, CONTENT_TYPE_MSGPACK

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
        return self._States.set('yomboapi.valid_api_key', val, value_type='bool', source=self)

    @property
    def api_auth(self):
        return self._api_auth()

    @api_auth.setter
    def api_auth(self, val):
        self._Configs.set('core', 'api_auth', val)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo API library"

    def _init_(self, **kwargs):
        self.session_validation_cache = self._Cache.lru(maxsize=64, tags=('sessions', 'api'))
        self.custom_agent = Agent(reactor, connectTimeout=20)
        self.contentType = self._Configs.get('yomboapi', 'contenttype', CONTENT_TYPE_JSON, False)  # TODO: Msgpack later
        self.base_url = self._Configs.get('yomboapi', 'baseurl', "https://api.yombo.net/api", False)

        self.gateway_id = self._Configs.get2('core', 'gwid', 'local', False)
        self.gateway_hash = self._Configs.get2('core', 'gwhash', None, False)

        self.api_key = self._Configs.get('yomboapi', 'api_key', '4Pz5CwKQCsexQaeUvhJnWAFO6TRa9SafnpAQfAApqy9fsdHTLXZ762yCZOct', False)
        self._api_auth = self._Configs.get2('core', 'api_auth', None, False)  # to be encrypted with gpg later
        self.valid_api_auth = False

    def clear_session_cache(self, session=None):
        if session is None:
            self._Cache.clear(self.session_validation_cache)
        else:
            hashed = sha224(session)
            if hashed in self.session_validation_cache:
                del self.session_validation_cache[hashed]

    @inlineCallbacks
    def check_gateway_auth_valid(self):
        """
        Validate that the current gateway id / hash is valid. It's basically checking to see
        the current username/password for the gateway is valid.

        Returns True/False.

        :return:
        """
        logger.debug("About to validate api auth: %s" % self.api_auth)

        if self.api_auth is not None:
            gateway_id = self.gateway_id()
            gateway_hash = self.gateway_hash()
            try:
                results = yield self.request("POST", "/v1/gateway/%s/check_hash" % gateway_id,
                                             {
                                                'gw_hash': gateway_hash,
                                             }
                                             )

            except Exception as e:
                logger.debug("check_gateway_auth_valid API Error: {error}", error=e)
                return False
            else:
                data = results['data']
                if data['gw_hash'] is False or data['api_auth'] is False:
                    return False
                else:
                    return True
        return False

    @inlineCallbacks
    def check_if_new_gateway_credentials_needed(self, session):
        if self.valid_api_auth is False:
            yield self.get_new_gateway_credentials(session)

    @inlineCallbacks
    def check_gateway_api_auth_valid(self, session=None):
        """
        check_gateway_auth_valid above, but checks that the session is valid for this gateway.

        Returns True/False.

        :return:
        """
        logger.debug("About to validate api auth: %s" % self.api_auth)

        if self.api_auth is not None:
            gateway_id = self.gateway_id()
            gateway_hash = self.gateway_hash()
            try:
                results = yield self.request("POST", "/v1/gateway/%s/check_api_auth" % gateway_id,
                                             {
                                                'gw_hash': gateway_hash,
                                                'api_auth': self.api_auth
                                             },
                                             session=session,
                                             )

            except Exception as e:
                logger.debug("check_gateway_api_auth_valid API Error: {error}", error=e)
                self.valid_api_auth = False
            else:
                data = results['data']
                if data['gw_hash'] is False or data['api_auth'] is False:
                    self.valid_api_auth = False
                else:
                    self.valid_api_auth = True
        else:
            self.valid_api_auth = False

        logger.debug("Do Validate Session results: {results}", results=self.valid_api_auth)
        return self.valid_api_auth

    @inlineCallbacks
    def get_new_gateway_credentials(self, session=None, session_type=None):
        """
        Get new auth information for the current gateway. This includes the gateway's uuid, gateway hash, and
        api_auth token.

        If session is provided, it will use that information to collect the new tokens.

        :param session: Session string to use.
        :param session_type: Type of session.
        :return:
        """
        try:
            results = yield self.request("GET", "/v1/gateway/%s/new_hash" % self.gateway_id(),
                                         session=session,
                                         session_type=session_type)
        except Exception as e:
            return False
        data = results['data']
        logger.info("Gateway new hash results: {data}", data=data)
        logger.info("System now has a valid auth token.")
        self.api_auth = data['api_auth']
        self._Configs.set('core', 'api_auth', data['api_auth'])
        self._Configs.set('core', 'gwhash', data['hash'])
        self._Configs.set('core', 'gwuuid', data['uuid'])
        self.valid_api_auth = True
        results = yield self.check_gateway_api_auth_valid()
        if results:
            yield self._Configs.save(force_save=True)
            raise YomboRestart("Mandatory gateway restart happening now.")
        else:
            raise YomboWarning("Unable to get new gateway authentication information.")

    @inlineCallbacks
    def validate_login_key(self, login_key):
        try:
            results = yield self.request("POST", "/v1/user/login_key/validate", {'login_key': login_key})
        except Exception as e:
            logger.debug("validate_login_key API Errror: {error}", error=e)
            return False

        if (results['content']['code'] != 200):
            return False
        else:
            return results['data']

    @inlineCallbacks
    def validate_session(self, session):
        try:
            results = yield self.request("POST", "/v1/user/session/validate", {'session': session})
            # results = yield self.request("GET", "/v1/user/session/validate", None, session=session)
        except Exception as e:
            logger.debug("$$$1 API Errror: {error}", error=e)
            return False

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
    def request(self, method, path, data=None, session=None, session_type=None):
        path = self.base_url + path

        logger.debug("{method}: {path}: {data}", method=method, path=path, data=data)
        if session is None:
            if self.api_auth is None:
                if self.valid_api_auth is False:
                    raise YomboAPICredentials("Yombo API::request has no valid API credentials.")
            session = "%s:%s" % (self.gateway_id(), self.api_auth)
            session_type = 'Gateway'
        elif session is False:
            session = None

        if session_type is None:
            session_type = 'Bearer'

        logger.debug("session: {session_type} {session}", session_type=session_type, session=session)
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
            raise YomboWarning("Bad request type?? %s: %s" % (method, path) )

        return results

    @inlineCallbacks
    def _get(self, path, headers, args=None):
        path = path
        # response = yield treq.get(path, params=args, agent=self.custom_agent, headers=headers)
        response = yield treq.get(path, headers=headers, params=args)
        content = yield treq.content(response)
        # logger.debug("getting URL: {path}  headers: {headers}", path=path, agent=self.custom_agent, headers=headers)
        final_response = self.decode_results('get', content, self.response_headers(response), response.code,
                                             response.phrase, path, headers, args)
        return final_response

    @inlineCallbacks
    def _patch(self, path, headers, args):
        response = yield treq.patch(path, data=args, agent=self.custom_agent, headers=headers)
        content = yield treq.content(response)
        final_response = self.decode_results('patch', content, self.response_headers(response), response.code,
                                             response.phrase, path, headers, args)
        return final_response

    @inlineCallbacks
    def _post(self, path, headers, args):
        response = yield treq.post(path, data=args, agent=self.custom_agent, headers=headers)
        content = yield treq.content(response)
        final_response = self.decode_results('post', content, self.response_headers(response), response.code,
                                             response.phrase, path, headers, args)
        return final_response

    @inlineCallbacks
    def _put(self, path, headers, args):
        response = yield treq.put(path, data=args, agent=self.custom_agent, headers=headers)
        content = yield treq.content(response)
        final_response = self.decode_results('put', content, self.response_headers(response), response.code,
                                             response.phrase, path, headers, args)
        return final_response

    @inlineCallbacks
    def _delete(self, path, headers, args={}):
        response = yield treq.delete(path, params=args, agent=self.custom_agent, headers=headers)
        content = yield treq.content(response)
        final_response = self.decode_results('delete', content, self.response_headers(response), response.code,
                                             response.phrase, path, headers, args)
        return final_response

    def response_headers(self, response):
        data = {}
        raw_headers = bytes_to_unicode(response.headers._rawHeaders)
        for key, value in raw_headers.items():
            data[key.lower()] = value
        return data

    def decode_results(self, request_type, content, response_headers, code, phrase, path, request_headers, args):
        content_type = response_headers['content-type'][0]
        phrase = bytes_to_unicode(phrase)

        if content_type == CONTENT_TYPE_JSON:
            try:
                content = json.loads(content)
                content_type = "dict"
            except Exception:
                raise YomboWarning("Receive yombo api response reported json, but isn't: %s" % content)
        elif content_type == CONTENT_TYPE_MSGPACK:
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
        content = bytes_to_unicode(content)

        if code >= 300:
            logger.warn("-----==( Error: API received an invalid response )==----")
            logger.warn("Path: {request_type} {path}", request_type=request_type, path=path)
            logger.warn("Header: {request_headers}", request_headers=request_headers)
            logger.warn("Data sent: {args}", args=args)
            logger.warn("Content: {content}", content=content)
            logger.warn("--------------------------------------------------------")

            if 'message' in content:
                message = content['message']
            else:
                message = phrase
            if 'html_message' in content:
                html_message = content['html_message']
            else:
                html_message = phrase

            raise YomboWarning(message, code, 'decode_results', 'Yomboapi', html_message=html_message, details=content)
        results = {
            'status': 'ok',
            'content': content,
            'content_type': content_type,
            'code': code,
            'phrase': phrase,
            'headers': request_headers,
        }

        if content_type == "string":
            logger.warn("Error content: {content}", content=content)
            raise YomboWarning('Unknown api error', content['code'], html_message='Unknown api error', details=content)
        else:
            if 'response' in content:
                if 'locator' in content['response']:
                    results['data'] = content['response'][content['response']['locator']]
                else:
                    results['data'] = []

            # Check if there was any errors, if so, raise something.
            return results
