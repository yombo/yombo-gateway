# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For more information see: `Automation Rules @ Yombo.net <https://yombo.net/docs/features/automation-rules/>`_

Helpers for automation items. Adds some core platforms to the source, filters, and actions systems. See
:py:mod:`yombo.lib.automation` for additional details.

.. versionadded:: 0.10.0
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
import operator

# Import python libraries
# from time import time

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.module import YomboModule
from yombo.core.log import get_logger
from yombo.utils import is_string_bool
import collections

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

class AutomationHelpers(YomboModule):
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
    def _automation_action_list_(self, **kwargs):
        """
        Adds 'call_function' to the available action platforms. Allows functions to be called as an action defined
        within an automation rule.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'call_function',  # Defines a new action platform.
              'description': 'Allows functions to be called as an action.',
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
                if not isinstance(action['component_callback'], collections.Callable):
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
                            if not isinstance(method, collections.Callable):
                                logger.warn("Rule '{rule_name}' is not callable by name: 'component_type, component_name, component_function'", rule_name=rule['name'])
                                return False
                            else:
                                action['_my_callback'] = method
                    elif action['component_type'] == 'module':
                        if action['component_name'] not in self._Modules:
                            return False
                        if hasattr(self._Modules[action['component_name']], action['component_function']):
                            method = getattr(self._Modules[action['component_name']], action['component_function'])
                            if not isinstance(method, collections.Callable):
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

        if isinstance(method, collections.Callable):
            if 'arguments' in action:
                return method(**action['arguments'])
            else:
                return method()
        else:
            logger.warn("method not callable: {method}", method=method)
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
        filter_value = portion['filter']['value']

        # logger.debug("Checking new = old: {new_value} = {filter_value}", new_value=new_value, filter_value=filter_value)

        if 'operator' in portion['filter']:
            op_func = ops[portion['filter']['operator']]
            return op_func(new_value, filter_value)
        else:
            if new_value == filter_value:
                return True
            else:
                try:
                    if is_string_bool(new_value) == is_string_bool(filter_value):
                        return True
                except:
                    return False
        return False

