"""
Helpers for automation items.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from time import time

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import is_string_bool, epoch_from_string

logger = get_logger("library.automationhelper")


class AutomationHelpers(YomboLibrary):
    """
    Reads "automation.txt" for automation rules.
    """
    def _init_(self, loader):
        self._ModDescription = "Automation Helper Library"
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "https://yombo.net"

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

    # Helper functions for any automation
    def get_action_delay(self, delay):
        """
        Used to check the 'delay' field of an action. If 'delay' is specified, but useless, will raise

        :param action: Pass in the action to be checked. Will return in epoch time or None if invalid
        :return:
        """
        return (float(epoch_from_string(delay)) - float(time()))


    def AutomationHelpers_automation_action_list(self, **kwargs):
        """
        hook_automation_action_list called by the automation library to list possible actions.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'call_function',
              'validate_action_callback': self.basic_values_validate_action_callback,  # function to call to validate an action is possible.
              'do_action_callback': self.basic_values_do_action_callback  # function to be called to perform an action
            }
         ]

    def basic_values_validate_action_callback(self, rule, action, **kwargs):
        """
        A callback to check if a provided action is valid before being added as a possible action.

        :param rule: The potential rule being added.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        if action['platform'] == 'call_function':
            if 'component_callback' in action:
                if not callable(action['component_callback']):
                    logger.warn("Rule '{rule_name}' is not callable by reference: 'component_callback': {callback}", rule_name=rule['name'], callback=action['component_callback'])
                    return False
                else:
                    action['_my_callback'] = action['component_callback']
            else:
                if all(required in action for required in ['component_type', 'component_name', 'component_function']):
                    if action['component_type'] == 'library':
                        if action['component_name'] not in self._Libraries:
                            return False
                        if hasattr(self._Libraries[action['component_name']], action['component_function']):
                            method = getattr(self._Libraries[action['component_name']], action['component_function'])
                            if not callable(method):
                                logger.warn("Rule '{rule_name}' is not callable by name: 'component_type, component_name, component_function'", rule_name=rule['name'])
                                return False
                            else:
                                action['_my_callback'] = method
                    elif action['component_type'] == 'module':
                        if action['component_name'] not in self._Modules:
                            return False
                        if hasattr(self._Modules[action['component_name']], action['component_function']):
                            method = getattr(self._Modules[action['component_name']], action['component_function'])
                            if not callable(method):
                                logger.warn("Rule '{rule_name}' is not callable by name: 'component_type, component_name, component_function'", rule_name=rule['name'])
                                return False
                            else:
                                action['_my_callback'] = method
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

    def basic_values_do_action_callback(self, rule, action, **kwargs):
        """
        A callback to perform an action.

        :param rule: The complete rule being fired.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        method = action['_my_callback']

        if callable(method):
            if 'arguments' in action:
                return method(**action['arguments'])
            else:
                return method()
        else:
            print "method not callable: %s" % method
        return

    def AutomationHelpers_automation_filter_list(self, **kwargs):
        return [
             {
                 'platform': 'basic_values',
                 'validate_filter_callback': self.basic_values_validate_filter_callback,  # validate a condition combo is possible
                 'run_filter_callback': self.basic_values_run_filter_callback,  # perform a condition check
             }
        ]

    def basic_values_validate_filter_callback(self, rule, portion, **kwargs):
        """
        A callback to check if a provided condition is valid before being added as a possible condition.

        :param rule: The rule. We don't use this here.
        :param kwargs: None
        :return:
        """
#        logger.debug("Validating filter: {filter}", filter=portion['filter'])
        if not all( required in portion['filter'] for required in ['platform', 'value']):
            raise YomboWarning("Required fields (platform, value) are missing from 'basic_values' filter.")
        return rule

    def basic_values_run_filter_callback(self, rule, portion, new_value, **kwargs):
        """
        A callback to check if a provided condition is valid before being added as a possible condition.

        :param rule: The rule. We don't use this here.
        :param kwargs: None
        :return:
        """
        logger.debug("Checking filter: {filter}", filter=portion['filter'])
        trigger_value = portion['filter']['value']
        try:
            trigger_value = is_string_bool(trigger_value)
        except YomboWarning:
            pass

#        logger.debug("Checking new = old: {new_value} = {trigger_value}", new_value=new_value, trigger_value=trigger_value)
        if new_value == trigger_value:
            return True
        return False
