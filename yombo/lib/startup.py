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
        first_run = self._Configs.get('core', 'first_run', False, False)
        if self._Loader.operating_mode == 'first_run':  # will know if first_run already or yombo.ini is missing.
            return
        if first_run is True:
            self._Loader.operating_mode = 'first_run'
            return True
        items_needed = []

        gwid = self._Configs.get('core', 'gwid', 'local', False)
        if gwid is None or gwid == "":
            items_needed.append("Gateway ID")
        gwuuid = self._Configs.get("core", "gwuuid", None)
        if gwuuid is None or gwuuid == "":
            items_needed.append("Gateway private UUID")
        hash = self._Configs.get("core", "gwhash", None)
        if hash is None or hash == "":
            items_needed.append("Gateway login password hash")
        is_master = self._Configs.get("core", "is_master", True)
        if is_master is False:
            master_gateway = self._Configs.get("core", "master_gateway", None, False)
            if master_gateway is None or master_gateway == "":
                items_needed.append("Gateway is marked as slave, but not master gateway set.")
        else:
            master_gateway = self._Configs.get("core", "master_gateway", None, False)

        gpg_key = self._Configs.get("gpg", "keyid", None)
        gpg_key_ascii = self._Configs.get("gpg", "keyascii", None)
        if gpg_key is None or gpg_key == '' or gpg_key_ascii is None or gpg_key_ascii == '':
            items_needed.append("GPG keys")

        if len(items_needed) > 0:
            needed_text = '</li><li>'.join(items_needed)
            print("start needetext: %s" % needed_text)
            self._Notifications.add({'title': 'Need configurations',
                                     'message': 'System has been places into configuration mode. Reason: The following configurations are needed:<p><ul><li>%s</li></ul>' % needed_text,
                                     'source': 'Yombo Startup Library',
                                     'persist': False,
                                     'priority': 'high',
                                     'always_show': True,
                                     'always_show_allow_clear': True,
                                     })
            self._Loader.operating_mode = 'config'
        else:
            self._Loader.operating_mode = 'run'
