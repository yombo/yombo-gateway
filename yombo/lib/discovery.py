# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Discovery @ Module Development <https://yombo.net/docs/libraries/discovery>`_

Tracks all auto-discovered devices in one location.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/discovery.html>`_
"""
# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from datetime import datetime, timedelta
from hashlib import sha256
from time import time

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.utils import random_string
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import search_instance, do_search_instance

logger = get_logger('library.discovery')


class Discovery(YomboLibrary):
    """
    A one-stop location to track discovered devices. This allows the user to quickly find auto-discovered devices
    and add them as a Yombo controlled device.

    """
    def __contains__(self, device_requested):
        """
        Checks to if a provided device id is found.

            >>> if '129da137ab9318' in self._Discovery:

        or:

            >>> if 'module.mymodule.mycron' in self._Discovery:

        :raises YomboWarning: Raised when request is malformed.
        :param device_requested: The discovered device ID, label, or machine_label to search for.
        :type device_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(device_requested)
            return True
        except:
            return False

    def __getitem__(self, device_requested):
        """
        Attempts to find the device requested using a couple of methods.

            >>> off_cmd = self._Discovery['129da137ab9318']  #by id

        or:

            >>> off_cmd = self._Discovery['something here']  #by description or other attributes

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param device_requested: The discovered device ID, label, or machine_label to search for.
        :type device_requested: string
        :return: A pointer to the discovered device instance.
        :rtype: instance
        """
        return self.get(device_requested)

    def __setitem__(self, device_requested, value):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, device_requested):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter discovered devices. """
        return self.discovered.__iter__()

    def __len__(self):
        """
        Returns an int of the number of discovered devices configured.

        :return: The number of discovered devices configured.
        :rtype: int
        """
        return len(self.discovered)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo discovered devices library"

    def keys(self):
        """
        Returns the keys (discovered device ID's) that are configured.

        :return: A list of discovered device IDs.
        :rtype: list
        """
        return list(self.discovered.keys())

    def items(self):
        """
        Gets a list of tuples representing the discovered devices configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.discovered.items())

    def values(self):
        return list(self.discovered.values())

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Setups up the basic framework.

        :param loader: A pointer to the Loader library.
        :type loader: Instance of Loader
        """
        self.discovered_search_attributes = ['description']
        self.discovered = {}
        self.discovery_history = yield self._SQLDict.get(self, "discovery_history")

    def get(self, discover_id, source=None):
        """
        Looks for a discovered device by it's id OR by the device_id and source.
        """
        if source is not None:
            device_id = sha256(str(source, discover_id).encode('utf-8')).hexdigest()
        else:
            device_id = discover_id
        if discover_id in self.discovered:
            return self.discovered[device_id]
        raise KeyError("Could not find a matching discovered device.")

    def new(self, **kwargs):
        device_id = sha256(str(kwargs['source'] + kwargs['device_id']).encode('utf-8')).hexdigest()
        if device_id in self.discovered:
            self.discovered[device_id].enable()
            return self.discovered[device_id]

        if device_id not in self.discovery_history:
            self.discovery_history[device_id] = time()
        kwargs['discovered_at'] = self.discovery_history[device_id]

        self.discovered[device_id] = DiscoveredDevice(self, device_id, kwargs)
        discovered = self.discovered[device_id]
        if device_id not in self.discovery_history:
            self.discovery_history[device_id] = time()
            if 'notification_title' in kwargs:
                notification_title = kwargs['notification_title']
            else:
                notification_title = "New %s device found." % kwargs['source']
            if 'notification_message' in kwargs:
                notification_message = kwargs['notification_message']
            else:
                notification_message = "<p>New %s device found:</p><p>Description: %s</p>" \
                                       % (kwargs['source'], kwargs['display_description'])
                if discovered.mfr != '':
                    notification_message += "<p>Manufacturer: %s</p>" % discovered.mfr
                if discovered.model != '':
                    notification_message += "<p>Model: %s</p>" % discovered.model
                if discovered.serial != '':
                    notification_message += "<p>Serial: %s</p>" % discovered.serial
            self._Notifications.add({
                'title': notification_title,
                'message': notification_message,
                'source': discovered.source,
                'persist': True,
                'priority': 'high',
                'always_show': True,
                'always_show_allow_clear': True,
            })
        return discovered

    def disable(self, discovered_id):
        if discovered_id in self.discovered:
            discovered = self.discovered[discovered_id]
            discovered.disable()
            return True
        return False

    def enable(self, discovered_id):
        if discovered_id in self.discovered:
            discovered = self.discovered[discovered_id]
            discovered.disable()
            return True
        return False

class DiscoveredDevice(object):
    """
    A single discovered device.
    """
    def __init__(self, parent, device_id, data):
        """
        Setup the cron event.
        """
        self._Parent = parent
        self.device_id = device_id
        self.discovered_at = data['discovered_at']
        self.source = data['source']
        self.display_description = data['display_description']
        self.description = data.get('description', '')
        self.mfr = data.get('mfr', '')
        self.model = data.get('model', '')
        self.serial = data.get('serial', '')
        self.label = data.get('label', '')
        self.machine_label = data.get('machine_label', '')
        self.device_type = data.get('device_type', '')
        self.variables = data.get('variables', {})
        self.yombo_device = data.get('yombo_device', None)
        self.enabled = data.get('enabled', True)

    def update_attributes(self, device, source=None):
        """
        Update any attributes passed in.
        :param device:
        :return:
        """
        if 'source' in device:
            self.source = device["source"]
        if 'display_description' in device:
            self.display_description = device["display_description"]
        if 'description' in device:
            self.description = device["description"]
        if 'model' in device:
            self.model = device["model"]
        if 'serial' in device:
            self.serial = device["serial"]
        if 'label' in device:
            self.label = device["label"]
        if 'machine_label' in device:
            self.machine_label = device["machine_label"]
        if 'device_type' in device:
            self.device_type = device["device_type"]
        if 'variables' in device:
            self.variables = device["variables"]
        if 'yombo_device' in device:
            self.yombo_device = device["yombo_device"]

    def disable(self):
        self.enabled = False

    def enable(self):
        self.enabled = True

    @property
    def json_output(self):
        out_variables = {}
        counter = 90
        for variable_name, variables in self.variables.items():
            if variable_name not in out_variables:
                out_variables[variable_name] = {}
            if isinstance(variables, list):
                for variable in variables:
                    out_variables[variable_name]["new_%s" % counter] = variable
                    counter += 1
            else:
                out_variables[variable_name]["new_%s" % counter] = variables
                counter += 1
        data = {
            'label': self.label,
            'machine_label': self.machine_label,
            'description': self.description,
            'device_type_id': self.device_type.device_type_id,
            'vars': out_variables,
        }
        return json.dumps(data)
