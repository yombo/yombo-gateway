"""
.. note::

  * End user documentation: `Scenes @ User Documentation <https://yombo.net/docs/gateway/web_interface/scenes>`_
  * For library documentation, see: `Scenes @ Library Documentation <https://yombo.net/docs/libraries/scenes>`_

Handles scenes that are stored as nodes. Devices, states, and atoms can be referenced from any gateway
connected within the cluster.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.18.0
.. versionchanged:: 0.24.0

    Merged automation rules into scenes. They were nearly the same, except for the triggers.

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/scenes.html>`_
"""
# Import python libraries
from copy import deepcopy
import msgpack
import traceback
import types
from typing import Any, ClassVar, Dict, List, Optional, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants.scenes import (REQUIRED_ADDON_TRIGGER_KEYS, REQUIRED_ADDON_CONDITION_KEYS,
                                    REQUIRED_ADDON_ACTION_KEYS)
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
from yombo.lib.nodes import Node
from yombo.mixins.parent_storage_accessors_mixin import ParentStorageAccessorsMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.utils import random_string, sleep, is_true_false, bytes_to_unicode
from yombo.utils.dictionaries import dict_filter

from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.scenes")


class Scenes(YomboLibrary, ParentStorageAccessorsMixin, LibrarySearchMixin):
    """
    Scenes can be used to group actions together. Optionally, a trigger can be specified to
    automatically call the scene. For example, when a state or device changes to a particular value.

    Scene capabilities can be extended by implementing the _scenes_something_ hook.
    """
    scenes: dict = {}  # Stores all loaded scenes, which are simply nodes.

    additional_scene_triggers = {}  # Additional available scene triggers added by hook
    additional_scene_conditions = {}  # Additional available scene conditions added by hook
    additional_scene_actions = {}  # Additional available scene actions added by hook

    additional_triggers: ClassVar[List[str]] = {  # All possible triggers that are currently available
        "device": {},
        "scene": {},
    }

    # builtin_scene_action_variables

    startup_items_checked: ClassVar = {}  # If any items need to be called during startup.

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "scene_id"
    _storage_label_name: ClassVar[str] = "scene"
    _storage_class_reference: ClassVar = None
    _storage_attribute_name: ClassVar[str] = "scenes"
    _storage_search_fields: ClassVar[List[str]] = [
        "scene_id", "node_type", "machine_label", "label"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "machine_label"

    def _load_(self, **kwargs) -> None:
        """
        Gets all scene based nodes and init's them. This is called here because template library needs
        to load first, so the scene class cannot use it's _init_.

        :return:
        """
        try:
            self.scenes = self._Nodes.get_advanced({"node_type": "scene"})
        except KeyError:
            self.scenes = {}

        # self.scenes_running = {}  # tracks if scene is running, stopping, or stopped
        # self.scene_templates = {}  # hold any templates for scenes here for caching.
        # self.scene_types_extra = {}  # any addition action types, fill by _scene_action_list_ hook.

    @inlineCallbacks
    def _start_(self, **kwargs):
        """
        Calls libraries and modules to check if any additional scene types should be defined.

        For an example, see the states library.

        **Hooks called**:

        * _scene_actions_ : Expects a list of dictionaries containing additional scene action types.

        **Usage**:

        .. code-block:: python

           def _scene_actions_(self, **kwargs):
               '''
               Adds additional scene action types.
               '''
               return [
                   {
                       "action_type": "state",
                       "description": "Change a state value",
                       "render_table_column": self.scene_render_table_column,  # Show summary line in a table.
                       "validate_scene_action": self.scene_item_update,  # Return a dictionary to store as the item.
                       "handle_scene_action_triggered": self.scene_item_triggered,  # Do item activity
                   }
               ]

        """
        # Collect addon triggers
        addon_triggers = yield global_invoke_all("_scene_triggers_", called_by=self)
        logger.debug("addon_triggers: {addon_triggers}", addon_triggers=addon_triggers)
        for component_name, hook_response in addon_triggers.items():
            for addon_trigger in hook_response:
                if not all(addon_trigger_key in addon_trigger for addon_trigger_key in REQUIRED_ADDON_TRIGGER_KEYS):
                    logger.info("Scene addon trigger doesn't have required fields, skipping: {required}",
                                required=REQUIRED_ADDON_TRIGGER_KEYS)
                    continue
                trigger = dict_filter(addon_trigger, REQUIRED_ADDON_TRIGGER_KEYS)
                trigger["trigger_source"] = component_name
                try:
                    self.additional_scene_triggers[addon_trigger["trigger_type"]] = {
                        "trigger_type": addon_trigger["trigger_type"],
                        "match_scene_trigger": addon_trigger["match_scene_trigger"],
                    }
                except KeyError as e:
                    logger.warn("Unable to extend scene trigger capabilities from component {component_name},"
                                " reason: {e}",
                                component_name=component_name, e=e)

        # Collect addon conditions
        addon_conditions = yield global_invoke_all("_scene_conditions_", called_by=self)
        logger.debug("addon_conditions: {addon_conditions}", addon_conditions=addon_conditions)
        for component_name, hook_response in addon_conditions.items():
            for addon_condition in hook_response:
                if not all(addon_condition_key in addon_condition for addon_condition_key in REQUIRED_ADDON_CONDITION_KEYS):
                    logger.info("Scene addon condition doesn't have required fields, skipping: {required}",
                                required=REQUIRED_ADDON_CONDITION_KEYS)
                    continue
                trigger = dict_filter(addon_condition, REQUIRED_ADDON_CONDITION_KEYS)
                trigger["trigger_source"] = component_name
                try:
                    self.additional_scene_conditions[addon_condition["trigger_type"]] = {
                        "trigger_type": addon_condition["trigger_type"],
                        "description": addon_condition["description"],
                    }
                except KeyError as e:
                    logger.warn("Unable to extend scene condition capabilities from component {component_name},"
                                " reason: {e}",
                                component_name=component_name, e=e)

        # Collect addon actions
        addon_actions = yield global_invoke_all("_scene_actions_", called_by=self)
        logger.debug("addon_actions: {addon_actions}", addon_actions=addon_actions)
        for component_name, hook_response in addon_actions.items():
            for addon_action in hook_response:
                if not all(addon_action_key in addon_action for addon_action_key in REQUIRED_ADDON_ACTION_KEYS):
                    logger.info("Scene addon action doesn't have required fields, skipping: {required}",
                                required=REQUIRED_ADDON_ACTION_KEYS)
                    continue
                action = dict_filter(addon_action, REQUIRED_ADDON_ACTION_KEYS)
                action["action_source"] = component_name
                try:
                    self.additional_scene_actions[addon_action["action_type"]] = {
                        "action_type": addon_action["action_type"],
                        "description": addon_action["description"],
                        "validate_scene_action": addon_action["validate_scene_action"],
                        "handle_scene_action": addon_action["handle_scene_action"],
                        "generate_scene_action_data_options": addon_action["generate_scene_action_data_options"]
                    }
                except KeyError as e:
                    logger.warn("Unable to extend scene action capabilities from component {component_name},"
                                " reason: {e}",
                                component_name=component_name, e=e)

        logger.debug("_start_: Calling scene_inits to validate each scene and get it started.")
        for scene_id, scene in self.scenes.items():
            try:
                scene.scene_init(**kwargs)
            except Exception as e:
                logger.warn("Error validating scene '{label}'", label=scene.label)

    def _started_(self, **kwargs):
        """
        Called when the gateway is running. This is used to check if any scenes need to be called on
        gateawy startup.
        """
        logger.debug("_started_: System started, about to iterate scenes and call their _started_ function.")
        for scene_id, scene in self.scenes.items():
            scene._started_(**kwargs)

    # @inlineCallbacks
    # def set_from_gateway_communications(self, scene):
    #     """
    #     Used by the gateway coms (mqtt) system to set scene values.
    #     :param key:
    #     :param data:
    #     :return:
    #     """
    #     gateway_id = data["gateway_id"]
    #     if gateway_id == self.gateway_id:
    #         return
    #     if gateway_id not in self.states:
    #         self.states[gateway_id] = {}
    #     source_type, source_label = get_yombo_instance_type(source)
    #
    #     self.states[data["gateway_id"]][key] = {
    #         "gateway_id": data["gateway_id"],
    #         "value": data["value"],
    #         "value_human": data["value_human"],
    #         "value_type": data["value_type"],
    #         "live": False,
    #         "source": source_label,
    #         "created_at": data["created_at"],
    #         "updated_at": data["updated_at"],
    #     }
    #
    #     self._Scenes.trigger_monitor("state",
    #                                      key=key,
    #                                      value=data["value"],
    #                                      value_type=data["value_type"],
    #                                      value_full=self.states[gateway_id][key],
    #                                      action="set",
    #                                      gateway_id=gateway_id,
    #                                      source=source,
    #                                      source_label=source_label,
    #                                      )
    #
    #     # Call any hooks
    #     yield global_invoke_all("_states_set_",
    #                             called_by=self,
    #                             key=key,
    #                             value=data["value"],
    #                             value_type=data["value_type"],
    #                             value_full=self.states[gateway_id][key],
    #                             gateway_id=gateway_id,
    #                             source=source,
    #                             source_label=source_label,
    #                             )

    def scene_user_access(self, scene_id, access_type=None):
        """
        Gets all users that have access to this scene.

        :param access_type: If set to "direct", then gets list of users that are specifically added to this device.
            if set to "roles", returns access based on role membership.
        :return:
        """
        if access_type is None:
            access_type = "direct"

        scene = self.get(scene_id)

        if access_type == "direct":
            permissions = {}
            for email, user in self._Users.users.items():
                item_permissions = user.item_permissions
                if "scene" in item_permissions and scene.machine_label in item_permissions["scene"]:
                    if email not in permissions:
                        permissions[email] = []
                    for action in item_permissions["scene"][scene.machine_label]:
                        if action not in permissions[email]:
                            permissions[email].append(action)
            return permissions
        elif access_type == "roles":
            return {}

    # Migrated for 0.24
    # def scene_types_urls_sorted(self):
    #     """
    #     Return scene_type_urls, but sorted by display value.
    #
    #     :param url_type:
    #     :return:
    #     """
    #     return dict(sorted(self.scene_types_urls.items(), key=lambda x: x))
    #
    # def get_scene_type_column_data(self, scene, action):
    #     """
    #     Called by the scenes macros.tpl file to get scene detail action for a custom scene type.
    #
    #     :param scene:
    #     :param action:
    #     :return:
    #     """
    #     action_type = action["action_type"]
    #     if action_type in self.addon_actions:
    #         return self.addon_actions[action_type]["render_table_column_callback"](scene, action)

    def sorted(self, key: Optional[str] = None) -> dict:
        """
        Returns a dict, sorted by key.  If key is not set, then default is "label".

        :param key: Attribute contained in a scene to sort by.
        :return: All scenes, sorted by key.
        """
        if key is None:
            key = "label"
        return dict(sorted(iter(self.scenes.items()), key=lambda i: getattr(i[1], key)))

    def get(self, requested_scene=None, gateway_id=None):
        """
        Return the requested scene, if it's found.

        :param requested_scene: The scene ID or machine_label of the scene to return.
        :param gateway_id: The gateway_id to restrict results to.
        :return:
        """
        if isinstance(requested_scene, Node):
            if requested_scene.node_type == "scene":
                return requested_scene
            else:
                raise YomboWarning("Must submit a node type of scene if submitting an instance")

        if requested_scene is None:
            if gateway_id is None:
                gateway_id = self._gateway_id
            outgoing = {}
            for scene_id, scene in self.scenes.items():
                if scene.gateway_id == gateway_id:
                    outgoing[scene_id] = scene
            return dict(sorted(outgoing.items(), key=lambda x: x[1].label))

        if requested_scene in self.scenes:
            return self.scenes[requested_scene]
        for temp_scene_id, scene in self.scenes.items():
            if scene.machine_label.lower() == requested_scene.lower():
                return scene
        raise KeyError(f"Cannot find requested scene : {requested_scene}")

    def disable(self, scene_id):
        """
        Disable a scene. Just marks the configuration for the scene as disabled.

        :param scene_id:
        :return:
        """
        scene = self.get(scene_id)
        scene.disable()

    def enable(self, scene_id):
        """
        Enable a scene. Just marks the configuration for the scene as enabled.

        :param scene_id:
        :return:
        """
        scene = self.scenes[scene_id]
        scene.enable()

    def disable_intent(self, scene_id, **kwargs):
        """
        Disallow scene to be called via an intent.

        :param scene_id:
        :return:
        """
        scene = self.get(scene_id)
        scene.disable_intent()

    def enable_intent(self, scene_id, **kwargs):
        """
        Allow scene to be called via an intent.

        :param scene_id:
        :return:
        """
        scene = self.scenes[scene_id]
        scene.enable_intent()

    def check_duplicate_scene(self, label=None, machine_label=None, scene_id=None):
        """
        Checks if a new/update scene label and machine_label are already in use.

        :param label:
        :param machine_label:
        :param scene_id: Ignore matches for a scene_id
        :return:
        """
        if label is None and machine_label is None:
            raise YomboWarning("Must have at least label or machine_label, or both.")
        for temp_scene_id, scene in self.scenes.items():
            if scene_id is not None and scene.node_id == scene_id:
                continue
            if scene.label.lower() == label.lower():
                raise YomboWarning(f"Scene with matching label already exists: {scene.node_id}")
            if scene.machine_label.lower() == machine_label.lower():
                raise YomboWarning(f"Scene with matching machine_label already exists: {scene.node_id}")

    @inlineCallbacks
    def new(self, label, machine_label, description, status):
        """
        Add new scene.

        :param label:
        :param machine_label:
        :return:
        """
        self.check_duplicate_scene(label, machine_label)
        data = {
            "configs": {
                "description": description,
            },
            "triggers": {},
            "conditions": {},
            "actions": {},
        }
        new_scene = yield self._Nodes.create(label=label,
                                             machine_label=machine_label,
                                             node_type="scene",
                                             data=data,
                                             data_content_type="json",
                                             gateway_id=self._gateway_id,
                                             destination="gw",
                                             status=1)
        self.scenes[new_scene.node_id] = new_scene
        reactor.callLater(0.001, global_invoke_all,
                                    "_scene_added_",
                                    called_by=self,
                                    arguments={
                                        "scene_id": new_scene.node_id,
                                        "scene": new_scene,
                                        }
                          )
        return new_scene

    def edit(self, scene_id, label=None, machine_label=None, description=None, status=None, allow_intents=None):
        """
        Edit a scene label and machine_label.

        :param scene_id:
        :param label:
        :param machine_label:
        :param description:
        :param status:
        :return:
        """
        scene = self.get(scene_id)
        scene.edit(label=label, machine_label=machine_label, description=description, status=status,
                   allow_intents=allow_intents)
        return scene

    @inlineCallbacks
    def delete(self, scene_id, session=None):
        """
        Deletes the scene. Will disappear on next restart. This allows the user to recover it.
        This marks the node to be deleted!

        :param scene_id:
        :return:
        """
        scene = self.get(scene_id)
        results = yield self._Nodes.delete_node(scene.scene_id, session=session)
        yield global_invoke_all("_scene_deleted_",
                                called_by=self,
                                arguments={
                                    "scene_id": scene_id,
                                    "scene": scene,
                                    }
                                )
        return results

    @inlineCallbacks
    def duplicate_scene(self, scene_id):
        """
        Deletes the scene. Will disappear on next restart. This allows the user to recover it.
        This marks the node to be deleted!

        :param scene_id:
        :return:
        """
        scene = self.get(scene_id)
        label = f"{scene.label} ({_('common::copy')})"
        machine_label = f"{scene.machine_label}_{_('common::copy')}"
        if label is not None and machine_label is not None:
            self.check_duplicate_scene(label, machine_label, scene_id)
        new_data = bytes_to_unicode(msgpack.unpackb(msgpack.packb(scene.data)))  # had issues with deepcopy
        new_scene = yield self._Nodes.new(label=label,
                                          machine_label=machine_label,
                                          node_type="scene",
                                          data=new_data,
                                          data_content_type="json",
                                          gateway_id=self._gateway_id,
                                          destination="gw",
                                          status=1)
        self.scenes[new_scene.node_id] = new_scene
        yield global_invoke_all("_scene_added_",
                                called_by=self,
                                arguments={
                                    "scene_id": scene_id,
                                    "scene": scene,
                                    }
                                )
        return new_scene

    def get_action(self, scene_id: str, action_id: Optional[str] = None):
        """
        Get a scene item.

        :param scene_id:
        :param action_id:
        :return:
        """
        scene = self.get(scene_id)
        return scene.get_action(action_id)

    def sort_actions(self, scene_id: str):
        """ Re-sorts all the actions in order by weight. It also updates the weights to make them more sane. """
        scene = self.get(scene_id)
        scene.sort_actions()

    def add_action(self, scene_id: str, data: dict):
        """
        Add scene action item.

        :param scene_id:
        :param data:
        :return:
        """
        scene = self.get(scene_id)
        scene.add_action(data)
        return scene

    def edit_action(self, scene_id: str, action_id: str, data: dict):
        """
        Edit scene action item.

        :param scene_id:
        :param action_id:
        :param data:
        :return:
        """
        scene = self.get(scene_id)
        scene.edit_action(action_id, data)
        return scene

    def delete_action(self, scene_id: str, action_id: str):
        """
        Delete a scene action.

        :param scene_id:
        :param action_id:
        :return:
        """
        scene = self.get(scene_id)
        scene.delete_action(action_id)
        return scene

    def move_action_down(self, scene_id, action_id):
        """
        Move an action down.

        :param scene_id:
        :param action_id:
        :return:
        """
        scene = self.get(scene_id)
        scene.move_action_down(action_id)
        return scene

    def move_action_up(self, scene_id, action_id):
        """
        Move an action up.

        :param scene_id:
        :param action_id:
        :return:
        """
        scene = self.get(scene_id)
        scene.move_action_up(action_id)
        return scene

    def start(self, scene_id, **kwargs):
        """
        Trigger a scene to start.

        :param scene_id:
        :param kwargs:
        :return:
        """
        scene = self.get(scene_id)
        return scene.start()

    def stop(self, scene_id, **kwargs):
        """
        Stop a currently running scene.

        :param scene_id:
        :param kwargs:
        :return:
        """
        scene = self.get(scene_id)
        return scene.stop()

    def generate_scene_action_data_options(self):
        """
        Generates all possible actions and all their possible values.

        :return:
        """
        results = {
            "device": {
                "variables": {
                    "device_machine_label": {
                        "data_type": "string",
                        "multiple": False,
                        "required": True,
                        "values": [],
                    },
                    "command_machine_label": {
                        "data_type": "string",
                        "multiple": False,
                        "required": True,
                        "values": [],
                    },
                    "inputs": {
                        "data_type": "dict",
                        "multiple": True,
                        "required": False,
                        "values": [],
                    },
                },
            },
            "pause": {
                "variables": {
                    "pause": {
                        "data_type": "decimal",
                        "multiple": False,
                        "required": True,
                        "values": [],
                    },
                },
            },
            "scene": {
                "variables": {
                    "scene_machine_label": {
                        "data_type": "string",
                        "multiple": False,
                        "required": True,
                        "values": [],
                    },
                    "scene_action": {
                        "data_type": "string",
                        "multiple": False,
                        "required": True,
                        "values": [
                            {
                                "text": "start",
                                "value": "start"
                            },
                            {
                                "text": "stop",
                                "value": "stop"
                            },
                            {
                                "text": "enable",
                                "value": "enable"
                            },
                            {
                                "text": "disable",
                                "value": "disable"
                            },
                        ],
                    },
                },
            },

        }

        # Fill in the device values
        for device_id, device in self._Devices.devices.items():
            results["device"]["variables"]["device_machine_label"]["values"].append({
                "text": device.full_label,
                "value": device.device_id
            })
        # Todo: use device.available_commands() somehow....?
        for command_id, command in self._Commands.commands.items():
            results["device"]["variables"]["command_machine_label"]["values"].append({
                "text": command.label,
                "value": command.command_id
            })

        # Fill in the scene values.
        for scene_id, scene in self._Scenes.scenes.items():
            results["scene"]["variables"]["scene_machine_label"]["values"].append({
                "text": scene.machine_label,
                "value": scene.machine_label
            })

        # Add on additional scene action types
        for action_type, data in self.additional_scene_actions.items():
            try:
                results[action_type] = data["generate_scene_action_data_options"](self)
            except Exception as e:
                logger.warn("Error calling scene action data options for: {action_type}: {e}",
                            action_type=action_type, e=e)

        return results

    def trigger_monitor(self, trigger_type, **kwargs):
        """
        Various libraries and modules will call this when something happens to see if a scene
        needs to be triggered.

        :param trigger_type: scene, device, state, etc.
        :param kwargs:
        :return:
        """
        if hasattr(self, '_Loader') is False:
            return
        run_phase_name, run_phase_int = self._Loader.run_phase
        if run_phase_int < 5500:  # 'modules_prestart' is when we start processing automation triggers.
            return

        if "called_by" not in kwargs:
            kwargs["called_by"] = "trigger_monitor"

        for scene_id, scene in self.scenes.items():
            scene.check_for_triggers(trigger_type, **kwargs)
