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
from yombo.core.log import getLogger
import yombo.utils

logger = getLogger('utils.utils')

def memoize_(func):
    """
    Reuse the results of a static function. Subsequent calls will get cached results.

    *Usage**:

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
