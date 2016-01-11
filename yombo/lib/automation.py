"""
Reads a text file for simple automation rules. Allows you to quickly setup simple
automation rules.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
import yombo.ext.hjson as hsjon

from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger
import yombo.ext.hjson
from yombo.utils import global_invoke_all

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
        self._rulesRaw = None  # Used to store raw input from reading file.
        self.loader = loader
        self.rules = {}  # Store processed rules
        self._automation_enabled = False

        self.triggers_pre = {}
        self.conditions_pre = {}
        self.actions_pre = {}
        self.triggers = []
        self.conditions = []
        self.actions = []

        # lets load the raw json and see if we can even parse anything.
        try:
            with yombo.utils.fopen('automation.txt', 'r') as fp_:
                self._rulesRaw = yombo.ext.hjson.load(fp_.read())
        except Exception, e:
            logger.warn("Simple automation is unable to parse 'automation.txt' file: %s." % e)
            return
        self._automation_enabled = True

        if 'rules' not in self._rulesRaw:
            logger.warn("There are no simple automation rules. Quiting.")

        # First pass - do basic checks
        for item in self.rulesRaw['rules']:
            rule = self.rulesRaw['rules'][item]
            if not all(section in rule for section in REQUIRED_RULE_FIELDS):
                logger.info("Rule ({rule}) doesn't have required fields: {required}", rule=rule, required=REQUIRED_RULE_FIELDS)
                continue  # Doesn't have all required fields.

            if not all(section in rule['trigger'] for section in REQUIRED_TRIGGER_FIELDS):
                logger.info("Rule: {rule} Doesn't have required trigger fields, has: ({trigger})  Required:{required}",rule=rule, trigger=rule['trigger'], required=REQUIRED_RULE_FIELDS)
                continue  # Doesn't have all required fields.

            if not all(section in rule['trigger'] for section in REQUIRED_ACTION_FIELDS):
                logger.info("Rule: {rule} Doesn't have required action fields, has: ({action})  Required:{required}",rule=rule, action=rule['action'], required=REQUIRED_ACTION_FIELDS)
                continue  # Doesn't have all required fields.

            if 'condition' in rule:
                if not all(section in rule['trigger'] for section in REQUIRED_CONDITION_FIELDS):
                    logger.info("Rule: {rule} Doesn't have required condition fields, has: ({condition})  Required:{required}",rule=rule, condition=rule['condition'], required=REQUIRED_CONDITION_FIELDS)
                    continue  # Doesn't have all required fields.

            self.rules[rule['name']] =  rule

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

        automation_triggers = global_invoke_all('automation_trigger_list')
        logger.info("message: automation_triggers: {automation_triggers}", automation_triggers=automation_triggers)
        for moduleName, items in automation_triggers.iteritems():
            for item in items:
                logger.debug("module:{moduleName} has a trigger type: {type}", moduleName=moduleName, item=item)
                self.triggers_pre['moduleName'] = item


        automation_conditions = global_invoke_all('automation_conditions_list')
        logger.info("message: automation_conditions: {automation_conditions}", automation_conditions=automation_conditions)
        for moduleName, items in automation_conditions.iteritems():
            for item in items:
                logger.debug("module:{moduleName} has a condition type: {item}", moduleName=moduleName, item=item)
                self.conditions_pre['moduleName'] = item


        automation_actions = global_invoke_all('automation_action_list')
        logger.info("message: automation_actions: {automation_actions}", automation_actions=automation_actions)
        for moduleName, items in automation_actions.iteritems():
            for item in items:
                logger.debug("module:{moduleName} has an action type: {item}", moduleName=moduleName, item=item)
                self.actions_pre['moduleName'] = item


        # for each rule, make sure the trigger, condition, and action checker is valid.
        for ruleName, rule in self.rules:
            is_valid = None
            if rule['type'] in self.triggers_pre:
                is_valid = self.triggers_pre['validation_callback']
                isValid = VCB(rule)

                if is_valid is not True:
                    continue
                VCB = self.triggers_pre['validation_callback']
                is_valid = VCB(rule)

                if is_valid is not True:
                    continue
                if 'condition' in rule:
                  VCB = self.condition_pre['validation_callback']
                  is_valid = VCB(rule)

                if is_valid is not True:
                    continue
                VCB = self.action_pre['validation_callback']
                is_valid = VCB(rule)

                if is_valid:
                    add_trigger = self.trigger_pre['add_callback']
                    add_trigger(rule, self.automation_condition)


    def automation_condition(self, rule):
        """
        Directs the rule to the condition checker callback.

        :return:
        """
        #compile all types, send them to a callback in bulk: EG- all time based conditions at once.
        conditionsdict = {}
        for item, condition in rule['condition'].iteritems():
            if condition['type'] not in conditionsdict:
                conditionsdict[condition['type']] = []
            conditionsdict[condition['type']].append(condition)

        is_valid = True
        for type, condition in conditionsdict.iteritems():
            check_condition = self.conditions_pre[type]['check_callback']
            is_valid = check_condition(rule)


        if is_valid is not True:
            return False

        # if we get here, we should now run the actions!
        return self.automation_action(rule)


    def automation_action(self, rule):
        """
        Directs the rule to the action callback.
        :param rule:
        :return:
        """
        actionsdict = {}
        for action in rule['action'].iteritems():
            do_action = self.actions_pre[type]['action_callback']
            do_action(rule)
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