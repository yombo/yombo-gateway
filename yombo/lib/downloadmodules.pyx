# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
Downloads modules from Yombo servers to ensure the gateway has lastest version.

It compares the 'modules' table for columns prodVersion and devVersion table
against 'gitmodules' table.  If the version are the same, then nothing
happens.  If versions are newer, it downloads newer versions.

Download Steps:

1) check if new version exists in config
2) check if cloudfront version matches new vesion in config
3) download new zip files of modules to archives folder
4) if all ok so far, delete current module
5) make sure destination directory exists (this could be a new modules)
6) unzip new module into destination directory
7) resume loading modules

.. warning::

   Module developers and users should not access any of these functions
   or variables.  This is listed here for completeness. Use a :ref:`Helpers`
   function to get what is needed.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""

from itertools import izip
import os
import shutil
import time
import zipfile

from twisted.web.client import downloadPage, getPage
from twisted.internet import defer
   
from yombo.core.library import YomboLibrary
from yombo.core.db import get_dbconnection
from yombo.core.helpers import getConfigValue
from yombo.core.log import getLogger

logger = getLogger('library.downloadmodules')

class DownloadModules(YomboLibrary):
    """
    Handle downloading of modules.

    Checks to make sure basic configurations are valid and other pre-startup
    operations have completed before continuing.  The class will generate
    twisted deferred and will hold up the loading process until all the
    modules have been downloaded.
    
    A semaphore is used to allow processing and downloading of 2 modules at
    a time.
    """

    MAX_PATH = 50
    DL_PATH = "usr/opt/"
    MAX_KEY = 50
    MAX_VALUE = 50

    def _init_(self, loader):
        """
        Gets the library setup and preconfigures some items.  Sets up the
        semaphore for queing downloads.
        """
        self.loader = loader
        self.dbpool = get_dbconnection()

        self._getVersion = []
        self.maxDownload = getConfigValue("misc", 'downloadmodulesconcurrent', 2)
        self.allDownloads = []   # to start deferreds
        self.mysemaphore = defer.DeferredSemaphore(2)  #used to queue deferreds

    def _load_(self):
        """
        Prepare the cloudfront download location, and :func:`checkModules`
        to see if any modules need to be downloaded.
        """
        environment = getConfigValue("server", 'environment', "production")
        if getConfigValue("server", 'cloudfront', "") != "":
            self.cloudfront = "http://%s/" % getConfigValue("server", 'cloudfront')
        else:
            if(environment == "production"):
                self.cloudfront = "http://cloudfront.yombo.net/"
            elif (environment == "staging"):
                self.cloudfront = "http://cloudfrontstg.yombo.net/"
            elif (environment == "development"):
                self.cloudfront = "http://cloudfrontdev.yombo.net/"
            else:
                self.cloudfront = "http://cloudfront.yombo.net/"
            
        return self.checkModules()

    def _start_(self):
        """
        Not used, here to prevent method not implemented exception.
        """
        pass

    def _stop_(self):
        """
        Not used, here to prevent method not implemented exception.
        """
        pass

    def _unload_(self):
        """
        Not used, here to prevent method not implemented exception.
        """
        pass

    def checkModules(self):
        """
        Check if the currently installed module is the latest version available.
        If it's not, then add to queue for downloading.  After the queue is
        loaded call start the semaphore and get it going to download modules.
        """
        m = self.dbpool.cursor()
        gm = self.dbpool.cursor()
        m.execute("SELECT moduleuuid, modulelabel, installsource, prodversion, devversion FROM modules WHERE status = 1")
        row = m.fetchone()
        if row == None:
            return None
        field_names = [n[0].lower() for n in m.description]
        deferredList = []
        while row is not None:
            record = (dict(izip(field_names, row)))
            modulelabel = record['modulelabel']
            modulelabel = modulelabel.lower()
            moduleuuid = record['moduleuuid']
            gmrow = ''
            if ( ( ( record['prodversion'] != '' and record['prodversion'] != None and record['prodversion'] != "*INVALID*") or
              ( record['devversion'] != '' and record['devversion'] != None and record['devversion'] != "*INVALID*") ) and
#              record['installsource'] != 'local') and ( not os.path.exists("yombo/modules/%s/.git" % modulelabel )  ):
              record['installsource'] != 'local') and ( not os.path.exists("yombo/modules/%s/.git" % modulelabel) and not os.path.exists("yombo/modules/%s/.freeze" % modulelabel)  ):
                gm.execute("SELECT moduleuuid, installedversion, installtime FROM modulesinstalled WHERE moduleuuid = '%s'" % (moduleuuid))
                gmrow = gm.fetchone()
                gmfield_names = []
                gmrecord = {}
                if gmrow == None:
                    gmrecord = {'moduleuuid' : moduleuuid, 'installedversion' : '', 'installtime' : 0}
                else:
                    gmfield_names = [gn[0].lower() for gn in gm.description]
                    gmrecord = (dict(izip(gmfield_names, gmrow)))
  
                modulus = moduleuuid[0:1]
                clouduri = self.cloudfront + "gateway/modules/%s/%s/" % (str(modulus), str(moduleuuid))
                installVersion = ''
                data = {}

                if (record['installsource'] == 'prodbranch' and gmrecord['installedversion'] != record['prodversion']):
                    installVersion = record['prodversion']
                    data = {'zipuri'    : str(clouduri + record['prodversion'] + ".zip"),
                            'zipfile'   : self.DL_PATH + record['prodversion'] + ".zip",
                            'type'      : "prodversion",
                            'module'    : record,
                            'installedmodule' : gmrecord,
                            'version'   : record['prodversion'],
                            }
                elif (record['installsource'] == 'devbranch' and gmrecord['installedversion'] != record['devversion']):
                    installVersion = record['prodversion']
                    data = {'zipuri'    : str(clouduri + record['devversion'] + ".zip"),
                            'zipfile'   : self.DL_PATH + record['devversion'] + ".zip",
                            'type'      : "devversion",
                            'module'    : record,
                            'installedmodule' : gmrecord,
                            'version'   : record['devversion'],
                            }
                else:
                    logger.debug("Either no correct version to install, or version already installed..")
                    row = m.fetchone()
                    continue
 
                logger.debug("Adding to download module queue: %s (%s)", modulelabel, data['zipuri'])
               
                d = self.mysemaphore.run(downloadPage, data['zipuri'], data['zipfile'])
                self.allDownloads.append(d)
                d.addErrback(self.downloadFileFailed, data)
                d.addCallback(self.unzipVersion, data)
                d.addErrback(self.unzipVersionFailed, data)
                d.addCallback(self.updateDatabase, data)
                d.addErrback(self.updateDatabaseFailed, data)

            row = m.fetchone()

        finalD = defer.DeferredList(self.allDownloads)
        finalD.addCallback(self.downloadCleanup)
        return finalD
    
    def downloadCleanup(self, something):
        """
        When the downloads are completed, come here for any house cleaning.
        """
        self.dbpool.commit()

    def downloadFile(self, version, data):
        """
        Helper function to download the module as a zip file.
        """
        logger.debug("!! Downlod version:::  %s", data)
        zipuri =  data['zipuri']
        zipfile =  data['zipfile']
        logger.debug("getting uri: %s  saving to:%s", zipuri,zipfile)
        d = downloadPage(data['zipuri'], data['zipfile'])
        return d

    def downloadFileFailed(self, data, data2):
        """
        Helper function for cleanup is called when the download failed.  Won't
        continue processing the zip file.
        """
        logger.warning("Couldn't download the file...")
        return defer.fail()

    def unzipVersion(self, tossaway, data):
        """
        Helper function to unzip the module and place the module in the
        final location.
        
        :param tossaway: Blank, nothing to see here.
        :type data: None
        :param data: Contains the module information, passed on.
        :type data: dict
        """
        moduleLabel = data['module']['modulelabel']
        moduleLabel = moduleLabel.lower()
        logger.debug("Modulelabel = %s", moduleLabel)
        zipFile = data['zipfile']
        modDir = 'yombo/modules/' + moduleLabel

        if not os.path.exists(modDir):
            os.makedirs(modDir)
        else:
            for root, dirs, files in os.walk('modDir'):
                for f in files:
                    os.unlink(os.path.join(root, f))
                for d in dirs:
                    shutil.rmtree(os.path.join(root, d))
        z = zipfile.ZipFile(zipFile)
        z.extractall(modDir)
        listing = os.listdir(modDir)
        return "1"

    def unzipVersionFailed(self, data, data2):
        """
        Helper function for cleanup when the zip process fails
        or unable to move the module to it's final destination.
        """
        logger.warning("unzip failed (%s) (%s)" % (data, data2))
        if data != None:
          return defer.fail()

    def updateDatabase(self, data, data2):
        moduleUUID = data2['module']['moduleuuid']

        c = self.dbpool.cursor()
        if (data2['installedmodule']['installtime'] > 0):
            logger.debug("About to UPDATE to modulesinstalled!")
            c.execute("""
                update modulesinstalled set installedversion=?, installtime=? where moduleUUID=?;""", (data2['version'], int(time.time()), moduleUUID) )
        else:
            logger.debug("About to replace into to modulesinstalled!")
            c.execute("""
                replace into modulesinstalled (moduleuuid, installedversion, installtime)
                values  (?, ?, ?);""", (moduleUUID, data2['version'], int(time.time()) ) )
        return "1"

    def updateDatabaseFailed(self, data, data2):
        """
        Helper function for cleanup is called when unable to update the database.
        """
        logger.warning("Download Version, updateDatabase failed (%s) (%s)" % (data, data2))
        if data != None:
          return defer.fail()
