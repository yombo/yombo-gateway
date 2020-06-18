# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Cache @ Library Documentation <https://yombo.net/docs/libraries/cache>`_

Consolidates all the caching features into here so that they can be monitored and flushed.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.20.1

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/cache.html>`_
"""
from cachetools import TTLCache, LFUCache, LRUCache
from threading import RLock
from typing import Optional, Union

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
# from yombo.mixins.child_storage_accessors_mixin import ChildStorageAccessorsMixin
from yombo.mixins.parent_storage_accessors_mixin import ParentStorageAccessorsMixin
from yombo.utils import random_string
from yombo.utils.caller import caller_string
from yombo.utils.decorators import setup_cache

logger = get_logger("library.cache")


class Cache(YomboLibrary, ParentStorageAccessorsMixin):
    """
    Create and manage caches for various items.
    """
    def _pre_init_(self, **kwargs) -> None:
        """
        Setup the cache decorator.

        :param kwargs:
        :return:
        """
        setup_cache(self)
        self.caches = {}
        self.lock = RLock()  # lock of last resort

    def lfu(self, tags: Optional[Union[list, str]] = None, name: Optional[str] = None,
            maxsize: Optional[int]=None) -> LFUCache:
        """
        Create a new LFU (Least Frequently Used) based cache. This counts how often
        the cache items are used, and when the maxsize is reached, it will discard
        the least freqently used item. Use this with caution, new items tend to be
        pushed off faster and older but less freqently used items. See LRU cache.

        Default is a maxsize of 512 entires.

        :param tags: Associate tags with this cache for purging.
        :param name: Name of the cache.
        :param maxsize: Max number of entries.
        :return:
        """
        if maxsize is None:
            maxsize = 512

        if isinstance(tags, str):
            tags = (tags,)
        elif tags is None:
            tags = ()

        if name is None:
            name = caller_string() + random_string(length=10)
        if name not in self.caches:
            self.caches[name] = {
                "cache": LFUCache(maxsize),
                "tags": tags,
                "type": "LFUCache",
                "lock": RLock(),
            }

    def lru(self, tags: Optional[Union[list, str]] = None, name: Optional[str] = None,
            maxsize: Optional[int] = None) -> LRUCache:
        """
        Create a new LRU (least recently used) based cache. This cache discards the
        least recently used items to make space if needed.

        Default is a maxsize of 512 entires.

        :param ttl: seconds cache should be good for.
        :param tags: Associate tags with this cache for purging.
        :param name: Name of the cache.
        :param maxsize: Max number of entries.
        :return:
        """
        if maxsize is None:
            maxsize = 512

        if isinstance(tags, str):
            tags = (tags,)
        elif tags is None:
            tags = ()

        if name is None:
            name = caller_string() + random_string(length=10)

        if name not in self.caches:
            self.caches[name] = {
                "cache": LRUCache(maxsize),
                "tags": tags,
                "type": "LRUCache",
                "lock": RLock(),
            }
        return self.caches[name]["cache"]

    def ttl(self, ttl: Optional[int] = None, tags: Optional[Union[list, str]] = None, name: Optional[str] = None,
            maxsize: Optional[int] = None) -> TTLCache:
        """
        Create a new TTL based cache. Items in this cache will timeout after a certain period
        of time.

        Default is 120 seconds timeout with a maxsize of 512 entires.

        :param ttl: seconds cache should be good for.
        :param tags: Associate tags with this cache for purging.
        :param name: Name of the cache.
        :param maxsize: Max number of entries.
        :return:
        """
        if ttl is None:
            ttl = 120
        if maxsize is None:
            maxsize = 512

        if isinstance(tags, str):
            tags = (tags,)
        elif tags is None:
            tags = ()

        if name is None:
            name = caller_string() + random_string(length=10)

        if name not in self.caches:
            self.caches[name] = {
                "cache": TTLCache(maxsize, ttl),
                "tags": tags,
                "type": "TTLCache",
                "lock": RLock(),
            }
        return self.caches[name]["cache"]

    def flush(self, tags: Optional[Union[list, str]] = None) -> None:
        """
        Flush all caches with the specified tag/tags.

        :param tags: string, list, or tuple of tags to flush.
        :return:
        """
        if isinstance(tags, str):
            tags = (tags,)
        elif isinstance(tags, list) is False and isinstance(tags, tuple) is False:
            return

        for name, cache in self.caches.items():
            if any(x in cache["tags"] for x in tags):
                with cache["lock"]:
                    cache["cache"].clear()

    def clear(self, cache_item: Union[LFUCache, LRUCache, TTLCache]) -> None:
        """
        Flush a specific cache. The cache_item must be a cache object.

        :param cache_item: Reference cache to clear.
        :return:
        """
        with self.lock:
            cache_item.clear()

    def clear_item(self, cachename: str) -> None:
        """
        Flush a specific cache: cachename must be the name of the cache, not the actual cache object.

        :param cachename: Name of the cache to flush.
        :return:
        """
        if cachename in self.caches:
            cache = self.caches[cachename]
            with cache["lock"]:
                cache["cache"].clear()

    def flush_all(self, tags: Optional[Union[list, str]] = None) -> None:
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
            with cache["lock"]:
                cache["cache"].clear()
