# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For more information see:
  `Atoms @ Module Development <https://yombo.net/docs/modules/automation/>`_

The automation library provides users an easy method to setup simple automation rules and tasks without the need to
write a single line of code. It can also be extended by modules to include additional platforms. See link above for
details on extending automation rule capabilities.

The automation library also doubles as a 'macro' library. This allows rules to be called through other rules or
other means, bypassing a rule trigger and filter.

There are three steps to every rule:

1) Source - A rule must be triggered by some source. A device state changes, an internal value changes, system
   status changes, etc.
2) Filters - Rules can be filtered. For example, if a rule was triggered by some source, it can be stop from
   firing it's action if certain conditions aren't met. For example, a device source such as 'motion' is detected
   outside. But, a condition check of "is sunny" is true, then don't bother turning on the light.
3) Action - Do something. In the above example, turn on a light.

A naming convention of 'platforms' is used to direct the automation system. It's just another way of saying
'atoms, devices, and states can be used as sources'. for example, atoms, states, and devices can all be platforms
for sources, filters, and actions. A state change can trigger a rule, a state value can be a condition, and a state
can be changed as an action.

*For End Users*: It's strongly recommended to visit
`Automation @ Projects.yombo.net <https://projects.yombo.net/projects/modules/wiki/Automation>`_ for details on usage
and writing automation rules.

*For developers*: This library only provides the base framework. Features are actually implemented by hooks to other
libraries and modules. Developers can extend the capabilities of the automation library using modules.

Developers should review the following modules for examples of implementation:

* :py:mod:`yombo.lib.automationhelpers` - Implements various platforms
* :py:mod:`yombo.lib.atoms` - Look near the bottom for hooks into triggers, conditions, and actions.
* :py:mod:`yombo.lib.states` - Look near the bottom for hooks into triggers, conditions, and actions.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.10.0

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries



# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor

# Import 3rd-party libs
import yombo.ext.hjson as hjson
import yombo.ext.umsgpack as msgpack

# Import Yombo libraries
from yombo.core.exceptions import YomboAutomationWarning, YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.utils
import collections

logger = get_logger("library.automation")


# REQUIRED_RULE_FIELDS = ['trigger', 'action', 'name']
REQUIRED_RULE_FIELDS = ['action']
REQUIRED_TRIGGER_FIELDS = ['source']
REQUIRED_CONDITION_FIELDS = ['source', 'filter']
REQUIRED_ACTION_FIELDS = ['platform']

REQUIRED_SOURCE_FIELDS = ['platform']
REQUIRED_FILTER_FIELDS = ['platform']

CONDITION_TYPE_AND = 'and'
CONDITION_TYPE_OR = 'or'


