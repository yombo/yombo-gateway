"""
Helpers for automation items.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger
from yombo.utils import is_string_bool

logger = getLogger("library.automationhelper")


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

    def AutomationHelpers_automation_action_list(self, **kwargs):
        """
        hook_automation_action_list called by the automation library to list possible actions.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'call_function',
              'validate_callback': self.basic_values_action_validate,  # function to call to validate an action is possible.
              'do_action_callback': self.basic_values_action_do  # function to be called to perform an action
            }
         ]

    def basic_values_action_validate(self, rule, **kwargs):
        """
        A callback to check if a provided action is valid before being added as a possible action.

        :param kwargs: None
        :return:
        """
        item = kwargs['item']
        action = rule['action'][item]

        if action['platform'] == 'call_function':
            if 'component_callback' in action:
                if not callable(action['component_callback']):
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

    def basic_values_action_do(self, rule, **kwargs):
        """
        A callback to perform an action.

        :param kwargs: None
        :return:
        """
        item = kwargs['item']
        action = rule['action'][item]
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
                 'validate_callback': self.basic_values_filter_validate,  # validate a condition combo is possible
                 'check_callback': self.basic_values_filter_check,  # perform a condition check
             }
        ]

    def basic_values_filter_validate(self, rule, **kwargs):
        """
        A callback to check if a provided condition is valid before being added as a possible condition.

        :param kwargs: None
        :return:
        """
        filter = kwargs['filter']
        logger.debug("Validating filter: {filter}", filter=filter)
        if not all( required in filter for required in ['platform', 'value']):
            return False
        return True

# needs trigger:filter or condition:filter
    def basic_values_filter_check(self, rule, **kwargs):
        """
        A callback to check if a provided condition is valid before being added as a possible condition.

        :param kwargs: None
        :return:
        """
        filter = kwargs['filter']
        logger.debug("Checking filter: {filter}", filter=filter)
        trigger_value = filter['value']
        try:
            trigger_value = is_string_bool(trigger_value)
        except YomboWarning:
            pass

        new_value = kwargs['new_value']
#        logger.debug("Checking new = old: {new_value} = {trigger_value}", new_value=new_value, trigger_value=trigger_value)
        if new_value == trigger_value:
            return True
        return False
