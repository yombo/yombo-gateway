# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * End user documentation: `Automation Rules @ User Documentation <https://yombo.net/docs/gateway/web_interface/automation_rules>`_
  * For library documentation, see: `Automation @ Library Documentation <https://yombo.net/docs/libraries/automation>`_

The automation library provides users an easy method to setup simple automation rules that can respond to events.
The automation rules can be setup using a simple web interface. Advanced templating is also possible using the
template library.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.19.0

:copyright: Copyright 2016-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/automation.html>`_
"""
# Import python libraries
from collections import OrderedDict
from copy import deepcopy
import msgpack
import traceback
import types

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.lib.nodes import Node
from yombo.utils import is_true_false, random_string, sleep, bytes_to_unicode
from yombo.utils.datatypes import coerce_value

logger = get_logger("library.automation")

REQUIRED_RULE_FIELDS = ["trigger", "actions"]
REQUIRED_TRIGGER_FIELDS = ["template"]
REQUIRED_CONDITION_FIELDS = ["template"]
REQUIRED_ACTION_FIELDS = ["action_type"]

REQUIRED_SOURCE_FIELDS = ["platform"]
REQUIRED_FILTER_FIELDS = ["platform"]

CONDITION_TYPE_AND = "and"
CONDITION_TYPE_OR = "or"


class Automation(YomboLibrary):
    """
    Allows users to easily listen for events and trigger actions to respond to them.
    Also calls hook_automation_rules_list for additional automation rules defined by modules.
    It also implements various hooks so modules can extend the capabilites of the automation system.
    """
    triggers = {  # Place to track rules to be fired.
        "device": {},
        "scene": {},
        "state": {},
    }
    startup_items_checked = {}

    def __contains__(self, requested_rule):
        """
        Looks for an automation rule by it's ID or machine_label and returns true or false.

            >>> if "137ab129da9318" in self._Automation:

        or:

            >>> if "tv time" in self._Automation:

        :raises YomboWarning: Raised when request is malformed.
        :param requested_rule: The automation rule ID or machine_label to search for.
        :type requested_rule: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(requested_rule)
            return True
        except:
            return False

    def __getitem__(self, requested_rule):
        """
        Looks for an automation rule based on trigger ID or trigger machine_label and
        returns the automation rule.

        Attempts to find the device requested using a couple of methods.

            >>> off_cmd = self._Automation["137ab129da9318"]  #by id

        or:

            >>> off_cmd = self._Automation["bed_time"]  #by label & machine_label

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param requested_rule: The automation rule ID or machine_label to search for.
        :type requested_rule: string
        :return: A pointer to the automation rule instance.
        :rtype: instance
        """
        return self.get(requested_rule)

    def __setitem__(self, requested_rule, value):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, requested_rule):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter automation rules. """
        return self.rules.__iter__()

    def __len__(self):
        """
        Returns an int of the number of automation rules configured.

        :return: The number of automation rules configured.
        :rtype: int
        """
        return len(self.rules)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo automation library"

    def keys(self):
        """
        Returns the keys (automation rule ID's) that are configured.

        :return: A list of automation rule IDs.
        :rtype: list
        """
        return list(self.rules.keys())

    def items(self):
        """
        Gets a list of tuples representing the automation rules configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.rules.items())

    def _init_(self, **kwargs):
        """
        Get the Automation library started. Setups various dictionarys to be used.
        :return:
        """
        self.rules = {}   # Store processed / active rules
        self.active_triggers = {}  # Track various triggers - help find what rules to fire when a trigger matches.
        self.gateway_id = self._Configs.get2("core", "gwid", "local", False)

        self.action_types = {  # things that rules can do as a result if it being triggered.
            "device": {
                "label": "Device",
                "add_url": "/automation/{rule_id}/add_action_device",
                "edit_url": "/automation/{rule_id}/edit_action_device/{action_id}",
                "delete_url": "/automation/{rule_id}/delete_action_device/{action_id}",
                "down_url": "/automation/{rule_id}/move_down/{action_id}",
                "up_url": "/automation/{rule_id}/move_up/{action_id}",
            },
            "pause": {
                "label": "Pause",
                "add_url": "/automation/{rule_id}/add_action_pause",
                "edit_url": "/automation/{rule_id}/edit_action_pause/{action_id}",
                "delete_url": "/automation/{rule_id}/delete_action_pause/{action_id}",
                "down_url": "/automation/{rule_id}/move_down/{action_id}",
                "up_url": "/automation/{rule_id}/move_up/{action_id}",
            },
            "scene": {
                "label": "Scene",
                "add_url": "/automation/{rule_id}/add_action_scene",
                "edit_url": "/automation/{rule_id}/edit_action_scene/{action_id}",
                "delete_url": "/automation/{rule_id}/delete_action_scene/{action_id}",
                "down_url": "/automation/{rule_id}/move_down/{action_id}",
                "up_url": "/automation/{rule_id}/move_up/{action_id}",
            },
            "state": {
                "label": "State",
                "add_url": "/automation/{rule_id}/add_action_state",
                "edit_url": "/automation/{rule_id}/edit_action_state/{action_id}",
                "delete_url": "/automation/{rule_id}/delete_action_state/{action_id}",
                "down_url": "/automation/{rule_id}/move_down/{action_id}",
                "up_url": "/automation/{rule_id}/move_up/{action_id}",
            },
            "template": {
                "label": "Template",
                "add_url": "/automation/{rule_id}/add_action_template",
                "edit_url": "/automation/{rule_id}/edit_action_template/{action_id}",
                "delete_url": "/automation/{rule_id}/delete_action_template/{action_id}",
                "down_url": "/automation/{rule_id}/move_down/{action_id}",
                "up_url": "/automation/{rule_id}/move_up/{action_id}",
            },
        }

        self.trigger_types = {  # Type of items that can potentially trigger a rule.
            "device": {
                "label": "Device",
                "set_url": "/automation/{rule_id}/set_trigger_device",
            },
            "scene": {
                "label": "Scene",
                "set_url": "/automation/{rule_id}/set_trigger_scene",
            },
            "state": {
                "label": "State",
                "set_url": "/automation/{rule_id}/set_trigger_state",
            },
        }

        self.condition_templates = {}  # hold any templates for condition templates
        self.action_templates = {}  # hold any templates for automation rule action templates
        self.actions_running = {}  # tracks if scene is running, stopping, or stopped

    def _start_(self, **kwargs):
        """
        Loads automation rules and validates them.

        :return:
        """
        logger.debug("Automation rule starting, about to iterate rules and validate&activate.")
        self.rules = self._Nodes.search({"node_type": "automation_rules"})
        for rule_id, rule in self.rules.items():
            self.patch_automation_rule(rule)
            self.actions_running[rule_id] = "stopped"
            try:
                self.validate_and_activate_rule(rule)
            except Exception:
                pass

    def _started_(self, **kwargs):
        """
        Looks for rules that have "run_on_start' set to true.

        :return:
        """
        # device_triggered = []
        # states_triggered = []

        logger.debug("_started_: System started, about to iterate rules and look for 'run_on_start' is True.")
        for rule_id, rule in self.rules.items():
            logger.debug("_started_: Checking rule '{label}' has runstart. Type: {rule_type}",
                         label=rule.label, rule_type=rule.data['trigger'])
            run_on_start = rule.data["config"]["run_on_start"]
            if run_on_start is not True:
                continue

            trigger = rule.data["trigger"]
            trigger_type = trigger["trigger_type"]
            logger.debug("_started_: Trigger type: {trigger_type}", trigger_type=trigger_type)
            if trigger_type == "device":
                device = self.get_device(trigger["device_machine_label"])
                if trigger_type in self.startup_items_checked and \
                        device.device_id in self.startup_items_checked[trigger_type]:
                    continue

                self.trigger_monitor("device",
                                     _run_on_start=True,
                                     device=device,
                                     action="set_status")

            elif trigger_type == "state":
                state = trigger["name"]
                logger.debug("_started_: State: name: {state}", state=state)
                logger.debug("_started_: State: self.startup_items_checked: {startup_items_checked}",
                             startup_items_checked=self.startup_items_checked)

                if trigger_type in self.startup_items_checked and \
                        state in self.startup_items_checked[trigger_type]:
                    logger.debug("_started_: State skipping...{state}", state=state)
                    continue

                gateway_id = trigger["gateway_id"]
                try:
                    logger.debug("_started_: State is about to 'trigger_monitor'")
                    self.trigger_monitor("state",
                                         _run_on_start=True,
                                         key=state,
                                         value=self._States.get(state, gateway_id=gateway_id),
                                         value_full=self._States.get(state, full=True, gateway_id=gateway_id),
                                         action="set",
                                         gateway_id=gateway_id,
                                         called_by="_started_")
                except Exception as e:
                    logger.error("---------------==(Traceback)==--------------------------")
                    logger.error("Error: {e}", e=e)
                    logger.error("{trace}", trace=traceback.format_exc())
                    logger.error("--------------------------------------------------------")

        logger.debug("_started_: System started, DONE iterating rules and look for 'run_on_start' is True.")

    def automation_user_access(self, rule_id, access_type=None):
        """
        Gets all users that have access to this automation rule.

        :param access_type: If set to "direct", then gets list of users that are specifically added to this device.
            if set to "roles", returns access based on role membership.
        :return:
        """
        if access_type is None:
            access_type = "direct"

        rule = self.get(rule_id)

        if access_type == "direct":
            permissions = {}
            for email, user in self._Users.users.items():
                item_permissions = user.item_permissions
                if "automation" in item_permissions and rule.machine_label in item_permissions["automation"]:
                    if email not in permissions:
                        permissions[email] = []
                    for action in item_permissions["automation"][rule.machine_label]:
                        if action not in permissions[email]:
                            permissions[email].append(action)
            return permissions
        elif access_type == "roles":
            return {}

    def sorted(self, key=None):
        """
        Returns an OrderedDict, sorted by key.  If key is not set, then default is "label".

        :param key: Attribute contained in a automation rule to sort by.
        :type key: str
        :return: All devices, sorted by key.
        :rtype: OrderedDict
        """
        if key is None:
            key = "label"
        return OrderedDict(sorted(iter(self.rules.items()), key=lambda i: getattr(i[1], key)))

    def get(self, requested_rule=None):
        """
        Return the requested rule, if it's found.

        :param requested_rule:
        :return:
        """
        if isinstance(requested_rule, Node):
            if requested_rule.node_type == "automation_rules":
                return requested_rule
            else:
                raise YomboWarning("Must submit an automation_rule node type of automation_rules if submitting an instance")
        if requested_rule is None:
            return OrderedDict(sorted(self.rules.items(), key=lambda x: x[1].label))
        if requested_rule in self.rules:
            return self.rules[requested_rule]
        requested_rule = requested_rule.lower()
        for temp_rule_id, rule in self.rules.items():
            if rule.machine_label.lower() == requested_rule:
                return rule
        raise YomboWarning("Cannot find requested automation rule: {requested_rule}", requested_rule=requested_rule)

    def get_trigger_types(self, trigger_type=None):
        """
        Return available trigger types.

        :param trigger_type:
        :return:
        """
        if trigger_type is None:
            return OrderedDict(sorted(self.trigger_types.items(), key=lambda x: x))
        else:
            return self.trigger_types[trigger_type]

    def get_action_types(self, action_type=None):
        """
        Return available action types.

        :param action_type:
        :return:
        """
        if action_type is None:
            return OrderedDict(sorted(self.action_types.items(), key=lambda x: x))
        else:
            return OrderedDict(sorted(self.action_types[action_type].items(), key=lambda x: x))

    def get_action_items(self, rule_id, action_id=None):
        """
        Get an action item or multiple action items if action_id is not provided. The results will be returned
        ordered by weight as an OrderedDict.

        :param rule_id:
        :param action_id:
        :return:
        """
        rule = self.get(rule_id)
        if action_id is None:
            return OrderedDict(sorted(rule.data["actions"].items(), key=lambda x: x[1]["weight"]))
        else:
            try:
                return rule.data["actions"][action_id]
            except YomboWarning:
                raise YomboWarning("Unable to find requested action for the provide rule_id.")

    def ensure_data_minimum_fields(self, data):
        """
        Ensure that the autoamtion rule has the minimum required fields setup. Provides baseline sanity checks.

        :param data:
        :return:
        """
        if "trigger" not in data or isinstance(data["trigger"], dict) is False:
            data["trigger"] = {}
        if "trigger_type" not in data["trigger"]:
            data["trigger"]["trigger_type"] = None

        if "condition" not in data or isinstance(data["condition"], dict) is False:
            data["condition"] = {}

        if "actions" not in data or isinstance(data["actions"], dict) is False:
            data["actions"] = {}

        if "config" not in data or isinstance(data["config"], dict) is False:
            data["config"] = {}
        config = data["config"]
        if "enabled" not in config:
            config["enabled"] = True
        if "run_on_start" not in config:
            config["run_on_start"] = True
        else:
            config["run_on_start"] = is_true_false(config["run_on_start"])

    def validate_and_activate_rule(self, rule, complete_validation=None):
        """
        Validate and activate a rule.

        :param rule: A dictionary containing the rule to add. Must have "trigger" and "actions", with an
          optional "conditions" section.
        :type rule: Node
        :return:
        """
        if complete_validation is None:
            complete_validation = True
        rule.is_valid = False
        rule.is_valid_message = "Validation starting"
        if rule.status == 0:
            rule.status = 1
        data = rule.data
        try:
            self.ensure_data_minimum_fields(data)
        except Exception as e:
            logger.debug("validate_and_activate_rule got exception during ensure_data_minimum_fields: {e}", e)

        if data["trigger"]["trigger_type"] is None:
            rule.is_valid_message = "No trigger type."
            raise YomboWarning("Trigger doesn't have any trigger type defined")
        if data["trigger"]["trigger_type"] not in self.trigger_types:
            logger.info("Trigger type ({trigger_type}) doesn't exist as a possible trigger trigger type.",
                        trigger_type=data["trigger"]["trigger_type"])
            rule.is_valid_message = "Invalid trigger type."
            raise YomboWarning("Rule trigger doesn't have a valid trigger type.")

        if "condition" in data and "template" in data["condition"]:
            condition = data["condition"]
            if complete_validation:
                self.condition_templates[rule.rule_id] = self._Template.new(condition["template"])
            try:
                self.condition_templates[rule.rule_id].ensure_valid()  # this will raise YomboWarning if invalid.
            except YomboWarning as e:
                rule.is_valid_message = f"Condition template is invalid: {e.message}"
                raise YomboWarning(f"Automation rule condition has in invalid template: {e.message}")
        try:
            for action_id, action in data["actions"].items():
                self.validate_rule_action_item(rule, action, complete_validation)
        except Exception as e:
            rule.is_valid_message = f"Problem with automation rule: {e}"
            raise YomboWarning(f"Automation rule has invalid action: {e}")

        if len(data["actions"]) == 0:
            rule.is_valid_message = "Rule has no actions."
            raise YomboWarning("Rule has no actions. Disabling.")

        logger.debug("Automation rule, after basic checks: {rule}", rule=rule.data)

        if complete_validation:
            self.setup_rule_trigger(rule, data["trigger"])
        rule.is_valid = True
        rule.is_valid_message = "Automation rule is ready."
        return True

    def validate_rule_action_item(self, rule, action, complete_validation=None):
        """
        Validates a single action from a rule.

        :param rule:
        :param action:
        :param complete_validation:
        :return:
        """
        if complete_validation is None:
            complete_validation = True

        if not all(section in action for section in REQUIRED_ACTION_FIELDS):
            raise YomboWarning(f"Rule '{rule.label}': Action item is missing a required field.")
            
        action_type = action["action_type"]
        if action_type not in self.action_types:
            logger.info("Action type ({action_type}) doesn't exist as a possible trigger action type.",
                        action_type=action["action_type"])
            raise YomboWarning(f"Rule '{rule.label}': Action item has invalid action type: {action_type}")

        if action_type == "device":
            if not all(section in action for section in ["device_machine_label", "command_machine_label"]):
                raise YomboWarning(f"Rule '{rule.label}': Action type 'device' is missing a required field.")
            self.get_device(action["device_machine_label"])
            if "inputs" not in action:
                action["inputs"] = {}

        elif action_type == "pause":
            if not all(section in action for section in ["duration"]):
                raise YomboWarning(f"Rule '{rule.label}': Action type 'pause' is missing field 'duration'.")

        elif action_type == "scene":
            if not all(section in action for section in ["scene_machine_label", "scene_action"]):
                raise YomboWarning(f"Rule '{rule.label}': Action type 'scene' is missing a required field.")
            if action["scene_action"] not in ["enable", "disable", "start", "stop"]:
                raise YomboWarning(f"Rule '{rule.label}': Action device has ")
            try:
                self._Scenes.get(action["scene_machine_label"])
            except KeyError as e:
                raise YomboWarning("Cannot find requested scene by it's id or machine_label.")

        elif action_type == "state":
            if not all(section in action for section in ["name", "value", "gateway_id", "value_type"]):
                raise YomboWarning(f"Rule '{rule.label}': Action type 'state' is missing a required field.")

        elif action_type == "template":
            if not all(section in action for section in ["template"]):
                raise YomboWarning(f"Rule '{rule.label}': Action 'template' is missing field 'template'.")
            if complete_validation:
                try:
                    self.action_templates[f"{rule.rule_id}_{action['action_id']}"] = \
                        self._Template.new(action["template"])
                except Exception as e:
                    raise YomboWarning(f"Action type 'template' does not have a valid template: {e}")
            try:
                self.action_templates[f"{rule.rule_id}_{action['action_id']}"].ensure_valid()
            except YomboWarning as e:
                logger.info("Rule '{label} has invalid action template: {reason}",
                            label=rule.label, reason=e.message)
                raise

        else:
            raise YomboWarning(f"Invalid action type ({action_type}) for rule '{rule.label}'.")

    def get_device(self, machine_label):
        """
        Get a yombo device. Throws YomboWarning exception if one isn't found.

        :param machine_label:
        :return:
        """
        try:
            return self._Devices.get(machine_label)
        except KeyError:
            raise YomboWarning("Device doesn't exist.")

    def setup_rule_trigger(self, rule, trigger):
        """
        Adds an automation rule trigger to be monitored. Other libraries will call
        trigger_monitor() whenever a value changes.

        :param rule:
        :param trigger:
        :return:
        """
        rule_id = rule.rule_id
        if rule_id in self.triggers:
            del self.triggers_by_rule[rule_id]

        for local_trigger_type, monitored_trigger in self.triggers.items():
            if rule_id in monitored_trigger:
                del self.triggers[local_trigger_type][rule_id]

        trigger_type = trigger["trigger_type"]
        if trigger_type not in self.trigger_types:
            logger.info("Action type ({action_type}) doesn't exist as a possible trigger action type.",
                        action_type=trigger["trigger_type"])
            raise YomboWarning(f"Rule '{rule.label}': trigger has invalid trigger type: {trigger_type}")

        if trigger_type == "device":
            if not all(section in trigger for section in ["device_machine_label"]):
                raise YomboWarning(f"Rule '{rule.label}': trigger is missing a required field.")
            device = self.get_device(trigger["device_machine_label"])
            self.triggers["device"][rule_id] = {
                "device_machine_label": device.machine_label
            }

        elif trigger_type == "state":
            if not all(section in trigger for section in ["name", "value", "value_type", "gateway_id"]):
                raise YomboWarning(f"Rule '{rule.label}': Trigger is missing a required field.")
            if "value" not in trigger:
                trigger["value"] = None
            self.triggers["state"][rule_id] = {
                "name": trigger["name"],
                "value": trigger["value"],
                "value_type": trigger["value_type"],
                "gateway_id": trigger["gateway_id"],
            }

        elif trigger_type == "scene":
            if not all(section in trigger for section in ["scene_machine_label", "scene_action"]):
                raise YomboWarning(
                    "Rule '{label}': Trigger is missing a required field: scene_machine_label or scene_action",
                    label=rule.label)
            self.triggers["scene"][rule_id] = {
                "scene_machine_label": trigger["scene_machine_label"],
                "scene_action": trigger["scene_action"],
            }

    def trigger_monitor(self, trigger_type, _run_on_start=None, source=None, **kwargs):
        """
        Various libraries will call this when something happens to see if an automation rule
        needs to be triggered.

        :param trigger_type:
        :param kwargs:
        :return:
        """
        if hasattr(self, '_Loader') is False:
            return
        run_phase_name, run_phase_int = self._Loader.run_phase
        if run_phase_int < 1400:  # 'modules_preload' is when we start processing automation triggers.
            return
        if trigger_type not in self.startup_items_checked:
            self.startup_items_checked[trigger_type] = []
        if "called_by" not in kwargs:
            kwargs["called_by"] = "trigger_monitor"
        template_variables = {
            "trigger": {
                "type": trigger_type,
            }
        }
        logger.debug("Trigger_monitor started: {trigger_type}", trigger_type=trigger_type)
        if trigger_type == "device":
            device = kwargs["device"]
            if device.device_id not in self.startup_items_checked[trigger_type]:
                self.startup_items_checked[trigger_type].append(device.device_id)

            template_variables["trigger"]["device"] = device
            for rule_id, trigger in self.triggers["device"].items():
                rule = self.get(rule_id)
                if _run_on_start is True and rule.data["config"]["run_on_start"] is not True:
                    continue
                if trigger["device_machine_label"] == device.machine_label:
                    logger.debug("Scheduling device rule to run: {label}", label=rule.label)
                    reactor.callLater(0.001, self.run_rule, rule_id, template_variables, **kwargs)

        elif trigger_type == "scene":
            scene = kwargs["scene"]
            if scene.scene_id not in self.startup_items_checked[trigger_type]:
                self.startup_items_checked[trigger_type].append(scene.scene_id)
            template_variables["trigger"]["scene"] = scene
            template_variables["trigger"]["action"] = kwargs["action"]
            for rule_id, trigger in self.triggers["scene"].items():
                rule = self.get(rule_id)
                if trigger["scene_machine_label"] == scene.machine_label and trigger["scene_action"] == kwargs["action"]:
                    logger.debug("Scheduling scene rule to run: {label}", label=rule.label)
                    reactor.callLater(0.001, self.run_rule, rule_id, template_variables, **kwargs)

        elif trigger_type == "state":
            name = kwargs["key"]
            if name not in self.startup_items_checked[trigger_type]:
                self.startup_items_checked[trigger_type].append(name)
            gateway_id = kwargs["gateway_id"]
            template_variables["trigger"]["name"] = kwargs["key"]
            template_variables["trigger"]["value"] = kwargs["value"]
            template_variables["trigger"]["value_full"] = kwargs["value_full"]
            for rule_id, trigger in self.triggers["state"].items():
                rule = self.get(rule_id)
                if _run_on_start is True and rule.data["config"]["run_on_start"] is not True:
                    continue
                if trigger["name"] == name and trigger["gateway_id"] == gateway_id:
                    value_type = trigger["value_type"]
                    # if trigger["value"] == "" or trigger["value"] is None:
                    #     reactor.callLater(0.001, self.run_rule, rule_id, template_variables, **kwargs)
                    #     continue
                    trigger_value = deepcopy(trigger["value"])
                    if value_type == "string":
                        value = coerce_value(kwargs["value"], "string")
                        trigger_value = coerce_value(trigger_value, "string")
                    elif value_type == "integer":
                        try:
                            value = coerce_value(kwargs["value"], "int")
                            trigger_value = coerce_value(trigger_value, "int")
                        except Exception:
                            logger.info("Trigger monitor couldn't force state value to int.")
                            continue

                    elif value_type == "float":
                        try:
                            value = coerce_value(kwargs["value"], "float")
                            trigger_value = coerce_value(trigger_value, "float")
                        except Exception:
                            logger.info("Trigger monitor couldn't force state value to float.")
                            continue

                    elif value_type == "boolean":
                        try:
                            value = coerce_value(is_true_false(kwargs["value"]), "bool")
                            trigger_value = coerce_value(is_true_false(trigger_value), "bool")
                        except Exception:
                            logger.info("Trigger monitor couldn't force state value to bool.")
                            continue

                    if value_type == "any" or trigger_value == value:
                        logger.info("Scheduling state rule to run: {label}", label=rule.label)
                        reactor.callLater(0.001, self.run_rule,
                                          rule_id, template_variables, **kwargs)

    @inlineCallbacks
    def run_rule(self, rule_id, template_variables=None, **kwargs):
        """
        Called when a rule should fire.

        :param rule_id:
        :param kwargs:
        :return:
        """
        # if "called_by" in kwargs:
        #     print("run_rule called by: %s" % kwargs["called_by"])
        rule = self.rules[rule_id]
        logger.debug("Rule is about to start: {label}", label=rule.label)
        if rule_id in self.actions_running:
            if self.actions_running[rule_id] in ("running", "stopping"):
                logger.debug("Rule is stopping since it's already running: {label}", label=rule.label)
                return False  # already running
        self.actions_running[rule_id] = "running"

        if template_variables is None:
            template_variables = {}
        template_variables["current_rule"] = rule

        data = rule.data
        self.validate_and_activate_rule(rule)  # check everything before firing. Something may have changed.
        if rule.is_valid is False:
            logger.debug("Rule is stopping since it's not valid: {label}", label=rule.label)
            return False

        if len(data["condition"]) > 0:
            try:
                condition_results = yield self.condition_templates[rule_id].render(template_variables)
                condition_results = condition_results.strip()
            except Exception as e:
                logger.warn("-==(Warning: Automation library had trouble with template==-")
                logger.warn("Input template:")
                logger.warn("{template}", template=data["condition"]["template"])
                logger.warn("---------------==(Traceback)==------------------------------")
                logger.warn("{trace}", trace=traceback.format_exc())
                logger.warn("------------------------------------------------------------")
                logger.warn("Template processing error: {message}", message=e)
            condition_results_bool = is_true_false(condition_results)
            if condition_results_bool is None:
                logger.warn("Condition template for rule '{label}' must return true/false, or on/off, or 1/0. Returned invalid results: {results}.",
                            rule.label, condition_results)
            elif condition_results_bool is not True:
                logger.debug("Stopping rule due to condition is false: {label}", label=rule.label)
                return

        action_items = self.get_action_items(rule_id)
        logger.debug("Rule is firing {label} action:", label=rule.label)
        for action_id, action in action_items.items():
            action_type = action["action_type"]
            if action_type not in self.action_types:
                logger.info("Action type ({action_type}) doesn't exist as a possible trigger action type.",
                            action_type=action["action_type"])
                rule.is_valid = False
                raise YomboWarning(f"Rule '{rule.label}': Action has invalid action type: {action_type}")


            if action_type == "device":
                device = self._Devices[action["device_machine_label"]]
                command = self._Commands[action["command_machine_label"]]
                device.command(cmd=command,
                               auth=self._Users.system_user,
                               control_method="automation",
                               inputs=action["inputs"],
                               **kwargs)

            elif action_type == "pause":
                duration = action["duration"]
                if duration < 6:
                    final_duration = duration
                    loops = 1
                else:
                    loops = int(round(duration/5))
                    final_duration = duration / loops
                for current_loop in range(loops):
                    yield sleep(final_duration)
                    if self.actions_running[rule_id] != "running":  # a way to kill this trigger
                        self.actions_running[rule_id] = "stopped"
                        return False

            elif action_type == "scene":
                local_scene = self._Scenes.get(action["scene_machine_label"])
                scene_action = action["scene_action"]
                if scene_action == "enable":
                    self._Scenes.enable(local_scene.scene_id)
                elif scene_action == "disable":
                    self._Scenes.disable(local_scene.scene_id)
                elif scene_action == "start":
                    try:
                        self._Scenes.start(local_scene.scene_id)
                    except Exception as e:  # Gobble everything up..
                        pass
                elif scene_action == "stop":
                    try:
                        self._Scenes.stop(local_scene.scene_id)
                    except Exception as e:  # Gobble everything up..
                        pass

            elif action_type == "state":
                self._States.set(action["name"], action["value"], source=self)

            elif action_type == "template":
                try:
                    yield self.action_templates[f"{rule.rule_id}_{action['action_id']}"].render(
                        template_variables
                    )
                except Exception as e:
                    logger.warn("-==(Warning: Automation library had trouble with template==-")
                    logger.warn("Input template:")
                    logger.warn("{template}", template=self.action_templates[f"{rule.rule_id}_{action['action_id']}"])
                    logger.warn("---------------==(Traceback)==------------------------------")
                    logger.warn("{trace}", trace=traceback.format_exc())
                    logger.warn("------------------------------------------------------------")
                    logger.warn("Template processing error: {message}", message=e)

            if self.actions_running[rule_id] != "running":  # a way to kill this trigger
                self.actions_running[rule_id] = "stopped"
                return False

        self.actions_running[rule_id] = "stopped"

    def stop(self, rule_id, **kwargs):
        """
        Stop a currently running action.

        :param rule_id:
        :param kwargs:
        :return:
        """
        rule = self.get(rule_id)
        if rule_id in self.actions_running and self.actions_running[rule_id] == "running":
            self.actions_running[rule_id] = "stopping"
            return True
        return False

    def check_duplicate_rule(self, label=None, machine_label=None, rule_id=None):
        """
        Checks if a new/update automation rule label and machine_label are already in use.

        :param label:
        :param machine_label:
        :param rule_id: Ignore matches for a rule_id
        :return:
        """
        if label is None and machine_label is None:
            raise YomboWarning("Must have at least label or machine_label, or both.")
        for temp_rule_id, rule in self.rules.items():
            if rule_id is not None and rule.node_id == rule_id:
                continue
            if rule.label.lower() == label.lower():
                raise YomboWarning(f"Automation rule with matching label already exists: {rule.node_id}")
            if rule.machine_label.lower() == machine_label.lower():
                raise YomboWarning(f"Automation rule with matching machine_label already exists: {rule.node_id}")

    def disable(self, rule_id, **kwargs):
        """
        Disable an automation rule. Just marks the configuration for the rule as disabled.

        :param rule_id:
        :return:
        """
        rule = self.rules.get(rule_id)
        data = rule.data
        data["config"]["enabled"] = False
        rule.on_change()

    def enable(self, rule_id, **kwargs):
        """
        Enable an automation rule. Just marks the configuration for the rule as enabled.

        :param rule_id:
        :return:
        """
        rule = self.rules[rule_id]
        data = rule.data
        data["config"]["enabled"] = True
        rule.on_change()

    @inlineCallbacks
    def add(self, label, machine_label, description, status, run_on_start):
        """
        Add new automation rule.

        :param label:
        :param machine_label:
        :param description:
        :param status:
        :param run_on_start:
        :return:
        """
        self.check_duplicate_rule(label, machine_label)
        data = {
            "config": {
                "enabled": is_true_false(status),
                "description": description,
                "run_on_start": run_on_start,
            },
        }
        new_rule = yield self._Nodes.create(label=label,
                                            machine_label=machine_label,
                                            node_type="automation_rules",
                                            data=data,
                                            data_content_type="json",
                                            gateway_id=self.gateway_id(),
                                            destination="gw",
                                            status=1)
        new_rule.rule_type = "node"
        self.patch_automation_rule(new_rule)
        self.rules[new_rule.node_id] = new_rule
        try:
            self.validate_and_activate_rule(new_rule)
        except Exception:
            pass
        return new_rule

    def edit(self, rule_id, label=None, machine_label=None, description=None, status=None, run_on_start=None):
        """
        Edit a automation rule label and machine_label.

        :param rule_id:
        :param label:
        :param machine_label:
        :param description:
        :param status:
        :param run_on_start:
        :return:
        """
        if label is not None and machine_label is not None:
            self.check_duplicate_rule(label, machine_label, rule_id)

        rule = self.get(rule_id)
        if label is not None:
            rule.label = label
        if machine_label is not None:
            rule.machine_label = machine_label
        if description is not None:
            rule.data["config"]["description"] = description
        if rule is not None:
            rule.status = is_true_false(status)
            rule.data["config"]["enabled"] = rule.status
        if run_on_start is not None:
            rule.data["config"]["run_on_start"] = run_on_start
        return rule

    @inlineCallbacks
    def delete(self, rule_id, session=None):
        """
        Deletes the automation rule. Will disappear on next restart. This allows the user to recover it.
        This marks the node to be deleted!

        :param rule_id:
        :return:
        """
        rule = self.get(rule_id)
        data = rule.data
        data["config"]["enabled"] = False
        results = yield self._Nodes.delete_node(rule.rule_id, session=session)
        return results

    @inlineCallbacks
    def duplicate_automation_rule(self, rule_id):
        """
        Duplicates an automation rule.

        :param rule_id:
        :return:
        """
        rule = self.get(rule_id)
        label = f"{rule.label} (copy)"
        machine_label = f"{rule.machine_label}_copy"
        if label is not None and machine_label is not None:
            self.check_duplicate_rule(label, machine_label, rule_id)
        new_data = bytes_to_unicode(msgpack.unpackb(msgpack.packb(rule.data)))  # had issues with deepcopy
        new_rule = yield self._Nodes.create(label=label,
                                            machine_label=machine_label,
                                            node_type="automation_rules",
                                            data=new_data,
                                            data_content_type="json",
                                            gateway_id=self.gateway_id(),
                                            destination="gw",
                                            status=1)
        self.patch_automation_rule(new_rule)
        self.rules[new_rule.node_id] = new_rule
        return new_rule

    def set_rule_trigger(self, rule_id, **kwargs):
        """
        Set the trigger for the rule.

        :param rule_id:
        :param kwargs:
        :return:
        """
        rule = self.get(rule_id)
        trigger_type = kwargs["trigger_type"]

        if trigger_type == "device":
            rule.data["trigger"] = {
                "trigger_type": "device",
                "device_machine_label": kwargs["device_machine_label"],
            }
        elif trigger_type == "state":
            value_type = kwargs["value_type"]
            if value_type == "string":
                try:
                    value = coerce_value(kwargs["value"], "string")
                except Exception:
                    raise YomboWarning("Could not force matching value to request value type of string.")

            elif value_type == "integer":
                try:
                    value = coerce_value(kwargs["value"], "int")
                except Exception:
                    raise YomboWarning("Could not force matching value to request value type of int.")

            elif value_type == "float":
                try:
                    value = coerce_value(kwargs["value"], "float")
                except Exception:
                    raise YomboWarning("Could not force matching value to request value type of float.")

            elif value_type == "boolean":
                try:
                    value = coerce_value(kwargs["value"], "bool")
                except Exception:
                    raise YomboWarning("Could not force matching value to request value type of bool.")
            else:
                value = ""

            rule.data["trigger"] = {
                "trigger_type": "state",
                "name": kwargs["name"],
                "value": value,
                "value_type": kwargs["value_type"],
                "gateway_id": kwargs["gateway_id"],
            }
        elif trigger_type == "scene":
            rule.data["trigger"] = {
                "trigger_type": "scene",
                "scene_machine_label": kwargs["scene_machine_label"],
                "scene_action": kwargs["scene_action"],
            }
        else:
            raise YomboWarning(f"Unknown trigger_type: {trigger_type}")
        try:
            self.validate_and_activate_rule(rule)
        except Exception:
            pass

        try:
            self.validate_and_activate_rule(rule)
        except Exception:
            pass

        self.setup_rule_trigger(rule, rule.data["trigger"])

    def balance_action_weights(self, rule_id):
        if rule_id not in self.rules:
            return
        rule = self.get(rule_id)
        actions = deepcopy(rule.data["actions"])
        ordered_actions = OrderedDict(sorted(actions.items(), key=lambda x: x[1]["weight"]))
        weight = 10
        for action_id, action in ordered_actions.items():
            self.rules[rule_id].data["actions"][action_id]["weight"] = weight
            weight += 10

    def set_rule_condition(self, rule_id, **kwargs):
        """
        Set's the rule's condition template.

        :param rule_id:
        :param kwargs:
        :return:
        """
        rule = self.get(rule_id)
        rule.data["condition"] = {
            "description": kwargs["description"],
            "template": kwargs["template"],
        }
        try:
            self.condition_templates[rule_id] = self._Template.new(kwargs["template"])
        except Exception as e:
            raise YomboWarning(f"Action type 'template' does not have a valid condition template: {e}")
        try:
            self.condition_templates[rule_id].ensure_valid()
        except YomboWarning as e:
            logger.info("Rule '{label} has invalid template template: {reason}",
                        label=rule.label, reason=e.message)
            raise

        try:
            self.validate_and_activate_rule(rule)
        except Exception as e:
            logger.info("Cannot enable automation rule ({label}) after adding an action: {reason}",
                        label=rule.label,
                        reason=e)
            pass

        self.balance_action_weights(rule_id)
        rule.on_change()

    def add_action_item(self, rule_id, **kwargs):
        """
        Add new action to an automation rule.

        :param rule_id:
        :param kwargs:
        :return:
        """
        rule = self.get(rule_id)
        action_type = kwargs["action_type"]
        if "weight" not in kwargs:
            kwargs["weight"] = (len(rule.data["actions"]) + 1) * 10

        action_id = random_string(length=15)
        if action_type == "device":
            device = self._Devices[kwargs["device_machine_label"]]
            command = self._Commands[kwargs["command_machine_label"]]
            # This fancy inline just removes None and "" values.
            kwargs["inputs"] = {k: v for k, v in kwargs["inputs"].items() if v}

            rule.data["actions"][action_id] = {
                "action_id": action_id,
                "action_type": "device",
                "device_machine_label": device.machine_label,
                "command_machine_label": command.machine_label,
                "inputs": kwargs["inputs"],
                "weight": kwargs["weight"],
            }

        elif action_type == "pause":
            rule.data["actions"][action_id] = {
                "action_id": action_id,
                "action_type": "pause",
                "duration": kwargs["duration"],
                "weight": kwargs["weight"],
            }

        elif action_type == "scene":
            rule.data["actions"][action_id] = {
                "action_id": action_id,
                "action_type": "scene",
                "scene_machine_label": kwargs["scene_machine_label"],
                "scene_action": kwargs["scene_action"],
                "weight": kwargs["weight"],
            }

        elif action_type == "state":
            if rule.data["trigger"]["trigger_type"] == "state" and rule.data["trigger"]["name"] == kwargs["name"]:
                raise YomboWarning("Cannot set state name where the trigger is a state that matches the same name.")
            rule.data["actions"][action_id] = {
                "action_id": action_id,
                "action_type": "state",
                "name": kwargs["name"],
                "value": kwargs["value"],
                "value_type": kwargs["value_type"],
                "gateway_id": kwargs["gateway_id"],
                "weight": kwargs["weight"],
            }

        elif action_type == "template":
            try:
                self.action_templates[f"{rule_id}_{action_id}"] = \
                    self._Template.new(kwargs["template"])
                self.action_templates[f"{rule_id}_{action_id}"].ensure_valid()
            except Exception as e:
                raise YomboWarning(f"Action type 'template' does not have a valid template: {e}")
            try:
                self.action_templates[f"{rule_id}_{action_id}"].ensure_valid()
            except YomboWarning as e:
                logger.info("Rule '{label} has invalid action template: {reason}",
                            label=rule.label, reason=e.message)
                raise

            rule.data["actions"][action_id] = {
                "action_id": action_id,
                "action_type": "template",
                "description": kwargs["description"],
                "template": kwargs["template"],
                "weight": kwargs["weight"],
            }

        else:
            raise YomboWarning("Invalid action type.")

        try:
            self.validate_and_activate_rule(rule)
        except Exception as e:
            logger.info("Cannot enable automation rule after adding action: {reason}", reason=e)
            pass

        self.balance_action_weights(rule_id)
        rule.on_change()
        return action_id

    def edit_action_item(self, rule_id, action_id, **kwargs):
        """
        Edit action.

        :param rule_id:
        :param action_id:
        :param kwargs:
        :return:
        """
        rule = self.get(rule_id)
        action = self.get_action_items(rule_id, action_id)

        action_type = action["action_type"]

        if action_type == "device":
            device = self._Devices[kwargs["device_machine_label"]]
            command = self._Commands[kwargs["command_machine_label"]]
            action["device_machine_label"] = device.machine_label
            action["command_machine_label"] = command.machine_label
            kwargs["inputs"] = {k: v for k, v in kwargs["inputs"].items() if v}
            action["inputs"] = kwargs["inputs"]
            action["weight"] = kwargs["weight"]

        elif action_type == "pause":
            action["duration"] = kwargs["duration"]
            action["weight"] = kwargs["weight"]

        elif action_type == "scene":
            action["scene_machine_label"] = kwargs["scene_machine_label"]
            action["scene_action"] = kwargs["scene_action"]
            action["weight"] = kwargs["weight"]

        elif action_type == "state":
            action["name"] = kwargs["name"]
            action["value"] = kwargs["value"]
            action["value_type"] = kwargs["value_type"]
            action["gateway_id"] = kwargs["gateway_id"]
            action["weight"] = kwargs["weight"]

        elif action_type == "template":
            self.action_templates[f"{rule_id}_{action_id}"] = self._Template.new(kwargs["template"])
            self.action_templates[f"{rule_id}_{action_id}"].ensure_valid()
            action["description"] = kwargs["description"]
            action["template"] = kwargs["template"]
            action["weight"] = kwargs["weight"]
            self.action_templates[f"{rule_id}_{action_id}"] = self._Template.new(kwargs["template"])

        else:
            raise YomboWarning("Invalid action type.")

        try:
            self.validate_and_activate_rule(rule)
        except Exception as e:
            logger.info("Cannot enable automation rule ({label}) after editing action: {reason}",
                        label=rule.label,
                        reason=e)
            pass
        self.balance_action_weights(rule_id)
        rule.on_change()

    def delete_action_item(self, rule_id, action_id):
        """
        Delete a action.

        :param rule_id:
        :param action_id:
        :return:
        """
        rule = self.get(rule_id)
        action = self.get_action_items(rule_id, action_id)
        del rule.data["actions"][action_id]
        self.balance_action_weights(rule_id)
        try:
            self.validate_and_activate_rule(rule)
        except Exception as e:
            logger.info("Cannot enable automation rule ({label}) after editing action: {reason}",
                        label=rule.label,
                        reason=e)
            pass
        self.balance_action_weights(rule_id)
        rule.on_change()
        return action

    def move_action_down(self, rule_id, action_id):
        """
        Move an action down.

        :param rule_id:
        :param action_id:
        :return:
        """
        rule = self.get(rule_id)
        action = self.get_action_items(rule_id, action_id)
        action["weight"] += 11
        self.balance_action_weights(rule_id)
        return action

    def move_action_up(self, rule_id, action_id):
        """
        Move an action up.

        :param rule_id:
        :param action_id:
        :return:
        """
        rule = self.get(rule_id)
        action = self.get_action_items(rule_id, action_id)
        action["weight"] -= 11
        self.balance_action_weights(rule_id)
        return action


    def patch_automation_rule(self, rule):
        """
        Adds additional attributes and methods to a node or rule instance.

        :param rule:
        :return:
        """
        rule.rule_id = rule.node_id
        rule._rule = self
        rule.conditions = {}
        rule._Automation = self

        @inlineCallbacks
        def delete(node, session):
            results = yield node._Automation.delete(node._node_id, session=session)
            return results

        def description(node):
            return node.data["config"]["description"]

        def disable(node, session):
            results = node._action.disable(node._node_id, session=session)
            return results

        def effective_status(node):
            if node.status == 2:
                return 2
            elif node.data["config"]["enabled"] is True:
                return 1
            else:
                return 0

        def enabled(node):
            return node.data["config"]["enabled"]

        def enable(node, session):
            results = node._Automation.enable(node._node_id)
            return results

        def stop(node, session):
            results = node._Automation.stop(node._node_id)
            return results

        rule.delete = types.MethodType(delete, rule)
        rule.description = types.MethodType(description, rule)
        rule.disable = types.MethodType(disable, rule)
        rule.effective_status = types.MethodType(effective_status, rule)
        rule.enabled = types.MethodType(enabled, rule)
        rule.enable = types.MethodType(enable, rule)
        rule.stop = types.MethodType(stop, rule)