class Automation(YomboLibrary):
    """
    Reads "automation.txt" for user automation rules and parses them into rules. Also calls hook_automation_rules_list
    for additional automation rules defined by modules. It also implements various hooks so modules can extend the
    capabilites of the automation system.
    """
    def _init_(self):
        """
        Get the Automation library started. Setups various dictionarys to be used.
        :return: 
        """
        self._rulesRaw = {}  # Used to store raw input from reading file.
        self._rulesParse = {}  # Used to store raw input from reading file.
        self.rules = {}   # Store processed / active rules
        self.active_triggers = {}  # Track various triggers - help find what rules to fire whena trigger matches.

        self.tracker = {}  # Registered items to track, will be checked against if a trigger check fires.
        self.sources = {}  # List of source processors
        self.filters = {}  # List of filter processors
        self.actions = {}  # List of actionprocessors

        # lets load the raw json and see if we can even parse anything.

    def _start_(self):
        """
        Loads the automation.txt file and processes any rules included.
        
        :return: 
        """
        try:
            with yombo.utils.fopen('automation.txt', 'r') as fp_:
                temp_rules = hjson.loads(fp_.read())
                self._rulesRaw = msgpack.loads(msgpack.dumps(temp_rules))  # remove ordered dict.
                # logger.debug("automation.txt rules RAW: {rules}", rules=self._rulesRaw)
        except Exception as e:
            logger.warn("Simple automation is unable to parse 'automation.txt' file: %s." % e)
            self._rulesRaw = {}
        else:
            if 'rules' in self._rulesRaw:
                for rule in self._rulesRaw['rules']:
                    rule['source'] = 'hsjon'

    @inlineCallbacks
    def _modules_prestarted_(self, **kwargs):
        """
        This function is called before the _start_ function of all modules is called.

        Calls libraries and modules to check if any additional rules should be defined. It also makes calls to see
        if the automation features are being extended, such as adding new automation platforms.

        **Hooks called**:

        * _automation_rules_list_ :  Expects a list of dictionarys containing automation rules.
        * _automation_action_list_ : Expects a list of dictionarys containing automation action platforms.
        * _automation_filter_list_ : Expects a list of filter callbacks to validate and check against
          a library or module supports.
        * _automation_source_list_ : Expects a list of source callbacks to get, check, and validate

        **Usage**:

        .. code-block:: python

           def ModuleName_automation_source_list(self, **kwargs):
               '''
               Adds additional platforms to the source platform. Creates additional rule triggers.
               '''
               return [
                 { 'platform': 'atom',
                   'validate_source_callback': self.atoms_validate_source_callback,  # validate a trigger
                   'add_trigger_callback': self.atoms_add_trigger_callback,  # function to call to add a trigger
                   'get_value_callback': self.atoms_get_value_callback,  # get a value
                 }
               ]

           def ModuleName_automation_filter_list(self, **kwargs):
               '''
               Adds additional platforms to the filters system. Allows rules to be filtered.
               '''
               return [
                 { 'platform': 'basic_values',
                   'validate_filter_callback': self.Atoms_validate_filter_callback,  # validate a condition is possible
                   'run_filter_callback': self.Atoms_run_filter_callback,  # perform a condition check
                 }
               ]

           def ModuleName_automation_action_list(self, **kwargs):
               '''
               Adds additional platforms to the action system. Allows new types of actions to be taken.
               '''
               return [
                 { 'platform': 'x10',
                   'fields': ['name', 'command']  #can be either UUID's or Machine Labels
                   'validate_action_callback': callBackFunction  # function to call to validate an action
                   'do_action_callback': callBackFunction  # function to call to perform an action
                 }
               ]

        For "automation_rules_list" hook, see the :ref:`Automation Example <automationexample>` example module.

        """
        automation_sources = yield yombo.utils.global_invoke_all('_automation_source_list_', called_by=self)
        # logger.debug("automation_sources: {automation_sources}", automation_sources=automation_sources)
        for component_name, item in automation_sources.items():
            for vals in item:
                vals['platform_source'] = component_name
                self.sources[vals['platform']] = vals
        # logger.debug("sources: {sources}", sources=self.sources)

        automation_filters = yield yombo.utils.global_invoke_all('_automation_filter_list_', called_by=self)
        # logger.debug("automation_filters: {automation_sources}", automation_sources=automation_filters)
        for component_name, item in automation_filters.items():
            for vals in item:
                vals['platform_source'] = component_name
                self.filters[vals['platform']] = vals
        # logger.debug("filters: {filters}", filters=self.filters)

        automation_actions = yield yombo.utils.global_invoke_all('_automation_action_list_', called_by=self)
