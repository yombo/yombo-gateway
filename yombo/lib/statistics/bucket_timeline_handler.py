# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Statistics @ Module Development <https://yombo.net/docs/Libraries/Statistics>`_


.. moduleauthor:: https://github.com/freekotya
.. versionadded:: 0.14.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
"""

from yombo.lib.statistics.timeline import Timeline
from yombo.lib.statistics.interval import Point, Interval
from yombo.lib.statistics.aggregator import AggregatorFactory


class BucketTimelineHandler:
    def __init__(self, bucket_name, bucket_type, db_values, aggregator=None, default=0):
        self._bucket_name = bucket_name
        self._bucket_type = bucket_type
        self._aggregator = aggregator if aggregator is not None else AggregatorFactory.get_aggregator(bucket_type)
        # sort db values by bucket_time
        self._db_values = sorted(db_values, key=lambda d: d['bucket_time'])
        intervals = []
        for db_value in self._db_values:
            start = db_value['bucket_time']
            end = db_value['bucket_time'] + db_value['bucket_size']
            value = db_value['bucket_value']
            if self._bucket_type == "datapoint":
                intervals.append(Point(start, value))
            else:
                intervals.append(Interval(start, end, value))
        self._timeline = Timeline(intervals=intervals, start=None, end=None, default=default)

    @property
    def start(self):
        return self._timeline.start

    @property
    def end(self):
        return self._timeline.end

    def group_into_buckets(self, bucket_size, start=None, end=None):
        return self._timeline.group_into_buckets(bucket_size, start, end)

    def stat(self, bucket_size, start=None, end=None):
        start = self.start if start is None else start
        end = self.end if end is None else end

        return self._aggregator.aggregate(self.group_into_buckets(bucket_size, start, end))
