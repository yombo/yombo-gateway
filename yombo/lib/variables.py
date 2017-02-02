# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

A small library for various variable tools.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from __future__ import print_function
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

from hashlib import sha1
import copy
from collections import deque, namedtuple
from time import time
from collections import OrderedDict

# Import 3rd-party libs
import yombo.ext.six as six

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue

# Import Yombo libraries
from yombo.core.exceptions import YomboPinCodeError, YomboDeviceError, YomboFuzzySearchError, YomboWarning
from yombo.utils.fuzzysearch import FuzzySearch
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import random_string, split, global_invoke_all, string_to_number
from yombo.utils.maxdict import MaxDict
from yombo.lib.commands import Command  # used only to determine class type
logger = get_logger('library.devices')


class Variables(YomboLibrary):
    """
    Various variable tools.
    """
    def _init_(self):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.load_deferred = None  # Prevents loader from moving on past _load_ until we are done.

        self._LocalDB = self._Libraries['localdb']
        self.gwid = self._Configs.get("core", "gwid")

    @inlineCallbacks
    def dev_add_group(self, data, **kwargs):
        """
        Add a new variable group.

        :param data:
        :param kwargs:
        :return:
        """

        var_results = yield self._YomboAPI.request('POST', '/v1/variable/group', data)
        # print("module edit results: %s" % module_results)
        print("var_results: %s" % var_results)
        if var_results['code'] != 200:

            results = {
                'status': 'failed',
                'msg': "Couldn't add variable group",
                'apimsg': var_results['content']['message'],
                'apimsghtml': var_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Variable group added.",
            'group_id': var_results['data']['id'],
        }
        returnValue(results)
