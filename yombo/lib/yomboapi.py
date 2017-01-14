#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://yombo.net
"""
Manages interactions with api.yombo.net

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.11.0

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries

import msgpack
try: # python 2/3
    from urllib import quote as parse
except ImportError:
    from urllib import parse
from hashlib import sha1

try: import simplejson as json
except ImportError: import json

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
from twisted.web.client import Agent
from twisted.internet import reactor

import yombo.ext.treq as treq
from yombo.ext.expiringdict import ExpiringDict

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboWarningCredentails
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger('library.yomboapi')

class YomboAPI(YomboLibrary):

    contentType = None

    def _init_(self):
        self.custom_agent = Agent(reactor, connectTimeout=20)
        self.contentType = self._Configs.get('yomboapi', 'contenttype', 'application/json', False)  # TODO: Msgpack later
        self.base_url = self._Configs.get('yomboapi', 'baseurl', "https://api.yombo.net/api", False)
        self.allow_system_session = self._Configs.get('yomboapi', 'allow_system_session', True)
        self.init_defer = None

        self.api_key = self._Configs.get('yomboapi', 'api_key', 'aBMKp5QcQoW43ipauw88R0PT2AohcE', False)
        self.valid_system_session = None
        self.session_validation_cache = ExpiringDict()

        if self.allow_system_session:
            self.system_session = self._Configs.get('yomboapi', 'auth_session')  # to be encrypted with gpg later
            self.system_login_key = self._Configs.get('yomboapi', 'login_key')  # to be encrypted with gpg later
        else:
            self.system_session = None
            self.system_login_key = None

    def _load_(self):
        if self._Atoms['loader.operation_mode'] == 'run':
            self.init_defer = Deferred()
            self.validate_system_login()
            return self.init_defer

    def _start_(self):
        # print "system_session status: %s" % self.system_session
        # print "system_login_key status: %s" % self.system_login_key
        pass

    def _stop_(self):
        pass

    def _unload_(self):
        pass

    @inlineCallbacks
    def gateway_index(self, session=None):
        results = yield self.request("GET", "/v1/gateway", None, session)
        if results['code'] == 200:
            returnValue(results)
        elif results['code'] == 404:
            raise YomboWarning("Server cannot get gateways")
        else:
            if results['content']['message'] == "Invalid Token.":
                raise YomboWarningCredentails("URI: '%s' requires credentials." % results['content']['response']['uri'])
            raise YomboWarning("Unknown error: %s" % results['content'])

    @inlineCallbacks
    def gateway_get(self, gateway_id, session=None):
        results = yield self.request("GET", "/v1/gateway/%s" % gateway_id, None, session)
        if results['code'] == 200:
            returnValue(results)
        elif results['code'] == 404:
            raise YomboWarning("Server cannot find requested gateway: %s" % gateway_id)
        else:
            raise YomboWarning("Unknown error: %s" % results['content']['message'])

    @inlineCallbacks
    def gateway_put(self, gateway_id, values, session=None):
        results = yield self.request("PATCH", "/v1/gateway/%s" % gateway_id, values, session)
        if results['code'] == 200:
            returnValue(results)
        elif results['code'] == 404:
            raise YomboWarning("Server cannot find requested gateway: %s" % gateway_id)
        else:
            raise YomboWarning("Unknown error: %s" % results['content']['message'])

    @inlineCallbacks
    def gateway__module_get(self, gateway_id, session=None):
        results = yield self.request("GET", "/v1/gateway/%s/modules" % gateway_id, None, session)
        if results['code'] == 200:
            returnValue(results)
        elif results['code'] == 404:
            raise YomboWarning("Server cannot find requested gateway: %s" % gateway_id)
        else:
            raise YomboWarning("Unknown error: %s" % results['content']['message'])

    @inlineCallbacks
    def gateway__module_put(self, gateway_id, values, session=None):
        results = yield self.request("PATCH", "/v1/gateway/%s/modules" % gateway_id, values, session)
        if results['code'] == 200:
            returnValue(results)
        elif results['code'] == 404:
            raise YomboWarning("Server cannot find requested gateway: %s" % gateway_id)
        else:
            raise YomboWarning("Unknown error: %s" % results['content']['message'])

    @inlineCallbacks
    def gateway_config_index(self, gateway_id, session=None):
        results = yield self.request("GET", "/v1/gateway/%s/config" % gateway_id, None, session)
        if results['code'] == 200:
            returnValue(results)
        elif results['code'] == 404:
            raise YomboWarning("Server cannot get gateways")
        else:
            raise YomboWarning("Unknown error: %s" % results['content']['message'])

    # Below are the core help functions

    def save_system_session(self, session):
        print "api save_system_session0: %s" % session
        self.system_session = session
        print "api save_system_session1: %s" % session
        self._Configs.set('yomboapi', 'auth_session', session)  # to be encrypted with gpg later
        print "api save_system_session2: %s" % session

    def save_system_login_key(self, login_key):
        print "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@api save_system_login_key: %s" % login_key
        self.system_login_key = login_key
        print "api save_system_login_key1: %s" % login_key
        self._Configs.set('yomboapi', 'login_key', login_key)  # to be encrypted with gpg later
        print "api save_system_login_key2: %s" % login_key

    def select_session(self, session_id=None, session_key=None):
        if session_id is None or session_key is None:
            if self.allow_system_session:
                return self.system_session, self.system_login_key

        logger.info("select_session: Yombo API has no session data for 'selection_session'")
        return None, None

    def clear_session_cache(self, session=None):
        if (session is None):
            self.session_validation_cache.clear()
        else:
            hashed = sha1(session)
            if hashed in self.session_validation_cache:
                del self.session_validation_cache[hashed]  # None works too...

    @inlineCallbacks
    def validate_system_login(self):
        """
        Validates a system session if it exists. If not, it tries the login_key and creates a new session.

        :return:
        """
        if self.allow_system_session is False:
            self._States.set('yomboapi.valid_system_session', False)
            self.init_defer.callback(10)
            returnValue(False)

        if self.system_session is None and self.system_login_key is None:
            print "validate_system_login: self.system_session: %s" % self.system_session
            print "validate_system_login: self.system_login_key: %s" % self.system_login_key
            logger.warn("No saved system session information and no login_key. Disabling automated system changes.")
            self._States.set('yomboapi.valid_system_session', False)
            self.valid_system_session = False
            if self.init_defer is not None:
                self.init_defer.callback(10)
            returnValue(None)

        self.clear_session_cache()
        if self.system_session is not None:
            results = yield self.do_validate_session(self.system_session)
            if (results is True):
                print "has a system session!"
                self._States.set('yomboapi.valid_system_session', True)
                self.valid_system_session = True
                self.init_defer.callback(10)
                returnValue(True)

        if self.system_login_key is not None:
            results = yield self.user_login_with_key(self.system_login_key)
            print "reslts: %s" % results
            if (results is not False):
                print "has a system login key!"
                self._Configs.set('yomboapi', 'auth_session', results['session'])  # to be encrypted with gpg later
                self.system_session = results['session']
                self._States.set('yomboapi.valid_system_session', True)
                self.valid_system_session = True
                self.init_defer.callback(10)
                returnValue(True)

        print "API system has some data, but it's invalid!"
        self._States.set('yomboapi.valid_system_session', False)
        self.valid_system_session = False
        self.init_defer.callback(10)
        returnValue(False)

    @inlineCallbacks
    def validate_session(self, session_id=None, session_key=None, clear_cache=False):
        session_id, session_key = self.select_session(session_id, session_key)
        if session_id is None or session_key is None:
            logger.debug("Yombo API session information is not valid: {id}:{key}", id=session_id, key=session_key)

        hashed = sha1(session_id + session_key)
        if hashed in self.session_validation_cache:
            if clear_cache is True:
                del self.session_validation_cache[hashed]
            else:
                returnValue(self.session_validation_cache[hashed])

        results = yield self.do_validate_session(session_id, session_key)
        self.session_validation_cache[hashed] = results
        returnValue(results)

    @inlineCallbacks
    def do_validate_session(self, session):
        try:
            results = yield self.request("GET", "/v1/user/session/validate", None, session)
        except Exception, e:
            logger.debug("$$$1 API Errror: {error}", error=e)
            returnValue(False)


        logger.debug("$$$a REsults from API: {results}", results=results['content'])
# waiting on final API.yombo.com to complete this.  If we get something, we are good for now.

        if (results['content']['code'] != 200):
            returnValue(False)
        elif (results['content']['response']['session_status'] == 'valid'):
            returnValue(True)
        else:
            returnValue(False)

    @inlineCallbacks
    def user_login_with_key(self, login_key):
        results = yield self.request("POST", "/v1/user/login", {'login_key': login_key}, False)
        try:
            results = yield self.request("POST", "/v1/user/login", {'login_key': login_key}, False)
        except Exception, e:
            logger.debug("$$$2 API Errror: {error}", error=e)
            returnValue(False)

        logger.debug("$$$ Results from API for login w key: {results}", results=results['content'])
        # waiting on final API.yombo.com to complete this.  If we get something, we are good for now.

        if (results['content']['code'] != 200):
            returnValue(False)
        elif (results['content']['message'] == 'Logged in'):
            returnValue(results['content']['response']['login'])
        else:
            returnValue(False)

    @inlineCallbacks
    def user_login_with_credentials(self, username, password):
        credentials = { 'username':username, 'password':password}
        results = yield self.request("POST", "/v1/user/login", {'username':username, 'password':password}, False)
        logger.debug("$$$3 REsults from API login creds: {results}", results=results)

        # print "results:::::::::::::::::  %s" % results
        if (results['content']['code'] != 200):
            returnValue(False)
        elif (results['content']['message'] == 'Logged in'):
            returnValue(results['content']['response']['login'])
        else:
            returnValue(False)

    @inlineCallbacks
    def gateways(self, session_info=None):
        results = yield self.request("GET", "/v1/gateway")
        logger.debug("$$$4 REsults from API: {results}", results=results)

        if results['Code'] == 200:  # life is good!
            returnValue(results['Response']['Gateway'])
        else:
            returnValue(False)

    def make_headers(self, session):
        headers = {
            'Content-Type': self.contentType,
            'Authorization': 'Yombo-Gateway-v1',
            'x-api-key': self.api_key,
        }
        if session is not None:
            headers['Authorization'] = 'Bearer %s' % session

        for k, v in headers.iteritems():
            headers[k] = v.encode('utf-8')
        return headers

    def errorHandler(self,result):
        raise YomboWarning("Problem with request: %s" % result)

    @inlineCallbacks
    def request(self, method, path, data=None, session=None):
        # print "base_url: %s" % self.base_url
        # print "path: %s" % path
        path = self.base_url + path
        # print "method: %s" % method
        print "path full: %s" % path
        # print "session: %s" % session
        # if session is False:
        #     session = None
        if session is None:
            if self.system_session is None:
                if self.validate_system_login() is False:
                    raise YomboWarningCredentails("Yombo request needs an API session.")
            session = self.system_session
        if session is False:
            session = None
        results = None
        # print "session2: %s" % session
        headers = self.make_headers(session)

        if method == 'GET':
            results = yield self.__get(path, headers, data)
        elif method == 'POST':
            results = yield self.__post(path, headers, data)
        elif method == 'PATCH':
            results = yield self.__patch(path, headers, data)
        elif method == 'PUT':
            results = yield self.__put(path, headers, data)
        elif method == 'DELETE':
            results = yield self.__delete(path, headers, data)
        else:
            raise Exception("Bad request type?? %s: %s" % (method, path) )


#        print "request api results: %s" % results
        returnValue(results)

    @inlineCallbacks
    def __get(self, path, headers, args=None):
        path = path
        # response = yield treq.get(path, params=args, agent=self.custom_agent, headers=headers)
        response = yield treq.get(path, headers=headers, params=args)
        content = yield treq.content(response)
        logger.debug("getting URL: {path}  headers: {headers}", path=path, agent=self.custom_agent, headers=headers)
        final_response = self.decode_results(content, self.response_headers(response), response.code, response.phrase)
        returnValue(final_response)

    @inlineCallbacks
    def __patch(self, path, headers, data):
        response = yield treq.patch(path, data=data, agent=self.custom_agent, headers=headers)
        content = yield treq.content(response)
        final_response = self.decode_results(content, self.response_headers(response), response.code, response.phrase)
        returnValue(final_response)

    @inlineCallbacks
    def __post(self, path, headers, data):
        response = yield treq.post(path, data=data, agent=self.custom_agent, headers=headers)
        content = yield treq.content(response)
        final_response = self.decode_results(content, self.response_headers(response), response.code, response.phrase)
        returnValue(final_response)

    @inlineCallbacks
    def __put(self, path, headers, data):
        response = yield treq.put(path, data=data, agent=self.custom_agent, headers=headers)
        content = yield treq.content(response)
        final_response = self.decode_results(content, self.response_headers(response), response.code, response.phrase)
        returnValue(final_response)

    @inlineCallbacks
    def __delete(self, path, headers, args={}):
        response = yield treq.put(path, params=args, agent=self.custom_agent, headers=headers)
        content = yield treq.content(response)
        final_response = self.decode_results(content, self.response_headers(response), response.code, response.phrase)
        returnValue(final_response)

    def __encode(self, data):
        return json.dumps(data)

    def response_headers(self, response):
        data = {}
        for key, value in response.headers._rawHeaders.iteritems():
            data[key.lower()] = value
        return data

    def decode_results(self, content, headers, code, phrase):
        # print "raw headers: %s" % response.headers
        # print "decoded headers: %s" % headers
        # print "headers: %s" % headers['content-type'][0]

        content_type = headers['content-type'][0]

        # print "######  content: %s" % content
        if content_type == 'application/json':
            if self.is_json(content):
                content = json.loads(content)
                content_type = "dict"
            else:
                raise YomboWarning("Receive yombo api response reported json, but isn't: %s" % content)
        elif content_type == 'application/msgpack':
            if self.is_msgpack(content):
                content = msgpack.loads(content)
                content_type = "dict"
            else:
                raise YomboWarning("Receive yombo api response reported msgpack, but isn't.")
        else:
            if self.is_json(content):
                content = json.loads(content)
                content_type = "dict"
            elif self.is_msgpack(content):
                content = msgpack.loads(content)
                content_type = "dict"
            else:
                content_type = "string"

        # print "!!!!!!!!!!!!!!content: %s" % content

        results = {
            'content': content,
            'content_type': content_type,
            'code': code,
            'phrase': phrase,
            'headers': headers,
        }
        if 'response' in content:
            if 'locator' in content['response']:
                results['data'] = content['response'][content['response']['locator']]
            else:
                results['data'] = []
        return results

    def is_json(self, myjson):
        """
        Helper function to determine if data is json or not.

        :param myjson:
        :return:
        """
        try:
            json_object = json.loads(myjson)
        except ValueError, e:
            return False
        return True

    def is_msgpack(self, mymsgpack):
        """
        Helper function to determine if data is msgpack or not.

        :param mymsgpack:
        :return:
        """
        try:
            json_object = msgpack.loads(mymsgpack)
        except ValueError, e:
            return False
        return True