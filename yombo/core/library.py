# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Library Core @ Module Development <https://yombo.net/docs/core/library>`_


Used by the Yombo Gateway framework to set up it's libraries.

.. warning::

   These functions are for internal use and **should not** be used directly
   within modules.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/library.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

from yombo.core.entity import Entity


class YomboLibrary(Entity):
    """
    Define a basic class that setup basic library class variables.

    This is the only class where the Entity class won't fully populate this class.
    """
    _Entity_type: str = "library"

    def __init__(self, parent, *args, **kwargs):
        try:  # Some exceptions parent being caught. So, catch, display and release.
            super().__init__(self, **kwargs)
        except Exception as e:
            print(f"YomboLibrary caught init exception in {self._Name}: {e}")
            raise e

    def _init_(self, **kwargs):
        """
        Called to init the library, at the yombo gateway level.
        """
        if hasattr(super(), '_init_'):
            super()._init_(**kwargs)

    def _load_(self, **kwargs):
        """
        Called when a library should start running its process
        operations.
        """
        if hasattr(super(), '_load_'):
            super()._load_(**kwargs)

    def _start_(self, **kwargs):
        """
        Called when a library can now send requests externally.
        """
        if hasattr(super(), '_start_'):
            super()._start_(**kwargs)

    def _stop_(self, **kwargs):
        """
        Called when a library is about to be stopped..then unloaded.
        """
        if hasattr(super(), '_stop_'):
            super()._stop_(**kwargs)

    def _unload_(self, **kwargs):
        """
        Called when a library is about to be unloaded. 
        """
        if hasattr(super(), '_unload_'):
            super()._unload_(**kwargs)
