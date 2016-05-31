#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
.. rst-class:: floater

.. note::

  For more information see: `Automation @ Projects.yombo.net <https://projects.yombo.net/projects/modules/wiki/Automation>`_

The automation library provides users an easy method to setup simple automation rules and tasks without the need
to write a single line of code.

For developers: This library only provides the base framework. Features are actually implemented by hooks to other
libraries and modules. Developers can extend the capabilites of the automation library using modules..

Developers should the following modules for examples of implementation:

* :py:mod:`yombo.lib.automationhelpers` - Library for implementation of calling a function by automation rule.
* :py:mod:`yombo.lib.atoms` - Look near the bottom for hooks into triggers, conditions, and actions.
* :py:mod:`yombo.lib.states` - Look near the bottom for hooks into triggers, conditions, and actions.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import 3rd-party libs
import yombo.ext.hjson as hjson

# Import Yombo libraries
from yombo.core.exceptions import YomboAutomationWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger
import yombo.utils

logger = getLogger("library.automation")

#for testing...
#from pprint import pprint


REQUIRED_RULE_FIELDS = ['trigger', 'action', 'name']
REQUIRED_TRIGGER_FIELDS = ['source', 'filter']
REQUIRED_CONDITION_FIELDS = ['source', 'filter']
REQUIRED_ACTION_FIELDS = ['platform']

REQUIRED_SOURCE_FIELDS = ['platform']
REQUIRED_FILTER_FIELDS = ['platform']

CONDITION_TYPE_AND = 'and'
CONDITION_TYPE_OR = 'or'


class Automation(YomboLibrary):
    """
    Reads "automation.txt" for automation rules and parses them into rules. Also calls hook_automation_rules_list for
    additional automation rules.
    """
    def _init_(self, loader):
        self._ModDescription = "Easy Automation for everyone"
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "https://yombo.net"
        self.loader = loader

        self._rulesRaw = {}  # Used to store raw input from reading file.
        self._rulesParse = {}  # Used to store raw input from reading file.
        self.rules = {}   # Store processed / active rules
        self.active_triggers = {}  # Track various triggers - help find what rules to fire whena trigger matches.

        self.tracker = {}  # Basic tracking
        self.triggers = {}  # List of source processors
        self.filters = {}  # List of filter processors
        self.actions = {}  # List of actionprocessors

        # lets load the raw json and see if we can even parse anything.
        try:
            with yombo.utils.fopen('automation.txt', 'r') as fp_:
                self._rulesRaw = hjson.loads(fp_.read())
#                print "hjosn: %s" % hjson.loads(self._rulesRaw)
                logger.debug("automation.txt rules RAW: {rules}", rules=self._rulesRaw['rules'])
        except Exception, e:
            logger.warn("Simple automation is unable to parse 'automation.txt' file: %s." % e)
            self._rulesRaw = {}

    def _load_(self):
        pass

    def _start_(self):
        print "track - %s" % self.tracker
        pass

    def _stop_(self):
        pass

    def _unload_(self):
        pass

    def message(self, message):
        pass

    def _module_prestart_(self, **kwargs):
        """
        Implements the _module_prestart_ hook and is called before _start_ is called for all the modules.

        Implements three hooks: hook_automation_trigger, hook_automation_condition, hook_automation_action

        *hook_automation_source_list : Expects a list of source callbacks to get, check, and validate
        *hook_automation_filter_list : Expects a list of filter callbacks to validate and check against
          a library or module supports.
        *hook_automation_action : Expects a list of dictionarys containging automation action platforms
          a library or module supports.

        **Usage**:

        .. code-block:: python

           def ModuleName_automation_trigger_list(self, **kwargs):
               return [
                 { 'platform': 'atom',
                   'add_trigger_callback': callBackFunction,  # function to call to add a trigger
                   'validate_callback': callBackFunction,  # function to call to validate a source
                   'get_value_callback': callBackFunction,  # get a value
                 }
               ]

           def ModuleName_automation_filter_list(self, **kwargs):
               return [
                 { 'platform': 'basic_values',
                   'validate_callback': self.automation_condition_validation,  # validate a condition combo is possible
                   'check_callback': self.Atoms_automation_condition_check,  # perform a condition check
                 }
               ]

           def ModuleName_automation_action(self, **kwargs):
               return [
                 { 'platform': 'x10',
                   'fields': ['name', 'command']  #can be either UUID's or Machine Labels
                   'action_callback': callBackFunction  # function to call to perform an action
                   'validate_callback': callBackFunction  # function to call to validate an action
                 }
               ]

        For "automation_rules_list" hook, see the :ref:`Automation Example <automationexample>` example module.

        """
        automation_sources = yombo.utils.global_invoke_all('automation_trigger_list')
        logger.debug("message: automation_sources: {automation_sources}", automation_sources=automation_sources)
        for moduleName, item in automation_sources.iteritems():
            for vals in item:
                self.triggers[vals['platform']] = vals

        automation_filters = yombo.utils.global_invoke_all('automation_filter_list')
