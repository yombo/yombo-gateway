"""
A simple module to test and demonstrate various automation hooks.

This module also creates a few rules for demonstration.

:copyright: 2016 Yombo
:license: MIT
"""
from twisted.internet import reactor

from yombo.core.module import YomboModule
from yombo.core.log import get_logger

logger = get_logger("modules.automationexample")


class AutomationExample(YomboModule):
    """
    This module adds a couple rules and toggles
    """
    def _init_(self):
        self._ModDescription = "Empty module, copy to get started building a new module."
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "https://yombo.net"
#        self._States['automationexample'] = 0

    def _load_(self):
        # in 3 seconds from now, change the state - test the trigger
#        reactor.callLater(3, self.set_low)
        pass

    def AutomationExample_automation_rules_list(self, **kwargs):
        """
        Implements hook_automation_rules_list hook as implemented by the library automation. This defines a few
        example rules. Notice the reference to 'component_function'. This the function that is called when the
        rule fires. Notice that the function name can be reference by name as if it were implemented by a text file,
        or a reference to the function be submitted. Passing a reference to a function provides higher assurance the
        proper function is called and should be used when creating rules within a module.

        :return: Returns a dictionary of rules to be parsed.
        :rtype: dict
        """
        return{'rules': [
            {
                'name': 'Empty test 0',
                'trigger': {
                    'source': {
                        'platform': 'states',
                        'name': 'automationexample',
                    },
                    'filter': {
                        'platform': 'basic_values',
                        'value': 0
                    }
                },
                'condition': [
                    {
                    'source': {
                        'platform': 'atoms',
                        'name': 'kernel',
                        },
                    'filter': {
                        'platform': 'basic_values',
                        'value': 'Linux'
                        }
                    },
                    {
                    'source': {
                        'platform': 'states',
                        'name': 'is.light',
                        },
                    'filter': {
                        'platform': 'basic_values',
                        'value': 'true'
                        }
                    },
                ],
                'action': [
                    {
                        'platform': 'call_function',
                        'component_type': 'module',
                        'component_name': 'AutomationExample',
                        'component_function': 'call_when_low',
                        'arguments': {
                            'argument1': 'somevalue'
                        }
                    }
                ,
                    {
                        'platform': 'devices',
                        'device': 'Christmas tree',
                        'command': 'off',
                    }
                ]
            },
            {
                'name': 'Empty test 1',
                'trigger': {
                    'source': {
                        'platform': 'states',
                        'name': 'automationexample',
                    },
                    'filter': {
                        'platform': 'basic_values',
                        'value': 1
                    }
                },
                'action': [
                    {
                        'platform': 'call_function',
                        'component_callback': self.call_when_high,
                        'arguments': {
                            'argument1': 'somevalue'
                        }
                    }
                ,

                    {
                        'platform': 'devices',
                        'device': 'Christmas tree',
                        'command': 'on',
                    }
                ],
            },
            {
                'name': 'AutomationExample',
                'description': 'Test rule created in AutomationExample module',
                'trigger': {
                    'source': {
                        'platform': 'devices',
                        'device': 'Christmas Tree',
                    },
                    'filter': {
                        'platform': 'basic_values',
                        'value': 1
                    }
                },
                'action': [
                    {
                        'platform': 'call_function',
                        'component_callback': self.call_when_high,
                        'arguments': {
                            'command': 'off'
                        }
                    }
                ]
            }
            ]
        }
        
    def _start_(self):
        logger.info("States: Is Light: {times_light}", times_light=self._States['is.light'])
        logger.info("Atoms: Kernel: {kernel}", kernel=self._Atoms['kernel'])
        self._States['automationexample'] = 0

    def set_high(self):
        logger.info("in set_high - setting automationexample = 1")
        self._States['automationexample'] = 1

    def set_low(self):
        logger.info("in set_low - setting automationexample = 0")
        self._States['automationexample'] = 0

    def call_when_high(self, **kwargs):
        logger.info("it's now high! {kwargs}", kwargs=kwargs)
        reactor.callLater(5, self.set_low)

    def call_when_low(self, **kwargs):
        logger.info("it's now low! {kwargs}", kwargs=kwargs)
        reactor.callLater(5, self.set_high)

    def _stop_(self):
        pass
    
    def _unload_(self):
        pass
