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
from yombo.core.entity import Entity
from yombo.utils.hookinvoke import global_invoke_all


class YomboLibrary(Entity):
    """
    Define a basic class that setup basic library class variables.

    This is the only class where the Entity class won't fully populate this class.
    """
    def __init__(self, parent, *args, **kwargs):
        self._Entity_type = "yombo_library"
        self._Name = self.__class__.__name__
        self._FullName = f"yombo.gateway.lib.{self.__class__.__name__}"
        super().__init__(parent, *args, **kwargs)

    def _init_(self, **kwargs):
        """
        Called to init the library, at the yombo gateway level.
        """
        pass

    def _load_(self, **kwargs):
        """
        Called when a library should start running its process
        operations.
        """
        pass

    def _start_(self, **kwargs):
        """
        Called when a library can now send requests externally.
        """
        pass

    def _stop_(self, **kwargs):
        """
        Called when a library is about to be stopped..then unloaded.
        """
        pass

    def _unload_(self, **kwargs):
        """
        Called when a library is about to be unloaded. 
        """
        pass

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

    def _generic_load_into_memory(self, storage, hook_name, klass, incoming, source, **kwargs):
        """
        Loads data into memory using basic hook calls.

        :param storage: Dictionary to store new data in.
        :param hook_name: name of the hook to publish
        :param klass: The class to use to store the data
        :param incoming: Data to be saved
        :return:
        """
        run_phase_name, run_phase_int = self._Loader.run_phase
        if run_phase_int < 4000:  # just before 'libraries_started' is when we start processing automation triggers.
            call_hooks = False
        else:
            call_hooks = True
        storage_id = incoming["id"]
        if storage_id not in storage:
            if call_hooks:
                global_invoke_all(f"_{hook_name}_before_load_",
                                  called_by=self,
                                  id=storage_id,
                                  data=incoming,
                                  )
            storage[storage_id] = klass(self,
                                        incoming,
                                        source=source, **kwargs)
            if call_hooks:
                global_invoke_all(f"_{hook_name}_loaded_",
                                  called_by=self,
                                  id=storage_id,
                                  data=storage[storage_id],
                                  )

        else:
            if call_hooks:
                global_invoke_all(f"_{hook_name}_before_update_",
                                  called_by=self,
                                  id=storage_id,
                                  data=storage[storage_id],
                                  )
            storage[storage_id].update_attributes(incoming, source=source)
            if call_hooks:
                global_invoke_all(f"_{hook_name}_updated_",
                                  called_by=self,
                                  id=storage_id,
                                  data=storage[storage_id],
                                  )
        if call_hooks:
            global_invoke_all(f"_{hook_name}_imported_",
                              called_by=self,
                              id=storage_id,
                              data=storage[storage_id],
                              )
        return storage[storage_id]