#        logger.info("message: automation_sources: {automation_sources}", automation_sources=automation_sources)
        for moduleName, item in automation_filters.iteritems():
            for vals in item:
                self.filters[vals['platform']] = vals
        logger.debug("filters: {filters}", filters=self.filters)

        automation_actions = yombo.utils.global_invoke_all('automation_action_list')
#        logger.info("message: automation_actions: {automation_actions}", automation_actions=automation_actions)
        for moduleName, item in automation_actions.iteritems():
            for vals in item:
                self.actions[vals['platform']] = vals

        other_rules = yombo.utils.global_invoke_all('automation_rules_list')
        for component, rules in other_rules.iteritems():
            self._rulesRaw = yombo.utils.dict_merge(self._rulesRaw, rules)

        logger.debug("rulesRaw: {rawrules}", rawrules=self._rulesRaw)
        if 'rules' not in self._rulesRaw:
            logger.warn("There are no simple automation rules!!!")
            return

        for rule in self._rulesRaw['rules']:
            self.add_rule(rule)
#        pprint(self.rules)

    def add_rule(self, rule):
        """
        Adds a rule to the self.rules.  Do not add rules directly, they must be validated before so less validation
        can happen during run time.

        :param rule: A dictionary containing the rule to add
        :type rule: dict
        :return:
        """
#       if len([k for k,v in rule['trigger'].items() if k.startswith('_')]):  # we don't like values starting with '_'.
#          continue

        # First pass - do basic checks
        logger.debug("About to add rule: {rule}", rule=rule)
        if not all(section in rule for section in REQUIRED_RULE_FIELDS):
            logger.info("Rule doesn't have required trigger fields, skipping: ({rule}) {required}",
                        rule=rule, required=REQUIRED_RULE_FIELDS)
            return False  # Doesn't have all required fields.
        if not all(section in rule['trigger'] for section in REQUIRED_TRIGGER_FIELDS):
            logger.info("Rule:'{rule}' Doesn't have required trigger fields, has: ({trigger})  Required:{required}",
                        rule=rule['name'], trigger=rule['trigger'], required=REQUIRED_RULE_FIELDS)
            return False  # Doesn't have all required fields.
        if not all(section in rule['trigger']['source'] for section in REQUIRED_SOURCE_FIELDS):
            logger.info("Rule:'{rule}' Doesn't have required trigger source fields: ({trigger}) Required:{required}",
                        rule=rule['name'], trigger=rule['trigger']['source'], required=REQUIRED_SOURCE_FIELDS)
            return False  # Doesn't have all required fields.
        if not all(section in rule['trigger']['filter'] for section in REQUIRED_FILTER_FIELDS):
            logger.info("Rule:'{rule}' Doesn't have required trigger filter fields: ({trigger})  Required:{required}",
                        rule=rule['name'], trigger=rule['trigger']['source'], required=REQUIRED_FILTER_FIELDS)
            return False  # Doesn't have all required fields.

        if 'condition' in rule:
            for item in range(len(rule['condition'])):
                if not all(section in rule['condition'][item] for section in REQUIRED_CONDITION_FIELDS):
                    logger.info("Rule:'{rule}' Doesn't have required condition fields:({condition}) Required:{required}",
                                rule=rule['name'], condition=rule['condition'][item], required=REQUIRED_CONDITION_FIELDS)
                    return False
                if not all(section in rule['condition'][item]['source'] for section in REQUIRED_SOURCE_FIELDS):
                    logger.info("Rule:'{rule}' Doesn't have required condition source fields, has: ({condition})  Required:{required}",
                                rule=rule['name'], condition=rule['condition'][item]['source'], required=REQUIRED_SOURCE_FIELDS)
                    return False
                if not all(section in rule['condition'][item]['filter'] for section in REQUIRED_FILTER_FIELDS):
                    logger.info("Rule:'{rule}' Doesn't have required condition filter fields, has: ({condition})  Required:{required}",
                                rule=rule['name'], condition=rule['condition'][item]['source'], required=REQUIRED_FILTER_FIELDS)
                    return False

        for item in range(len(rule['action'])):
            if not all(section in rule['action'][item] for section in REQUIRED_ACTION_FIELDS):
                logger.info("Rule:'{rule}' Doesn't have required action fields,  has: ({action})  Required:{required}",
                            rule=rule['name'], action=rule['action'][item], required=REQUIRED_ACTION_FIELDS)
                is_valid = False   # Doesn't have all required fields.
                return False

        rule['rule_id'] = yombo.utils.random_string(length=15)
        rule_id = rule['rule_id']

        logger.debug("Automation rule, after basic checks: {rule}", rule=rule)

        # for each rule, make sure the trigger, condition, and action checker is valid.
        if not self._check_source_platform(rule, rule['trigger']['source'], True):
            return False
        if not self._check_filter_platform(rule, rule['trigger']['filter']):
            return False

        if 'condition' in rule:
            if 'condition_type' in rule:
                if not any(section.lower() in rule['condition_type'] for section in ['and', 'or']):
                    logger.warn("Invalid condition_type: {condition_type}   Must be either 'and' or 'or. Skipping rule: {rule_name}",
                                condition_type=rule['condition_type'], rule_name=rule['name'])
                    return False
            for item in range(len(rule['condition'])):
                if not self._check_source_platform(rule, rule['condition'][item]['source']):
                    return False
                if not self._check_filter_platform(rule, rule['condition'][item]['filter']):
                    return False

        for item in range(len(rule['action'])):
            platform = rule['action'][item]['platform']
            VCB = self.actions[platform]['validate_callback']
            if not VCB(rule, rule['action'][item]):
                logger.warn("Action platform '{action_platform}' not in rule: {rule_name}. Skipping rule.",
                            action_platform=platform, rule_name=rule['name'])
                return False

        logger.info("Passed adding rule condition check....")
        add_trigger = self.triggers[rule['trigger']['source']['platform']]['add_trigger_callback']
        add_trigger(rule, condition_callback=self.automation_check_conditions)

        if rule['trigger']['source']['platform'] not in self.active_triggers:
            self.active_triggers[rule['trigger']['source']['platform']] = []
        self.active_triggers[rule['trigger']['source']['platform']].append(rule_id)
        self.rules[rule_id] = rule
