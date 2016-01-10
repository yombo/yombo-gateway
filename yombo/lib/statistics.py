# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
Used to track gateway statistics and various usage information.

.. warning::

  This library should be considered a placeholder and is not functional.

..versionadded:: 0.10.0
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2015 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import math
#import functools
import datetime

# Import twisted libraries
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.helpers import getConfigValue, generateRandom
from yombo.core.log import getLogger

logger = getLogger('library.statistics')

class Statistics(YomboLibrary):
    """
    There are three types of stats: counter, timing, gauge.

    Counter: This just counts the number of times somethings happens. It's best to simply call the increment and
    decrement functions to handle the creatio and counting at same time..

    Timing: Time how long sometime takes. For example, how long an AMQP message takes to process.

    Gauge: A set value for any given time. Eg: Memory usage, SQL Database size, uptime, etc.

    All stat names must start with "lib" or "module" and must contain the name of library or module
    and the name of the counter. Some example names:
    * lib.configuration.cache.hits
    * lib.configuration.cache.misses
    * lib.messages.count.status
    * lib.messages.count.command
    * lib.amqp.count.sent
    * lib.amqp.count.received
    * core.yombo.memory.used
    * core.yombo.memory.free

    Currently, Yombo limits logging up to 10,000 statistics items per day per gateway. This limit is subject
    to change.
    """
    countDuration = 300 # 5 minutes for count buckets
    timingDuration = 300 # 5 minutes for timing buckets

    enabled = None
    collections = {}

    def _init_(self, loader):
        self.loader = loader
        self._count = {}
        self._timing = {}
        self._gauge = {}
        self.gwuuid = getConfigValue("core", "gwuuid")
        self.countDuration = 3 # 5 minutes for count buckets
        self.timingDuration = 3 # 5 minutes for timing buckets

        self.enabled = getConfigValue('statistics', 'enabled', False)

    def _load_(self):
        pass

    def _start_(self):
        logger.info("Stats module enabled? {enabled}", enabled=self.enabled)
        if self.enabled is True:
            self.sendDataLoop = LoopingCall(self.sendData)
            self.sendDataLoop.start(self.countDuration, False)
            return

    def _stop_(self):
        if self.enabled is True:
            self.sendData()

    def _unload_(self):
        pass

    def _getTime(self, type):
        """
        Internal function to get time in the format required for various statistics.

        :param type: Either count or timing.
        :return: A unix epoch time in buckets.
        """
        bucketSeconds = None
        if type == "count":
            bucketSeconds = self.countDuration
        elif type == "timing":
            bucketSeconds = self.timingDuration

        tm = datetime.datetime.now()
        tm = tm - datetime.timedelta(minutes=tm.minute,
        seconds=tm.second % bucketSeconds,
        microseconds=tm.microsecond)
        return int(tm.strftime('%s'))

    def _validateName(self, name):
        """
        Validates the name being submitted is valid. No point in sending badly named
        items to the server, as the server will simply perform this same check and
        discard any invalid ones.

        .. note::

            If the server detects too many invalid names, the gateway will be blocked from
            saving statistics in the future.

        :param name: Label for the statistic
        :type name: string
        """
        parts = name.split('.', 10)
        if len(parts) < 3:
            raise YomboWarning("Name must have at least 3 parts, preferable at least 4.")
        elif len(parts) > 8:
            raise YomboWarning("Name has too many parts, no more than 8.")
        elif parts[0] not in ['lib', 'module', 'core']:
            raise YomboWarning("Name must start with lib, module, or core.")
        elif len(parts[1]) < 3:
            raise YomboWarning("Second part of 'name' is too short, must be at least 3 characters: " % parts[1])
        elif len(parts[2]) < 3:
            raise YomboWarning("Third part of 'name' is too short, must be at least 3 characters: " % parts[2])

        if len(parts) == 4:
            if len(parts[3]) < 3:
                raise YomboWarning("Fourth part of 'name' is too short, must be at least 3 characters: " % parts[3])
        elif len(parts) == 5:
            if len(parts[4]) < 2:
                raise YomboWarning("Fourth part of 'name' is too short, must be at least 2 characters: " % parts[4])
        elif len(parts) == 6:
            if len(parts[5]) < 2:
                raise YomboWarning("Fifth part of 'name' is too short, must be at least 2 characters: " % parts[5])
        elif len(parts) == 7:
            if len(parts[6]) < 2:
                raise YomboWarning("Fifth part of 'name' is too short, must be at least 2 characters: " % parts[6])
        elif len(parts) == 8:
            if len(parts[7]) < 2:
                raise YomboWarning("Fifth part of 'name' is too short, must be at least 2 characters: " % parts[7])

    def gauge(self, name, value):
        """
        Set a guage level. For example, set the ammount of memory used every so often.

        :param name: Name of the statistic to save.
        :type name: string
        :param value: A numbered value to set.
        :type value: int
        """
        if self.enabled is not True:
            return

        self._validateName(name)
        bucket = datetime.datetime.now().strftime('%s')
        if bucket not in self.data:
            self._gauge[bucket] = {}
        self._gauge[bucket][name] = value

    def count(self, name, value):
        """
        Set a count value. Typically, this isn't used, instead use ``inc`` due to bucket time rollover.

        :param name: Name of the statistic to save.
        :type name: string
        :param value: A numbered value to set.
        :type value: int
        """
        if self.enabled is not True:
            return

        self._validateName(name)

        bucket = self._getTime('count')

        if bucket not in self.data:
            self._count[bucket] = {}
        self._count[bucket][name] = value

    def increment(self, name, count=1):
        """
        Increment a counter value. If doesn't exist, will create the new counter for the given name.

        :param name: Name of the statistic to save.
        :type name: string
        :param count: How many to increment by, defaults to 1.
        :type count: int
        """
        if self.enabled is not True:
            return
        self._validateName(name)

        bucket = self._getTime('count')

        if bucket not in self._count:
            self._count[bucket] = {}

        if name not in self._count[bucket]:
                self._count[bucket][name] = count
        else:
                self._count[bucket][name] += count

    def decrement(self, name, count=1):
        """
        Decrement a counter value. If doesn't exist, will create the new counter for the given name.

        :param name: Name of the statistic to save.
        :type name: string
        :param count: How many to increment by, defaults to -1.
        :type count: int
        """
        if self.enabled is not True:
            return

        self._validateName(name)

        bucket = self._getTime('count')

        if bucket not in self._count:
            self._count[bucket] = {}
        if name not in self._count[bucket]:
            self._count[bucket][name] = - count
        else:
            self.data[bucket][name] -= count

    def timing(self, name, duration):
        """
        Set a time on how long something took to complete in milliseconds. A single timer can be set many times, but
        it will be averaged per bucket.

        :param name: Name of the statistic to save.
        :type name: string
        :param duration: How long something took in milliseconds.
        :type duration: int
        """
        if self.enabled is not True:
            return

        self._validateName(name)

        bucket = self._getTime('timing')

        if bucket not in self._timing:
            self._timing[bucket] = {}

        if name not in self._timing[bucket]:
            self._timing[bucket][name] = [duration]
        else:
            self._timing[bucket][name].append(duration)

    def sendData(self, full=False):
        """
        Sends stats to the Yombo servers periodically. Typically only sends all but the
        last time bucket in case this function is called between time buckets.
        """
        if self.enabled is not True:
            return

        bucket = self._getTime('count')
        bucketsSent = []
        amqpBody = []
        logger.info("stats. count: {count}", count=self._count)
        for key, items in self._count.iteritems():
            if (key <= (bucket - (self.countDuration +10))):
