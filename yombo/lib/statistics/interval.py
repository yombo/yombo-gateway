# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Statistics @ Module Development <https://yombo.net/docs/libraries/statistics>`_


.. moduleauthor:: https://github.com/freekotya
.. versionadded:: 0.14.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
"""

import numpy as np

from abc import ABCMeta, abstractmethod, abstractproperty


class IntervalBase():
    __metaclass__ = ABCMeta

    @abstractproperty
    def size(self):
        raise NotImplementedError

    @abstractproperty
    def value(self):
        raise NotImplementedError

    @abstractmethod
    def trim(self, start=None, end=None):
        raise NotImplementedError


class Interval(IntervalBase):
    def __init__(self, start, end, value=0.0, part=1.0, fake=False):
        self._start = start
        self._end = end
        self._value = value
        self._part = part
        self._fake = fake
        return

    @property
    def size(self):
        assert (self._end > self._start)
        return self._end - self.start

    @property
    def value(self):
        return self._value * self._part

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end

    def trim(self, start=None, end=None):
        if start is None:
            start = self._start
        if end is None:
            end = self._end
        new_start = max(self._start, start)
        new_end = min(self._end, end)
        assert (new_start <= new_end)
        # assert(self.size > 0)
        if self.size > 0:
            part = self._part * ((new_end - new_start) / self.size)
        else:
            part = 0.0
        return Interval(new_start, new_end, self._value, part, self._fake)

    def split(self, coord):
        if self._start >= coord or self._end <= coord:
            raise ValueError("split coordinate must lie in [{}, {}) interval, but has value of {}" \
                             .format(self._start, self._end, coord))
        first_part = self._part * ((coord - self._start) / self.size)
        second_part = self._part - first_part
        return (Interval(self._start, coord, self._value, first_part, self._fake),
                Interval(coord, self._end, self._value, second_part, self._fake))

    def __repr__(self):
        return "[{}, {}]({}, {}, {})".format(self._start, self._end, self._value, self._part, self._fake)


class Point(IntervalBase):
    def __init__(self, coord, value=0.0):
        self._coord = coord
        self._value = value
        # it will behave like an very small interval
        self._end = np.nextafter(self._coord, self._coord + 1)

    @property
    def value(self):
        return self._value

    @property
    def coord(self):
        return self._coord

    @property
    def size(self):
        return 0.0

    @property
    def start(self):
        return self._coord

    @property
    def end(self):
        return self._end

    def trim(self, start=None, end=None):
        # no trimming for point
        return self

    def __repr__(self):
        return "[{}, {}]".format(self._coord, self._value)