#        self.rules[rule_id] = Rule(rule)

    def _check_source_platform(self, rule, source, trigger_required=False):
        """
        Help function to add_rule.  It checks to make sure a any 'source': {'platform': 'platform_name'} exists. It
        tests against self.triggers that was gathered from various modules and modules using hooks.

        :param rule: the rule
        :param source: source to check
        :param trigger_required: If a trigger is required, this is true.
        :return:
        """
        source_platform = source['platform']
        if trigger_required:
            if 'add_trigger_callback' in self.triggers[source_platform]:
                if not callable(self.triggers[source_platform]['add_trigger_callback']):
                    logger.warn("Rule '{rule}': {source_platform} doesn't have a callable trigger adder.", rule=rule['name'], source_platform=source_platform)
                    return False
            else:
                logger.warn("Rule '{rule}': {source_platform} Doesn't have a listing for a trigger adder.", rule=rule['name'], source_platform=source_platform)
                return False

        if source_platform in self.triggers:
            method = self.triggers[source_platform]['validate_callback']
            if not method(rule, rule['trigger']):
                logger.warn("Rule '{rule}': Has invalid source platform params. source_platform: {source_platform}.", rule=rule['name'], source_platform=source_platform)
                return False
        else:
            logger.warn("Rule '{rule}': Source doesn't have platform: {source_platform}", rule=rule['name'], source_platform=source_platform)
            return False
        return True

    def _check_filter_platform(self, rule, filter_):
        """
        Help function to add_rule.  It checks to make sure a any 'filter': {'platform': 'platform_name'} exists. It
        tests against self.filters that was gathered from various modules and modules using hooks.

        :param rule: the rule
        :param filter_: source to check
        :return:
        """
        filter_platform = filter_['platform']
        if filter_platform in self.filters:
            method = self.filters[filter_platform]['validate_callback']
            if not method(rule, platform=filter_platform, filter=filter_):
                logger.warn("Rule '{rule}': Has invalid filter platform params. filter_platform: {filter_platform}.", rule=rule['name'], filter_platform=filter_platform)
                return False
        else:
            logger.warn("Rule '{rule}': Filter doesn't have platform: {filter_platform}", rule=rule['name'], filter_platform=filter_platform)
            return False
        return True

    def track_trigger_basic_add(self, rule_id, platform_label, tracked_key):
        """
        A public function that modules and libraries can use to trigger rules. Used to track simple dictionary
        type items or things that can be contained in a dictionary.

        :param rule_id: Rule ID to attach trigger to
        :param platform_label: Platform being added.
        :param tracked_key: An immutable key to monitor. Usually a dictionary key.
        :return:
        """
