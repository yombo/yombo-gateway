# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Discovery @ Library Documentation <https://yombo.net/docs/libraries/discovery>`_

Tracks all auto-discovered devices in one location.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/discover.html>`_
"""
# Import python libraries
import json
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.entity import Entity
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import DiscoverySchema
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.utils import random_string
from yombo.utils.caller import caller_string

logger = get_logger("library.discovery")


class DiscoveredDevice(Entity, LibraryDBChildMixin):
    """
    A single discovered device.
    """
    _Entity_type: ClassVar[str] = "Discovered device"
    _Entity_label_attribute: ClassVar[str] = "discovery_id"

    def load_attribute_values_pre_process(self, incoming):
        if "yombo_device" in incoming:
            self.yombo_device = incoming["yombo_device"]
        else:
            self.yombo_device = None

    def enable(self):
        """ Enable displaying of this discovered device. """
        self. update({"status": 1})

    def disable(self):
        """ Disable displaying of this discovered device. """
        self. update({"status": 0})

    def delete(self):
        """ Delete this discovered device. This sets the status to 0, where it will eventually be cleaned up. """
        self. update({"status": 2})

    def touch(self):
        self. update({"last_seen_at": int(time())})

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

    # def asdict(self):
    #     """
    #     Display all the various details about the discovered device.
    #     :return:
    #     """
    #     out_variables = {}
    #     counter = 90
    #     for variable_name, variables in self.variables.items():
    #         if variable_name not in out_variables:
    #             out_variables[variable_name] = {}
    #         if isinstance(variables, list):
    #             for variable in variables:
    #                 out_variables[variable_name][f"new_{counter}"] = variable
    #                 counter += 1
    #         else:
    #             out_variables[variable_name][f"new_{counter}"] = variables
    #             counter += 1
    #     if self.yombo_device is not None:
    #         yombo_device_id = self.yombo_device.device_id
    #         yombo_device_label = self.yombo_device.full_label
    #     else:
    #         yombo_device_id = None
    #         yombo_device_label = ""
    #
    #     return {
    #         "label": self.label,
    #         "machine_label": self.machine_label,
    #         "description": self.description,
    #         "source": self.source,
    #         "device_type_id": self.device_type.device_type_id,
    #         "device_type_machine_label": self.device_type.machine_label,
    #         "yombo_device_id": yombo_device_id,
    #         "yombo_device_label": yombo_device_label,
    #         "model": self.model,
    #         "serial": self.serial,
    #         "vars": out_variables,
    #     }


class Discovery(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    A one-stop location to track discovered devices. This allows the user to quickly find auto-discovered devices
    and add them as a Yombo controlled device.
    """
    discovery: ClassVar[dict] = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "discovery_id"
    _storage_attribute_name: ClassVar[str] = "discovery"
    _storage_pickled_fields: ClassVar[Dict[str, str]] = {"variables": "msgpack_zip"}
    _storage_label_name: ClassVar[str] = "discovery"
    _storage_class_reference: ClassVar = DiscoveredDevice
    _storage_schema: ClassVar = DiscoverySchema()
    _storage_search_fields: ClassVar[str] = [
        "discovery_id", "machine_label", "description"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "machine_label"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Loads previously found devices from the database.
        """
        yield self.load_from_database()

    @inlineCallbacks
    def new(self, discover_id: str, mfr: str, model: str, serial: str, label: str, machine_label: str,
            description: str, request_context: str, device_type: Optional = None, device_type_id: Optional[str] = None,
            gateway_id: Optional[str] = None, variables: Optional[dict] = None, yombo_device: Optional = None,
            discovered_at: Optional[Union[float, int]] = None, last_seen_at: Optional[Union[float, int]] = None,
            created_at: Optional[Union[float, int]] = None, updated_at: Optional[Union[float, int]] = None,
            notification: Optional[dict] = None, _load_source: Optional[str] = None,
            _request_context: Optional[str] = None,
            _authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None):
        """
        Creates a new auto-discovered device.

        Note:
          * Either discovery source or load_source must be supplied.
          * Either device type or device type id must be supplied.

        :param discover_id: A unique id to reference this discovered device. No need to worry about conflicts from other modules.
        :param device_type: A device type to associate this device with.
        :param device_type_id: A device type id to associate this device with.
        :param gateway_id: Gateway_id where device was found on.
        :param discovered_at: When this device was first discovered.
        :param last_seen_at: When this device was last scene at.
        :param mfr: Who makes this device.
        :param model: Model of this device.
        :param serial: Serial number.
        :param label: A human friendly label.
        :param machine_label: A machine friendly label.
        :param description: A description about this device.
        :param yombo_device: Attach an already created yombo device to the discovered device.
        :param request_context: A reference to the module / library, or a string to store.
        :param variables: A dictionary of variables which is used when creating the device.
        :param created_at: A float/int when this device was created.
        :param updated_at: A float/int when this device was last updated.
        :param notification: Notification details.
        :param _load_source: Where the data originated from. One of: local, database, yombo, system
        :param _request_context: Context about the request. Such as an IP address of the source.
        :param _authentication: An auth item such as a websession or authkey.
        :return:
        """
        logger.debug("new discovered device: {discover_id}", discover_id=discover_id)
        self.check_authorization(_authentication, "create", required=False)

        if _load_source is None and request_context is None:
            raise YomboWarning(f"Device discovery must include either a load_source or request_context:"
                               f" {machine_label} - {label}")

        if _load_source == "database":
            discovery_source_string = request_context
        elif request_context is None:
            raise YomboWarning(f"If load_souce is not database, request_context must be a string."
                               f" {machine_label} - {label}")
        else:
            if isinstance(request_context, str) is False:
                request_context = request_context._FullName

        machine_label = self._Validate.slugify(machine_label)
        if discover_id is None:
            discovered_id = random_string()

        if gateway_id is None:
            gateway_id = self._gateway_id

        discover_id = self.get_device_hash(discover_id, request_context)

        if device_type is None and device_type_id is None:
            raise YomboWarning(f"Either device_type or device_type_id must be supplied."
                               f" {machine_label} - {label}")
        if device_type is not None:
            device_type_id = device_type.device_type_id
            device_type = None
        else:
            device_type_id = self._DeviceTypes.get(device_type_id).device_type_id

        device_data = {
            "id": discover_id,
            "gateway_id": gateway_id,
            "device_type_id": device_type_id,
            "discovered_at": discovered_at,
            "last_seen_at": last_seen_at,
            "mfr": mfr,
            "model": model,
            "serial": serial,
            "label": label,
            "machine_label": machine_label,
            "description": description,
            "yombo_device": yombo_device,
            "request_context": request_context,
            "variables": variables,
            "created_at": created_at,
            "updated_at": updated_at,
        }
        if discover_id in self.discovery:
            filtered = {k: v for k, v in device_data.items() if v is not None}
            self.discovery[discover_id].update(filtered)
            self.discovery[discover_id].enable()
            self.discovery[discover_id].touch()
            return self.discovery[discover_id]

        # print(f"discovered device2: {device_data}")
        yield self.load_an_item_to_memory(
            device_data,
            load_source=_load_source,
            request_context=_request_context if _request_context is not None else caller_string(),
            authentication=_authentication
        )

        if _load_source != "database":  # TODO: review. Probably not the correct check to display notificaiton.
            if notification is None:
                notification = {}

            if "notification_title" in notification:
                notification_title = notification["notification_title"]
            else:
                notification_title = f"New {request_context} device found."

            if "notification_message" in notification:
                notification_message = notification["notification_message"]
            else:
                notification_message = f"<p>New {{source._FullName}} device found:</p><p>Description: {device_data['notification_description']}</p>"
                if mfr != "":
                    notification_message += f"<p>Manufacturer: {mfr}</p>"
                if model != "":
                    notification_message += f"<p>Model: {model}</p>"
                if serial != "":
                    notification_message += f"<p>Serial: {serial}</p>"

            yield self._Notifications.new(title=notification_title,
                                          message=notification_message,
                                          persist=True,
                                          priority="high",
                                          always_show=True,
                                          always_show_allow_clear=True,
                                          _request_context=_request_context,
                                          _authentication=_authentication
                                          )
        return self.discovery[discover_id]

    def update(self, discover_id, data, source=None):
        discover_id = self.get_device_hash(discover_id, source)
        self.discovery[discover_id].update(data)

    def touch(self, discover_id, source):
        discover_id = self.get_device_hash(discover_id, source)
        self.discovery[discover_id].touch()

    def set_yombo_device(self, discover_id, yombo_device, request_context):
        discover_id = self.get_device_hash(discover_id, request_context)
        self.discovery[discover_id].yombo_device = yombo_device
        return self.discovery[discover_id]

    def get_device_hash(self, discover_id, source=None):
        if discover_id in self.discovery:
            return discover_id

        if source is None:
            raise YomboWarning("Discovery device updates requires a reference from the caller as 'source'.")

        if isinstance(source, str):
            return self._Hash.sha224_compact(str(source + discover_id).encode("utf-8"))

        return self._Hash.sha224_compact(str(source._FullName + discover_id).encode("utf-8"))

    def disable(self, discovered_id):
        if discovered_id in self.discovery:
            discovery = self.discovery[discovered_id]
            discovery.disable()
            return True
        return False

    def enable(self, discovered_id):
        if discovered_id in self.discovery:
            discovery = self.discovery[discovered_id]
            discovery.disable()
            return True
        return False

    def delete(self, discovered_id):
        if discovered_id in self.discovery:
            del self.discovery[discovered_id]
            return True
        return False


