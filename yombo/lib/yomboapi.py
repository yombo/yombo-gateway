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
from hashlib import sha224

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.web.client import Agent
from twisted.internet import reactor

# Import Yombo libraries
from yombo.constants import VERSION
from yombo.core.exceptions import YomboWarning, YomboAPICredentials, YomboRestart
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import bytes_to_unicode

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
    def request(self, method, request_url, request_data=None, session=None, session_type=None):
        url = self.base_url + request_url

        logger.debug("{method}: {path}: {request_data}", method=method, url=url, request_data=request_data)
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
        logger.debug("yombo api request headers: {headers}", headers=headers)
        logger.debug("yombo api request request_data: {request_data}", request_data=request_data)
        treq_results = yield self._Requests.request(method, url, headers=headers, json=request_data, timeout=30)

        final_response = self.decode_results(method, url, treq_results, headers, request_data)
        return final_response

    def decode_results(self, method, url, treq_results, request_headers, request_data):
        content = treq_results['content']
        response = treq_results['response']
        content_type = treq_results['content_type']
        response_phrase = bytes_to_unicode(response.phrase)
        response_code = response.code
        if response_code >= 300:
            logger.warn("-----==( Error: API received an invalid response )==----")
            logger.warn("URL: {method} {url}", method=method, url=url)
            logger.warn("Header: {request_headers}", request_headers=request_headers)
            logger.warn("Data sent: {request_data}", request_data=request_data)
            logger.warn("Content: {content}", content=content)
            logger.warn("--------------------------------------------------------")

            if 'message' in content:
                message = content['message']
            else:
                message = response_phrase
            if 'html_message' in content:
                html_message = content['html_message']
            else:
                html_message = response_phrase

            raise YomboWarning(message, response_code, 'decode_results', 'Yomboapi', html_message=html_message, details=content)

        results = {
            'status': 'ok',
            'content': content,
            'content_type': content_type,
            'code': response_code,
            'phrase': response_phrase,
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

            return results
