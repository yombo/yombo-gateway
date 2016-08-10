"""
Various function decorators.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
from time import time
# Import python libraries
from functools import wraps

# Import Yombo libraries
from yombo.core.log import get_logger
import yombo.utils

logger = get_logger('utils.utils')

def memoize_(func):
    """
    Reuse the results of a static function. Subsequent calls will get cached results.

    **Usage**:

    .. code-block:: python

        from yombo.utils.decorators import memoize_

        print fib(35) # Without decorator, will take a little bit of time.
        print fib(35) # With decorator, will be nearly instant - even on first call for a fib.

        @memoize_
        def fib(x):
            if num < 2:
                return num
            else:
                return fib(num-1) + fib(num-2)
    """
    saved = {}

    @wraps(func)
    def _memoize(*args):
        if args not in saved:
            saved[args] = func(*args)
        return saved[args]
    return _memoize

class memoize_ttl(object):
    """
    Taken from: http://jonebird.com/2012/02/07/python-memoize-decorator-with-ttl-argument/

    Decorator that caches a function's return value each time it is called within a TTL.
    If called within the TTL and the same arguments, the cached value is returned,
    If called outside the TTL or a different value, a fresh value is returned.

    Default TTL is 60 seconds

    **Usage**:

    .. code-block:: python

        from yombo.utils.decorators import memoize_ttl

        print fib(35) # Without decorator, will take a little bit of time.
        print fib(35) # With decorator, will be nearly instant - even on first call for a fib.

        @memoize_ttl(5) # memoize for 5 seconds
        def fib(x):
            if num < 2:
                return num
            else:
                return fib(num-1) + fib(num-2)
    """
    def __init__(self, ttl=60):
        self.cache = {}
        self.ttl = ttl
    def __call__(self, f):
        def wrapped_f(*args):
            now = time.time()
            try:
                value, last_update = self.cache[args]
                if self.ttl > 0 and now - last_update > self.ttl:
                    raise AttributeError
                #print 'DEBUG: cached value'
                return value
            except (KeyError, AttributeError):
                value = f(*args)
                self.cache[args] = (value, now)
                #print 'DEBUG: fresh value'
                return value
            except TypeError:
                # uncachable -- for instance, passing a list as an argument.
                # Better to not cache than to blow up entirely.
                return f(*args)
        return wrapped_f

def timing(function):
    """
    Decorator wrapper that logs the time it takes to complete function.

    Primarily used for profiling.
    """
    @wraps(function)
    def wrapped(*args, **kwargs):
        start_time = time()
        data = function(*args, **yombo.utils.clean_kwargs(**kwargs))
        end_time = time()
        mod_name = function.__module__
        logger.debug("Function {mod_name}.{name} took {time} seconds to execute.", mod_name=mod_name, name=function.__name__, time=end_time - start_time)
        return data
    return wrapped
