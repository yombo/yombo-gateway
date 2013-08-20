# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
"""
Checks for basic requirements.  If anything is wrong/missing, halts
start and displays an error.

.. warning::

  Module developers and users should not access any of these functions
  or variables.  This is listed here for completeness. Use a
  :mod:`helpers` function to get what is needed.
  
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""

from time import time

from twisted.internet import reactor, defer

from yombo.core.exceptions import GWCritical
from yombo.core.library import YomboLibrary
from yombo.core.helpers import getConfigValue, setConfigValue, pgpDownloadRoot
from yombo.core.log import getLogger

logger = getLogger('library.startup')

class Startup(YomboLibrary):
    """
    Start-up checks

    Checks to make sure basic configurations are valid and other start-up operations.
    """

    MAX_PATH = 50
    MAX_KEY = 50
    MAX_VALUE = 50

    def init(self, loader):
        pgpDownloadRoot()

        self.loader = loader

        gwuuid = getConfigValue("core", "gwuuid", None)
        if gwuuid == None or gwuuid == "":
            raise GWCritical("ERROR: No gateway ID, please run configure.py", 503, "startup")

        hash = getConfigValue("core", "gwhash", None)
        if hash == None or hash == "":
            raise GWCritical("ERROR: No gateway hash, please run configure.py", 503, "startup")


        gpg_key = getConfigValue("core", "gpgkeyid",None)
        gpg_key_ascii = getConfigValue("core", "gpgkeyascii", None)
        if gpg_key == None or gpg_key == '' or gpg_key_ascii == None or gpg_key_ascii == '':
            raise GWCritical("ERROR: No GPG/PGP key pair found. Please run configure.py", 503, "startup")

    def load(self):
        lastcheck = getConfigValue("local", "configlastcheckbygw", 0)
#        return ##this doesn't work!!
        if lastcheck > (int(time()) - 10):
            return
        logger.info("Doing last check...")
        setConfigValue("local", "configlastcheckbygw", int(time()) )
        return

        environment = getConfigValue("server", 'environment', "production")
        latitude = getConfigValue("location", 'latitude', '39.555')
        longitude = getConfigValue("location", 'longitude', '-95.555')
        url = '';
        if getConfigValue("server", 'hostname', "") != "":
            host = getConfigValue("server", 'webnearhostname')
        else:
            if(environment == "production"):
                host = "www.yombo.net"
            elif (environment == "staging"):
                host = "wwwstg.yombo.net"
            elif (environment == "development"):
                host = "wwwdev.yombo.net"
            else:
                host = "www.yombo.net"
        if(environment == "prod"):
            uri = getConfigValue("server", 'nearesturi', "")
            url = "http://www" + uri + ".yombo.net/info.php"
        elif (environment == "stg"):
            url = "http://wwwst.yombo.net/info.php"
        else:
            url = "http://wwwdev.yombo.net/info.php"
 
#        print type(longitude)
        url = "%s?lat=%s&long=%s" % (url, latitude, longitude)
        logger.debug("URL = %s", url)

        

        #d = getPage(url)


#TODO: ???  Move to here???   Get updated configs before going on...



    def start(self):
        pass

    def stop(self):
        pass

    def unload(self):
        pass

