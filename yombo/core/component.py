#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found athttp://www.yombo.net
"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""

import zope.interface

class IComponent(zope.interface.Interface):
    _Name = zope.interface.Attribute("""Component name""")
    _FullName = zope.interface.Attribute("""Full name (with namespace)""")
    description = zope.interface.Attribute("""Description what this module
        does""")
    version = zope.interface.Attribute("""Module version""")
    author = zope.interface.Attribute("""Module author""")
    url = zope.interface.Attribute("""URL of module details. Usually documentation about module""")
#    register_distributions = zope.interface.Attribute("""A list of what message distributions this module should receive.
#        For example: ["all", "cmd", "status"]
#        """        

    def load(self):
        """
        Consider to be starting phase 2 of 3.

        Called after everything is loaded (instantiated, __init__).

        After self.load is done, this module should be able to fully
        process incoming messages or respond to actions being asked of
        it from a message.

        This module shouldn't send new requests to other modules, only
        be able to respond to requests.

        Example usage: A log file monitor can open a file, but not start
        reading it and processing it.
        """

    def loadDone(self):
        """
        Called by load() once load is done..
        """
        
    def start(self):
        """
        Consider to be starting phase 3 of 3.

        Called after everything has been loaded. Now is the time to start
        making requests of other components and expect responses.

        Example usage: Start processing the opened log file.
        """

    def stop(self):
        """
        Consider to be stopping phase 1 of 2.

        After this method has been completed, the module should stop
        sending messages, however, it should still be able to respond

        Example usage: Stop prossessing the opened log file.
        """

    def unload(self):
        """
        Consider to be stopping phase 2 of 2.

        After this method has been completed, the module should close
        any connections, files, etc. It should be assumed that
        after this function ends, the module will be unloaded from memory
        and everything will be lost.  Make config saves here.

        Example usage: Close open file, save file location pointer.
        """

    def unloadDone(self):
        """
        Called by unload() once unload is done.
        """

    def message(self, message):
        """
        Called by the message system with a message object. Will receive
        a message if this module is marked as a destination, or the module
        has subscribed to a message distribution list.
        """

class IModule(IComponent):
    pass

class ILibrary(IComponent):
    pass