#        logger.info("message: automation_actions: {automation_actions}", automation_actions=automation_actions)
        for component_name, item in automation_actions.items():
            for vals in item:
                vals['platform_source'] = component_name
                self.actions[vals['platform']] = vals

        callback_rules = yield yombo.utils.global_invoke_all('_automation_rules_list_', called_by=self)
        for component_name, component_rules in callback_rules.items():
            for rule in component_rules['rules']:
                rule['source'] = 'callbacks:%s' % component_name
                self._rulesRaw['rules'].append(rule)

        # logger.debug("rulesRaw: {rawrules}", rawrules=pprint(self._rulesRaw))
        if 'rules' not in self._rulesRaw:
            logger.warn("No automation rules found.")
            returnValue(None)

        for rule in self._rulesRaw['rules']:
            if 'run_on_start' in rule:
                rule['run_on_start'] = yombo.utils.is_true_false(rule['run_on_start'])
            if 'description' not in rule:
                    rule['description'] = ''
            self.add_rule(rule)

        # logger.debug("All active rules: {rules}", rules=self.rules)
        for source, functions in self.sources.items():
            if 'startup_trigger_callback' in functions:
                functions['startup_trigger_callback']()

    def get_action_delay(self, delay):
        """
        Used to check the 'delay' field of an action. It's used to send delayed commands. It converts strings such as
        '1m 3s', '1 hour', '6 min' into an epoch time so that the automation system can handle it. Must be a time
        in the future, any times set to the past will be disable the rule.

        :param delay: String - A string to be parsed into epoch time in the future.
        :return: Float in seconds in the future.
        """
        seconds = (float(yombo.utils.epoch_from_string(delay, True)))
        if seconds <0:
            raise YomboWarning("get_action_delay on accepts delays in the future, not the past.", 'get_action_delay', 'automationhelpers')
        return seconds

    def add_rule(self, rule):
        """
        Internal function, adds a rule to the self.rules. Do not add rules directly, they must be validated before
        so less validation can happen during run time.

        To add rules, use 'automation.txt' file or hook_automation_rules_list within a module.

        :param rule: A dictionary containing the rule to add
        :type rule: dict
        :return:
        """
        # make sure rule_id is unique. If it's a duplication, we will toss! make one if needed
        rule_is = None
        if 'rule_id' in rule:
            if rule['rule_id'] in self.rules:
                logger.warn("Duplicate rule id found, dropping it.")
                return False
            else:
                rule_id = rule['rule_id']
        else:
            rule['rule_id'] = yombo.utils.random_string(length=20)
            rule_id = rule['rule_id']

        # First pass - do basic checks
        logger.debug("About to add rule: {rule}", rule=rule)
        if not all(section in rule for section in REQUIRED_RULE_FIELDS):
            logger.info("Rule doesn't have required trigger fields, skipping: {required}",
                        rule=rule, required=REQUIRED_RULE_FIELDS)
            return False  # Doesn't have all required fields.

        # logger.debug("about to check trigger.")
        if 'trigger' in rule:
            if rule['trigger']['source']['platform'] not in self.sources:
                logger.info("Platform ({platform}) doesn't exist as a trigger.",
                        platform=rule['trigger']['source']['platform'], rule=rule, required=REQUIRED_RULE_FIELDS)
                return False
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

        # logger.debug("Rule is good past trigger checks.")
        if 'condition' in rule:
            for item in range(len(rule['condition'])):
                if not all(section in rule['condition'][item] for section in REQUIRED_CONDITION_FIELDS):
                    logger.info("Rule:'{rule}' Doesn't have required condition fields:({condition}) Required:{required}",
                                rule=rule['name'], condition=rule['condition'][item], required=REQUIRED_CONDITION_FIELDS)
                    return False
                if rule['condition'][item]['source']['platform'] not in self.sources:
                    logger.info("Platform ({platform}) doesn't exist as a source:({rule}) {required}",
                                platform=rule['condition'][item]['source']['platform'], rule=rule, required=REQUIRED_RULE_FIELDS)
                    return False
                if not all(section in rule['condition'][item]['source'] for section in REQUIRED_SOURCE_FIELDS):
                    logger.info("Rule:'{rule}' Doesn't have required condition source fields, has: ({condition})  Required:{required}",
                                rule=rule['name'], condition=rule['condition'][item]['source'], required=REQUIRED_SOURCE_FIELDS)
                    return False
                if not all(section in rule['condition'][item]['filter'] for section in REQUIRED_FILTER_FIELDS):
                    logger.info("Rule:'{rule}' Doesn't have required condition filter fields, has: ({condition})  Required:{required}",
                                rule=rule['name'], condition=rule['condition'][item]['source'], required=REQUIRED_FILTER_FIELDS)
                    return False
                if rule['condition'][item]['filter']['platform'] not in self.filters:
                    logger.info("Platform ({platform}) doesn't exist as a filter: ({rule}) {required}",
                                platform=rule['condition'][item]['filter']['platform'], rule=rule, required=REQUIRED_RULE_FIELDS)
                    return False

        # logger.debug("Rule is good past condition checks.")
        for item in range(len(rule['action'])):
            # Global settings

            # use automationhelpers.get_action_delay(action) to perform the actual work.
            # Just checking that it can be parsed during rule setup so that it can be used
            # during rule run time.
            if 'delay' in rule['action'][item]:
                try:
                    self.get_action_delay(rule['action'][item]['delay'])
                except Exception as e:
                    logger.warn("Error parsing 'delay' within action, dropping rule. Delay:{delay}. Other reasons: {e}",
                                delay=rule['action'][item]['delay'], e=e)
                    return False
            if not all(section in rule['action'][item] for section in REQUIRED_ACTION_FIELDS):
                logger.info("Rule:'{rule}' Doesn't have required action fields,  has: ({action})  Required:{required}",
                            rule=rule['name'], action=rule['action'][item], required=REQUIRED_ACTION_FIELDS)
                is_valid = False   # Doesn't have all required fields.
                return False
            if rule['action'][item]['platform'] not in self.actions:
                logger.info("Platform ({platform}) doesn't exist as an action.  ({rule})",
                            platform=rule['action'][item]['platform'], rule=rule, required=REQUIRED_RULE_FIELDS)
                return False


        logger.debug("Automation rule, after basic checks: {rule}", rule=rule)

        # for each rule, make sure the trigger, condition, and action checker is valid.
        try:
            if 'trigger' in rule:
                rule['trigger'] = self._check_returned_rule(rule['trigger'], self._check_source_platform(rule, rule['trigger'], True))
                rule['trigger'] = self._check_returned_rule(rule['trigger'], self._check_filter_platform(rule, rule['trigger']))

            if 'condition' in rule:
                if 'condition_type' in rule:
                    if not any(section.lower() in rule['condition_type'] for section in ['and', 'or']):
                        logger.warn("Invalid condition_type: {condition_type}  Must be either 'and' or 'or. Skipping rule: {rule_name}",
                                    condition_type=rule['condition_type'], rule_name=rule['name'])
                        return False
                for item in range(len(rule['condition'])):
                    try:
                        rule['condition'][item] = \
                            self._check_returned_rule(rule['condition'][item],
                                                self._check_source_platform(rule, rule['condition'][item]))
                        rule['condition'][item] = \
                            self._check_returned_rule(rule['condition'][item],
                                                self._check_filter_platform(rule, rule['condition'][item]))
                    except YomboWarning as e:
                        return False

            for item in range(len(rule['action'])):
                # make sure every rule has an "arguments" section. This will be passed to the do_action as kwargs
                if 'arguments' not in rule['action'][item]:
                    rule['action'][item]['arguments'] = {}

                platform = rule['action'][item]['platform']
                validate_action_callback_function = self.actions[platform]['validate_action_callback']
                try:
                    rule['action'][item] = self._check_returned_rule(rule['action'][item], validate_action_callback_function(rule, rule['action'][item]))
                except YomboWarning as e:
                    logger.warn("Warning: {e}", e=e)
                    return False

            # logger.debug("Passed adding rule condition check.... {rule}", rule=rule)
            logger.debug("about to add triggers....")
            if 'trigger' in rule:
                logger.debug("about to add triggers....now")
                add_trigger_callback_function = self.sources[rule['trigger']['source']['platform']]['add_trigger_callback']
                add_trigger_callback_function(rule, condition_callback=self.automation_check_conditions)

        except YomboWarning as e:
            logger.warn("Some error: {e}", e=e)
            return False

        if 'trigger' in rule:
            if rule['trigger']['source']['platform'] not in self.active_triggers:
                self.active_triggers[rule['trigger']['source']['platform']] = []
            self.active_triggers[rule['trigger']['source']['platform']].append(rule_id)
        self.rules[rule_id] = rule
