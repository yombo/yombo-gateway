"""
A simple module to test and demonstrate various automation hooks.

:copyright: 2016 Yombo
:license: MIT
"""
from twisted.internet import reactor

from yombo.core.module import YomboModule
from yombo.core.log import getLogger

logger = getLogger("module.automationexample")

class AutomationExample(YomboModule):
    """
    This module adds a couple rules and toggles
    """
    def _init_(self):
        self._ModDescription = "Empty module, copy to get started building a new module."
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "https://yombo.net"
        self._States['automationexample'] = 0

    def _load_(self):
        # in 3 seconds from now, change the state - test the trigger
#        reactor.callLater(3, self.set_low)
        pass

    def AutomationExample_automation_rules_list(self, **kwargs):
        return {'rules': [
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
                        'name': 'is_light',
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
                ]
            }
            ]
        }
        
    def _start_(self):
        logger.info("States: Is Light: {is_light}", is_light=self._States['is_light'])
        logger.info("Atoms: Kernel: {kernel}", kernel=self._Atoms['kernel'])

    def set_high(self):
        self._States['automationexample'] = 1

    def set_low(self):
        self._States['automationexample'] = 0

    def call_when_high(self, **kwargs):
        logger.info("it's now high! {kwargs}", kwargs=kwargs)
        reactor.callLater(10, self.set_low)

    def call_when_low(self, **kwargs):
        logger.info("it's now low! {kwargs}", kwargs=kwargs)
        reactor.callLater(10, self.set_high)

    def _stop_(self):
        pass
    
    def _unload_(self):

        pass

    def message(self, message):

        pass
