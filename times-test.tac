import pyximport; pyximport.install()
from yombo.lib.loader import setupLoader, getLoader



setupLoader()
_loader = getLoader()
_loader.importLibraries()
from yombo.core.helpers import getTimes,getComponent
print "**********************************************************************************************************************************************************************************"
print "**************************************HERE WE STARTING TESTS -- ALL ERRORS ABOVE(about reactor) DO NOT MATTER*********************************************************************"
times = getTimes()
times.init(_loader,PatchEnvironment=True)

messages = getComponent('yombo.gateway.lib.messages')
messages.init(_loader)

times.run_inner_tests()
moonrise = times.objRise(1, 'Moon') # 1 - we want the next moon rise
print moonrise




import os
from twisted.application import service, internet
from twisted.web import static, server

def getWebService():
    """
    Return a service suitable for creating an application object.

    This service is a simple web server that serves files on port 8080 from
    underneath the current working directory.
    """
    # create a resource to serve static files
    fileServer = server.Site(static.File(os.getcwd()))
    return internet.TCPServer(8080, fileServer)

# this is the core part of any tac file, the creation of the root-level
# application object
application = service.Application("Demo application")

# attach the service to its parent application
service = getWebService()
service.setServiceParent(application)
service.stopService()
#do not know how to stop 
print "**************************************HERE WE STOP TESTING -- ALL ERRORS BELOW(exception) DO NOT MATTER***************************************************************************"
print "**********************************************************************************************************************************************************************************"
raise 'stop!'

       # The following can be used in logic for day/night/light/dark events.
       #times.isTwilight = True - it's not dark (sundown) or light (sun up), or False if not.
       #times.isLight = True - Its either twilight or sun up - False - it's really dark!
       #times.isDark = Opposite of isLight
       #times.isDay = True - sunup, False - sun below twilightHorizon (-6 degrees)
       #times.isNight = Opposite of isDay
       #times.isDawn = True - Is twilight in the morning, else false.
       #times.isDusk = True - Is twilight at night, else false.
