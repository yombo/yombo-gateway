# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Hash @ Module Development <https://yombo.net/docs/libraries/hash>`_


Responsible for creating and checking password hashes.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.16.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/hash.html>`_
"""
from passlib.hash import argon2, bcrypt
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet import threads

# Import Yombo libraries
#from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger('library.tasks')

MAX_DURATION = 300

class Hash(YomboLibrary):
    """
    Responsible for creating and checking password hashes. This library supports the following hash
    algorithms:

    * argon2

    """
    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo hash library"

    @inlineCallbacks
    def _init_(self, **kwargs):
        self.argon2_rounds = self._Configs.get('hash', 'argon2_rounds', None, False)
        self.argon2_memory = self._Configs.get('hash', 'argon2_memory', None, False)
        self.argon2_duration = self._Configs.get('hash', 'argon2_duration', None, False)
        self.argon2_rounds_fast = self._Configs.get('hash', 'argon2_rounds_fast', None, False)
        self.argon2_memory_fast = self._Configs.get('hash', 'argon2_memory_fast', None, False)
        self.argon2_duration_fast = self._Configs.get('hash', 'argon2_duration_fast', None, False)

        if self.argon2_rounds is None or self.argon2_memory is None:
            results = yield self.argon2_find_cost()
            self.argon2_rounds = results[0]
            self.argon2_memory = results[1]
            self.argon2_duration = results[0]
            self._Configs.set('hash', 'argon2_rounds', results[0])
            self._Configs.set('hash', 'argon2_memory', results[1])
            self._Configs.set('hash', 'argon2_duration', results[2])
        if self.argon2_rounds_fast is None or self.argon2_memory_fast is None:
            results = yield self.argon2_find_cost(max_time=MAX_DURATION/2)
            self.argon2_rounds_fast = results[0]
            self.argon2_memory_fast = results[1]
            self.argon2_duration_fast = results[0]
            self._Configs.set('hash', 'argon2_rounds_fast', results[0])
            self._Configs.set('hash', 'argon2_memory_fast', results[1])
            self._Configs.set('hash', 'argon2_duration_fast', results[2])

        # hash2 = yield self.hash('asdf')
        # print("hash = %s" % hash2)
        # hash2 = yield self.hash('asdf', fast=True)
        # print("hash = %s" % hash2)

    def argon2_find_cost(self, max_time=None):
        """
        Finds a good cost factor for the current system. It tests various factors and finds the most expensive one
        for this system that is still under 400 milliseconds.

        :param force_update: If true, will force a new search.
        :return:
        """
        if max_time is None:
            max_time = 300
        else:
            try:
                max_time = int(max_time)
            except Exception as e:
                max_time = MAX_DURATION

        max_time = max_time * .95
        memory_base = 1
        memory_min = 12
        memory_max = 17
        rounds_min = 0
        rounds_max = 16
        duration = 0
        skip = 0
        for memory_step in range(memory_min, memory_max):
            for rounds in range(rounds_min + round(memory_step * 0.4), rounds_max):
                # We implement a skipper if we blast through some of the early checks.
                if skip > 0:
                    skip -= 1
                    duration = 0
                    continue
                max_time_skip = duration / 4
                if duration > 0 and duration < max_time * 0.1:
                    skip = 5
                    if (rounds + skip) > rounds_max:
                        skip = rounds_max - rounds
                    duration = 0
                    continue
                if duration > 0 and duration < max_time * 0.125:
                    skip = 4
                    if (rounds + skip) > rounds_max:
                        skip = rounds_max - rounds
                    duration = 0
                    continue
                if duration > 0 and duration < max_time * 0.25:
                    skip = 3
                    if (rounds + skip) > rounds_max:
                        skip = rounds_max - rounds
                    duration = 0
                    continue
                if duration > 0 and duration < max_time * 0.375:
                    skip = 2
                    if (rounds + skip) > rounds_max:
                        skip = rounds_max - rounds
                    duration = 0
                    continue
                if duration > 0 and duration < max_time * 0.5:
                    skip = 1
                    duration = 0
                    continue

                start = time()
                memory_cost = memory_base << memory_step
                argon2.using(rounds=rounds, memory_cost=memory_cost).hash('testingpassword!')
                end = time()
                duration = (end - start) * 1000
                # print("rounds=%s, memory=%s (%s), time=%.3f" % (rounds, memory_cost, memory_step, duration))
                if duration > max_time:
                    break
                memory_best = memory_step
                rounds_best = rounds
                duration_best = duration
            if rounds == rounds_min + round(memory_step * 0.4):
                break
        return([rounds_best, memory_best, duration_best])
        # print("Best = rounds=%s, memory=%s, time=%.3f" % (rounds_best, memory_best, duration_best))

    @inlineCallbacks
    def hash(self, password, algorithm=None, rounds=None, memory=None, fast=None):
        """
        Hash's a password. This is a wrapper around various hash algorithms supported by this library.

        :param password:
        :param algorithm: Default - argon2
        :return:
        """
        if algorithm is None or algorithm.lower() == 'argon2':
            results = yield self.argon2_hash(password, rounds=rounds, memory=memory, fast=fast)
            return results

    @inlineCallbacks
    def verify(self, password, hashed, algorithm=None):
        """
        Validates a password against a provided hash. This is a wrapper around various hash algorithms supported
        by this library.

        This function will try to guess the algorithm based on the hash.

        :param password:
        :param hashed:
        :param algorithm:
        :return:
        """
        if algorithm is None:
            if argon2.identify(hashed):
                results = yield self.argon2_verify(password, hashed)
                return results
            if bcrypt.identify(hashed):
                results = yield self.bcrypt_verify(password, hashed)
                return results

        if algorithm is None:
            logger.warn("Unable to detect password hash algorithm")
            return False

    @inlineCallbacks
    def argon2_hash(self, password, rounds=None, memory=None, fast=None):
        """
        Creates an argon2 hash. Uses the argon2_find_cost to get the required cost.
        :param password:
        :param rounds:
        :param memory:
        :return:
        """
        if fast is True:
            if rounds is None:
                rounds = self.argon2_rounds_fast
            if memory is None:
                memory = self.argon2_memory_fast
        else:
            if rounds is None:
                rounds = self.argon2_rounds
            if memory is None:
                memory = self.argon2_memory
        # print("rounds=%s, memroy=%s" % (rounds, memory))
        hasher = argon2.using(rounds=rounds, memory_cost=1 << memory).hash
        hash = yield threads.deferToThread(hasher, password)
        return hash

    @inlineCallbacks
    def argon2_verify(self, password, hashed):
        """
        Verifies an argon2 hash.

        :param password:
        :param hashed:
        :return:
        """
        results = yield threads.deferToThread(argon2.verify, password, hashed)
        return results

    @inlineCallbacks
    def bcrypt_verify(self, password, hashed):
        """
        Verifies an bcrypt hash.

        :param password:
        :param hashed:
        :return:
        """
        results = yield threads.deferToThread(bcrypt.verify, password, hashed)
        return results
