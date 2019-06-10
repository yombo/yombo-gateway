# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Discovery @ Library Documentation <https://yombo.net/docs/libraries/discovery>`_

Tracks all auto-discovered devices in one location.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/discovery.html>`_
"""
# Import python libraries
import json
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import sha256_compact

logger = get_logger("library.discovery")


class Discovery(YomboLibrary):
    """
    A one-stop location to track discovered devices. This allows the user to quickly find auto-discovered devices
    and add them as a Yombo controlled device.

    """
    def __contains__(self, device_requested):
        """
        Checks to if a provided device id is found.

            >>> if "129da137ab9318" in self._Discovery:

        or:

            >>> if "module.mymodule.mycron" in self._Discovery:

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

            >>> off_cmd = self._Discovery["129da137ab9318"]  #by id

        or:

            >>> off_cmd = self._Discovery["something here"]  #by description or other attributes

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
        self.discovered_search_attributes = ["description"]
        self.discovered = {}
        self.discovery_history = yield self._SQLDict.get(self, "discovery_history")

    def get(self, discover_id, source=None):
        """
        Looks for a discovered device by it's id OR by the discover_id and source.
        """
        discover_id = self.get_device_hash(discover_id, source)
        if discover_id in self.discovered:
            return self.discovered[discover_id]
        raise KeyError("Could not find a matching discovered device.")

    def new(self, discover_id, device_data, **kwargs):
        """
        Creates a new auto-discovered device.
        :param discover_id:
        :param device_data:
        :return:
        """
        newly_found = False
        logger.debug("new device: {discover_id}", discover_id=discover_id)
        source = device_data["source"]
        discover_id = self.get_device_hash(discover_id, source)
        if discover_id in self.discovered:
            self.discovered[discover_id].update_attributes(device_data)
            self.discovered[discover_id].enable()
            self.discovered[discover_id].touch()
            return self.discovered[discover_id]

        self.discovered[discover_id] = DiscoveredDevice(self, discover_id, device_data)
        discovered = self.discovered[discover_id]
        if discover_id not in self.discovery_history:
            self.discovery_history[discover_id] = time()
            newly_found = True

        device_data["discovered_at"] = self.discovery_history[discover_id]

        if "notification_title" in kwargs:
            notification_title = kwargs["notification_title"]
        else:
            notification_title = f"New {device_data['source']} device found."
        if "notification_message" in kwargs:
            notification_message = kwargs["notification_message"]
        else:
            notification_message = f"<p>New {device_data['source']} device found:</p><p>Description: {device_data['notification_description']}</p>"
            if discovered.mfr != "":
                notification_message += f"<p>Manufacturer: {discovered.mfr}</p>"
            if discovered.model != "":
                notification_message += f"<p>Model: {discovered.model}</p>"
            if discovered.serial != "":
                notification_message += f"<p>Serial: {discovered.serial}</p>"

        if newly_found is True:
            self._Notifications.add({
                "title": notification_title,
                "message": notification_message,
                "source": discovered.source,
                "persist": True,
                "priority": "high",
                "always_show": True,
                "always_show_allow_clear": True,
            })
        return discovered

    def update(self, discover_id, data, source=None):
        discover_id = self.get_device_hash(discover_id, source)
        self.discovered[discover_id].update_attributes(data)

    def touch(self, discover_id, source):
        discover_id = self.get_device_hash(discover_id, source)
        self.discovered[discover_id].touch()

    def set_yombo_device(self, discover_id, yombo_device, source):
        discover_id = self.get_device_hash(discover_id, source)
        self.discovered[discover_id].yombo_device = yombo_device
        return self.discovered[discover_id]

    def get_device_hash(self, discover_id, source=None):
        if discover_id in self.discovered:
            return discover_id

        if source is None:
            source = "unknown"
        return sha256_compact(str(source + discover_id).encode("utf-8"))

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

    def delete(self, discovered_id):
        if discovered_id in self.discovered:
            del self.discovered[discovered_id]
            return True
        return False


class DiscoveredDevice(object):
    """
    A single discovered device.
    """
    def __init__(self, parent, discover_id, data):
        """
        Setup the cron event.
        """
        self._Parent = parent
        self.discover_id = discover_id
        self.discovered_at = data.get("discovered_at", time())
        self.last_seen_at = data.get("last_seen_at", time())
        self.source = data["source"]
        self.description = data.get("description", "")
        self.mfr = data.get("mfr", "")
        self.model = data.get("model", "")
        self.serial = data.get("serial", "")
        self.label = data.get("label", "")
        self.machine_label = data.get("machine_label", "")
        self.device_type = data.get("device_type", "")
        self.variables = data.get("variables", {})
        self.yombo_device = data.get("yombo_device", None)
        self.enabled = data.get("enabled", True)

    def update_attributes(self, device, source=None):
        """
        Update any attributes passed in.
        :param device:
        :return:
        """
        if "source" in device:
            self.source = device["source"]
        if "description" in device:
            self.description = device["description"]
        if "mfr" in device:
            self.mfr = device["mfr"]
        if "model" in device:
            self.model = device["model"]
        if "serial" in device:
            self.serial = device["serial"]
        if "label" in device:
            self.label = device["label"]
        if "machine_label" in device:
            self.machine_label = device["machine_label"]
        if "device_type" in device:
            self.device_type = device["device_type"]
        if "variables" in device:
            self.variables = device["variables"]
        if "yombo_device" in device:
            self.yombo_device = device["yombo_device"]
        if "discovered_at" in device:
            self.discovered_at = device["discovered_at"]
        if "last_seen_at" in device:
            self.last_seen_at = device["last_seen_at"]

    def disable(self):
        self.enabled = False

    def enable(self):
        self.enabled = True

    def touch(self):
        self.last_seen_at = time()

    def __str__(self):
        return f"Discovered: {self.label} - {self.description}"

    @property
    def create_yombo_device_details(self):
        """
        Used to create a new device.
        :return:
        """
        out_variables = {}
        counter = 90
        for variable_name, variables in self.variables.items():
            if variable_name not in out_variables:
                out_variables[variable_name] = {}
            if isinstance(variables, list):
                for variable in variables:
                    out_variables[variable_name][f"new_{counter}"] = variable
                    counter += 1
            else:
                out_variables[variable_name][f"new_{counter}"] = variables
                counter += 1
        return json.dumps({
            "label": self.label,
            "machine_label": self.machine_label,
            "description": self.description,
            "device_type_id": self.device_type.device_type_id,
            "vars": out_variables,
        })

    def asdict(self):
        """
        Display all the various details about the discovered device.
        :return:
        """
        out_variables = {}
        counter = 90
        for variable_name, variables in self.variables.items():
            if variable_name not in out_variables:
                out_variables[variable_name] = {}
            if isinstance(variables, list):
                for variable in variables:
                    out_variables[variable_name][f"new_{counter}"] = variable
                    counter += 1
            else:
                out_variables[variable_name][f"new_{counter}"] = variables
                counter += 1
        if self.yombo_device is not None:
            yombo_device_id = self.yombo_device.device_id
            yombo_device_label = self.yombo_device.full_label
        else:
            yombo_device_id = None
            yombo_device_label = ""

        return {
            "label": self.label,
            "machine_label": self.machine_label,
            "description": self.description,
            "source": self.source,
            "device_type_id": self.device_type.device_type_id,
            "device_type_machine_label": self.device_type.machine_label,
            "yombo_device_id": yombo_device_id,
            "yombo_device_label": yombo_device_label,
            "model": self.model,
            "serial": self.serial,
            "vars": out_variables,
        }
