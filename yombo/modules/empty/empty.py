"""
A starting point to creating your own module. This is a simple,
nearly empty starter module.

:copyright: 2012-2020 Yombo
"""
from twisted.internet import reactor

from yombo.core.module import YomboModule
from yombo.core.log import get_logger

logger = get_logger("modules.empty")

class Empty(YomboModule):
    """
    This is an empty module used to bootstrap your own module. Simply copy/paste this
    directory to a new directory. Be sure to edit the __init__.py to match the new name.

    All methods (functions) defined below are optional.
    """
    def _init_(self, **kwargs):
        """
        Init the module.  Don't use __init__ as that will override the
        setup functions of the base YomboModule class.
        
        Startup phase 1 of 3.

        .. literalinclude:: ../../../yombo/modules/empty/empty.py
           :language: python
           :lines: 20,33
        """
        pass

    def _load_(self, **kwargs):
        """
        After this phase, module should be able to
        processing incoming messages.
        
        In this example, we call the self.loaded function after 2 seconds.
        This load function doesn't really do anything.
        
        Startup phase 2 of 3.

        .. literalinclude:: ../../../yombo/modules/empty/empty.py
           :language: python
           :lines: 35,49-62
        """
        logger.debug("Empty module is loading.")
        if self.module_variables != {}:
            logger.info("Empty module has the following module variables:")
            for field_name, data_type in self.module_variables.items():
                # Remember, each variable can be multi-valued. Within each variable, contains a lot of additional
                # information, such as when it was created, last updated, etc.
                logger.info("{key} = {value}", key=field_name, value=self.module_variables[field_name][data_type])
        else:
            logger.info("Empty module has no defined variables.")

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
           :lines: 64,78
        """
        logger.debug("yombo.modules.empty.loaded() has been called.")
    
        
    def _start_(self, **kwargs):
        """
        Assume all other modules are loaded, we can start
        sending messages to other modules.  Here, is where we enable or turn on
        message sending from within our module.
        
        Startup phase 3 of 3.

        .. literalinclude:: ../../../yombo/modules/empty/empty.py
           :language: python
           :lines: 81,93-97
        """
        logger.info("Is Light: {light}", light=self._States['is.light'])
        logger.info("Is Dark: {dark}", dark=self._States['is.dark'])
        logger.info("Is Day: {day}", day=self._States['is.day'])
        logger.info("Is Night: {night}", night=self._States['is.night'])
        logger.info("Mars Next Rise: {mars_rise}", mars_rise=self._Times.item_rise(dayOffset=1, item='Mars'))
    
    def _stop_(self, **kwargs):
        """
        Stop sending messages.  Other components are unable to receive
        messages.  Queue up or pause functionality.

        .. literalinclude:: ../../../yombo/modules/empty/empty.py
           :language: python
           :lines: 99,108
        """
        pass
    
    def _unload_(self, **kwargs):
        """
        Called just before the gateway is about to shutdown
        or reload all the modules.  Should assume gateway is going down.

        .. literalinclude:: ../../../yombo/modules/empty/empty.py
           :language: python
           :lines: 110,119
        """
        pass
