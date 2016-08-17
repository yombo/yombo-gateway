"""
Helpers for automation items. Adds some core platforms to the source, filters, and actions systems. See
:py:mod:`yombo.lib.automationhelpers` for additional details.

.. versionadded:: 0.10.0
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
import operator

# Import python libraries
from time import time

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import is_string_bool, epoch_from_string

logger = get_logger("library.automationhelper")

# A list of possible operations that can be used in "basic_values" filters.
ops = {
    "==": operator.eq,
    "!=": operator.ne,
   "<": operator.lt,
   "<=": operator.le,
   ">=": operator.ge,
   ">": operator.gt,
    "eq": operator.eq,
    "ne": operator.ne,
   "lt": operator.lt,
   "le": operator.le,
   "ge": operator.ge,
   "gt": operator.gt,
   }

class AutomationHelpers(YomboLibrary):
    """
    Provides the following core platforms:

    1) Source platforms: (None currently defined)
    2) Filter platforms:
       1) *any* - A simple filter that always returns True.
       2) *basic_values* - Allows basic logic to be applied. Greater than a given value, is equal to, etc. See
          `Automation @ Projects <https://projects.yombo.net/projects/modules/wiki/Automation>`_ for
          details.
    3) Action platforms:
       1) *call_function* - A very powerful platform that allwos nearly any Yombo Gateway function to be called. It
          can call functions by name or by reference if defined within a module.
    """
    def _init_(self):
        self._ModDescription = "Automation Helper Library"
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "https://yombo.net"

    # Helper functions for any automation
    def get_action_delay(self, delay):
        """
        Used to check the 'delay' field of an action. It's used to send delayed commands. It converts strings such as
        '1m 3s', '1 hour', '6 min' into an epoch time so that the automation system can handle it. Must be a time
        in the future, any times set to the past will be disable the rule.

        :param delay: String - A string to be parsed into epoch time in the future.
        :return: Float in seconds in the future.
        """
        seconds = (float(epoch_from_string(delay)) - float(time()))
        if seconds <0:
            raise YomboWarning("get_action_delay on accepts delays in the future, not the past.", 'get_action_delay', 'automationhelpers')
        return seconds

    def _automation_action_list_(self, **kwargs):
        """
        Adds 'call_function' to the available action platforms. Allows functions to be called as an action defined
        within an automation rule.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'call_function',  # Defines a new action platform.
              'validate_action_callback': self.call_function_validate_action_callback,  # function to call to validate an action is possible.
              'do_action_callback': self.call_function_do_action_callback  # function to be called to perform an action
            },
         ]

    def call_function_validate_action_callback(self, rule, action, **kwargs):
        """
        A callback to check if a provided action is valid before being added as a possible action for a rule.

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

    def call_function_do_action_callback(self, rule, action, **kwargs):
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

    def _automation_filter_list_(self, **kwargs):
        return [
             {
                 'platform': 'any', # allow any value. Always returns true.
                 'validate_filter_callback': self.any_validate_filter_callback,  # validate a condition combo is possible
                 'run_filter_callback': self.any_run_filter_callback,  # perform a condition check
             },
             {
                 'platform': 'basic_values',
                 'validate_filter_callback': self.basic_values_validate_filter_callback,  # validate a condition combo is possible
                 'run_filter_callback': self.basic_values_run_filter_callback,  # perform a condition check
             },
        ]

    def any_validate_filter_callback(self, rule, portion, **kwargs):
        """
        Will always return True.

        :param rule: The rule. We don't use this here.
        :param kwargs: None
        :return: True
        """
        return True

    def any_run_filter_callback(self, rule, portion, new_value, **kwargs):
        """
        A callback to check if a provided condition is valid before being added as a possible condition.

        :param rule: The rule. We don't use this here.
        :param kwargs: None
        :return: True
        """
        return True

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
        if 'operator' in portion['filter']:
            if 'operator' not in ops:
                raise YomboWarning("Supplied filter operator is invalid: %s" % portion['filter']['operator'])
        return portion

    def basic_values_run_filter_callback(self, rule, portion, new_value, **kwargs):
        """
        A callback to check if a provided condition is valid before being added as a possible condition.

        :param rule: The rule. We don't use this here.
        :param kwargs: None
        :return:
        """
        logger.debug("Checking filter: {filter}", filter=portion['filter'])
        filter_value = portion['filter']['value']
        try:
            trigger_value = is_string_bool(filter_value)
        except YomboWarning:
            pass

#        logger.debug("Checking new = old: {new_value} = {trigger_value}", new_value=new_value, trigger_value=trigger_value)

        if 'operator' in portion['filter']:
            op_func = ops[portion['filter']['operator']]
            return op_func(new_value, filter_value)
        else:
            if new_value == filter_value:
                return True
            return False

