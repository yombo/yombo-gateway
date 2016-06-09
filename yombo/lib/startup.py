# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
Checks for basic requirements.  If anything is wrong/missing, halts start and displays an error.

.. warning::

  Module developers and users should not access any of these functions
  or variables.  This is listed here for completeness.
  
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import Yombo libraries
from yombo.core.exceptions import YomboCritical
from yombo.core.library import YomboLibrary


class Startup(YomboLibrary):
    """
    Start-up checks

    Checks to make sure basic configurations are valid and other start-up operations.
    """

#    @inlineCallbacks
    def _init_(self, loader):
        gwuuid = yield self._Configs.get("core", "gwuuid", None)
        if gwuuid is None or gwuuid == "":
            raise YomboCritical("ERROR: No gateway ID, please run configure.py", 503, "startup")

        hash = yield self._Configs.get("core", "gwhash", None)
        if hash is None or hash == "":
            raise YomboCritical("ERROR: No gateway hash, please run configure.py", 503, "startup")

        gpg_key = self._Configs.get("core", "gpgkeyid", None)
        gpg_key_ascii = self._Configs.get("core", "gpgkeyascii", None)
        if gpg_key is None or gpg_key == '' or gpg_key_ascii is None or gpg_key_ascii == '':
            raise YomboCritical("ERROR: No GPG/PGP key pair found. Please run configure.py", 503, "startup")

    def _load_(self):
        pass

    def _start_(self):
        pass

    def _stop_(self):
        pass

    def _unload_(self):
        pass
