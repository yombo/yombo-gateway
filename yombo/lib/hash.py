# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `Hash @ Library Documentation <https://yombo.net/docs/libraries/hash>`_

Responsible for creating and checking password hashes.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.16.0

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/hash.html>`_
"""
from hashlib import sha224, sha256, sha384, sha512

from passlib.hash import argon2, bcrypt
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor, threads

# Import 3rd-party libs
import yombo.ext.base62 as base62

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import sleep, unicode_to_bytes, encode_binary

logger = get_logger("library.hash")

MAX_DURATION = 300  # How long it should take to validate a password, in milliseconds.


class Hash(YomboLibrary):
    """
    Responsible for creating and checking password hashes. This library supports the following hash
    algorithms:

    * argon2
    * bcrypt

    """
    @inlineCallbacks
    def _init_(self, **kwargs):
        self.argon2_rounds = self._Configs.get("hash.argon2_rounds", None, False)
        self.argon2_memory = self._Configs.get("hash.argon2_memory", None, False)
        self.argon2_duration = self._Configs.get("hash.argon2_duration", None, False)
        self.argon2_rounds_fast = self._Configs.get("hash.argon2_rounds_fast", None, False)
        self.argon2_memory_fast = self._Configs.get("hash.argon2_memory_fast", None, False)
        self.argon2_duration_fast = self._Configs.get("hash.argon2_duration_fast", None, False)

        # Find argon2 cost now if don't have. Or find it in 70 seconds
        # Want to do this incase the gateway is moved to a faster/slow processor.
        if self.argon2_rounds is None or self.argon2_memory is None or\
                        self.argon2_rounds_fast is None or self.argon2_memory_fast is None:
            logger.info("Calculating the size of the earth.")
            yield self.argon2_find_cost()
        else:
            reactor.callLater(76, self.argon2_find_cost, slow=True)

    @inlineCallbacks
    def argon2_find_cost(self, slow=None):
        max_duration = self._Configs.get("hash.max_duration", MAX_DURATION)
        results = yield threads.deferToThread(self.argon2_find_cost_calculator, max_time=max_duration)
        self.argon2_rounds = results[0]
        self.argon2_memory = results[1]
        self.argon2_duration = results[2]
        self._Configs.set("hash.argon2_rounds", results[0], ref_source=self)
        self._Configs.set("hash.argon2_memory", results[1], ref_source=self)
        self._Configs.set("hash.argon2_duration", results[2], ref_source=self)

        if slow is True:
            yield sleep(1)

        results = yield threads.deferToThread(self.argon2_find_cost_calculator, max_time=max_duration/2)
        self.argon2_rounds_fast = results[0]
        self.argon2_memory_fast = results[1]
        self.argon2_duration_fast = results[2]
        self._Configs.set("hash.argon2_rounds_fast", results[0], ref_source=self)
        self._Configs.set("hash.argon2_memory_fast", results[1], ref_source=self)
        self._Configs.set("hash.argon2_duration_fast", results[2], ref_source=self)

    def argon2_find_cost_calculator(self, max_time=None):
        """
        Finds a good cost factor for the current system. It tests various factors and finds the most expensive one
        for this system that is still around 300 milliseconds, or whatever max_time is set to or MAX_DURATION.

        :param force_update: If true, will force a new search.
        :return:
        """
        if max_time is None:
            max_time = self._Configs.get("hash.max_duration", MAX_DURATION)
        else:
            try:
                max_time = int(max_time)
            except Exception as e:
                max_time = MAX_DURATION

        max_time = max_time * .98
        memory_base = 1
        memory_min = 11
        memory_max = 23
        rounds_min = 0
        rounds_max = 45
        duration = -1
        skip = 0
        rounds_best = 7
        memory_best = 11
        duration_best = 300
        for memory_step in range(memory_min, memory_max):
            for rounds in range(rounds_min + round(memory_step * 0.6), rounds_max):
                # We implement a skipper if we blast through some of the early checks/fast checks.
                if skip > 0:
                    skip -= 1
                    duration = 0
                    continue
                if duration > 0 and duration < max_time * 0.15:
                    skip = 5
                    if (rounds + skip) > rounds_max:
                        skip = rounds_max - rounds
                    duration = 0
                    continue
                if duration > 0 and duration < max_time * 0.25:
                    skip = 4
                    if (rounds + skip) > rounds_max:
                        skip = rounds_max - rounds
                    duration = 0
                    continue
                if duration > 0 and duration < max_time * 0.40:
                    skip = 3
                    if (rounds + skip) > rounds_max:
                        skip = rounds_max - rounds
                    duration = 0
                    continue
                if duration > 0 and duration < max_time * 0.50:
                    skip = 2
                    if (rounds + skip) > rounds_max:
                        skip = rounds_max - rounds
                    duration = 0
                    continue
                if duration > 0 and duration < max_time * 0.60:
                    skip = 1
                    duration = 0
                    continue
                if rounds > round((memory_step-7)*2.6):
                    break

                start = time()
                memory_cost = memory_base << memory_step
                argon2.using(rounds=rounds, memory_cost=memory_cost).hash("testingpassword!")
                end = time()
                duration = (end - start) * 1000
                # print("rounds=%s, memory=%s (%s), time=%.3f" % (rounds, memory_cost, memory_step, duration))
                if duration > max_time:
                    return [rounds_best, memory_best, duration_best]
                rounds_best = rounds
                memory_best = memory_step
                duration_best = duration
        return [rounds_best, memory_best, duration_best]

    @inlineCallbacks
    def hash(self, password, algorithm=None, rounds=None, memory=None, fast=None):
        """
        Hash"s a password. This is a wrapper around various hash algorithms supported by this library.

        :param password:
        :param algorithm: Default - argon2
        :return:
        """
        if algorithm is None or algorithm.lower() == "argon2":
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
        Creates an argon2 hash.

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

    @staticmethod
    def sha224_compact(value, encoder: Optional[str] = None, convert_to_unicode: Optional[bool] = True):
        """
        Returns a shorter sha224 - 38 characters long instead of 56.

        This uses a base62 encoding which uses the entire alphabet, with mixed case.

        Returned length is 38 characters.

        :param value:
        :return:
        """
        if encoder is None:
            encoder = "base62"
        if convert_to_unicode is None:
            convert_to_unicode = True

        if value is None:
            return None
        return encode_binary(sha224(unicode_to_bytes(value)).digest(), encoder, convert_to_unicode)

    @staticmethod
    def sha256_compact(value, encoder: Optional[str] = None, convert_to_unicode: Optional[bool] = True):
        """
        Returns a shorter sha256 - 43 characters long instead of 64.

        This uses a base62 encoding which uses the entire alphabet, with mixed case.

        Returned length is 43 characters.

        :param value:
        :return:
        """
        if encoder is None:
            encoder = "base62"
        if convert_to_unicode is None:
            convert_to_unicode = True

        if value is None:
            return None
        return encode_binary(sha256(unicode_to_bytes(value)).digest(), encoder, convert_to_unicode)

    @staticmethod
    def sha384_compact(value, encoder: Optional[str] = None, convert_to_unicode: Optional[bool] = True):
        """
        Returns a shorter sha384 - 64 characters long instead of 96.

        This uses a base62 encoding which uses the entire alphabet, with mixed case.

        Returned length is 64 characters.

        :param value:
        :return:
        """
        if encoder is None:
            encoder = "base62"
        if convert_to_unicode is None:
            convert_to_unicode = True

        if value is None:
            return None
        return encode_binary(sha384(unicode_to_bytes(value)).digest(), encoder, convert_to_unicode)

    @staticmethod
    def sha512_compact(value, encoder: Optional[str] = None, convert_to_unicode: Optional[bool] = True):
        """
        Returns a shorter sha512 - 86 characters long instead of 128.

        This uses a base62 encoding which uses the entire alphabet, with mixed case.

        Returned length is 86 characters.

        :param value:
        :return:
        """
        if encoder is None:
            encoder = "base62"
        if convert_to_unicode is None:
            convert_to_unicode = True

        if value is None:
            return None
        return encode_binary(sha512(unicode_to_bytes(value)).digest(), encoder, convert_to_unicode)
