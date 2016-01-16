"""
Reads a text file for simple automation rules. Allows you to quickly setup simple
automation rules.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import 3rd-party libs
import yombo.ext.hjson as hjson

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger
import yombo.utils

logger = getLogger("library.automation")

REQUIRED_RULE_FIELDS = ['trigger', 'action', 'name']
REQUIRED_TRIGGER_FIELDS = ['type']
REQUIRED_ACTION_FIELDS = ['type']
REQUIRED_CONDITION_FIELDS = ['type']

CONDITION_TYPE_AND = 'and'
CONDITION_TYPE_OR = 'or'


class Automation(YomboLibrary):
    """
    Reads "automation.txt" for automation rules.
    """
    def _init_(self, loader):
        self._ModDescription = "Easy Automation for everyone"
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "https://yombo.net"
        self._rulesRaw = {}  # Used to store raw input from reading file.
        self._rulesParse = {}  # Used to store raw input from reading file.
        self.loader = loader
        self.rules = {}  # Store processed rules

        self.triggers_pre = {}
        self.conditions_pre = {}
        self.actions_pre = {}
        self.triggers = []
        self.conditions = []
        self.actions = []
        self.tracker = {}

        # lets load the raw json and see if we can even parse anything.
        try:
            with yombo.utils.fopen('automation.txt', 'r') as fp_:
                self._rulesRaw = hjson.loads(fp_.read())
#                print "hjosn: %s" % hjson.loads(self._rulesRaw)
#                self._rulesRaw = hjson.load(fp_.read())
                logger.debug("automation.txt rules RAW: {rules}",rules= self._rulesRaw['rules'])
        except Exception, e:
            logger.warn("Simple automation is unable to parse 'automation.txt' file: %s." % e)
            self._rulesRaw = {}

    def _load_(self):
        pass

    def _start_(self):
        pass

    def _stop_(self):
        pass

    def _unload_(self):
        pass

    def message(self, message):
        pass

    def _module_prestart_(self, **kwargs):
        """
        Implements the _module_prestart_ and is called before _start_ is called for all the modules.

        Implements three hook: hook_automation_trigger, hook_automation_condition, hook_automation_action

        * hook_automation_trigger : Expects a list of automation triger types a library or module supports.
        *hook_automation_condition : Expects a list of dictionaries containting automation condition types
          a library or module supports.
        *hook_automation_action : Expects a list of dictionarys containging automation action types
          a library or module supports.

        **Usage**:

        .. code-block:: python

           def ModuleName_automation_trigger(self, **kwargs):
               return [
                 { 'type': 'state',
                   'add_callback': callBackFunction  # function to call to add a trigger
                   'validation_callback': callBackFunction  # function to call to validate a trigger
                 }
               ]
           def ModuleName_automation_condition(self, **kwargs):
               return [
                 { 'type': 'state',
                   'fields': ['name', 'value'],
                   'check_callback': callBackFunction  # function to call to perform condition checkking
                   'validation_callback': callBackFunction  # function to call to validate a trigger
                 }
               ]
           def ModuleName_automation_action(self, **kwargs):
               return [
                 { 'type': 'x10',
                   'fields': ['name', 'command']  #can be either UUID's or Machine Labels
                   'action_callback': callBackFunction  # function to call to perform an action
                   'validation_callback': callBackFunction  # function to call to validate an action
                 }
               ]
        """
        # get list of triggers, condition_validation, action_validation
        # for each support type listed, search type in hjson file
        # send the conditional portion of the rule to the trigger_validation, condition_validation
        # and action_validation checkers to make sure the rule is valid before being added by
        # calling the trigger_add

        # send lib/mod trigger our condition callback

        # on trigger event, will call our condition callback
        # we will get the rule being called, including it's condition.
        # the condition callback will call the matchin remote condition checker for true/false
        # if we get a true, we will pass the rule to the action callback for that type.



        other_rules = yombo.utils.global_invoke_all('automation_rules_list')
        for component, rules in other_rules.iteritems():
            self._rulesRaw = yombo.utils.dict_merge(self._rulesRaw, rules)
        print self._rulesRaw

        logger.debug("rulesRaw: {rawrules}", rawrules=self._rulesRaw)
        if 'rules' not in self._rulesRaw:
            logger.warn("There are no simple automation rules!!!")
            return

        # First pass - do basic checks
        for rule in self._rulesRaw['rules']:
            is_valid = True
 #           print "item = %s" % rule
            if not all(section in rule for section in REQUIRED_RULE_FIELDS):
                logger.info("Rule doesn't have required fields, skipping: ({rule}) {required}", rule=rule, required=REQUIRED_RULE_FIELDS)
                continue  # Doesn't have all required fields.

            if not all(section in rule['trigger'] for section in REQUIRED_TRIGGER_FIELDS):
                logger.info("Rule:  Doesn't have required trigger fields, has: {rule} ({trigger})  Required:{required}",
                            rule=rule, trigger=rule['trigger'], required=REQUIRED_RULE_FIELDS)
                continue  # Doesn't have all required fields.

            if len([k for k,v in rule['trigger'].items() if k.startswith('_')]):  # we don't like values starting with '_'.
                continue

            conditionsdict = {}
            if 'condition' in rule:
                for item in range(len(rule['condition'])):
                    if not all(section in rule['condition'][item] for section in REQUIRED_CONDITION_FIELDS):
                        logger.info("Rule:  Doesn't have required condition fields, has: ({condition})  Required:{required}",
                                    condition=rule['condition'][item], required=REQUIRED_CONDITION_FIELDS)
                        is_valid = False  # Doesn't have all required fields.
                        continue
                    if len([k for k,v in rule['condition'][item].items() if k.startswith('_')]):  # we don't like values starting with '_'.
                        is_valid = False
                        continue
                    if rule['condition'][item]['type'] not in conditionsdict:
                        conditionsdict[rule['condition'][item]['type']] = []
                    conditionsdict[rule['condition'][item]['type']].append(rule)

            if not is_valid:
                continue

#            actionsdict = {}
            for item in range(len(rule['action'])):
                if not all(section in rule['action'][item] for section in REQUIRED_ACTION_FIELDS):
                    logger.info("Rule: Doesn't have required action fields,  has: ({action})  Required:{required}",
                                rule=rule, action=rule['action'][item], required=REQUIRED_ACTION_FIELDS)
                    is_valid = False   # Doesn't have all required fields.
                    continue

                if len([k for k,v in rule['action'][item].items() if k.startswith('_')]):  # we don't like values starting with '_'.
                    is_valid = False
                    continue

            if is_valid:
                rule['rule_id'] = yombo.utils.random_string(length=15)
                rule['conditions'] = conditionsdict
                self._rulesParse[rule['rule_id']] =  rule
        logger.debug("Automation rules, after basic checks: {rules}", rules=self._rulesParse)
        self._rulesRaw = None

        automation_triggers = yombo.utils.global_invoke_all('automation_trigger_list')
        logger.debug("message: automation_triggers: {automation_triggers}", automation_triggers=automation_triggers)
        for moduleName, triggers in automation_triggers.iteritems():
#            logger.info("triggers: {triggers}", triggers=triggers)
            for items in triggers:
#                logger.debug("module:{moduleName} has a trigger type: {items}", moduleName=moduleName, items=items)
                self.triggers_pre[items['type']] = items

        automation_conditions = yombo.utils.global_invoke_all('automation_conditions_list')
#        logger.info("message: automation_conditions: {automation_conditions}", automation_conditions=automation_conditions)
        for moduleName, conditions in automation_conditions.iteritems():
            for items in conditions:
#                logger.debug("module:{moduleName} has a condition type: {items}", moduleName=moduleName, items=items)
                self.conditions_pre[items['type']] = items

        automation_actions = yombo.utils.global_invoke_all('automation_action_list')
#        logger.info("message: automation_actions: {automation_actions}", automation_actions=automation_actions)
        for moduleName, actions in automation_actions.iteritems():
            for items in actions:
#                logger.debug("module:{moduleName} has an action type: {items}", moduleName=moduleName, items=items)
                self.actions_pre[items['type']] = items

        # for each rule, make sure the trigger, condition, and action checker is valid.
        for rule_name, rule in self._rulesParse.iteritems():
            print "^1111 ^^^: %s" % rule
            is_valid = True
            rule_type = rule['trigger']['type']
            if rule_type in self.triggers_pre:
                VCB = self.triggers_pre[rule_type]['validation_callback']
                if not VCB(rule, type=rule_type, condition_callback=self.automation_condition):
                    continue

            print "^2222 ^^^: %s" % rule
            if 'condition' in rule:
                print "^2222 A ^^^: %s" % rule
                for item in range(len(rule['condition'])):
                    print "^2222 B ^^^: %s" % rule
                    type_ = rule['condition'][item]['type']
                    if type_ in self.conditions_pre:
                        print "^2222 C ^^^: %s" % rule
                        VCB = self.conditions_pre[type_]['validation_callback']
                        if not VCB(rule, type=type_, item=item):
                            logger.warn("Condition pre-check validation failed.")
                            is_valid = False
                            continue
                    else:
                        logger.warn("Condition Type ({condition_type} doesn't exist. Skipping rule: {rule_name}",
                                    condition_type=type_, rule_name=rule_name)
                        logger.warn("condition types avail: {types}", types=self.conditions_pre)
                        is_valid = False
                        continue

            print "^3333 ^^^: %s" % rule
            for item in range(len(rule['action'])):
                type_ = rule['action'][item]['type']
                VCB = self.actions_pre[type_]['validation_callback']
                if not VCB(rule, type=type_, item=item):
                    logger.warn("Action Type '{action_type}' not in rule: {rule_name}. Skipping rule.",
                                action_type=type_, rule_name=rule['action'][item])
                    is_valid = False
                else:
                    print "!@#!@#!@#!@#!@#!::::: %s" % rule
#                    rule['action'][item] = rule

            print "^4444 ^^^: %s" % rule
            if is_valid is False:
                continue
            add_trigger = self.triggers_pre[rule_type]['add_callback']
            add_trigger(rule, condition_callback=self.automation_condition)
            print "^22^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ rule when adding: %s" % rule
            self.rules[rule_name] = rule

        self._rulesParse = None
#            logger.info("################# added rule: {rule}", rule=rule)

    # ruleID, 'atoms', 'is_light', True
    def track_trigger_basic_add(self, rule_id, tracked_label, tracked_key, to_state):
        logger.warn("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@adding ruleid: {rule}", rule=rule_id)
        if tracked_label not in self.tracker:
            self.tracker[tracked_label] = {}
#        logger.warn("trackedkey: {key}", key=tracked_key)
        tracked_key_tuple = (tracked_key, to_state)
        self.tracker[tracked_label][tracked_key_tuple] = {
            'rule_id': rule_id,
        }

    # 'atoms', 'is_light', False
    def track_trigger_basic_check(self, tracked_label, tracked_key, new_state):
        logger.warn("1@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@checking : {new_state}", new_state=new_state)
        logger.warn("tracked_label: {tracked_label}", tracked_label=tracked_label)
        logger.warn("tracked_key: {tracked_key}", tracked_key=tracked_key)
        logger.warn("new_state: {new_state}", new_state=new_state)
        logger.warn("trackers: {tracker}", tracker=self.tracker)
        if tracked_label not in self.tracker:
            return False
        tracked_key_tuple = (tracked_key, new_state)
        if tracked_key_tuple not in self.tracker[tracked_label]:
            return False
        logger.warn("found rule, ruleid: {rule}", rule=self.tracker[tracked_label][tracked_key_tuple]['rule_id'])
        return self.tracker[tracked_label][tracked_key_tuple]['rule_id']

    def track_trigger_basic_do(self, rule_id):
        return self.automation_condition(rule_id)

    def automation_condition(self, rule_id):
        """
        Directs the rule to the condition checker callback.

        :return:
        """
        logger.info("doing condition...ruleid: {rule}", rule=rule_id)
        # compile all types, send them to a callback in bulk: EG- all time based conditions at once.
        condition_type = 'and'
#        logger.warn("all rules: {ruleid} in {rules}", ruleid=rule_id, rules=self.rules)
        rule = self.rules[rule_id]
        if 'condition_type' in rule:
            condition_type = rule['condition_type']

        results = []
#        logger.warn("rule: {rule}", rule=rule)
        is_valid = True
        if 'conditions' in rule:
            for type_, condition in rule['conditions'].iteritems():
                condition_callback = self.conditions_pre[type_]['check_callback']
                if condition_callback(rule, type=type, conditions=rule['conditions'][type_]) is False:
                    results.append(False)
                else:
                    results.append(True)

            if condition_type == 'and':
                is_valid = all(results)
            else:
                is_valid = any(results)

        # if we get here, we should now run the actions!
        if is_valid:
            print "11111"
            return self.automation_action(rule)


    def automation_action(self, rule):
        """
        Directs the rule to the action callback.
        :param rule:
        :return:
        """

        print "^^^^^^^^^^^^^^^^^^^^^^^^^^^1 rule: %s"  % rule
        for item in range(len(rule['action'])):
            print "^^^^^^^^^^^^^^^^^^^^^^^^^^^2 callback: %s"  % rule['action']
            type_ = rule['action'][item]['type']
#            type, item in action:

#            logger.warn("rule['actions']: {rule}", rule=rule['action'])
#            logger.warn("action {action}", action=action)
#            logger.warn("actions_pre {pre}", pre=self.actions_pre)
            do_action = self.actions_pre[type_]['do_action_callback']
            do_action(rule, item=item, type=type_)

        return

    def Automation_automation_action_list(self, **kwargs):
        """
        hook_automation_action_list called by the automation library to list possible actions.

        :param kwargs: None
        :return:
        """
        return [
            { 'type': 'call_function',
              'validation_callback': self._automation_action_validation,  # function to call to validate an action is possible.
              'do_action_callback': self._automation_do_action  # function to be called to perform an action
            }
         ]

    def _automation_action_validation(self, rule, **kwargs):
        """
        A callback to check if a provided action is valid before being added as a possible action.

        :param kwargs: None
        :return:
        """
        item = kwargs['item']
        action = rule['action'][item]

        print "one %s" % action['type']
        if action['type'] == 'call_function':
            print "one"
            if 'component_callback' in action:
                print "one2"
                if not callable(action['component_callback']):
                    print "one3"
                    logger.warn("Rule '{rule_name}' is not callable by reference: 'component_callback': {callback}", rule_name=rule['name'], callback=action['component_callback'])
                    return False
                else:
                    rule['action'][item]['_my_callback'] = action['component_callback']
            else:
                if all( required in action for required in ['component_type', 'component_name', 'component_function']):
                    if action['component_type'] == 'library':
                        if action['component_name'] not in self._Libraries:
                            return False
                        if hasattr(self._Libraries[action['component_name']], action['component_function']):
                            method = getattr(self._Libraries[action['component_name']], action['component_function'])
                            if not callable(method):
                                logger.warn("Rule '{rule_name}' is not callable by name: 'component_type, component_name, component_function'", rule_name=rule['name'])
                                return False
                            else:
                                rule['action'][item]['_my_callback'] = method
                    elif action['component_type'] == 'module':
                        if action['component_name'] not in self._Modules:
                            return False
                        if hasattr(self._Modules[action['component_name']], action['component_function']):
                            method = getattr(self._Modules[action['component_name']], action['component_function'])
                            if not callable(method):
                                logger.warn("Rule '{rule_name}' is not callable by name: 'component_type, component_name, component_function'", rule_name=rule['name'])
                                return False
                            else:
                                rule['action'][item]['_my_callback'] = method
                    else:
                        logger.warn("Rule() '{rule_name}' doesn't have a valid component_type: ", rule_name=rule['name'])
                        return False

                else:
                    logger.warn("Rule '{rule_name}' needs either 'component_callback' or 'component_type, component_name, component_function'", rule_name=rule['name'])
                    return False
        else:
            logger.warn("Rule '{rule_name}' doesn't have a valid 'call_function' configuration", rule_name=rule['name'])
            return False
#        logger.warn("saving rule: {rule}", rule=rule)
        return True

    def _automation_do_action(self, rule, **kwargs):
        """
        A callback to perform an action.

        :param kwargs: None
        :return:
        """
        item = kwargs['item']
        action = rule['action'][item]
        method = action['_my_callback']

        print "^^^^^^^^^^^^^^^^^^^^^^^^^^^ callback: %s"  % rule['action']
        print "about to call method()"
        if callable(method):
            if 'arguments' in action:
                return method(**action['arguments'])
            else:
                return method()
        else:
            print "method not callable: %s" % method
        return

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