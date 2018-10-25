"""
Various function decorators.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from cachetools import TTLCache
from functools import wraps
import inspect
from time import time

from yombo.core.exceptions import YomboWarning
from yombo.utils.decorators.deprecation import deprecated

cache_library = None  # References to the Yombo libraries


def setup_cache(cache_library_reference):
    """
    Setups the module global variables. Called from Cache library pre_init...

    :param cache_library_reference:
    :return:
    """
    global cache_library
    cache_library = cache_library_reference


class cached(object):
    """
    Decorator that caches a function's return value each time it is called within a TTL.
    If called within the TTL and the same arguments, the cached value is returned,
    If called outside the TTL or a different value, a fresh value is returned.

    Default TTL is 120 seconds

    **Usage**:

    .. code-block:: python

        from yombo.utils.decorators import cached

        print fib(35) # Without decorator, will take a little bit of time.
        print fib(35) # With decorator, will be nearly instant - even on first call for a fib.

        @cached(5) # memoize for 5 seconds
        def fib(x):
            if num < 2:
                return num
            else:
                return fib(num-1) + fib(num-2)
    """
    def __init__(self, ttl=None, maxsize=None, cachename=None, tags=(), cache_type=None):
        """
        Setup the cache.

        :param ttl:
        :param maxsize:
        :param cachename:
        :param tags:
        :param cache_type: Type of cache, default is TTL.
        """
        from yombo.utils import generate_source_string, random_string

        global cache_library

        if cache_type is None:
            cache_type = 'ttl'
        else:
            cache_type = cache_type.lower()

        if cachename is None:
            cachename = "%s R:%s" % (generate_source_string(), random_string(length=10))

        self.kwd_mark = object()  # sentinel for separating args from kwargs
        if cache_library is None:  # Here in case cache is called before fully started.
            if ttl is None:
                ttl = 120
            if maxsize is None:
                maxsize = 512
            self.cache = TTLCache(maxsize, ttl)
        else:
            if cache_type == 'ttl':
                self.cache = cache_library.ttl(ttl=ttl, tags=tags, name=cachename, maxsize=maxsize)
            elif cache_type == 'lru':
                self.cache = cache_library.lru(tags=tags, name=cachename, maxsize=maxsize)
            elif cache_type == 'lfu':
                self.cache = cache_library.lfu(tags=tags, name=cachename, maxsize=maxsize)
            else:
                raise YomboWarning("Unknown cache type: %s" % cache_type)

    def __call__(self, f):
        def wrapped_f(*args, **kwargs):
            func_sig = inspect.signature(f)
            bind = func_sig.bind(*args, **kwargs)
            bind.apply_defaults()
            args, kwargs = bind.args, bind.kwargs
            key = (args, tuple(sorted(kwargs.items())))
            try:
                value = self.cache[key]
                # if here, we have a hit..
                return value
            except (KeyError, AttributeError):
                value = f(*args, **kwargs)
                self.cache[key] = value
                # if here, we have a miss...
                return value
            except TypeError as e:
                # uncachable -- for instance, passing a list as an argument.
                # Better to not cache than to blow up entirely.
                return f(*args, **kwargs)
        return wrapped_f


def static_var(varname, value):
    """
    Sets a static variable within a function. This is an easy way to set a default.

    **Usage**:

    .. code-block:: python

        from yombo.utils.decorators import static_var

        @static_var("my_variable", 0)
        def some_function(x):
            some_function.my_variable += 1
            print "I've been called %s times." % some_function.my_variable

    :param varname: variable name to create
    :param value: initial value to set.
    :return:
    """
    def decorate(func):
        setattr(func, varname, value)
        return func
    return decorate


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
        print("Function %s.%s took %s seconds to execute." % (mod_name, function.__name__, (end_time - start_time)))
        return data
    return wrapped