#        logger.warn("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@adding ruleid: {rule}", rule=rule_id)
        if platform_label not in self.tracker:
            self.tracker[platform_label] = {}
        if tracked_key not in self.tracker[platform_label]:
            self.tracker[platform_label][tracked_key] = []

        self.tracker[platform_label][tracked_key].append({
            'rule_id': rule_id,
        })

    # 'atoms', 'is_light', False
    def track_trigger_check_triggers(self, platform_label, tracked_key, new_value):
        """
        Modules and libraries can call this to check for any triggers on a dictionary. Will return a list

        :param platform_label:
        :param tracked_key:
        :param new_value:
        :return:
        """
#        logger.warn("1@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@checking : {new_value}", new_value=new_value)
#        logger.warn("tracked_label: {tracked_label}", tracked_label=platform_label)
#        logger.warn("tracked_key: {tracked_key}", tracked_key=tracked_key)
#        logger.warn("trackers: {tracker}", tracker=self.tracker)
        if platform_label not in self.tracker:
            return False
        if tracked_key not in self.tracker[platform_label]:
            return False
        rule_ids = self.tracker[platform_label][tracked_key]
        if len(rule_ids) == 0:
            logger.warn("There should be rules, but found none!")
            return False
        logger.debug("found rule IDs {rule_ids}", rule_ids=rule_ids)

        # We now have at least one trigger. Check the filters and return any rule IDs.
        rules_should_fire = []
        for item in range(len(rule_ids)):
            rule_id = rule_ids[item]['rule_id']
            rule = self.rules[rule_id]
            try:
                result = self.automation_check_filter(rule_id, rule['trigger']['filter'], new_value)
                if result:
                    rules_should_fire.append(rule_id)
            except YomboAutomationWarning:
                pass

#        print "rules that should fire: %s" % rules_should_fire
        return rules_should_fire

    def track_trigger_basic_do_actions(self, rule_ids):
        for item in range(len(rule_ids)):
            self.automation_check_conditions(rule_ids[item])

    def automation_check_filter(self, rule_id, filter_, new_value):
        if not filter_['platform'] in self.filters:
            raise YomboAutomationWarning("No filter platform: %s" % filter_['platform'])
        method = self.filters[filter_['platform']]['check_callback']
        return method(self.rules[rule_id], filter=filter_, new_value=new_value)

    def automation_check_conditions(self, rule_id):
        """
        Directs the rule to the condition checker callback.

        :return:
        """
        logger.debug("doing automation_check_conditions on rule_id: {rule}", rule=rule_id)
        condition_type = 'and'

        rule = self.rules[rule_id]
        if 'condition_type' in rule:
            condition_type = rule['condition_type']

        condition_results = []
#        logger.warn("rule: {rule}", rule=rule)
        is_valid = True
        if 'condition' in rule:
            condition = rule['condition']
#            print "testing conditons: %s" % condition
            for item in range(len(condition)):
                # get value(s)
                method = self.triggers[condition[item]['source']['platform']]['get_value_callback']
                value = method(rule, condition[item]['source'])

                # check value(s)
                try:
                    result = self.automation_check_filter(rule_id, condition[item]['filter'], value)
 #                   print "result of condition check filter: %s" % result
                    condition_results.append(result)
                except YomboAutomationWarning:
                    pass

            if condition_type == 'and':
                is_valid = all(condition_results)
            else:
                is_valid = any(condition_results)

        if is_valid:
            logger.debug("Condition check passed for: {rule}", rule=self.rules[rule_id]['name'])
            return self.automation_action(rule_id)
        else:
            logger.debug("Condition check failed for: {rule}", rule=self.rules[rule_id]['name'])


    def automation_action(self, rule_id):
        """
        Directs the rule_id to the correct module/library do_action_callback function

        :param rule:
        :return:
        """
        rule = self.rules[rule_id]
        for item in range(len(rule['action'])):
            platform = rule['action'][item]['platform']
            do_action = self.actions[platform]['do_action_callback']
            do_action(rule, rule['action'][item])

        return


