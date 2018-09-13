# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Cache @ Library Documentation <https://yombo.net/docs/libraries/cache>`_

Consolidates all the caching features into here so that they can be monitored and flushed.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.20.1

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/cache.html>`_
"""
from threading import RLock
from cachetools import TTLCache

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils.decorators import setup_cache

logger = get_logger('library.cache')

class Cache(YomboLibrary):
    """
    Create and manage caches for various items.
    """
    def __str__(self):
        """
        Returns the name of the library.

        :return: Name of the library
        :rtype: string
        """
        return "Yombo cache library"

    def _pre_init_(self, **kwargs):
        """
        Setup the cache decorator.

        :param kwargs:
        :return:
        """
        setup_cache(self)
        self.caches = {}
        self.lock = RLock()

    def new(self, name, ttl=120, maxsize=1024, tags=None):
        """
        Get a new cache. Naming standard is:
        lib/module.modulename.cachename

        :param name: Name of the cache.
        :param ttl: seconds cache shouuld be good for.
        :return:
        """
        if isinstance(tags, str):
            tags = (tags,)
        elif tags is None:
            tags = ()

        if name not in self.caches:
            self.caches[name] = {
                'cache': TTLCache(maxsize, ttl),
                'tags': tags,
            }
        return self.caches[name]

    def flush(self, cachename):
        """
        Flush a specific cache.

        :param cachename:
        :return:
        """
        if cachename in self.caches:
            with self.lock:
                self.caches[cachename]['cache'].clear()

    def flush_all(self, tags=None):
        """
        Flush all the caches. If tag/tags were sent in, then only flush those with a matching tag.

        :param tags: List / tuple of tags to filter. Only cache items with matching tags will flush.
        :return:
        """
        if isinstance(tags, str):
            tags = (tags,)
        elif isinstance(tags, list) is False and isinstance(tags, tuple) is False:
            tags = None

        for name, cache in self.caches.items():
            if tags is None:  # If no tags we sent, toss the cache.
                with self.lock:
                    cache['cache'].clear()
            else:
                if any(x in cache['tags'] for x in tags):
                    with self.lock:
                        cache['cache'].clear()
