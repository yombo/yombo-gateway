# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * End user documentation: `States @ User Documentation <https://yombo.net/docs/gateway/web_interface/states>`_
  * For developer documentation, see: `States @ Module Development <https://yombo.net/docs/libraries/states>`_

.. seealso::

   * The :doc:`Atoms library </lib/atoms>` is used to store static data about the environment.
   * The :doc:`System Data Mixin </mixins/systemdata_mixin>` handles the bulk of the actions.
   * The :doc:`MQTT library </lib/mqtt>` is used to allow IoT devices to interact with states.

The states library is used to collect and provide information about various states that the automation system
can be in or exist around it. For example, it can tell if it's light outside, dawn, dusk, or if it's connected
to the Yombo server. It can provide a list of users connected and what module they are connected through.

Example states: times_dark, weather_raining, alarm_armed, yombo_service_connection

*Usage**:

.. code-block:: python

   try:
     raining = self._States["weather.raining"]
   except:
     raining = None

   if raining is not True:
       # turn on sprinklers

   try:
     jeffIsHome = self._States["is.people.jeff.home"]
   except:
     jeffIsHome = None

   if jeffIsHome == "home":
       # turn on HVAC
   elif jeffIsHome is not None:
       # turn off HVAC
   else:
       # we don't know if Jeff is home or not, leave HVAC alone

   try:
     self._States["weather_is_cloudy"] = True
   except:
     pass  # unable to set state?


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/states.html>`_

"""
# Import python libraries
import re
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union
from voluptuous import Schema, Required, All, Length, Range

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.constants import SENTINEL
from yombo.core.entity import Entity
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
from yombo.core.schemas import StateSchema
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.mixins.systemdata_mixin import SystemDataParentMixin, SystemDataChildMixin
from yombo.utils import random_int

logger = get_logger("library.states")

ACTION_STATE_SCHEMA = Schema({
    Required('gateway_id'): All(str, Length(min=2)),
    Required('state_name'): All(str, Length(min=2)),
    Required('value'): All(str, Length(min=2)),
    Required('human_value'): All(str, Length(min=2)),
    Required('value_type'): ['str', 'dict', 'list', 'int', 'float', 'epoch'],
    Required('value'): All(str, Length(min=2)),
    Required('weight'): All(int, Range(min=0)),
})


class State(Entity, LibraryDBChildMixin, SystemDataChildMixin):
    """
    Represents a single system state.
    """
    _sync_to_api: ClassVar[bool] = False
    _Entity_type: ClassVar[str] = "State"
    _Entity_label_attribute: ClassVar[str] = "state_id"


class States(YomboLibrary, SystemDataParentMixin, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Provides a base API to store common states among libraries and modules.
    """
    states: dict = {"global": {}, "cluster": {}}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "state_id"
    _storage_attribute_name: ClassVar[str] = "states"
    _storage_label_name: ClassVar[str] = "state"
    _storage_class_reference: ClassVar = State
    _storage_schema: ClassVar = StateSchema()
    _storage_search_fields: ClassVar[List[str]] = [
        "state_id", "value"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "state_id"

    @inlineCallbacks
    def _init_(self, **kwargs):
        self.logger = logger
        self.states[self._gateway_id] = {}
        # print("states load from database...start")
        yield self.load_from_database()
        # print("states load from database...done")

        # setup cluster state defaults if not set
        try:
            self.get("is.away", gateway_id="cluster")
        except KeyError:
            self.set("is.away", False, value_type="bool", gateway_id="cluster", request_context=self._FullName)

    def _started_(self, **kwargs):
        self.memory_usage_checker_loop = LoopingCall(self.memory_usage_checker)
        self.memory_usage_checker_loop.start(random_int(1800, .10))

    def get(self, item_requested: str, default: Optional[Any] = SENTINEL, gateway_id: Optional[str] = None,
            instance: Optional[bool] = None, **kwargs):
        """
        Override some attribute requests.

        :raises KeyError: Raised when request is not found.
        :param item_requested: Name of data item to retrieve.
        :param default: Default value to return in a data instance if the requested item is missing.
        :param gateway_id: The gateway_id to reference.
        :param instance: If True, returns the object (atom/state), versus just the value.
        """
        if item_requested == "gateway.uptime":
            return float(time()) - float(self._Atoms.get("gateway.running_since", gateway_id=gateway_id))
        # print(f"states - get - {item_requested}")
        return super().get(item_requested, default=default, gateway_id=gateway_id, instance=instance)

    @inlineCallbacks
    def memory_usage(self):
        usage = yield self._Files.read("/proc/self/status", convert_to_unicode=True)
        return int(re.search(r"^VmRSS:\s+(\d+) kb$", usage, flags=re.IGNORECASE | re.MULTILINE).group(1))

    @inlineCallbacks
    def memory_usage_checker(self):
        """ Attempts to determine how much memory is being used."""
        usage = yield self.memory_usage()
        self.set("yombo.memory_usage", usage, request_context=self._FullName)


    ##############################################################################################################
    # Below this demonstrates adding additional scene action types. The following can be used as a simple demo   #
    # showing how to completely add a new scene item control type.                                               #
    ##############################################################################################################

    def _scene_triggers_(self, **kwargs):
        """
        Add an additional triggers to the scene triggers to handle state changes.

        :param kwargs:
        :return:
        """
        return [
            {
                "action_type": "state",
                "match_scene_trigger": self.match_scene_trigger,
            }
        ]

    def match_scene_trigger(self, scene, trigger):
        """
        Check if a trigger matches a scene's trigger.

        :param scene:
        :param trigger:
        :return:
        """
        trigger_gateway_id = trigger["gateway_id"]
        if trigger_gateway_id not in self.states:
            return False
        if trigger['state_id'] not in self.states[trigger_gateway_id]:
            return False
        return True

    def _scene_actions_(self, **kwargs):
        """
        Add an additional scene item control type: states

        :param kwargs:
        :return:
        """
        return [
            {
                "action_type": "state",
                "description": "Change a state value",
                # "render_table_column": self.scene_render_table_column,  # Show summary line in a table.
                "validate_scene_action": self.validate_scene_action,  # Return a dictionary to store as the item.
                "handle_scene_action": self.handle_scene_action,  # Do item activity
                "generate_scene_action_data_options": self.generate_scene_action_data_options,
            }
        ]

    # def scene_render_table_column(self, scene, action):
    #     """
    #     Return a dictionary that will be used to populate some variables for the Jinja2 template for scene action
    #     rendering.
    #
    #     :param scene:
    #     :param action:
    #     :return:
    #     """
    #     return {
    #         "action_type": f"<strong>State:</strong>{action['name']}<br>"
    #                        f"<strong>Gateway:</strong>{self._Gateways[action['gateway_id']].label}",
    #         "attributes": f"<strong>Set Value:</strong><br> {action['value']}",
    #         "edit_url": f"/scenes/{scene.scene_id}/edit_state/{action['action_id']}",
    #         "delete_url": f"/scenes/{scene.scene_id}/delete_state/{action['action_id']}",
    #     }

    def validate_scene_action(self, scene, data):
        action = {
            "scene_machine_label": data["scene_machine_label"],
            "scene_action": data["scene_action"],
            "weight": data["weight"]
        }
        return action

    def handle_scene_action(self, scene, action):
        self.set(action["name"], action["value"], action["value_type"], gateway_id=action["gateway_id"],
                 request_context=self._FullName)
        return True

    def generate_scene_action_data_options(self, scene, data):
        results = {
            "variables": {
                "gateway_id": {
                    "data_type": "any",
                    "multiple": False,
                    "required": True,
                    "values": [
                        {
                            "text": "cluster",
                            "value": "cluster"
                        }
                    ]
                },
                "state_name": {
                    "data_type": "string",
                    "multiple": False,
                    "required": True,
                    "values": [],
                },
                "value": {
                    "data_type": "any",
                    "multiple": False,
                    "required": True,
                    "values": [],
                },
                "human_value": {
                    "data_type": "any",
                    "multiple": False,
                    "required": False,
                    "values": [],
                },
                "value_type": {
                    "data_type": "any",
                    "multiple": False,
                    "required": True,
                    "values": [
                        {
                            "text": "string",
                            "value": "str"
                        },
                        {
                            "text": "dictionary",
                            "value": "dict"
                        },
                        {
                            "text": "list",
                            "value": "list"
                        },
                        {
                            "text": "integer",
                            "value": "int"
                        },
                        {
                            "text": "float",
                            "value": "float"
                        },
                        {
                            "text": "epoch (time)",
                            "value": "epoch"
                        },
                    ],
                },
            },
        }

        for gateway_id, gateway in self._Gateways.gateways.items():
            results["state"]["variables"]["state_name"]["values"].append({
                "text": gateway.label,
                "value": gateway.gateway_id
            })
