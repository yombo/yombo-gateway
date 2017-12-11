#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Library Core @ Module Development <https://yombo.net/docs/core/library>`_


Used by the Yombo Gateway framework to set up it's libraries.

.. warning::

   These functions are for internal use and **should not** be used directly
   within modules.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/library.html>`_
"""
class YomboLibrary:
    """
    Define a basic class that setup basic library class variables.
    """

    def __init__(self):
        self._Name = self.__class__.__name__
        self._FullName = "yombo.gateway.lib.%s" % (self.__class__.__name__)

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
        Basic routing of incoming AQMP message packagets to a module. Sends requests to 'amqp_incoming_request'
        and responses to 'amqp_incoming_response'.
        """
        if headers['message_type'] == 'request':
            self.amqp_incoming_request(headers=headers, **kwargs)
        if headers['message_type'] == 'response':
            self.amqp_incoming_response(headers=headers, **kwargs)

    def amqp_incoming_request(self, headers, body, **kwargs):
        """
        This method should be implemented by any modules expecting to receive amqp incoming requests.
        """
        pass

    def amqp_incoming_response(self, headers, body, **kwargs):
        """
        This method should be implemented by any modules expecting to receive amqp incoming responses.
        """
        pass
