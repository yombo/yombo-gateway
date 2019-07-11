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

:copyright: Copyright 2012-2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/library.html>`_
"""
# Import Yombo libraries
from yombo.core.exceptions import YomboWarning

from yombo.core.entity import Entity
from yombo.utils.hookinvoke import global_invoke_all


class YomboLibrary(Entity):
    """
    Define a basic class that setup basic library class variables.

    This is the only class where the Entity class won't fully populate this class.
    """
    def __init__(self, *args, **kwargs):
        try:  # Some exceptions not being caught. So, catch, display and release.
            if hasattr(self, '_import_init_'):
                self._import_init_(**kwargs)

            self._Entity_type = "library"
            super().__init__(self, **kwargs)
        except Exception as e:
            print(f"YomboLibrary caught init exception: {e}")
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

    def amqp_incoming(self, headers, **kwargs):
        """
        Basic routing of incoming AQMP message packagets to a module. Sends requests to "amqp_incoming_request"
        and responses to "amqp_incoming_response".
        """
        if headers["message_type"] == "request":
            self.amqp_incoming_request(headers=headers, **kwargs)
        if headers["message_type"] == "response":
            self.amqp_incoming_response(headers=headers, **kwargs)

    def amqp_incoming_request(self, **kwargs):
        """
        This method should be implemented by any modules expecting to receive amqp incoming requests.
        """
        pass

    def amqp_incoming_response(self, **kwargs):
        """
        This method should be implemented by any modules expecting to receive amqp incoming responses.
        """
        pass