#        self.rules[rule_id] = Rule(rule)

    def _check_returned_rule(self, portion, new_portion):
        if isinstance(new_portion, bool):
            if new_portion is True:
                return portion
            else:
                raise YomboWarning("Check failed in _check_returned_rule. Rule: %s" % new_portion, 110, '_check_returned_rule', 'automation')
        if isinstance(new_portion, type(None)):
            return portion

        return new_portion

    def _check_source_platform(self, rule, portion, trigger_required=False):
        """
        Help function to add_rule. It checks to make sure a any 'source': {'platform': 'platform_name'} exists. It
        tests against self.sources that was gathered from various modules and modules using hooks.

        :param rule: the rule
        :param portion: source to check
        :param trigger_required: If a trigger is required, this is true.
        :return:
        """
        source_platform = portion['source']['platform']
        if trigger_required:
            if 'add_trigger_callback' in self.sources[source_platform]:
                if not isinstance(self.sources[source_platform]['add_trigger_callback'], collections.Callable):
#                    logger.warn("Rule '{rule}': {source_platform} doesn't have a callable trigger adder.",
#  rule=rule['name'], source_platform=source_platform)
                    raise YomboWarning("'%s' doesn't have a callable trigger adder" % source_platform, 111,
                                       '_check_source_platform', 'automation')
            else:
 #               logger.warn("Rule '{rule}': {source_platform} Doesn't have a listing for a trigger adder.",
 #  rule=rule['name'], source_platform=source_platform)
                raise YomboWarning("'%s' Doesn't have a listing for a trigger adder" % source_platform, 112,
                                   '_check_source_platform', 'automation')

        if source_platform in self.sources:
            validate_source_callback_function = self.sources[source_platform]['validate_source_callback']
