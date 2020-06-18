# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Statistics @ Module Development <https://yombo.net/docs/libraries/statistics>`_


.. moduleauthor:: https://github.com/freekotya
.. versionadded:: 0.14.0

:copyright: Copyright 2017-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/statistics/aggregator.html>`_
"""
import numpy as np

from abc import ABCMeta, abstractmethod


class AggregatorBase:
    __metaclass__ = ABCMeta

    def __init__(self):
        self._agg_func = None
        self._default_agg_func_value = None

    @property
    def agg_func(self):
        return self._agg_func

    @property
    def default_agg_func_value(self):
        return self._default_agg_func_value

    @abstractmethod
    def aggregate(self, data):
        buckets = data["buckets"]
        if len(data) > 0:
            return [self._agg_func(data_part) if len(data_part) > 0 else self._default_agg_func_value for data_part in
                    buckets]
        else:
            return self._default_agg_func_value


class CounterAggregator(AggregatorBase):
    def __init__(self):
        super().__init__()
        self._agg_func = lambda x: np.sum([xx.value for xx in x])
        self._default_agg_func_value = 0


class AverageAggregator(AggregatorBase):
    def __init__(self):
        super().__init__()
        self._agg_func = lambda x: np.average([xx.value for xx in x])
        self._default_agg_func_value = 0


class PointAverageAggregator(AggregatorBase):
    def __init__(self):
        super().__init__()
        self._agg_func = lambda x: np.average([xx.value for xx in x])
        self._default_agg_func_value = 0

    def split_average(self, bucket, bucket_size, bucket_start):
        alphas = np.array([point.coord for point in bucket], dtype=np.float)
        values = np.array([point.value for point in bucket], dtype=np.float)
        alphas = 1.0 - (alphas - bucket_start) / bucket_size
        return alphas, values

    def aggregate(self, data):
        buckets, bucket_size, start = data["buckets"], data["bucket_size"], data["start"]
        current_value = self._default_agg_func_value
        aggregated = []
        for bucket, bucket_start in zip(buckets, range(start, start + bucket_size * len(buckets), bucket_size)):
            if len(bucket) == 0:
                aggregated.append(current_value)
            else:
                alphas, values = self.split_average(bucket, bucket_size, bucket_start)
                # print(alphas, values)
                aggregated.append(current_value + np.mean(alphas * (values - current_value)))
                current_value = values[-1]
                del alphas
                del values
        return aggregated


class CustomAggregator(AggregatorBase):
    def __init__(self, agg_func, default_agg_func_value):
        super().__init__()
        self._agg_func = agg_func
        self._default_agg_func_value = default_agg_func_value


class AggregatorFactory():
    # This is the factory method
    @staticmethod
    def get_aggregator(bucket_type, **kwargs):
        if bucket_type == "counter":
            return CounterAggregator()
        elif bucket_type == "average":
            return AverageAggregator()
        elif bucket_type == "datapoint":
            return PointAverageAggregator()
        else:
            # default behaviour for unknown bucket_type is averaging
            agg_func = kwargs.get("agg_func", np.average)
            default_agg_func_value = kwargs.get("default_agg_func_value", 0)
            return CustomAggregator(agg_func, default_agg_func_value)