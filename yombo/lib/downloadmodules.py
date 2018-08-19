# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Responsible for downloading and installing any modules as requested by the configuration.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
    and classes **should not** be accessed directly by modules. These are documented here for completeness.


.. note::

  For more information see: `Download Modules @ Module Development <https://yombo.net/docs/libraries/download_modules>`_


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
   or variables.  This is listed here for completeness. Use a :ref:`framework_utils`
   function to get what is needed.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/downloadmodules.html>`_
"""
# Import python libraries
import os
import shutil
import time
import zipfile

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
    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo download modules library"

    MAX_PATH = 50
    DL_PATH = "opt/"
    MAX_KEY = 50
    MAX_VALUE = 50
    MAX_DOWNLOAD_CONCURRENT = 3  # config: misc:downloadmodulesconcurrent

    def _init_(self, **kwargs):
        """
        Gets the library setup and preconfigures some items.  Sets up the
        semaphore for queing downloads.
        """
        # self.download_list_deferred = None
        self._LocalDBLibrary = self._Libraries['localdb']

        self._getVersion = []
        self.maxDownloadConcurrent = self._Configs.get("misc", 'downloadmodulesconcurrent', self.MAX_DOWNLOAD_CONCURRENT)
        self.download_path = self._Atoms.get('working_dir') + "/" + self.DL_PATH
        self.allDownloads = []   # to start deferreds
        self.mysemaphore = defer.DeferredSemaphore(self.maxDownloadConcurrent)  #used to queue deferreds

    @defer.inlineCallbacks
    def _load_(self, **kwargs):
        """
        Prepare the cloudfront download location, and :func:`checkModules`
        to see if any modules need to be downloaded.
        """
        environment = self._Configs.get("core", 'environment', "production", False)
        if(environment == "production"):
            self.cloudfront = "https://gwdl.yombo.net/"
        elif (environment == "staging"):
            self.cloudfront = "https://gwdlstg.yombo.net/"
        elif (environment == "development"):
            self.cloudfront = "https://gwdldev.yombo.net/"
        else:
            self.cloudfront = "https://gwdl.yombo.net/"
            
        yield self.download_modules()
    #
    # def _stop_(self, **kwargs):
    #     if self.download_list_deferred is not None and len(self.download_list_deferred.called) > 0:
    #         for defer in self.download_list_deferred:
    #             if defer.called is False:
    #                 self.download_list_deferred.callback(1)  # if we don't check for this, we can't stop!

    @defer.inlineCallbacks
    def download_modules(self):
        """
        Check if the currently installed module is the latest version available.
        If it's not, then add to queue for downloading.  After the queue is
        loaded call start the semaphore and get it going to download modules.
        """
        modules = yield self._LocalDBLibrary.get_modules_view()
        if len(modules) == 0:
            return None

        deferredList = []
        for module in modules:
            modulelabel = module.machine_label.lower()
            moduleuuid = module.id

            if ( ( ( module.prod_version != '' and module.prod_version != None and module.prod_version != "*INVALID*") or
              ( module.dev_version != '' and module.dev_version != None and module.dev_version != "*INVALID*") ) and
              module.install_branch != 'local') and ( not os.path.exists("yombo/modules/%s/.git" % modulelabel) and not os.path.exists("yombo/modules/%s/.freeze" % modulelabel)  ):
                logger.debug("Module doesn't have freeze: yombo/modules/{modulelabel}/.freeze", modulelabel=modulelabel)

                modulus = moduleuuid[0:1]
                clouduri = self.cloudfront + "modules/%s/%s/" % (str(modulus), str(moduleuuid))
                data = {}

                if module.install_branch == 'production' and module.installed_version != module.prod_version:
                    print("version compare: %s != %s" % (module.installed_version, module.prod_version))
                    data = {'download_uri'    : str(clouduri + module.prod_version + ".zip"),
                            'zip_file'   : self.download_path + modulelabel + "_" + module.prod_version + ".zip",
                            'type'      : "prod_version",
                            'install_version': module.prod_version,
                            'module'    : module,
                            }
                elif module.install_branch == 'development' and module.dev_version != "" and module.installed_version != module.dev_version:
                    data = {'download_uri': str(clouduri + module.dev_version + ".zip"),
                            'zip_file': self.download_path + modulelabel + "_" + module.dev_version + ".zip",
                            'type': "dev_version",
                            'install_version': module.dev_version,
                            'module': module,
                            }
                else:
                    logger.debug("Either no correct version to install, or version already installed..")
                    continue

                logger.debug("Adding to download module queue: {modulelable} (zipurl})", modulelabel=modulelabel, zipurl=data['zip_file'])
               
                d = self.mysemaphore.run(self.download_file, data)
                self.allDownloads.append(d)
                d.addErrback(self.download_file_failed, data)
                d.addCallback(self.unzip_file, data)
                d.addErrback(self.unzip_file_failed, data)
                d.addCallback(self.update_database, data)
                d.addErrback(self.update_database_failed, data)

        yield defer.DeferredList(self.allDownloads)
        #self.download_list_deferred = yield defer.DeferredList(self.allDownloads)

    def download_cleanup(self, something):
        """
        When the downloads are completed, come here for any house cleaning.
        """
        logger.info("Done with downloads!")

    def download_file(self, data):
        """
        Helper function to download the module as a zip file.
        """
        logger.debug("download_file data:  {data}", data=data)
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
        logger.debug("unzip_file data:  {data}", data=data)
        logger.debug("unzip_file data:  {data_module}", data_module=data['module'])
        logger.debug("unzip_file data:  {data_module_label}", data_module_label=data['module'].machine_label)
        moduleLabel = data['module'].machine_label
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
        z = zipfile.ZipFile(zip_file)
        z.extractall(modDir)
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
        module_id = module.id

        ModuleInstalled = self._LocalDBLibrary.get_model_class("ModuleInstalled")

        if module.install_at is None:
            self._LocalDBLibrary.modules_install_new(
                {'module_id': module_id,
                 'installed_version': data['install_version'],
                 'install_at': int(time.time())
                 })
        else:
            module_installed = ModuleInstalled.find(['module_id = ?', module_id])
            module_installed.installed_version = data['install_version']
            module_installed.install_at = int(time.time())
            module_installed.save()
        return "1"

    def update_database_failed(self, data, data2):
        """
        Helper function for cleanup is called when unable to update the database.
        """
        logger.warn("Download Version, updateDatabase failed ({data}) ({data2})", data=data, data2=data2)
        if data != None:
          return defer.fail()