class Rule:
    """
    A class to contain various aspects of a rule.
    """
    def __init__(self, device, allDevices, testDevice=False):
        """
        :param device: *(list)* - A device as passed in from the devices class. This is a
            dictionary with various device attributes.
        :ivar callBeforeChange: *(list)* - A list of functions to call before this device has it's status
            changed. (Not implemented.)
        :ivar callAfterChange: *(list)* - A list of functions to call after this device has it's status
            changed. (Not implemented.)
        :ivar device_id: *(string)* - The UUID of the device.
        :ivar device_type_id: *(string)* - The device type UUID of the device.
        :type device_id: string
        :ivar label: *(string)* - Device label as defined by the user.
        :ivar description: *(string)* - Device description as defined by the user.
        :ivar enabled: *(bool)* - If the device is enabled - can send/receive command and/or
            status updates.
        :ivar pin_required: *(bool)* - If a pin is required to access this device.
        :ivar pin_code: *(string)* - The device pin number.
            system to deliver commands and status update requests.
        :ivar created: *(int)* - When the device was created; in seconds since EPOCH.
        :ivar updated: *(int)* - When the device was last updated; in seconds since EPOCH.
        :ivar lastCmd: *(dict)* - A dictionary of up to the last 30 command messages.
        :ivar status: *(dict)* - A dictionary of strings for current and up to the last 30 status values.
        :ivar deviceVariables: *(dict)* - The device variables as defined by various modules, with
            values entered by the user.
        :ivar availableCommands: *(list)* - A list of cmdUUID's that are valid for this device.
        """
        logger.debug("New device - info: {device}", device=device)

        self.Status = namedtuple('Status', "device_id, set_time, device_state, human_status, machine_status, machine_status_extra, source, uploaded, uploadable")
        self.Command = namedtuple('Command', "time, cmduuid, source")
        self.callBeforeChange = []
        self.callAfterChange = []
        self.device_id = device["id"]
        self.device_type_id = device["device_type_id"]
        self.deviceTypeLabel = device["device_type_machine_label"]
        self.label = device["label"]
        self.deviceClass = device["device_class"]
        self.description = device["description"]
        self.enabled = int(device["status"])
        self.pin_required = int(device["pin_required"])
        self.pin_code = device["pin_code"]
        self.pin_timeout = int(device["pin_timeout"])
        self.voice_cmd = device["voice_cmd"]
        self.voice_cmd_order = device["voice_cmd_order"]
        self.created = int(device["created"])
        self.updated = int(device["updated"])
        self.lastCmd = deque({}, 30)
        self.status = deque({}, 30)
        self._allDevices = allDevices
        self.testDevice = testDevice
        self.availableCommands = []
        self.deviceVariables = {'asdf':'qwer'}

    def _init_(self):
        """
        Performs items that required deferreds.
        :return:
        """
        def set_commands(commands):
            self.availableCommands = commands

        def set_variables(vars):
            self.deviceVariables = vars

        def gotException(failure):
           print "Exception : %r" % failure
           return 100  # squash exception, use 0 as value for next stage

        d = self._allDevices._Libraries['localdb'].get_commands_for_device_type(self.device_type_id)
        d.addCallback(set_commands)
        d.addErrback(gotException)

        d.addCallback(lambda ignored: self._allDevices._Libraries['localdb'].get_variables('device', self.device_id))
        d.addErrback(gotException)
        d.addCallback(set_variables)
        d.addErrback(gotException)

        if self.testDevice is False:
            d.addCallback(lambda ignored: self.load_history(35))
        return d




"""
==== stopped here ====
rules: [
  {
  name: joe
  trigger:
    type: state
    name: isDark
    value: True
  condition:
    type: state
    name: isLight #redundant, i know
    value: False
    --
    type: device
    name: porch light
    value: off
  action:
    type: device
    name: porch light
    command: on
    --
    type: device
    name: porch side light
    command: on
  }
  ]

# conditions:
# time (can use or):
condition_type: or
condition:
  type: time
  before: '4:00'
  --
  type: time
  after: '22:00'

# state
# device
# numeric_state
type: numeric_state
entity_type: device
entity_id: hallway nest (name or uuid)
# At least one of the following required
above: 17
below: 25

    def check_conditions(self, rule):
        ""
        condition is the raw value of self.rule[ruleID]
        ""


    def perform_action(self, rule):
        ""
        action is the raw value of self.rule[ruleID]
        ""
        actiondict = {}
        for item, action in rule['action'].iteritems():
            if actiondict['type'] not in actiondict:
                actiondict[action['type']] = []
            actiondict[action['type']].append(action)

        for type, action in conditionsdict.iteritems():
            do_action = self.actions[type].(action)
"""