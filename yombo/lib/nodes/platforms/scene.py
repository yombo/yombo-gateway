# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * End user documentation: `Scene @ User Documentation <https://yombo.net/docs/gateway/web_interface/scenes>`_
  * For library documentation, see: `Automation @ Library Documentation <https://yombo.net/docs/libraries/scenes>`_

A scene node.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/nodes/platforms/scene.html>`_
"""
# Import python libraries
from copy import deepcopy
import traceback
from typing import Optional

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor

# Import Yombo libraries
from yombo.constants.scenes import SCENE_DATA_COMPONENTS
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.lib.nodes.node import Node
from yombo.utils import is_true_false, random_string, sleep
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.nodes.platforms.scene")


class Scene(Node):
    """
    Handles various tasks related to scenes.
    """
    @property
    def scene_id(self) -> str:
        return self.node_id

    @property
    def enabled(self) -> bool:
        if self.status is 1:
            return True
        else:
            return False

    @property
    def configs(self) -> dict:
        return self.data["configs"]

    @property
    def run_on_start(self) -> bool:
        return self.data["configs"]["run_on_start"]

    @property
    def run_on_start_forced(self) -> bool:
        return self.data["configs"]["run_on_start_forced"]

    @property
    def description(self) -> str:
        return self.data["configs"]["description"]

    @property
    def allow_intents(self) -> bool:
        return self.data["configs"]["allow_intents"]

    @property
    def conditions(self) -> dict:
        return self.data["conditions"]

    @property
    def triggers(self) -> dict:
        return self.data["triggers"]

    @property
    def actions(self) -> dict:
        return self.data["actions"]

    def scene_init(self, **kwargs):
        self.scene_templates = {}

        # Tracks if the scene is currently running or now.
        self.run_state = "stopped"  # stopped, running, stopping

        self.validate_scene()
        # for action_id, action in self.actions.items():
        #     if action["action_type"] == "template":
        #         self.scene_templates[f"{self.node_id}_{action_id}"] = self._Template.new(action["template"])

    def _started_(self, **kwargs):
        """
        Checks if the current state needs to be run when the gateway starts up.

        :param kwargs:
        :return:
        """
        try:
            if self.data["configs"]["run_on_start"] is False:
                return
        except:
            return

    def validate_scene(self, data: Optional[dict] = None):
        """ Validates the scene (node.data). Removes attributes that are not allowed. """
        validate_only = False
        if data is None:
            data = self.data
            validate_only = True

        for field in SCENE_DATA_COMPONENTS:
            if field not in data or isinstance(data[field], dict) is False:
                data[field] = {}

        if "allow_intents" not in data["configs"]:
            data["configs"]["allow_intents"] = True
        if isinstance(data["configs"]["allow_intents"], bool) is False:
            data["configs"]["allow_intents"] = is_true_false(data["configs"]["allow_intents"])
        if "description" not in data["configs"]:
            data["configs"]["description"] = self.label
        if "run_on_start" not in data["configs"]:
            data["configs"]["run_on_start"] = False
        if isinstance(data["configs"]["run_on_start"], bool) is False:
            data["configs"]["run_on_start"] = is_true_false(data["configs"]["run_on_start"])
        if "run_on_start_forced" not in data["configs"]:
            data["configs"]["run_on_start_forced"] = False
        if isinstance(data["configs"]["run_on_start_forced"], bool) is False:
            data["configs"]["run_on_start_forced"] = is_true_false(data["configs"]["run_on_start_forced"])

        for action_id, action in data["actions"].items():
            self.validate_action(action_id, action, validate_only=validate_only)

        return self.sort_actions(data)

    def validate_action(self, action_id, action, validate_only: Optional[bool] = None):
        if validate_only is None:
            validate_only = False
        if "action_type" not in action:
            raise KeyError("Scene action requires key: action_type")
        if "weight" not in action:
            raise KeyError("Scene action requires key: weight")
        try:
            action["weight"] = int(action["weight"])
        except:
            raise ValueError(f"Scene action key 'weight' must be an integer.")

        action_type = action["action_type"]

        action["action_id"] = action_id
        if action_type == "device":
            device = self._Devices[action["device_machine_label"]]
            command = self._Commands[action["command_machine_label"]]
            action["device_machine_label"] = device.machine_label
            action["command_machine_label"] = command.machine_label
            # This fancy inline just removes None and "" values.
            action["inputs"] = {k: v for k, v in action["inputs"].items() if v}

        elif action_type == "pause":
            action["duration"] = action["duration"]

        elif action_type == "scene":
            action["scene_machine_label"] = action["scene_machine_label"]
            action["scene_action"] = action["scene_action"]

        elif action_type == "template":
            template_action = self._Template.new(action["template"])
            if validate_only is False:
                self.scene_templates[action_id] = template_action
                self.scene_templates[action_id].ensure_valid()
            action["description"] = action["description"]
            action["template"] = action["template"]

        elif action_type in self._Scenes.additional_scene_actions:
            action_data = self.additional_scene_actions[action_type]["validate_scene_action"](self, action)
            action_data["action_type"] = action_type
            action_data["action_id"] = action_id
            action.clear()
            action.update(action_data)
        else:
            raise YomboWarning("Invalid scene action type.")

    @inlineCallbacks
    def delete(self, session):
        results = yield self._Scenes.delete(self.node_id, session=session)
        return results

    @inlineCallbacks
    def enable(self, session):
        results = yield self._Scenes.enable(self.node_id, session=session)
        return results

    def disable(self, session):
        results = self._Scenes.disable(self.node_id, session=session)
        return results

    def start(self, forced: Optional[bool] = None, **kwargs):
        """
        Trigger a scene to start.  Not to be confused with _start_.

        :param forced: If True, skips the conditional check(s).
        :param kwargs:
        :return:
        """
        logger.debug("Scene '{label}' is starting.", label=self.label)
        if self.status != 1:
            # lib::scenes::logger::cannot_start_disabled_scene
            logger.debug("Scene '{label}' is not enabled, cannot start.", label=self.label)
            raise YomboWarning("Scene is disabled.")

        if self.run_state == "running":
            # lib::scenes::logger::scene_already_running
            logger.debug("Scene '{label}' is already running, cannot start.", label=self.label)
            raise YomboWarning("Scene is already running.")

        if self.run_state == "stopping":
            # lib::scenes::logger::cannot_start_while_stopping
            logger.debug("Scene '{label}' is currently stopping, cannot start.", label=self.label)
            raise YomboWarning("Scene is still stopping.")

        if forced is not True:
            if self.check_conditions_for_start() is False:
                return

        self.run_state = "running"
        # Called later to handle any long running tasks.
        reactor.callLater(0.0001, self.do_start, **kwargs)
        return True

    def check_conditions_for_start(self):
        """
        Checks the scene's conditions to see if it can be started.
        :return:
        """
        # Implemented later.
        return True

    @inlineCallbacks
    def do_start(self, **kwargs):
        """
        Starts the scene.
        Performs the actual trigger. It's wrapped here to handle any requested delays.

        :param scene:
        :param kwargs:
        :return:
        """
        logger.debug("Scene '{label}' is now running.", label=self.label)
        actions = self.data["actions"]
        self._Scenes.trigger_monitor("scene",
                                    scene=self,
                                    name=self.machine_label,
                                    action="start")
        yield global_invoke_all("_scene_starting_",
                                called_by=self,
                                arguments={
                                    "scene_id": self.node_id,
                                    "scene": self,
                                    }
                                )

        logger.info("Scene is starting: {label}", label=self.label)

        for action_id, action in actions.items():
            action_type = action["action_type"]

            if action_type == "device":
                device = self._Devices[action["device_machine_label"]]
                logger.info("Scene is firing {label}, device: {device}", label=self.label, device=device.label)
                command = self._Commands[action["command_machine_label"]]
                device.command(command=command,
                               auth_id=self._Users.system_user,
                               control_method="scene",
                               inputs=action["inputs"],
                               **kwargs)

            elif action_type == "pause":
                final_duration = 0
                loops = 0
                sleep_duration = action["duration"]
                if sleep_duration < 6:
                    final_duration = sleep_duration
                    loops = 1
                else:
                    loops = int(round(sleep_duration/5))
                    final_duration = sleep_duration / loops
                for current_loop in range(loops):
                    yield sleep(final_duration)
                    if self.run_state != "running":  # a way to kill this trigger
                        self.run_state = "stopped"
                        return False

            elif action_type == "scene":
                local_scene = self._Scenes.get(action["scene_machine_label"])
                scene_action = action["scene_action"]
                if scene_action == "enable":
                    self.enable(local_scene.scene_id)
                elif scene_action == "disable":
                    self.disable(local_scene.scene_id)
                elif scene_action == "start":
                    try:
                        self.start(local_scene.scene_id)
                    except Exception:  # Gobble everything up..
                        pass
                elif scene_action == "stop":
                    try:
                        self.stop(local_scene.scene_id)
                    except Exception:  # Gobble everything up..
                        pass

            elif action_type == "template":
                try:
                    yield self.scene_templates[action_id].render(
                        {"current_scene": self}
                    )
                except Exception as e:
                    logger.warn("-==(Warning: Scenes library had trouble with template==-")
                    logger.warn("Input template:")
                    logger.warn("{template}", template=action["template"])
                    logger.warn("---------------==(Traceback)==--------------------------")
                    logger.warn("{trace}", trace=traceback.format_exc())
                    logger.warn("--------------------------------------------------------")

                    logger.warn("Scene had trouble running template: {message}", message=e)

            elif action_type in self._Scenes.additional_scene_actions:
                self._Scenes.additional_scene_actions[action_type]["handle_trigger_callback"](self, action)

            if self.run_state != "running":  # a way to kill this trigger
                self.run_state = "stopped"
                return False

        self.run_state = "stopped"

    def stop(self, scene_id, **kwargs):
        """
        Stop a currently running scene.

        :param scene_id:
        :param kwargs:
        :return:
        """
        if self.run_state == "stopped":
            return self.run_state
        if self.run_state == "running":
            self.run_state = "stopping"
        reactor.callLater(0.001, global_invoke_all,
                                 "_scene_stopping_",
                                 called_by=self,
                                 arguments={
                                     "scene_id": self.node_id,
                                     "scene": self,
                                     }
                          )

        self._Scenes.trigger_monitor("scene",
                                    scene=self,
                                    name=self.machine_label,
                                    action="stop")
        return self.run_state

    def sort_actions(self, data: Optional[dict] = None) -> dict:
        """ Re-sorts all the actions in order by weight. It also updates the weights to make them more sane. """
        if data is None:
            data = self.data

        actions = deepcopy(data["actions"])
        ordered_actions = dict(sorted(actions.items(), key=lambda i: i[1]["weight"]))
        weight = 20
        for action_id, action in ordered_actions.items():
            data["actions"][action_id]["weight"] = weight
            action["weight"] = weight
            weight += 20
        return data

    def get_action(self, action_id: Optional[str] = None):
        """ Gets the scene actions or a single action id. """
        if action_id is None:
            return self.data["actions"]
        if action_id not in self.data["actions"]:
            raise KeyError(f"'Action id '{action_id}' not found in scene ({self.node_id}) '{self.label}'.")
        return self.data["actions"][action_id]

    def edit(self, label=None, machine_label=None, description=None, status=None, allow_intents=None):
        """
        Edit various scene attributes. This anti-pythonic due to syncing back to to yombo api and the database.

        :param scene_id:
        :param label:
        :param machine_label:
        :param description:
        :param status:
        :return:
        """
        if label is not None and machine_label is not None:
            self._Scenes.check_duplicate_scene(label, machine_label, self.node_id)

        updates = {}
        if label is not None:
            updates["label"] = label
        if machine_label is not None:
            updates["machine_label"] = label
        if description is not None:
            self.data["configs"]["description"] = description
        if status is not None:
            updates["status"] = 1 if is_true_false(status, only_bool=True) else 0
        if allow_intents is not None:
            self.data["configs"]["allow_intents"] = allow_intents

        self.update(updates)
        reactor.callLater(0.001, global_invoke_all,
                                 "_scene_edited_",
                                 called_by=self,
                                 arguments={
                                     "scene_id": self.node_id,
                                     "scene": self,
                                     }
                          )

    def add_action(self, data: dict):
        """
        Add new scene item.

        :param scene_id:
        :param kwargs:
        :return:
        """
        action_id = random_string(length=15)
        self.validate_action(action_id, data)
        action_type = data["action_type"]
        if "weight" not in data:
            data["weight"] = (len(self.data["actions"]) + 1) * 20
        self.data["actions"][action_id] = data

        #
        #
        # if action_type == "device":
        #     device = self._Devices[data["device_machine_label"]]
        #     command = self._Commands[data["command_machine_label"]]
        #     # This fancy inline just removes None and "" values.
        #     data["inputs"] = {k: v for k, v in data["inputs"].items() if v}
        #
        #     self.data["actions"][action_id] = {
        #         "action_id": action_id,
        #         "action_type": "device",
        #         "device_machine_label": device.machine_label,
        #         "command_machine_label": command.machine_label,
        #
        #         # This fancy inline just removes None and "" values.
        #         "inputs": {k: v for k, v in data["inputs"].items() if v},
        #         "weight": data["weight"],
        #     }
        #
        # elif action_type == "pause":
        #     self.data["actions"][action_id] = {
        #         "action_id": action_id,
        #         "action_type": "pause",
        #         "duration": data["duration"],
        #         "weight": data["weight"],
        #     }
        #
        # elif action_type == "scene":
        #     self.data["actions"][action_id] = {
        #         "action_id": action_id,
        #         "action_type": "scene",
        #         "scene_machine_label": data["scene_machine_label"],
        #         "scene_action": data["scene_action"],
        #         "weight": data["weight"],
        #     }
        #
        # elif action_type == "template":
        #     self.scene_templates[action_id] = self._Template.new(data["template"])
        #     self.scene_templates[action_id].ensure_valid()
        #     self.data["actions"][action_id] = {
        #         "action_id": action_id,
        #         "action_type": "template",
        #         "description": data["description"],
        #         "template": data["template"],
        #         "weight": data["weight"],
        #     }
        #
        # elif action_type in self._Scenes.additional_scene_actions:
        #     # If here, then the scene capabilities have been extended. Now, ask that module to
        #     # validate the incoming data itself.
        #     action_data = self.additional_scene_actions[action_type]["validate_scene_action"](self, data)
        #     action_data["action_id"] = action_id
        #     action_data["action_type"] = action_type
        #     self.data["actions"][action_id] = action_data
        #
        # else:
        #     raise KeyError("Invalid scene action type.")

        self.sort_actions()
        self.on_change()
        reactor.callLater(0.001, global_invoke_all,
                          "_scene_edited_",
                          called_by=self,
                          arguments={
                              "scene_id": self.node_id,
                              "scene": self,
                              }
                          )
        return data

    def edit_action(self, action_id, data):
        """
        Edit scene action item.

        :param action_id:
        :param data:
        :return:
        """
        self.validate_action(action_id, data)
        self.data["actions"][action_id] = data
        self.sort_actions()
        self.on_change()
        reactor.callLater(0.001, global_invoke_all,
                          "_scene_edited_",
                          called_by=self,
                          arguments={
                              "scene_id": self.node_id,
                              "scene": self,
                          }
                          )

    def delete_action(self, action_id: str):
        """
        Delete a scene action.

        :param action_id:
        :return:
        """
        if action_id in self.data["actions"]:
            del self.data["actions"][action_id]

        self.sort_actions()
        reactor.callLater(0.001, global_invoke_all,
                          "_scene_edited_",
                          called_by=self,
                          arguments={
                              "scene_id": self.node_id,
                              "scene": self,
                              }
                          )

    def move_action_down(self, scene_id, action_id):
        """
        Move an action down.

        :param scene_id:
        :param action_id:
        :return:
        """
        action = self.data["actions"][action_id]
        action["weight"] += 21
        self.sort_actions(scene_id)
        reactor.callLater(0.001, global_invoke_all,
                          "_scene_edited_",
                          called_by=self,
                          arguments={
                              "scene_id": self.node_id,
                              "scene": self,
                              }
                          )

    def move_action_up(self, scene_id, action_id):
        """
        Move an action up.

        :param scene_id:
        :param action_id:
        :return:
        """
        action = self.data["actions"][action_id]
        action["weight"] -= 21
        self.sort_actions()
        reactor.callLater(0.001, global_invoke_all,
                          "_scene_edited_",
                          called_by=self,
                          arguments={
                              "scene_id": self.node_id,
                              "scene": self,
                              }
                          )

    def disable(self):
        """
        Disable a scene. Just marks the configuration for the scene as disabled.

        :param scene_id:
        :return:
        """
        self.status = 0
        self.on_change()
        self._Scenes.trigger_monitor("scene",
                                    scene=self,
                                    name=self.machine_label,
                                    action="disable")

    def enable(self):
        """
        Enable a scene. Just marks the configuration for the scene as disabled.

        :param scene_id:
        :return:
        """
        self.status = 1
        self.on_change()
        self._Scenes.trigger_monitor("scene",
                                    scene=self,
                                    name=self.machine_label,
                                    action="enable")

    def disable_intent(self, scene_id, **kwargs):
        """
        Disallow scene to be called via an intent.

        :param scene_id:
        :return:
        """
        self.data["configs"]["allow_intents"] = False
        self.on_change()
        self._Scenes.trigger_monitor("scene",
                                    scene=self,
                                    name=self.machine_label,
                                    action="disable_intent")

    def enable_intent(self, scene_id, **kwargs):
        """
        Allow scene to be called via an intent.

        :param scene_id:
        :return:
        """
        self.data["configs"]["allow_intents"] = True
        self.on_change()
        self._Scenes.trigger_monitor("scene",
                                    scen=self,
                                    name=self.machine_label,
                                    action="enable_intent")

    def to_dict(self, to_external: Optional[bool] = None, include_meta: Optional[bool] = None,
                incoming_data: Optional[dict] = None, filters: Optional[dict] = None):
        if include_meta is None:
            include_meta = False

        data = {
            "id": self.node_id,
            "status": self.status,
            "scene": self.data,
        }

        if include_meta is False:
            return deepcopy(data)
        else:
            return {"data": deepcopy(data), "meta": {}}

    def check_for_triggers(self, trigger_type, **kwargs):
        """
        Called by the Scenes library whenever a trigger is tripped. If any triggers matches the trigger,
        start() is called. Start() will check for conditions.

        :param trigger_type:
        :param kwargs:
        :return:
        """
        triggers = self.data["triggers"]

        if trigger_type == "device":
            device = kwargs["device"]
            for trigger in triggers:
                if trigger["trigger_type"] != "device":
                    continue
                if trigger["device_machine_label"] == device.machine_label:
                    self.start()
                    return
        elif trigger_type == "scene":
            scene = kwargs["scene"]
            for trigger in triggers:
                if trigger["trigger_type"] != "scene":
                    continue
                if trigger["scene_machine_label"] == scene.machine_label:
                    self.start()
                    return
        elif trigger_type in self._Scenes.additional_triggers:
            for trigger in triggers:
                if trigger["trigger_type"] != trigger_type:
                    continue
                if self._Scenes.additional_triggers(self, trigger) is True:
                    self.start()
                    return
        else:
            logger.info("Skipping trigger: {trigger_type}, not found.", trigger_type=trigger_type)
            return False
