# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For developer documentation, see: `Statistics @ Module Development <https://yombo.net/docs/libraries/statistics>`_
  * For library documentation, see: `Statistics @ Library Documentation <https://yombo.net/docs/libraries/loader>`_


Statistics allow the gateway to trace various data points. This can be used to track how much time of a day the
sun is up, or average temperatures, number of commands sent, etc.  Statistics can be used in conjunction with
or as a replacement for device status history. Sometimes it's easier to trace device status here so you can get
averages or a specific datapoint for a device.

.. warning::

  All data values must be an int or decimal (float). This is because data here should be chartable. Devices that
  are on/off or open/closed, can be 1/0.

There are three types of statistics:

  1) Counter - Used to track the number of events.
  2) Averages - Keep adding data points to this, and it will be be averaged along with 90 percentile stats.
  3) Datapoint - Just a simple data point. Not used much.

Any library or module can create statistics, however, a good name for the statistic must be created. A statistic is
named with a dot notation.  For example: module.mycoolmodule.commands.sent and module.mycoolmodule.commands.sent
This allows filtering like this: module.mycoolmodule.commands.* to see all the commands your module processed.

Some addtional examples:

  * lib.configuration.cache.hits
  * lib.configuration.cache.misses
  * lib.messages.count.status
  * lib.messages.count.command
  * lib.amqp.count.sent
  * lib.amqp.count.received
  * system.memory.used
  * system.memory.free
  * system.cpu.used
  * system.cpu.free
  * system.storage.disk1.used
  * system.storage.disk1.free
  * devices.myhome.groundfloor.kitchen.main_light = 1 - on
  * energy.myhome.groundfloor.kitchen.main_light = 100 - watts
  * devices.myhome.groundfloor.kitchen.accent

Here are some guidelines:

  1) The first section should be either lib or module.
  2) The second section should be the name of the library or module.
  3) The third-eigth sections should be named from a top-down order (like the example above).

Naming standards:

  1) Devices should start with device: device.devicename(or)deviceid.energyused
  2) State should start with state: state.sun.visable = 1
  3) Atoms should start with atom: atom.cpu.count (kind of useless info, but you get the idea)
  4) System type data (disk drive size, cpu, ram, etc, should start with system.
     Eg: system.memory.used, system.memory.free, system.storage.dropbox.used
  5) Things like your house environment is up to you within your module.  For example:
     house.downstairs.livingroom.temperature, house.refrigerator.temperature, house.refrigerator.open,
     house.upstairs.kidsbedroom.temperature, house.upstairs.kidsbedroom.occupied

In the house examples, you can get an average of all temperatures with a result set filter of "house.*.*.temperature",
or "house.upstairs.*.temperature"

*Usage**:

.. code-block:: python

   self._Statistics.increment("module.mymodule.requests.sent")
   self._Statistics.increment("module.mymodule.requests.received")
   self._Statistics.averages("house.upstairs.den.temperature", data['den'])
   self._Statistics.datapoint("house.upstairs.den.occupied", occupied_sensor['den'])

**Developer Notes/Ideas/Todo**:

An idea to mitigrate data loss would be to save data points more often, but marked as temporary. This would allow
the benefits of better averages, but mitigate loss of data. This is at a cost of higher CPU resources.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.11.0

