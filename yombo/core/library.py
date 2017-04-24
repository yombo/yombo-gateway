#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
Used by the Yombo Gateway framework to set up it's libraries.

.. warning::

   These functions are for internal use and **should not** be used directly
   within modules.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
class YomboLibrary:
    """
    Define a basic class that setup basic library class variables.
    """

    def __init__(self):
        self._Name = self.__class__.__name__
        self._FullName = "yombo.gateway.lib.%s" % (self.__class__.__name__)

    def _load_(self):
        """
        Called when a library should start running its process
        operations. 
        """
        pass

    def _start_(self):
        """
        Called when a library can now send requests externally.
        """
        pass

    def _stop_(self):
        """
        Called when a library is about to be stopped..then unloaded.
        """
        pass

    def _unload_(self):
        """
        Called when a library is about to be unloaded. 
        """
        pass
