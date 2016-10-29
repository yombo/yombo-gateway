"""
Manages interactions with api.yombo.net.

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
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger('library.yomboapi')

class YomboAPI(YomboLibrary):

    contentType = None

    def _init_(self):
        self.custom_agent = Agent(reactor, connectTimeout=20)
        self.contentType = self._Configs.get('api', 'contenttype', 'application/json', False)  # TODO: Msgpack later
        self.base_url = self._Configs.get('api', 'baseurl', "https://api.yombo.net/api", False)
        self.allow_system_session = self._Configs.get('yomboapi', 'allow_system_session', True)
        self.api_key = self._Configs.get('yomboapi', 'api_key', 'pZEi9fbEuU4bTpxs', False)
        self.load_deferred = None  # Prevents loader from moving on past _load_ until we are done.
        self.valid_system_session = None
        self.session_validation_cache = ExpiringDict()
        if self.allow_system_session:
            self.auth_session_id = self._Configs.get('yomboapi', 'session_id')  # to be encrypted with gpg later
            self.auth_session_key = self._Configs.get('yomboapi', 'session_key')  # to be encrypted with gpg later
        else:
            self.auth_session_id = None
            self.auth_session_key = None

    def _load_(self):
        if self._Atoms['loader.operation_mode'] == 'run':
            self.load_deferred = Deferred()
            self.validate_system_session()
            return self.load_deferred

    def _load_(self):
        pass

    def _stop_(self):
        if self.load_deferred is not None and self.load_deferred.called is False:
            self.load_deferred.callback(1)  # if we don't check for this, we can't stop!

    def _unload_(self):
        pass

    def save_system_session(self, session_id, session_hash):
        print "save_system_session!!!"
        self._Configs.set('yomboapi', 'session_id', session_id)  # to be encrypted with gpg later
        self._Configs.set('yomboapi', 'session_key', session_hash)  # to be encrypted with gpg later

    def select_session(self, session_id=None, session_key=None):
        if session_id is None or session_key is None:
            if self.allow_system_session:
                return self.auth_session_id, self.auth_session_key

        logger.debug("Yombo API has no session data for 'selection_session'")
        return None, None

    def clear_session_cache(self, session_id=None, session_key=None):
        hashed = sha1(session_id + session_key)
        if hashed in self.session_validation_cache:
            del self.session_validation_cache[hashed]  # None works too...

    @inlineCallbacks
    def validate_system_session(self):
        if self.allow_system_session is False:
            self._States.set('yomboapi.valid_system_session', False)
            self.load_deferred.callback(10)
            returnValue(False)

        if self.auth_session_id is None or self.auth_session_key is None:
            logger.warn("No saved system session information. Disabling autoamted system changes.")
            self._States.set('yomboapi.valid_system_session', False)
            self.load_deferred.callback(10)
            returnValue(None)

        self.clear_session_cache()
        results = yield self.do_validate_session(self.auth_session_id, self.auth_session_key)
        self._States.set('yomboapi.valid_system_session', results)
        print "here?!"
        self.load_deferred.callback(10)
        returnValue(results)

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
    def do_validate_session(self, session_id, session_key):
        try:
            results = yield self.request("GET", "/v1/session/validate?sessionid=%s&sessionkey=%s" % (session_id, session_key))
        except Exception, e:
            logger.debug("$$$ API Errror: {error}", error=e)
            returnValue(False)

        logger.debug("$$$ REsults from API: {results}", results=results)
# waiting on final API.yombo.com to complete this.  If we get something, we are good for now.

        self._States.set('yomboapi.valid_system_session', True)
        self.valid_system_session = True

    @inlineCallbacks
    def session_login_password(self, username, password):
        results = yield self.request("GET", "/v1/session/login?username=%s&password=%s" % (username, password))
        logger.info("$$$ REsults from API: {results}", results=results)

        if results['code'] == 200:  # life is good!
            returnValue(results['content']['Response']['Session'])
        else:
            returnValue(False)

    @inlineCallbacks
    def gateways(self, session_info=None):
        results = yield self.request("GET", "/v1/gateway")
        logger.debug("$$$ REsults from API: {results}", results=results)

        if results['code'] == 200:  # life is good!
            returnValue(results['content']['Response']['Gateway'])
        else:
            returnValue(False)

    def make_headers(self, session_id, session_key):
        headers = {
            'Content-Type': self.contentType,
            'User-Agent': 'Yombo Gateway API',
            'Authorization': 'YOMBO-TOKEN apikey=%s, session_id=%s, session_hash=%s' %
                             (self.api_key, self.auth_session_id, self.auth_session_key)
        }
        for k, v in headers.iteritems():
            headers[k] = v.encode('utf-8')
        return headers

    def errorHandler(self,result):
        raise YomboWarning("Problem with request: %s" % result)

    @inlineCallbacks
    def request(self, method, path, session_id=None, session_key=None, data=None):
        print "base_url: %s" % self.base_url
        print "path: %s" % path
        path = self.base_url + path
        print "path full: %s" % path
        results = None
        headers = self.make_headers(session_id, session_key)
        if method == 'GET':
            results = yield self.__get(path, headers, data)
        elif method == 'POST':
            results = self.__post(path, headers, data)
        elif method == 'PATCH':
            results = self.__patch(path, headers, data)
        elif method == 'PUT':
            results = self.__put(path, headers, data)
        elif method == 'DELETE':
            results = self.__delete(path, headers, data)
        else:
            raise Exception("Bad request type?? %s: %s" % (method, path) )

#        print "request api results: %s" % results
        returnValue(results)

    @inlineCallbacks
    def __get(self, path, headers, args=None):
        path = path
        logger.info("getting URL: {path}  headers: {headers}", path=path, agent=self.custom_agent, headers=headers)
        # response = yield treq.get(path, params=args, agent=self.custom_agent, headers=headers)
        response = yield treq.get(path, headers=headers, params=args)
        final_response = yield self.decode_results(response)
        returnValue(final_response)

    @inlineCallbacks
    def __patch(self, path, headers, data):
        url = self.baseURL + path
        response = yield treq.patch(path, data=data, agent=self.custom_agent, headers=headers)
        final_response = yield self.decode_results(response)
        returnValue(final_response)

    @inlineCallbacks
    def __post(self, path, headers, data):
        url = self.baseURL + path
        response = yield treq.post(path, data=data, agent=self.custom_agent, headers=headers)
        final_response = yield self.decode_results(response)
        returnValue(final_response)

    @inlineCallbacks
    def __put(self, path, headers, data):
        url = self.baseURL + path
        response = yield treq.put(path, data=data, agent=self.custom_agent, headers=headers)
        final_response = yield self.decode_results(response)
        returnValue(final_response)

    @inlineCallbacks
    def __delete(self, path, headers, args={}):
        url = self.baseURL + path
        response = yield treq.put(path, params=args, agent=self.custom_agent, headers=headers)
        final_response = yield self.decode_results(response)
        returnValue(final_response)

    def __encode(self, data):
        return json.dumps(data)

    def response_headers(self, response):
        data = {}
        for key, value in response.headers._rawHeaders.iteritems():
            data[key.lower()] = value
        return data

    @inlineCallbacks
    def decode_results(self, response):
        headers = self.response_headers(response)
        # print "decoded headers: %s" % headers
        if 'content_type' in headers:
            content_type = headers['content-type'][0]
            print "headers: %s" % headers['content-type'][0]
        else:
            content_type = None

        content = yield treq.content(response)

        if content_type == 'application/json':
            if self.is_json(content):
                content = json.loads(content)
                content_type = "dict"
            else:
                raise YomboWarning("Receive yombo api response reported json, but isn't.")
        elif content_type == 'application/msgpack':
            if self.is_msgpack(content):
                content = msgpack.loads(content)
                content_type = "dict"
            else:
                raise YomboWarning("Received msg reported msgpack, but isn't.")
        else:
            if self.is_json(content):
                content = json.loads(content)
                content_type = "dict"
            elif self.is_msgpack(content):
                content = msgpack.loads(content)
                content_type = "dict"
            else:
                content_type = "string"

        results = {
            'content': content,
            'content_type': content_type,
            'code': response.code,
            'phrase': response.phrase,
            'headers': headers,
        }
        returnValue(results)

        logger.info("Unknown Content-Type ({content_type}), returning raw content.", content_type=content_type)
        returnValue(content)

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