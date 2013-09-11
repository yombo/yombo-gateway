#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
"""
Used by the Yombo Gateway framework to set up it's libraries.

.. warning::

   These functions are for internal use and **should not** be used directly
   within modules.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""
#import zope.interface
from yombo.core.component import IModule

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
        raise NotImplementedError()

    def _unload_(self):
        """
        Called when a library is about to be unloaded. 
        """
        raise NotImplementedError()
