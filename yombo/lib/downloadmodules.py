# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
Responsible for downloading and installing any modules as requested by the configuration.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
    and classes **should not** be accessed directly by modules. These are documented here for completeness.


It compares the 'modules' table for columns prod_version and dev_version table
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

:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import os
import shutil
import time
import zipfile
from itertools import izip

from pprint import pprint

# Import twisted libraries
from twisted.internet import defer
from twisted.web.client import downloadPage

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger('library.downloadmodules')

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
    MAX_DOWNLOAD_CONCURRENT = 2  # config: misc:downloadmodulesconcurrent

    def _init_(self, loader):
        """
        Gets the library setup and preconfigures some items.  Sets up the
        semaphore for queing downloads.
        """
        self.loader = loader
        self._LocalDBLibrary = self._Libraries['localdb']

        self._getVersion = []
        self.maxDownload = self._Configs.get("misc", 'downloadmodulesconcurrent', self.MAX_DOWNLOAD_CONCURRENT)
        self.allDownloads = []   # to start deferreds
        self.mysemaphore = defer.DeferredSemaphore(2)  #used to queue deferreds

    def _load_(self):
        """
        Prepare the cloudfront download location, and :func:`checkModules`
        to see if any modules need to be downloaded.
        """
        environment = self._Configs.get("server", 'environment', "production")
        if self._Configs.get("server", 'cloudfront', "") != "":
            self.cloudfront = "http://%s/" % self._Configs.get("server", 'cloudfront')
        else:
            if(environment == "production"):
                self.cloudfront = "http://cloudfront.yombo.net/"
            elif (environment == "staging"):
                self.cloudfront = "http://cloudfrontstg.yombo.net/"
            elif (environment == "development"):
                self.cloudfront = "http://cloudfrontdev.yombo.net/"
            else:
                self.cloudfront = "http://cloudfront.yombo.net/"
            
        return self.download_modules()

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

    @defer.inlineCallbacks
    def download_modules(self):
        """
        Check if the currently installed module is the latest version available.
        If it's not, then add to queue for downloading.  After the queue is
        loaded call start the semaphore and get it going to download modules.
        """
        modules = yield self._LocalDBLibrary.get_modules_view()
        if len(modules) == 0:
            defer.returnValue(None)

        deferredList = []
        for module in modules:
            modulelabel = module.machine_label.lower()
            moduleuuid = module.id
            #pprint(module)

            if ( ( ( module.prod_version != '' and module.prod_version != None and module.prod_version != "*INVALID*") or
              ( module.dev_version != '' and module.dev_version != None and module.dev_version != "*INVALID*") ) and
#              module.install_branch != 'local') and ( not os.path.exists("yombo/modules/%s/.git" % modulelabel )  ):
              module.install_branch != 'local') and ( not os.path.exists("yombo/modules/%s/.git" % modulelabel) and not os.path.exists("yombo/modules/%s/.freeze" % modulelabel)  ):
                logger.warn("Module doesn't have freeze: yombo/modules/{modulelabel}/.freeze", modulelabel=modulelabel)

                modulus = moduleuuid[0:1]
                clouduri = self.cloudfront + "gateway/modules/%s/%s/" % (str(modulus), str(moduleuuid))
                data = {}

                if (module.install_branch == 'prodbranch' and module.installed_version != module.prod_version) or module.dev_version != "":
                    data = {'download_uri'    : str(clouduri + module.prod_version + ".zip"),
                            'zip_file'   : self.DL_PATH + modulelabel + "_" + module.prod_version + ".zip",
                            'type'      : "prod_version",
                            'install_version': module.prod_version,
                            'module'    : module,
                            }
                elif module.install_branch == 'devbranch' and module.dev_version != "" and module.installed_version != module.dev_version:
                    data = {'download_uri': str(clouduri + module.dev_version + ".zip"),
                            'zip_file': self.DL_PATH + modulelabel + "_" + module.dev_version + ".zip",
                            'type': "dev_version",
                            'install_version': module.dev_version,
                            'module': module,
                            }
                else:
                    logger.debug("Either no correct version to install, or version already installed..")
                    continue

                logger.debug("Adding to download module queue: {modulelable} (zipurl})", modulelabel=modulelabel, zipurl=data['zip_uri'])
               
#                d = self.mysemaphore.run(downloadPage, data['zip_uri'], data['zip_file'])
                d = self.mysemaphore.run(self.download_file, data)
                self.allDownloads.append(d)
                d.addErrback(self.download_file_failed, data)
                d.addCallback(self.unzip_file, data)
                d.addErrback(self.unzip_file_failed, data)
                d.addCallback(self.update_database, data)
                d.addErrback(self.update_database_failed, data)

        finalD = yield defer.DeferredList(self.allDownloads)
        defer.returnValue(finalD)
    
    def download_cleanup(self, something):
        """
        When the downloads are completed, come here for any house cleaning.
        """
        logger.info("Done with downloads!")

    def download_file(self, data):
        """
        Helper function to download the module as a zip file.
        """
        logger.debug("!! Downlod version:::  {data}", data=data)
        download_uri =  data['download_uri']
        zip_file =  data['zip_file']
        logger.debug("getting uri: {download_uri}  saving to:{zip_file}", download_uri=download_uri, zip_file=zip_file)
        d = downloadPage(data['download_uri'], data['zip_file'])
        return d

    def download_file_failed(self, data, data2):
        """
        Helper function for cleanup is called when the download failed.  Won't
        continue processing the zip file.
        """
        logger.warn("Couldn't download the file...")
        return defer.fail()

    def unzip_file(self, tossaway, data):
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
        logger.debug("Modulelabel = {moduleLabel}", moduleLabel=moduleLabel)
        zip_file = data['zip_file']
        modDir = 'yombo/modules/' + moduleLabel

        if not os.path.exists(modDir):
            os.makedirs(modDir)
        else:
            for root, dirs, files in os.walk('modDir'):
                for f in files:
                    os.unlink(os.path.join(root, f))
                for d in dirs:
                    shutil.rmtree(os.path.join(root, d))
        z = zip_file.ZipFile(zip_file)
        z.extractall(modDir)
        listing = os.listdir(modDir)
        return "1"

    def unzip_file_failed(self, data, data2):
        """
        Helper function for cleanup when the zip process fails
        or unable to move the module to it's final destination.
        """
        logger.warn("unzip failed ({data}) ({data2})", data=data, data2=data2)
        if data != None:
          return defer.fail()

    def update_database(self, tossaway, data):
        """

        :param tossaway: Blank, nothing to see here.
        :type data: None
        :param data: Contains the module information, passed on.
        :type data: dict
        :return:
        """
        module = data['module']
        moduleUUID = module.id

        c = self.dbpool.cursor()
        ModuleInstalled = self._LocalDBLibrary.get_model_class("ModuleInstalled")

        if module.instal_ltime is None:
            module_installed = ModuleInstalled(module_id=moduleUUID,
                                                                    installed_version=data['install_version'],
                                                                    install_time=time.time())
            module_installed.save()
        else:
            module_installed = ModuleInstalled.find(['module_id = ?', moduleUUID, "Smith"])
            module_installed.installed_version = data['install_version']
            module_installed.install_time = time.time()
            module_installed.save()
        return "1"

    def update_database_failed(self, data, data2):
        """
        Helper function for cleanup is called when unable to update the database.
        """
        logger.warn("Download Version, updateDatabase failed ({data}) ({data2})", data=data, data2=data2)
        if data != None:
          return defer.fail()
