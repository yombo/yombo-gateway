"""
A starting point to creating your own module. This is a simple,
nearly empty starter module.

:copyright: 2012-2015 Yombo
:license: GPL
"""
from twisted.internet import reactor

from yombo.core.module import YomboModule
from yombo.core.log import get_logger

logger = get_logger("modules.empty")

class Empty(YomboModule):
    """
    This is an empty module used to bootstrap your own module. Simply copy/paste this
    directory to a new directy. Be sure to edit the __init__.py to match the new name.
    """
    def _init_(self):
        """
        Init the module.  Don't use __init__ as that will override the
        setup functions of the base YomboModule class.
        
        Startup phase 1 of 3.

        .. literalinclude:: ../../../yombo/modules/empty/empty.py
           :language: python
           :lines: 20,31-34
        """
        self._ModDescription = "Empty module, copy to get started building a new module."
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "https://yombo.net"

        self._Times = self._Libraries['times']  # So we can access some time functions

    def _load_(self):
        """
        After this phase, module should be able to
        processing incoming messages.
        
        In this example, we call the self.loaded function after 2 seconds.
        This load function doesn't really do anything.
        
        Startup phase 2 of 3.

        .. literalinclude:: ../../../yombo/modules/empty/empty.py
           :language: python
           :lines: 37,51-60
        """
        logger.debug("Empty module is loading.")
        if self._ModVariables != {}:
            logger.info("Empty module has the following module variables:")
            for variable in self._ModVariables:
                # Remember, each variable can be multi-valued. Internally,
                # variables are treated the same if allowed to hav multiple
                # values or not. Hence the [0]
                logging.info("%s", self._ModVariables[variable][0])
        else:
            logger.debug("Empty module has no defined variables.")

        # an example to call a function at a later time. This example calles
        # self.loaded 2 seconds from now.
        reactor.callLater(2, self.loaded)

    def loaded(self):  #called from delayedcall
        """
        This method isn't required, but it's here for demonstation purposes.
        
        This is called from :meth:`load` 2 seconds after load was called.

        Due to asyncronous style of Twisted, the callLater cannot guarantee this
        is called exactly in two seconds.  It won't be called earlier, but may
        be called later if there was blocking code.

        .. literalinclude:: ../../../yombo/modules/empty/empty.py
           :language: python
           :lines: 66,80
        """
        logger.debug("yombo.modules.empty.loaded() has been called.")
    
        
    def _start_(self):
        """
        Assume all other modules are loaded, we can start
        sending messages to other modules.  Here, is where we enable or turn on
        message sending from within our module.
        
        Startup phase 3 of 3.

        .. literalinclude:: ../../../yombo/modules/empty/empty.py
           :language: python
           :lines: 83,95-99
        """
        logger.debug("Is Light: {light}", light=self._States['is_light'])
        logger.debug("Is Dark: {dark}", dark=self._States['is_dark'])
        logger.debug("Is Day: {day}", day=self._States['is_day'])
        logger.debug("Is Night: {night}", night=self._States['is_night'])
        logger.debug("Mars Next Rise: {mars_rise}", mars_rise=self._Times.objRise(dayOffset=1, object='Mars'))
    
    def _stop_(self):
        """
        Stop sending messages.  Other components are unable to receive
        messages.  Queue up or pause functionality.

        .. literalinclude:: ../../../yombo/modules/empty/empty.py
           :language: python
           :lines: 101,110
        """
        pass
    
    def _unload_(self):
        """
        Called just before the gateway is about to shutdown
        or reload all the modules.  Should assume gateway is going down.

        .. literalinclude:: ../../../yombo/modules/empty/empty.py
           :language: python
           :lines: 112,121
        """
        pass