#                bucket.append(key)
                for name, value in items:
                    amqpBody.append({"name":name, "value": value, "timestamp": key})

        for time in bucketsSent:
            del self._count[time]

        bucket = self._getTime('timing')
        bucketsSent = []
        for key, items in self._timing.iteritems():
            if key <= bucket - (self.timingDuration +10):
                bucketsSent.append(key)
                sortedItem = sorted(items)
                for name, values in items:
                    sortedValues = sorted(values)

                count = len(sortedValues)
                median = percentile(sortedValues, 0.50)

                min = sortedValues[0]
                max = sortedValues[-1]

                percentile90 = percentile(sortedValues, 0.90)
                temp = []
                for val in a:
                    if val < percentile90:
                        temp.append(val)
                    else:
                        break

                median_90 = percentile(temp, 0.50)

                amqpBody.append({"name":name + ".count", "value"  : count, "timestamp": key})
                amqpBody.append({"name":name + ".median", "value" : median, "timestamp": key})
                amqpBody.append({"name":name + ".upper", "value"  : max, "timestamp": key})
                amqpBody.append({"name":name + ".lower", "value"  : min, "timestamp": key})
                amqpBody.append({"name":name + ".upper_90", "value"  : temp[-1], "timestamp": key})
                amqpBody.append({"name":name + ".lower_90", "value"  : temp[0], "timestamp": key})
                amqpBody.append({"name":name + ".median_90", "value" : median_90, "timestamp": key})

        for time in bucketsSent:
            del self._timing[time]

        for key, items in self._gauge:
            for name, value in items:
                amqpBody.append({"name":name, "value" : value , "timestamp": key})

        #TODO: Send to AMQP library for actual sending.
        request = {
              "DataType": "Objects",
              "Request": amqpBody,
            }

        logger.info("Request (senddata): {request}", request=request)

        requestmsg = {
            "exchange_name"    : "ysrv.e.gw_stats",
            "routing_key"      : '*',
            "body"             : request,
            "properties" : {
                "correlation_id" : generateRandom(length=12),
                "user_id"        : self.gwuuid,
                "headers"        : {
                    "Source"        : "yombo.gateway.lib.statistics:" + self.gwuuid,
                    "Destination"   : "yombo.server.configs",
                    "Type"          : "Stats",
                    },
                },
            "callback"          : None,
            }

        return requestmsg

    def percentile(N, percent, key=lambda x:x):
        """
        Find the percentile of a list of values

        :param N: A list of values. Note N MUST BE already sorted.
        :param percent: A float value from 0.0 to 1.0.
        :param key: Optional key function to compute value from each element of N

        :return: The percentile of the values
        """
        if not N:
            return None
        k = (len(N)-1) * percent
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return key(N[int(k)])
        d0 = key(N[int(f)]) * (c-k)
        d1 = key(N[int(c)]) * (k-f)
        return d0+d1
