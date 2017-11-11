# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Statistics @ Module Development <https://docs.yombo.net/Libraries/Statistics>`_


.. moduleauthor:: https://github.com/freekotya
.. versionadded:: 0.14.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
"""

from collections import defaultdict

from yombo.lib.statistics.aggregator import AggregatorFactory
from yombo.lib.statistics.bucket_timeline_handler import BucketTimelineHandler


class BucketsManager:
    def __init__(self):
        self._handlers = {}

    def process(self, data):
        # print("bm process data: %s" % data)
#        flatten_inputs = sum(data, [])
        bucket_dict = defaultdict(lambda: [])

        for values in data:
            bucket_dict[values['bucket_name']].append(values)

        for bucket_name, values in bucket_dict.items():
            bucket_type = values[0]['bucket_type']
            self._handlers[bucket_name] = BucketTimelineHandler(bucket_name=bucket_name,
                                                                bucket_type=bucket_type,
                                                                db_values=values,
                                                                aggregator=AggregatorFactory.get_aggregator(
                                                                    bucket_type))

        # for dbvalue in map(DBValue.from_db_string, flatten_inputs):
        #     bucket_dict[dbvalue.bucket_name].append(dbvalue)
        #
        # for bucket_name, db_values in bucket_dict.items():
        #     bucket_type = db_values[0].bucket_type
        #     self._handlers[bucket_name] = BucketTimelineHandler(bucket_name=bucket_name,
        #                                                         bucket_type=bucket_type,
        #                                                         db_values=db_values,
        #                                                         aggregator=AggregatorFactory.get_aggregator(
        #                                                             bucket_type))

    def stat_bucket(self, bucket_name, bucket_size, start=None, end=None):
        return self._handlers[bucket_name].stat(bucket_size, start, end)

    def get_stats(self, bucket_size, start, end):
        granulated = list(range(start, end, bucket_size))
        result = {'buckets': granulated, 'values': {}}
        for bucket_name in self._handlers.keys():
            result['values'][bucket_name] = self.stat_bucket(bucket_name, bucket_size, start, end)
        return result

    def bucket_names(self):
        return list(sorted(self._handlers.keys()))