:copyright: Copyright 2015-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/statistics.html>`_
"""
# Import python libraries

try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time
from difflib import SequenceMatcher
import re

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.utils import percentile, global_invoke_all, pattern_search, random_int, dict_merge
from yombo.utils.decorators import cached
from yombo.core.log import get_logger

from yombo.lib.statistics.buckets_manager import BucketsManager
logger = get_logger('library.statistics')


class Statistics(YomboLibrary):
    """
    Library to process all the statistics. Allows long running data to be collectd on devices regardless of
    system actually running the devices. For example, can keep all history of a light bulb even when changing between
    X10, Insteon, or Z-Wave devices running the actual device. This also collections various system performance
    metrics.
    """
    enabled = True  # set to True to start, will be updated when configurations is loaded.
    count_bucket_duration = 300  # How many seconds
    averages_bucket_duration = 300
    _counters = {}  # stores counter information before it's saved to database
    _averages = {}  # stores averages type information
    _datapoints = {}  # stores datapoint data
    _datapoint_last_value = {}  # Used to track duplicates. Duplicate values are removed as it adds no value!

    bucket_lifetimes_default = {'size': 300, 'lifetime': 360}  # 300 seconds, saved for 180 days.
    bucket_lifetimes = {
        '#': {'size': 300, 'lifetime': 360},
        'lib.#': {'size': 300, 'lifetime': 180},
        'lib.atoms.#': {'size': 60, 'lifetime': 180},
        'lib.device.status.#':  {'size': 60, 'lifetime': 180},
        'lib.amqpyombo.amqp.#': {'size': 30, 'lifetime': 180},
        'modules.#': {'size': 60, 'lifetime': 180},
        'devices.#': {'size': 60, 'lifetime': 0},
        'energy.#': {'size': 60, 'lifetime': 0},
    }

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo statistics library"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Brings the library module online. Responsible for setting up framework for storing statistics.
        :param loader: Loader library.
        :return:
        """
        self.enabled = self._Configs.get('statistics', 'enabled', True)
        self.upload_allowed = self._Configs.get('statistics', 'upload', True)
        self.anonymous_allowed = self._Configs.get('statistics', 'anonymous', True)

        # defines bucket time span, default is 5 minutes for all buckets
        self.count_bucket_duration = self._Configs.get('statistics', 'count_bucket_duration', 300)  # 5 minutes for count buckets
        self.averages_bucket_duration = self._Configs.get('statistics', 'averages_bucket_duration', 300)  # 5 minutes for averages buckets

        if self.enabled is not True:
            return

        self.time_between_saves = self._Configs.get('statistics', 'time_between_saves', 308)  # ~5 mins
        self.saveDataLoop = LoopingCall(self._save_statistics)
        self.saveDataLoop.start(self.time_between_saves, False)

        self._upload_statistics_loop = LoopingCall(self._upload_statistics)

        self.unload_deferred = None

        # self.init_deferred = Deferred()
        yield self.load_last_datapoints()

        self.last_upload_count = None

        # return self.init_deferred

    def _start_(self, **kwargs):
        return  # Yombo doesn't currently store statistics in the cloud.
        self._upload_statistics_loop.start(random_int(60*10, .2), False)  # about every 10 minutes

    def _stop_(self, **kwargs):
        """
        Saves statistics data to database.
        :return: A deferred that the shutdown functions use to wait on.
        """
        # if self.init_deferred is not None and self.init_deferred.called is False:
        #     self.init_deferred.callback(1)  # if we don't check for this, we can't stop!

        if self.enabled is True:
            # todo: test more. Changed Oct 28, 2016. Previous method worked, just unclean.
            self.unload_deferred = Deferred()
            self._save_statistics(True, True)
            return self.unload_deferred

    @inlineCallbacks
    def load_last_datapoints(self):
        """
        Datapoints save a specific value at a specific time. Sometimes multiple datapoints are saved with the same
        value. Although this is data, it does not provide additional information. For example, if a thermostat
        module makes a node of the current temperate every 60 seconds, this data becomes usesless. We only care
        about when things change and can deduce that the temperate was the same between datapoints.

        This saves a lot of storage and processing later.

        This function calls a database method to collet a list of datapoints and their last value. It sets this
        into a variable to be used on lookup when a new datapoint is provided. See: :py:meth:`~datapoint`
        """
        if self.enabled is not True:
            return

        self._datapoint_last_value = yield self._LocalDB.get_stat_last_datapoints()
        stat_last_records = yield self._LocalDB.get_stat_last_records()

        # sadly, these are all slightly different...
        if 'counter' in stat_last_records:
            for bucket_time, data in stat_last_records['counter'].items():
                for bucket_name, bucket_data in data.items():
                    if bucket_time not in self._counters:
                        self._counters[bucket_time] = {}
                    if bucket_name not in self._counters[bucket_time]:
                        self._counters[bucket_time][bucket_name] = bucket_data
                    else:
                        self._counters[bucket_time][bucket_name]['value'] += bucket_data['value']
                        self._counters[bucket_time][bucket_name]['restored_from_db'] = bucket_data['restored_from_db']
                        self._counters[bucket_time][bucket_name]['restored_db_id'] = bucket_data['restored_db_id']

        if 'average' in stat_last_records:
            for bucket_time, data in stat_last_records['average'].items():
                for bucket_name, bucket_data in data.items():
                    if bucket_time not in self._averages:
                        self._averages[bucket_time] = {}
                    if bucket_name not in self._averages[bucket_time]:
                        self._averages[bucket_time][bucket_name] = bucket_data
                    else:
                        self._averages[bucket_time][bucket_name]['value']
                        self._averages[bucket_time][bucket_name]['average_data'] += bucket_data['average_data']
                        self._averages[bucket_time][bucket_name]['restored_from_db'] = bucket_data[
                            'restored_from_db']
                        self._averages[bucket_time][bucket_name]['restored_db_id'] = bucket_data[
                            'restored_db_id']

        if 'datapoint' in stat_last_records:
            for bucket_time, data in stat_last_records['datapoint'].items():
                for bucket_name, bucket_data in data.items():
                    if bucket_time not in self._datapoints:
                        self._datapoints[bucket_time] = {}
                    if bucket_name not in self._datapoints[bucket_time]:
                        self._datapoints[bucket_time][bucket_name] = bucket_data
                    else:
                        self._datapoints[bucket_time][bucket_name]['restored_from_db'] = bucket_data['restored_from_db']
                        self._datapoints[bucket_time][bucket_name]['restored_db_id'] = bucket_data['restored_db_id']

        # print("_counters: %s" % self._counters)
        # print("_averages: %s" % self._averages)
        # print("_datapoints: %s" % self._datapoints)
        # self.init_deferred.callback(10)

    @inlineCallbacks
    def _modules_prestarted_(self, **kwargs):
        """
        This function is called before the _start_ function of all modules is called. This implements the hook:
        _statistics_lifetimes_.  The hook should return a dictionary with the following possible keys - not
        all keys are required, only ones should override the default.

        How these values work: If your module is saving stats every 30 seconds, this can consume a lot of data. After
        a while this data might be useless (or important). Periodically, the statistics are merged and save space. The
        following default values: {'full':60, '5m':90, '15m':90, '60m':365, '6hr':730, '24h':1825}  that the system
        will keep full statistics for 60 days. Then, it'll collapse this down to 15 minute averages. It will keep this
        for an additional 90 days. After that, it will keep 15 minute averages for 90 days. At this point, we have 195
        days worth of statistics. The remaining consolidations should be self explanatory.

        *Usage**:

        .. code-block:: python

           def _statistics_lifetimes_(**kwargs):
               return {'modules.mymodulename.#': {'size': 300, 'lifetime': 0}}
        """
        if self.enabled is not True:
            return

        stat_lifetimes = yield global_invoke_all('_statistics_lifetimes_',
                                                 called_by=self,
                                                 )
        for moduleName, item in stat_lifetimes.items():
            if isinstance(item, dict):
                for bucket_name, lifetime in item.items():
                    self.add_bucket_lifetime(bucket_name, lifetime)

    def add_bucket_lifetime(self, bucket_name, values):
        """

        :param bucket_name: bucket_name of bucket
        :param lifetimes: dictionary: size, lifetime
        :return:
        """
        if isinstance(values, dict) is False:
            raise YomboWarning("Bucket lifetimes must be a dictionary.")
        if 'size' not in values:
            raise YomboWarning("Bucket lifetimes must have 'size' defined.")
        if 'lifetime' not in values:
            raise YomboWarning("Bucket lifetimes must have 'lifetime' defined.")
        self.bucket_lifetimes[bucket_name] = values

    @cached(1)
    def _get_bucket_time(self, type, bucket_size=None, bucket_name=None, bucket_lifetime=None):
        """
        Internal function to get time for a given bucket type.

        :param type: Either count, averages, or datapoint.
        :return: A unix epoch time for a bucket.
        """
        if bucket_name is None:
            raise YomboWarning("_get_bucket_time expects a bucket name, got None.")

        suggested_bucket_size, suggested_bucket_lifetime = self.find_bucket_time(bucket_name)
        if bucket_size is None:
            bucket_size = 1
        elif isinstance(bucket_size, int) is False and isinstance(bucket_size, float) is False:
            raise YomboWarning("Invalid bucket_time submitted to _get_bucket_time")

        if bucket_lifetime is None:
            bucket_lifetime = suggested_bucket_lifetime

        if type == 'datapoint':
            try:
                number_of_decimals = len(bucket_size.split('.')[1])
            except:
                number_of_decimals = 0

            if number_of_decimals > 0:
                the_time = round(round((time() / bucket_size), 1) * bucket_size, 1)
            else:
                the_time = int(int((time() / bucket_size)) * bucket_size)
            return {'size': bucket_size,
                    'time': the_time,
                    'lifetime': bucket_lifetime}

        return {'size': bucket_size,
                'time': int(int((time() / bucket_size)) * bucket_size),
                'lifetime': bucket_lifetime}

    @cached(1)  # use the version that support kwargs....
    def _validate_name(self, bucket_name):
        """
        Validates the bucket_name being submitted is valid. No point in sending badly bucket_named
        items to the server, as the server will simply perform this same check and
        discard any invalid ones.

        .. note::

            If the server detects too many invalid bucket_names, the gateway will be blocked from
            saving statistics in the future.

        :param bucket_name: Label for the statistic
        :type bucket_name: string
        """
        parts = bucket_name.split('.', 10)
        if len(parts) < 3:
            raise YomboWarning("bucket_name must have at least 3 parts, preferably at least 4.")
        elif len(parts) > 8:
            raise YomboWarning("bucket_name has too many parts, no more than 8.")

        for count in range(0, len(parts)):
            if len(parts[count]) < 3:
                raise YomboWarning("'%s' is too short, must be at least 3 characters: " % parts[count])

    def datapoint(self, bucket_name, value, anon=None, bucket_size=None, lifetimes=None):
        """
        Set a datapoint numberic value. For example, set the current measured temperature.

        .. code-block:: python

           self._Statistics.datapoint("house.upstairs.den.occupied", 1)

        :param bucket_name: bucket_name of the statistic to save.
        :type bucket_name: string
        :param value: A numbered value to set.
        :type value: int
        :param bucket_time: How many minutes the bucket should be. Must be a multiple that gets to 60.
        :type value: bool
        :param anon: If anonymous type data, set to True, default is False
        :type value: bool
        """
        if self.enabled is not True:
            return
        try:
            self._validate_name(bucket_name)
        except YomboWarning as e:
            return

        if bucket_name in self._datapoint_last_value:  # lookup last value saved.
            if self._datapoint_last_value[bucket_name] == value:  # we don't save duplicates!
                # print("stats datapoint droping duplicate bucketname/value: %s/%s" % (bucket_name, value))
                return

        if lifetimes is not None:
            self.add_bucket_lifetime(bucket_name, lifetimes)

        if bucket_size is None:
            bucket_size = 1

        bucket = self._get_bucket_time('datapoint', bucket_size=bucket_size, bucket_name=bucket_name)
        # print("stat datapoint bucket details: %s" % bucket)
        if bucket['time'] not in self._datapoints:
            self._datapoints[bucket['time']] = {}
        if bucket_name not in self._datapoints[bucket['time']]:
            self._datapoints[bucket['time']][bucket_name] = {
                'time': bucket['time'],
                'lifetime': bucket['lifetime'],
                'size': bucket_size,
                'type': 'datapoint',
                'name': bucket_name,
                'anon': False,
                'restored_from_db': False,
                'touched': True,
                'value': value,
            }
        else:
            self._datapoints[bucket['time']][bucket_name].update(
                {
                    'value': value,
                    'touched': True,
                }
            )

        # print("datapoint final: %s" % self._datapoints[bucket['time']][bucket_name])

        if anon is True:
            self._datapoints[bucket['time']][bucket_name]['anon'] = True
        else:
            self._datapoints[bucket['time']][bucket_name]['anon'] = False

    def count(self, bucket_name, value, bucket_size=None, anon=None, lifetimes=None):
        """
        Set a count value. Typically, this isn't used, instead use ``increment`` or ``decrement`` due to
        bucket time rollover.

        :param bucket_name: bucket_name of the statistic to save.
        :type bucket_name: string
        :param value: A numbered value to set.
        :type value: int
        :param bucket_size: How many seconds the bucket should be. Must be a multiple that gets to 60.
        :type value: bool
        :param anon: If anonymous type data, set to True, default is False
        :type value: bool
        """
        if self.enabled is not True:
            return
        try:
            self._validate_name(bucket_name)
        except YomboWarning as e:
            return

        if lifetimes is not None:
            self.add_bucket_lifetime(bucket_name, lifetimes)

        bucket = self._get_bucket_time('count', bucket_size=bucket_size, bucket_name=bucket_name)

        if bucket['time'] not in self._counters:
            self._counters[bucket['time']] = {}

        if bucket_name not in self._counters[bucket['time']]:
            self._counters[bucket['time']][bucket_name] = {
                'time': bucket['time'],
                'size': bucket['size'],
                'lifetime': bucket['lifetime'],
                'type': 'counter',
                'name': bucket_name,
                'anon': False,
                'restored_from_db': False,
                'touched': True,
                'value': value,
            }
        else:
            self._counters[bucket['time']][bucket_name].update(
                {
                    'value': value,
                    'touched': True,
                }
            )

        if anon is None:
            if 'anon' not in self._counters[bucket['time']][bucket_name]['anon']:
                self._counters[bucket['time']][bucket_name]['anon'] = False
        elif anon is True:
            self._counters[bucket['time']][bucket_name]['anon'] = True
        elif anon is False:
            self._counters[bucket['time']][bucket_name]['anon'] = False

    def increment(self, bucket_name, count=1, bucket_size=None, anon=None, lifetimes=None):
        """
        Increment a counter value. If doesn't exist, will create the new counter for the given bucket_name.

        .. code-block:: python
        
           self._Statistics.increment("module.mymodule.requests.sent")

        :param bucket_name: bucket_name of the statistic to save.
        :type bucket_name: string
        :param count: How many to increment by, defaults to 1.
        :type count: int
        :param bucket_size: How many seconds the bucket should be. Must be a multiple that gets to 60.
        :type value: bool
        :param anon: If anonymous type data, set to True, default is False
        :type value: bool
        """
        if self.enabled is not True:
            return
        try:
            self._validate_name(bucket_name)
        except YomboWarning as e:
            return

        if lifetimes is not None:
            self.add_bucket_lifetime(bucket_name, lifetimes)

        bucket = self._get_bucket_time('count', bucket_size=bucket_size, bucket_name=bucket_name)
        # if bucket_name == "lib.configuration.set.new":
        #     print("stat increment start: %s" % self._counters)
        if bucket['time'] not in self._counters:
            self._counters[bucket['time']] = {}

        if bucket_name not in self._counters[bucket['time']]:
            self._counters[bucket['time']][bucket_name] = {
                'time': bucket['time'],
                'size': bucket['size'],
                'lifetime': bucket['lifetime'],
                'type': 'counter',
                'name': bucket_name,
                'anon': False,
                'restored_from_db': False,
                'touched': True,
                'value': count,
            }
        else:
            self._counters[bucket['time']][bucket_name]['value'] += count
            self._counters[bucket['time']][bucket_name]['touched'] = True

        if anon is None:
            if 'anon' not in self._counters[bucket['time']][bucket_name]['anon']:
                self._counters[bucket['time']][bucket_name]['anon'] = False
        elif anon is True:
            self._counters[bucket['time']][bucket_name]['anon'] = True
        elif anon is False:
            self._counters[bucket['time']][bucket_name]['anon'] = False

        # if bucket_name == "lib.configuration.set.new":
        #     print("stat increment end: %s" % self._counters)

    def decrement(self, bucket_name, count=1, bucket_size=None, anon=None, lifetimes=None):
        """
        Decrement a counter value. If doesn't exist, will create the new counter for the given bucket_name.

        .. code-block:: python
        
           self._Statistics.decrement("module.mymodule.requests.sent")

        :param bucket_name: bucket_name of the statistic to save.
        :type bucket_name: string
        :param count: How many to increment by, defaults to -1.
        :type count: int
        :param bucket_size: How many seconds the bucket should be. Must be a multiple that gets to 60.
        :type value: bool
        :param anon: If anonymous type data, set to True, default is False
        :type value: bool
        """
        if self.enabled is not True:
            return
        try:
            self._validate_name(bucket_name)
        except YomboWarning as e:
            return

        if lifetimes is not None:
            self.add_bucket_lifetime(bucket_name, lifetimes)

        bucket = self._get_bucket_time('count', bucket_size=bucket_size, bucket_name=bucket_name)

        if bucket['time'] not in self._counters:
            self._counters[bucket['time']] = {}

        if bucket_name not in self._counters[bucket['time']]:
            self._counters[bucket['time']][bucket_name] = {
                'time': bucket['time'],
                'size': bucket['size'],
                'lifetime': bucket['lifetime'],
                'type': 'counter',
                'name': bucket_name,
                'anon': False,
                'restored_from_db': False,
                'touched': True,
                'value': count,
            }
        else:
            self._counters[bucket['time']][bucket_name]['value'] -= count
            self._counters[bucket['time']][bucket_name]['touched'] = True

        if anon is None:
            if 'anon' not in self._counters[bucket['time']][bucket_name]['anon']:
                self._counters[bucket['time']][bucket_name]['anon'] = False
        elif anon is True:
            self._counters[bucket['time']][bucket_name]['anon'] = True
        elif anon is False:
            self._counters[bucket['time']][bucket_name]['anon'] = False

    def averages(self, bucket_name, value, bucket_size=None, anon=None, lifetimes=None):
        """
        Set a time on how long something took to complete in milliseconds. A single timer can be set many times, but
        it will be averaged per bucket.

        .. code-block:: python
        
           self._Statistics.averages("house.upstairs.den.temperature", data['den'])

        :param bucket_name: bucket_name of the statistic to save.
        :type bucket_name: string
        :param value: How long something took in milliseconds.
        :type value: int4
        :param bucket_size: How many seconds the bucket should be. Must be a multiple that gets to 60.
        :type value: bool
        :param anon: If anonymous type data, set to True, default is False
        :type value: bool
        """
        if self.enabled is not True:
            return
        try:
            self._validate_name(bucket_name)
        except YomboWarning as e:
            return

        if lifetimes is not None:
            self.add_bucket_lifetime(bucket_name, lifetimes)

        bucket = self._get_bucket_time('averages', bucket_size=bucket_size, bucket_name=bucket_name)

        if bucket['time'] not in self._averages:
            self._averages[bucket['time']] = {}

        if bucket_name not in self._averages[bucket['time']]:
            self._averages[bucket['time']][bucket_name] = {
                'time': bucket['time'],
                'lifetime': bucket['lifetime'],
                'values': [value],
                'restored_from_db': False,
                'anon': False,
                'size': bucket['size'],
                'type': 'average',
                'name': bucket_name,
                'average_data': [],
                'touched': True,
            }
        else:
            self._averages[bucket['time']][bucket_name]['average_data'].append(value)
            self._counters[bucket['time']][bucket_name]['touched'] = True

        if anon is None:
            if 'anon' not in self._averages[bucket['time']][bucket_name]['anon']:
                self._averages[bucket['time']][bucket_name]['anon'] = False
        elif anon is True:
            self._averages[bucket['time']][bucket_name]['anon'] = True
        elif anon is False:
            self._averages[bucket['time']][bucket_name]['anon'] = False

    def get_stat(self, bucket_name, bucket_type=None):
        results = []
        # sum(value) as value, bucket_name, type, round(bucket / %s) * %s AS bucket
        find_name = bucket_name.replace('%', '#')
        if bucket_type is None or bucket_type is 'counter':
            for bucket in self._counters:
                for stat in pattern_search(find_name, self._counters[bucket]):
                    too_add = self._counters[bucket][stat]
                    new_result = {
                        'name': stat,
                        'value': too_add['value'],
                        'type': 'counter',
                        'bucket': bucket,
                    }
                    results.append(new_result)

        if bucket_type is None or bucket_type is 'average':
            for bucket in self._averages:
                for stat in pattern_search(find_name, self._averages[bucket]):
                    too_add = self._averages[bucket][stat]
                    new_result = {
                        'name': stat,
                        'value': too_add['value'],
                        'type': 'average',
                        'bucket': bucket,
                    }
                    results.append(new_result)

        if bucket_type is None or bucket_type is 'datapoint':
            for bucket in self._datapoints:
                for stat in pattern_search(find_name, self._datapoints[bucket]):
                    too_add = self._datapoints[bucket][stat]
                    new_result = {
                        'name': stat,
                        'value': too_add['value'],
                        'type': 'datapoint',
                        'bucket': bucket,
                    }
                    results.append(new_result)

        return results

    @inlineCallbacks
    def collect_stats(self, names, start, end=None, resolution=None):
        """
        Return statistics based on names, resolution (bucket size), start time, and end time.

        :param names: Either a single statistic name or a list of statistic names.
        :param start: Time (seconds since epoch) to start the collect stats from.
        :param end: Time (seconds since epoch) to end the stats (default is current time).
        :param resolution: How detailed the data should be. This helps to reduce stat size. Default is 300
        :return:
        """
        def is_number(s):
            try:
                float(s)
                return True
            except ValueError as e:
                return False

        if resolution is None:
            resolution = 300
        if end is None:
            end = int(time())

        if not is_number(resolution):
            raise ValueError("Resolution should be number, but {} is given".format(type(resolution)))
        if not is_number(start):
            raise ValueError("Start should be number, but {} is given".format(type(start)))
        if not is_number(end):
            raise ValueError("End should be number, but {} is given".format(type(end)))
        if isinstance(names, str):
            names = [names]
        if not (isinstance(names, (list, tuple)) and all(isinstance(name, str) for name in names)):
            raise ValueError("names must be a string or list/tuple of strings")

        data = yield self._LocalDB.statistic_get_range(names, start, end, minimal=True)
        bm = BucketsManager()
        bm.process(data)
        stat = bm.get_stats(resolution, start, end)
        return stat

    @inlineCallbacks
    def _save_statistics(self, full=False, gateway_stopping=False):
        """
        Internal function to save the statistics information to database. This is performed regularly while the gateway
        is running and during shutdown. For perfomance reasons, it's not saved instantly.
        """
        if self.enabled is not True:
            return

        current_time = time()

        to_save = []
        for bucket_time in list(self._counters.keys()):
            for bucket_name in list(self._counters[bucket_time].keys()):
                current_bucket = self._counters[bucket_time][bucket_name]
                current_bucket_time = self._get_bucket_time('count', bucket_name=bucket_name)
                if full or bucket_time < (current_bucket_time['time']):
                    # print("count bucket: %s" % current_bucket)
                    if 'restored_db_id' in current_bucket and current_bucket['restored_db_id'] is not False:
                        if current_bucket['touched'] is True:
                            # print("_counters stats save bucket, updating existing")
                            yield self._LocalDB.save_statistic(
                                current_bucket,
                                int(bucket_time < (current_bucket_time['time']))
                            )
                            current_bucket_time['touched'] = False
                    else:
                        # print("_counters stats save bucket, finished: %s < %s" % (int(bucket_time), current_bucket_time))
                        od = {
                            'bucket_time': current_bucket['time'],
                            'bucket_size': current_bucket_time['size'],
                            'bucket_lifetime': current_bucket['lifetime'],
                            'bucket_type': current_bucket['type'],
                            'bucket_name': current_bucket['name'],
                            'bucket_value': current_bucket['value'],
                            'updated_at': int(time()),
                            'anon': current_bucket['anon'],
                            'finished': int(bucket_time < (current_bucket_time['time'])),
                        }
                        to_save.append(od)

                    if bucket_time < (current_bucket_time['time']):
                        del self._counters[bucket_time][bucket_name]
            if len(self._counters[bucket_time]) == 0:
                del self._counters[bucket_time]


        for bucket_time in list(self._averages.keys()):
            for bucket_name in list(self._averages[bucket_time].keys()):
                current_bucket = self._averages[bucket_time][bucket_name]
                current_bucket_time = self._get_bucket_time('average', bucket_name=bucket_name)
                if full or bucket_time < (current_bucket_time['time']):

                    try:
                        self.calc_averages(bucket_time, bucket_name)
                    except Exception as e:
                        logger.warn("Not saving average bucket_time (no values): {bucket_time}:{bucket_name}  Error: {e}",
                                    bucket_time=bucket_time, bucket_name=bucket_name, e=e)
                        continue
                    else:
                        if 'restored_db_id' in current_bucket and current_bucket['restored_db_id'] is not False:
                            if current_bucket['touched'] is True:
                                # print("_averages stats save bucket, updating existing")
                                yield self._LocalDB.save_statistic(current_bucket,
                                                                   int(bucket_time < (current_bucket_time['time'])))
                                current_bucket_time['touched'] = False
                        else:
                            # print("_averages stats save bucket, finished: %s < %s" % (
                            # int(bucket_time), int((current_bucket_time['time']))))
                            od = {
                                'bucket_time': current_bucket['time'],
                                'bucket_size': current_bucket['size'],
                                'bucket_lifetime': current_bucket['lifetime'],
                                'bucket_type': current_bucket['type'],
                                'bucket_name': current_bucket['name'],
                                'bucket_value': current_bucket['value'],
                                'bucket_average_data': json.dumps(current_bucket['average_data'], separators=(',',':')),
                                'updated_at': int(time()),
                                'anon': current_bucket['anon'],
                                'finished': int(bucket_time < (current_bucket_time['time'])),
                            }
                            to_save.append(od)

                    if bucket_time < (current_bucket_time['time']):
                        del self._averages[bucket_time][bucket_name]
            if len(self._averages[bucket_time]) == 0:
                del self._averages[bucket_time]

        for bucket_time in list(self._datapoints.keys()):
            for bucket_name in list(self._datapoints[bucket_time].keys()):
                current_bucket = self._datapoints[bucket_time][bucket_name]
                if 'restored_db_id' in current_bucket and current_bucket['restored_db_id'] is not False:
                    if current_bucket['touched'] is True:
                        # print("_datapoints stats save bucket, updating existing")
                        yield self._LocalDB.save_statistic(current_bucket,
                                                           int(bucket_time < (current_bucket_time['time'])))
                        current_bucket_time['touched'] = False
                else:
                    # print("_datapoints stats save bucket, finished: %s < %s" % (
                    # int(bucket_time), int((current_bucket_time['time']))))
                    od = {
                        'bucket_time': current_bucket['time'],
                        'bucket_size': current_bucket['size'],
                        'bucket_lifetime': current_bucket['lifetime'],
                        'bucket_type': current_bucket['type'],
                        'bucket_name': current_bucket['name'],
                        'bucket_value': current_bucket['value'],
                        'updated_at': int(time()),
                        'anon': current_bucket['anon'],
                        'finished': 1,
                    }
                    to_save.append(od)

                if bucket_time < current_time - 300:
                    del self._datapoints[bucket_time][bucket_name]
            if len(self._datapoints[bucket_time]) == 0:
                del self._datapoints[bucket_time]

        try:
            if len(to_save) > 0:
                logger.debug("Stats save data: {to_save}", to_save=to_save)
                yield self._LocalDB.save_statistic_bulk(to_save)
            to_save = []
        except Exception as error:
            logger.warn("Error while trying to bulk save: {error}", error=error)

        if gateway_stopping is True:
            self.unload_deferred.callback(1)
        # else:
        #     self.consolidate_db()  # for testing

    def calc_averages(self, bucket_time, bucket_name):
        values = self._averages[bucket_time][bucket_name]['values']
        if len(values) > 0:
            sorted_values = sorted(values)

            median = percentile(list(sorted_values), 0.50)
            percentile90 = percentile(sorted_values, 0.90)
            values_90 = []

            for val in sorted_values:
                if val <= percentile90:
                    values_90.append(val)
                else:
                    break

            median_90 = percentile(values_90, 0.50)

            average_data = {
                'count': len(sorted_values),
                'median': median,
                'upper': sorted_values[-1],
                'lower': sorted_values[0],
                'upper_90': values_90[0],
                'lower_90': values_90[-1],
                'median_90': median_90,
            }

            restored_averages = self._averages[bucket_time][bucket_name]['restored_from_db']

            if restored_averages is not False:
                counts = [restored_averages['count'], average_data['count']]
                medians = [restored_averages['median'], average_data['median']]
                uppers = [restored_averages['upper'], average_data['upper']]
                lowers = [restored_averages['lower'], average_data['lower']]
                upper_90s = [restored_averages['upper_90'], average_data['upper_90']]
                lower_90s = [restored_averages['lower_90'], average_data['lower_90']]
                median_90s = [restored_averages['median_90'], average_data['median_90']]

                # found this weighted averaging method here:
                # http://stackoverflow.com/questions/29330792/python-weighted-averaging-a-list
                # new_average_data = {}
                average_data['count'] = restored_averages['count'] + average_data['count']
                average_data['median'] = sum(x * y for x, y in zip(medians, counts)) / sum(counts)
                average_data['upper'] = sum(x * y for x, y in zip(uppers, counts)) / sum(counts)
                average_data['lower'] = sum(x * y for x, y in zip(lowers, counts)) / sum(counts)
                average_data['upper_90'] = sum(x * y for x, y in zip(upper_90s, counts)) / sum(counts)
                average_data['lower_90'] = sum(x * y for x, y in zip(lower_90s, counts)) / sum(counts)
                average_data['median_90'] = sum(x * y for x, y in zip(median_90s, counts)) / sum(counts)

                # self._averages[bucket_time][bucket_name]['restored_from_db'] = True
            self._averages[bucket_time][bucket_name]['value'] = average_data['median_90']
            self._averages[bucket_time][bucket_name]['average_data'] = average_data

            return average_data
        elif self._averages[bucket_time][bucket_name]['restored_from_db'] is not False:
            self._averages[bucket_time][bucket_name]['average_data'] = \
                self._averages[bucket_time][bucket_name]['restored_from_db']
        else:
            raise YomboWarning("Calc_averages must have a list of ints or floats.")

    def find_bucket_time(self, bucket_name):
        """
        :return:
        """
        def make_regex(bucket_lifetimes):
            thelist = {}
            for filter, data in bucket_lifetimes.items():
                thelist[filter] = re.compile(filter.replace('#', '.*').replace('$', '\$').replace('+', '[/\$\s\w\d]+'))
            return thelist

        def select_closest( the_list, search_for):  # semi-reusing fuzzydict..
            stringDiffLib = SequenceMatcher()
            stringDiffLib.set_seq1(search_for.lower())
            # examine each key in the dict
            best_ratio = -1
            best_match = None
            for key in the_list:
                # key must be a string, otherwise it is skipped!
                try:
                    stringDiffLib.set_seq2(key.lower())
                except TypeError:
                    continue                # might get here, even though it's not a string. Catch it!
                try:
                    # get the match ratio
                    curRatio = stringDiffLib.ratio()
                except TypeError:
                    break
                # if this is the best ratio so far - save it and the value
                if curRatio > best_ratio:
                    best_ratio = curRatio
                    best_match = key
            return best_match

        regexs = make_regex(self.bucket_lifetimes)

        # get all possible matching filters
        filters = []
        for filter, regex in regexs.items():
            result = regex.match(bucket_name)
            if result is not None:
                filters.append(filter)

        # now lets strip this down
        if len('filters') > 0:
            bucket_time = select_closest(regexs, bucket_name)
            return self.bucket_lifetimes[bucket_time]['size'], self.bucket_lifetimes[bucket_time]['lifetime']
        else:
            return self.bucket_lifetimes_default['size'], self.bucket_lifetimes_default['lifetime']

    @inlineCallbacks
    def _upload_statistics(self):
        """
        Internal function to upload statistics to Yombo based on system settings. This is called periodically
        to check if any statistics need to be uploaded, usually after a save event occcurs.
        
        Not implemented yet.
        :return: 
        """
        stats = yield self._LocalDB.get_uploadable_statistics(0)
        if len(stats) > 0:

            headers = {
                "request_type": "stats_save",
            }
            request_msg = self._AMQPYombo.generate_message_request(
                'ysrv.e.py_stats',
                'yombo.gateway.statistics',
                'yombo.server.statistics',
                headers,
                stats)
            request_msg['callback'] = self.upload_statistics_complete

            # logger.debug("request_msg: {request_msg}", request_msg=request_msg)
            self._AMQPYombo.publish(**request_msg)
            self.last_upload_count = len(stats)
        else:
            self.last_upload_count = 0

    def upload_statistics_complete(self, msg=None, **kwargs):
        logger.debug("upload_statistics_complete got message: {msg}", msg=msg)
        if 'stats_completed' in msg and len(msg['stats_completed']) > 0:
            yield self._LocalDB.set_uploaded_statistics(2, msg['stats_completed'])
        if 'stats_failed' in msg and len(msg['stats_failed']) > 0:
            yield self._LocalDB.set_uploaded_statistics(-1, msg['stats_failed'])

        if self.last_upload_count > 1900: # if we upload a lot of stats last time, maybe we have more to upload.
            reactor.callLater(36, self._upload_statistics)  # give the system a few seconds to chill