#            logger.warn("Rule1 '{rule}': Checking platform params. source_platform: {source_platform}.",
            #  rule=rule['name'], source_platform=source_platform)
            return validate_source_callback_function(rule, portion)
        else:
            logger.warn("Rule '{rule}': Source doesn't have platform: {source_platform}", rule=rule['name'],
                        source_platform=source_platform)
            raise YomboWarning("Platform '%s' not found for source portion of rule" % source_platform, 113,
                               '_check_source_platform', 'automation')

    def _check_filter_platform(self, rule, portion):
        """
        Help function to add_rule.  It checks to make sure a any 'filter': {'platform': 'platform_name'} exists. It
        tests against self.filters that was gathered from various modules and modules using hooks.

        :param rule: the rule
        :param portion: source to check
        :return:
        """
        filter_platform = portion['filter']['platform']
        if filter_platform in self.filters:
            validate_filter_callback_function = self.filters[filter_platform]['validate_filter_callback']
            try:
                rule = validate_filter_callback_function(rule, portion)
            except YomboWarning as e:
                logger.warn("Rule '{rule}': Has invalid filter platform params. filter_platform: {filter_platform}.",
                            rule=rule['name'], filter_platform=filter_platform)
                raise YomboWarning("Rule '%s': Has invalid filter platform params. filter_platform: %s." %
                                   (rule['name'], filter_platform),
                                   113, '_check_filter_platform', 'automation')
        else:
            logger.warn("Rule '{rule}': Filter doesn't have platform: {filter_platform}", rule=rule['name'], filter_platform=filter_platform)
            raise YomboWarning("Rule '%s': Filter doesn't have platform: %s" % (rule['name'], filter_platform),
                                114, '_check_filter_platform', 'automation')

        return rule

    def triggers_add(self, rule_id, platform_label, tracked_key):
        """
        A public function that modules and libraries can use to trigger rules. Used to track simple dictionary
        type items or things that can be contained in a dictionary.

        See the :py:mod:`devices <yombo.lib.devices>` library for best example and documentation.

        Summary: When a rule is being added, the 'add_trigger_callback' is called to the platform to add any
        triggers required. Generally, it's up to the module to perform this task. However, the 'triggers_add'
        and 'triggers_check' can perform this task.

        In devices, states, atoms, etc, when 'add_trigger_callback' is called, they all register tracked_keys with
        this function. This function creates an entry in a dictionary and can store the values.  Now, whenever a
        device status changes, states change, atoms change, they call triggers_check with the tracked_key and
        the value. If the value's changed, :py:meth:`triggers_check <triggers_check>` will fire any rules as required.

        *Usage**:

        .. code-block:: python

           self._AutomationLibrary.triggers_add(rule['rule_id'], 'devices', automation_device_id)

        :param rule_id: Rule ID to attach trigger to.
        :param platform_label: Source platform being added: EG: devices, states, atoms
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
    def triggers_check(self, platform_label, tracked_key, new_value):
        """
        Modules and libraries can call this to check for any triggers on a dictionary. If a trigger matches, any
        defined rules for a given trigger will fire.

        See the :py:mod:`devices <yombo.lib.devices>` library for best example and documentation.

        :param platform_label: Platform label to track.
        :param tracked_key: Defined key from triggers_add
        :param new_value: New value to track
        :return:
        """
        # logger.warn("1@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@checking : {new_value}", new_value=new_value)
        # logger.warn("tracked_label: {tracked_label}", tracked_label=platform_label)
        # logger.warn("tracked_key: {tracked_key}", tracked_key=tracked_key)
        # logger.debug("trackers: {tracker}", tracker=self.tracker)
        if platform_label not in self.tracker:
            logger.debug("platform_label ({platform_label}) not in self.tracker. Skipping rule.", platform_label=platform_label)
            return False
        if tracked_key not in self.tracker[platform_label]:
            logger.debug("platform (%s), not tracking key: %s  " % (platform_label, tracked_key))
            return False
        rule_ids = self.tracker[platform_label][tracked_key]
        if len(rule_ids) == 0:
            logger.warn("There should be rules, but found none!")
            return False
        logger.debug("found rule IDs {rule_ids}", rule_ids=rule_ids)

        # We now have at least one trigger. Gather a list of rule id's that have permitted conditions.
        fired_rules = {}
        for item in range(len(rule_ids)):
            rule_id = rule_ids[item]['rule_id']
            rule = self.rules[rule_id]
            if 'filter' in rule['trigger']:
                try:
                    trigger_filter_valid = self.automation_check_filter(rule_id, rule['trigger'], new_value)
                except YomboAutomationWarning as e:
                    fired_rules[rule_id] = "Trigger filter failed with error: %s" % e
                    continue
            else:
                trigger_filter_valid = True

            if trigger_filter_valid is False:
                fired_rules[rule_id] = "Trigger filter is false."
                continue
            else:
                try:
                    condition_filter_valid = self.automation_check_conditions(rule_id)
                except YomboAutomationWarning as e:
                    fired_rules[rule_id] = "Condition filter failed with error: %s" % e
                    continue

            if condition_filter_valid is False:
                fired_rules[rule_id] = "Condition filter failed with error."
                continue
            else:
                try:
                    fired_rules[rule_id] = self.automation_action(rule_id)
                except YomboAutomationWarning as e:
                    fired_rules[rule_id] = "Do automation action failed with error: %s" % e
                    continue

        logger.debug("Fired Rules from trigger check: {rules}", rules=fired_rules)
        return fired_rules

    def get_available_items(self, **kwargs):
        platform = kwargs['platform']
        type = kwargs['type']
        if platform not in self.actions:
            logger.info("Platform ({platform}) doesn't exist as an action when gettings available platform items.",
                        platform=platform)
            return []

        return self.actions[platform]['get_available_items_callback']()

    def automation_check_filter(self, rule_id, portion, new_value):
        if not portion['filter']['platform'] in self.filters:
            raise YomboAutomationWarning("No filter platform: %s" % portion['filter']['platform'], 100, 'automation_check_filter', 'automation')
        run_filter_callback_function = self.filters[portion['filter']['platform']]['run_filter_callback']
        return run_filter_callback_function(self.rules[rule_id], portion, new_value)

    def automation_check_conditions(self, rule_id):
        """
        Directs the rule to the condition checker callback.

        :return:
        """
        logger.debug("doing automation_check_conditions on rule: {rule}", rule=self.rules[rule_id]['name'])
        condition_type = 'and'

        rule = self.rules[rule_id]
        if 'condition_type' in rule:
            condition_type = rule['condition_type']

        condition_results = []
#        logger.warn("rule: {rule}", rule=rule)
        if 'condition' in rule:
            condition = rule['condition']
            # print("testing conditons: %s" % condition)
            for item in range(len(condition)):
                # get value(s)
                get_value_callback_function = self.sources[condition[item]['source']['platform']]['get_value_callback']
                value = get_value_callback_function(rule, condition[item])

                # check value(s)
                result = self.automation_check_filter(rule_id, condition[item], value)

                if condition_type == 'and':
                    if result is False:
                        return False

                condition_results.append(result)

            is_valid = any(condition_results)
        else:
            is_valid = True

        if is_valid:
            logger.debug("Condition check passed for: {rule}", rule=self.rules[rule_id]['name'])
            return True
        else:
            logger.debug("Condition check failed for: {rule}", rule=self.rules[rule_id]['name'])
            return False

    def automation_action(self, rule_id):
        """
        Directs the rule_id to the correct module/library do_action_callback function

        :param rule:
        :return:
        """
        rule = self.rules[rule_id]
        delay = 0
        logger.debug("Performing actions on rule: {name}", name=rule['name'])
        for item in range(len(rule['action'])):
            logger.debug("running rule action:: {name}", name=rule['action'][item]['platform'])
            if 'delay' in rule['action'][item]:
                try:
                    delay = self.get_action_delay(rule['action'][item]['delay'])
                except Exception as e:
                    logger.error("Error parsing 'delay' within action. Cannot perform action: {e}", e=e)
                    raise YomboWarning("Error parsing 'delay' within action. Cannot perform action. (%s)" % rule['action'][item]['delay'],
                                   301, 'devices_validate_action_callback', 'lib.devices')


            # print("rule has delay: %s" % delay)
            platform = rule['action'][item]['platform']
            do_action_callback_function = self.actions[platform]['do_action_callback']
            if delay > 0:
                # print "called with delay"
                reactor.callLater(delay, do_action_callback_function, rule, rule['action'][item], **rule['action'][item]['arguments'])
                self._Statistics.increment("lib.automation.rules.fire_delayed", bucket_size=15, anon=True)
            else:
                # print "called withOUT delay"
                do_action_callback_function(rule, rule['action'][item], **rule['action'][item]['arguments'])
                self._Statistics.increment("lib.automation.rules.fired", bucket_size=15, anon=True)
        return


# class Rule:
#     """
#     A class to contain various aspects of a rule.
#     """
#     def __init__(self, device, allDevices, testDevice=False):
#         """
#         :param device: *(list)* - A device as passed in from the devices class. This is a
#             dictionary with various device attributes.
#         :ivar callBeforeChange: *(list)* - A list of functions to call before this device has it's status
#             changed. (Not implemented.)
#         :ivar callAfterChange: *(list)* - A list of functions to call after this device has it's status
#             changed. (Not implemented.)
#         :ivar device_id: *(string)* - The UUID of the device.
#         :ivar device_type_id: *(string)* - The device type UUID of the device.
#         :type device_id: string
#         :ivar label: *(string)* - Device label as defined by the user.
#         :ivar description: *(string)* - Device description as defined by the user.
#         :ivar enabled: *(bool)* - If the device is enabled - can send/receive command and/or
#             status updates.
#         :ivar pin_required: *(bool)* - If a pin is required to access this device.
#         :ivar pin_code: *(string)* - The device pin number.
#             system to deliver commands and status update requests.
#         :ivar created: *(int)* - When the device was created; in seconds since EPOCH.
#         :ivar updated: *(int)* - When the device was last updated; in seconds since EPOCH.
#         :ivar lastCmd: *(dict)* - A dictionary of up to the last 30 command messages.
#         :ivar status: *(dict)* - A dictionary of strings for current and up to the last 30 status values.
#         :ivar deviceVariables: *(dict)* - The device variables as defined by various modules, with
#             values entered by the user.
#         :ivar available_commands: *(list)* - A list of command_id's that are valid for this device.
#         """
#
#     def _init_(self):
#         """
#         Performs items that required deferreds.
#         :return:
#         """
#         def set_commands(commands):
#             self.available_commands = commands
#
#         def set_variables(vars):
#             self.deviceVariables = vars
#
#         def gotException(failure):
#            logger.error("Received exception: {failure}", failure=failure)
#            return 100  # squash exception, use 0 as value for next stage
#
#         d = self._allDevices._Libraries['localdb'].get_commands_for_device_type(self.device_type_id)
#         d.addCallback(set_commands)
#         d.addErrback(gotException)
#
#         d.addCallback(lambda ignored: self._allDevices._Variables.get_variable_data(relation_type='device', relation_id=self.device_id))
#         d.addErrback(gotException)
#         d.addCallback(set_variables)
#         d.addErrback(gotException)
#
#         if self.testDevice is False:
#             d.addCallback(lambda ignored: self.load_history(35))
#         return d
#