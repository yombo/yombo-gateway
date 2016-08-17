#cython: embedsignature=True
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

try: import simplejson as json
except ImportError: import json

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
from twisted.internet import ssl, protocol, defer
from twisted.web.client import getPage

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger('library.yomboapi')

class YomboAPI(YomboLibrary):

    contentType = None
    agent = "Yombo Service"
    timeout = 5

    def _init_(self):
        pass

    def _start_(self):
        self.allow_system_session = self._Configs.get('yomboapi', 'allow_system_session', True)

        self.api_key = self._Configs.get('yomboapi', 'api_key', 'pZEi9fbEuU4bTpxs', False)
        self.auth_sessionid = self._Configs.get('yomboapi', 'sessionid')  # to be encrypted with gpg later
        self.auth_sessionkey = self._Configs.get('yomboapi', 'sessionkey')  # to be encrypted with gpg later
        self.contentType = self._Configs.get('api', 'contenttype', 'application/json', False)
        self.baseURL = self._Configs.get('api', 'baseurl', "https://api.yombo.net/api", False)

        self._valid_session = False
        if self._Atoms['loader.operation_mode'] == 'run':
            self.init_defer = Deferred()
            self.validate_session()
            return self.init_defer

    def _load_(self):
        pass

    def _stop_(self):
        pass

    def _unload_(self):
        pass

    def save_session(self, session_id, session_hash):
        print "saving sessssionnnn!!!"
        self._Configs.set('yomboapi', 'sessionid', session_id)  # to be encrypted with gpg later
        self._Configs.set('yomboapi', 'sessionkey', session_hash)  # to be encrypted with gpg later

    def select_session(self, session_info):
        if session_info is not None:
            if isinstance(session_info, dict):
                if 'session_id' in session_info and 'session_key' in session_info:
                    return session_info

        if self.allow_system_session:
            return {'session_id': self.auth_sessionid, 'session_key': self.auth_sessionkey}
        return None

    @inlineCallbacks
    def validate_session(self, session_id=None, session_hash=None):
        if session_id is None or session_hash is None:
            session_id = self.auth_sessionid
            session_hash = self.auth_sessionkey

        if self.auth_sessionid is None or self.auth_sessionkey is None:
            logger.info("YomboAPI needs session information to make any requests.")
            self.init_defer.callback(10)
            returnValue(None)
        try:
            results = yield self.requestAPI("GET", "/v1/session/validate?sessionid=%s&sessionkey=%s" % (session_id, session_hash))
        except Exception, e:
            logger.debug("$$$ API Errror: {error}", error=e)
            results = None
        logger.debug("$$$ REsults from API: {results}", results=results)
        self._valid_session = True
        self.init_defer.callback(10)

    @inlineCallbacks
    def session_login_password(self, username, password):
        results = yield self.requestAPI("GET", "/v1/session/login?username=%s&password=%s" % (username, password))
        logger.debug("$$$ REsults from API: {results}", results=results)

        if results['Code'] == 200:  # life is good!
            returnValue(results['Response']['Session'])
        else:
            returnValue(False)

    @inlineCallbacks
    def gateways(self, session_info=None):
        results = yield self.requestAPI("GET", "/v1/gateway")
        logger.debug("$$$ REsults from API: {results}", results=results)

        if results['Code'] == 200:  # life is good!
            returnValue(results['Response']['Gateway'])
        else:
            returnValue(False)


    def _makeHeaders(self, parameters={}):
        headers = {}
        headers['Content-Type'] = self.contentType
        headers['X-Yombo-Server'] = 'TRUE'
        for k, v in headers.iteritems():
            headers[k] = v.encode('utf-8')
        return headers

    def __urlencode(self, h):
        rv = []
        for k,v in h.iteritems():
            rv.append('%s=%s' %
                (urllib.parse(k.encode("utf-8")),
                urllib.parse(str(v).encode("utf-8"))))
        return '&'.join(rv)

    def errorHandler(self,result):
        raise YomboWarning("Problem with request: %s" % result)

    @inlineCallbacks
    def requestAPI(self, method, path, data=None):
        results = None
        if method == 'GET':
            results = yield self.__get(path, data)
        elif method == 'POST':
            results = self.__post(path, data)

        if results == None:
            raise Exception("Bad request type?? %s: %s" % (method, path) )

        print "request api results: %s" % results
        returnValue(self.__decode(results))

    @inlineCallbacks
    def __get(self, path, args=None):
        url = self.baseURL + path
        if args:
            url += '?' + self.__urlencode(args)

        logger.debug("getting URL: {url}  agent: {agent}  headers: {headers}", url=url, agent=self.agent, headers=self._makeHeaders())
        body = yield getPage(url, method='GET', timeout=self.timeout, agent=self.agent, headers=self._makeHeaders())

        returnValue(body)

    @inlineCallbacks
    def __patch(self, path, data):
        url = self.baseURL + path
        body = yield getPage(url, method='PATCH', timeout=self.timeout, agent=self.agent,
            postdata=self.__encode(data), headers=self._makeHeaders())
        returnValue(body)

    @inlineCallbacks
    def __post(self, path, data):
        url = self.baseURL + path
        body = yield getPage(url, method='POST', timeout=self.timeout, agent=self.agent,
            postdata=self.__encode(data), headers=self._makeHeaders())
        returnValue(body)

    @inlineCallbacks
    def __put(self, path, data):
        url = self.baseURL + path
        body = yield getPage(url, method='PUT', timeout=self.timeout, agent=self.agent,
            postdata=self.__encode(data), headers=self._makeHeaders())
        returnValue(body)

    @inlineCallbacks
    def __delete(self, path, args={}):
        url = self.baseURL + path
        body = yield getPage(url, method='DELETE', timeout=self.timeout, agent=self.agent,
            postdata=self.__urlencode(args), headers=self._makeHeaders())
        returnValue(body)

    def __parsed(self, hdef, parser):
        deferred = defer.Deferred()
        hdef.addCallbacks(
            callback=lambda p: deferred.callback(parser(str(p))),
            errback=lambda e: deferred.errback(e))
        return deferred

    def __encode(self, data):
        return json.dumps(data)

    def __decode(self, data):
        print "data2: %s" % data
        return json.loads(data)
