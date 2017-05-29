# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Checks for basic requirements.  If anything is wrong/missing, displays an error and put the system into configuration
mode.

.. warning::

  Module developers and users should not access any of these functions
  or variables.  This is listed here for completeness.
  
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger('library.startup')

class Startup(YomboLibrary):
    """
    Start-up checks

    Checks to make sure basic configurations are valid and other start-up operations.
    """
#    @inlineCallbacks
    def _init_(self, **kwargs):
        if self._Loader.operation_mode != None:  # will know if firstrun already or yombo.ini is missing.
            return
        need_config = False
        gwuuid = self._Configs.get("core", "gwuuid", None)
        if gwuuid is None or gwuuid == "":
            self._Libraries['webinterface'].add_alert("No gateway ID, entering 'config' mode.", 'warning', type='system')
            logger.error("No gateway ID, entering 'config' mode.")
            need_config = True

        hash = self._Configs.get("core", "gwhash", None)
        if hash is None or hash == "":
            self._Libraries['webinterface'].add_alert("No gateway hash, entering 'config' mode.", 'warning', type='system')
            logger.error("No gateway hash, entering 'config' mode.")
            need_config = True

        gpg_key = self._Configs.get("gpg", "keyid", None)
        gpg_key_ascii = self._Configs.get("gpg", "keyascii", None)
        if gpg_key is None or gpg_key == '' or gpg_key_ascii is None or gpg_key_ascii == '':
            self._Libraries['webinterface'].add_alert("No GPG/PGP key pair found, entering 'config' mode.", 'warning', type='system')
            logger.error("No GPG/PGP key pair found, entering 'config' mode.")
            need_config = True

        first_run = self._Configs.get('core', 'firstrun', True)
        if first_run:
            self._Loader.operation_mode = 'firstrun'
        elif need_config:
            self._Loader.operation_mode = 'config'
        else:
            self._Loader.operation_mode = 'run'
