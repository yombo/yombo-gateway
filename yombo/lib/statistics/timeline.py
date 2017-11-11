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

class Timeline:
    def __init__(self, intervals, start=None, end=None, default=0):
        self._intervals = sorted(intervals, key=lambda d: d.start)
        self._start = self._intervals[0].start if start is None else start
        self._end = self._intervals[-1].end if end is None else end
        self._default = 0

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end

    def take_next_bucket(self, intervals, bucket_size, bucket_start):
        bucket_end = bucket_size + bucket_start
        bucket = []
        if len(intervals) == 0:
            return bucket, intervals
        for i, interval in enumerate(intervals):
            if bucket_start > interval.start:  # Invariance: interval.start < bucket_start
                if bucket_start >= interval.end:
                    # 1. interval lies completely before a bucket -- pass this interval
                    continue
                elif bucket_end >= interval.end:
                    # 2. interval lies within a bucket partially (second part)
                    first_part, second_part = interval.split(bucket_start)
                    bucket.append(second_part)
                    continue
                else:
                    # 3. interval surrounds bucket completely
                    first_part, second_part = interval.split(bucket_start)
                    second_part, third_part = second_part.split(bucket_end)
                    bucket.append(second_part)
                    return bucket, [third_part] + intervals[i + 1:]
            else:
                if bucket_end >= interval.end:  # Invariance: interval.start >= bucket_start
                    # 1. interval lies within a bucket completely
                    bucket.append(interval)
                    continue
                elif bucket_end > interval.start:
                    # 2. interval lies within a bucket partially (first part)
                    first_part, second_part = interval.split(bucket_end)
                    bucket.append(first_part)
                    return bucket, [second_part] + intervals[i + 1:]
                else:
                    # 3. interval lies completely after a bucket
                    return bucket, intervals[i:]
        return bucket, list()

    def group_into_buckets(self, bucket_size, start=None, end=None):
        start = self.start if start is None else start
        end = self.end if end is None else end

        buckets = []

        if start >= end:
            return buckets

        intervals = self._intervals

        for bucket_start in range(start, end, bucket_size):
            next_bucket, intervals = self.take_next_bucket(intervals, bucket_size, bucket_start)
            buckets.append(next_bucket)
        return {"buckets": buckets, "bucket_size": bucket_size, "start": start, "end": end}
