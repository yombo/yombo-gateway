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
        # print("group edit results: %s" % group_results)
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

    @inlineCallbacks
    def dev_edit_group(self, group_id, data, **kwargs):
        """
        Edit a group at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        group_results = yield self._YomboAPI.request('PATCH', '/v1/variable/group/%s' % (group_id), data)
        # print("group edit results: %s" % group_results)

        if group_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit variable group",
                'apimsg': group_results['content']['message'],
                'apimsghtml': group_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Variable group edited.",
            'group_id': group_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_delete_group(self, group_id, **kwargs):
        """
        Delete a variable group at the Yombo server level, not at the local gateway level.

        :param group_id:
        :param kwargs:
        :return:
        """
        group_results = yield self._YomboAPI.request('DELETE', '/v1/variable/group/%s' % group_id)

        if group_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't delete variable group",
                'apimsg': group_results['content']['message'],
                'apimsghtml': group_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Variable group deleted.",
            'group_id': group_id,
        }
        returnValue(results)


    @inlineCallbacks
    def dev_enable_group(self, group_id, **kwargs):
        """
        Enable a group at the Yombo server level, not at the local gateway level.

        :param group_id: The group ID to enable.
        :param kwargs:
        :return:
        """
        api_data = {
            'status': 1,
        }

        group_results = yield self._YomboAPI.request('PATCH', '/v1/variable/group/%s' % group_id, api_data)

        if group_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't enable variable group",
                'apimsg': group_results['content']['message'],
                'apimsghtml': group_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Variable group enabled.",
            'group_id': group_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_disable_group(self, group_id, **kwargs):
        """
        Enable a group at the Yombo server level, not at the local gateway level.

        :param group_id: The group ID to disable.
        :param kwargs:
        :return:
        """
        api_data = {
            'status': 0,
        }

        group_results = yield self._YomboAPI.request('PATCH', '/v1/variable/group/%s' % group_id, api_data)

        if group_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable variable group",
                'apimsg': group_results['content']['message'],
                'apimsghtml': group_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Variable group disabled.",
            'group_id': group_id,
        }
        returnValue(results)