# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `OAuth @ Library Documentation <https://yombo.net/docs/libraries/oauthendpoint>`_

Acts as an oauth client. Currently, this only handles the  authorization code grant type.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/oauthendpoint.html>`_
"""
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger("library.oauthendpoint")

class OauthEndpoint(YomboLibrary):
    """

    """
    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo oauth client library"

    # @inlineCallbacks
    def _init_(self, **kwargs):
        self.clients = {}
        self.new(client_id=self.gateway_id,
                 secret=self._Configs.get("core", "gwhash"),
                 scope="")

    # @inlineCallbacks
    # def _load_(self, **kwargs):

    # @inlineCallbacks
    # def _start_(self, **kwargs):

    # @inlineCallbacks
    # def _stop_(self, **kwargs):
    #     if hasattr(self, "self._LocalDB"):  # incase loading got stuck somewhere.
    #         yield self.check_tasks("stop")

    # @inlineCallbacks
    # def _unload_(self, **kwargs):
    #     if hasattr(self, "self._LocalDB"):  # incase loading got stuck somewhere.
    #         yield self.check_tasks("load")

    @inlineCallbacks
    def new(self):
        """ Create a new end point. """