"""
.. rst-class:: floater

.. note::

  For more information see: `Stats @ Projects.yombo.net <https://projects.yombo.net/projects/modules/wiki/States>`_

The states library is used to collect and provide information about various states that the automation system
can be in or exist around it. For example, it can tell if it's light outside, dawn, dusk, or if it's connected
to the Yombo server. It can provide a list of users connected and what module they are connected through.

Example states: times_dark, weather_raining, alarm_armed, yombo_service_connection

*Usage**:

.. code-block:: python

   try:
     raining = self._States['weather.raining']
   except:
     raining = None

   if raining is not True:
       # turn on sprinklers

   try:
     jeffIsHome = self._States['is.people.jeff.home']
   except:
     jeffIsHome = None

   if jeffIsHome == "home":
       # turn on HVAC
   elif jeffIsHome is not None:
       # turn off HVAC
   else:
       # we don't know if Jeff is home or not, leave HVAC alone

   try:
     self._States['weather_is_cloudy'] = True
   except:
     pass  # unable to set state?



.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from collections import deque
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboStateNotFound, YomboWarning, YomboHookStopProcessing
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
from yombo.utils import global_invoke_all


logger = get_logger("library.YomboStates")

class States(YomboLibrary, object):
    """
    Provides a base API to store common states among libraries and modules.
    """
    MAX_HISTORY = 100

    @inlineCallbacks
    def _init_(self, loader):
        self._ModDescription = "Yombo States API"
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "https://yombo.net"
        self.automation = self._Libraries['automation']

        self.__States = {}
        self._loaded = False
        self.__History = yield self._Libraries['SQLDict'].get(self, 'History')
#        logger.info("Recovered YomboStates: {states}", states=self.__States)

    def _load_(self):
        self._loaded = True
        pass

    def _start_(self):
        pass

    def _stop_(self):
        pass

    def _unload_(self):
        pass

    def __delitem__(self, key):
        self.delete(key)

    def __getitem__(self, key):
        return self.get(key)

    def __len__(self):
        return len(self.__States)

    def __setitem__(self, key, value):
        return self.set(key, value)

    def __contains__(self, key):
        return self.exists(key)

    def __str__(self):
        states = {}
        for key, state in self.__States.iteritems():
            if state['readKey'] is None:
                states[key] = state['value']
        return states

    # def __repr__(self):
    #     states = {}
    #     for key, state in self.__States.iteritems():
    #         if state['readKey'] is not None:
    #             state['readKey'] = True
    #         if state['writeKey'] is not None:
    #             state['writeKey'] = True
    #         states[key] = state
    #     return states

    def exists(self, key):
        """
        Checks if a given state exsist. Returns true or false.

        :param key: Name of state to check.
        :return: If state exists:
        :rtype: Bool
        """
        if key in self.__States:
            return True
        return False

    def get_last_update(self, key):
        """
        Get the time() the key was created or last updated.

        :param key: Name of state to check.
        :return: Time() of last update
        :rtype: float
        """
        if key in self.__States:
            return self.__States[key]['updated']
        else:
            raise YomboStateNotFound("Cannot get state time: %s not found" % key)

    def get(self, key=None):
        """
        Get the value of a given state (key).

        :param key: Name of state to get.
        :return: Value of state
        """
        if key in self.__States:
                self._Statistics.increment("lib.states.get.found", bucket_time=60, anon=True)
                return self.__States[key]['value']
        else:
            self._Statistics.increment("lib.states.get.not_found", bucket_time=60, anon=True)
            return None

    def get_states(self):
        """
        Get all states.

        :param key: Name of state to check.
        :return: Value of state
        """
        states = {}
        for name, state in self.__States.iteritems():
            states[name] = state
        return states

    def set(self, key, value):
        """
        Set the value of a given state (key).

        **Hooks implemented**:

        * hook_states_set : Sends kwargs 'key', 'value', and 'new'. *key* is the name of the state being set, *value* is
          the new value to set, and *new* is True if the state didn't have a value before - otherwise False.

        :param key: Name of state to set.
        :param value: Value to set state to. Can be string, list, or dictionary.
        :return: Value of state
        """

        if key in self.__States:
            if self.__States[key]['value'] == value:  # don't set the value to the same value
                return

            # Call any hooks
            try:
                state_changes = global_invoke_all('states_set', **{'keys': key, 'value': value, 'new': False})
            except YomboHookStopProcessing:
                logger.warning("Stopping processing 'hook_states_set' due to YomboHookStopProcessing exception.")
                return

            for moduleName, newValue in state_changes.iteritems():
                if newValue is not None:
                    logger.debug("statest::set Module ({moduleName}) changes state value to: {newValue}",
                                 moduleName=moduleName, newValue=newValue)
                    value = newValue
                    break

            self._Statistics.increment("lib.states.set.update", bucket_time=60, anon=True)
            self.__States[key]['value'] = value
            self.__States[key]['updated'] = time()
            self.__set_history(key, self.__States[key]['value'], self.__States[key]['updated'])
        else:
            # Call any hooks
            try:
                state_changes = global_invoke_all('states_set', **{'keys': key, 'value': value, 'new': True})
            except YomboHookStopProcessing:
                logger.warning("Stopping processing 'hook_states_set' due to YomboHookStopProcessing exception.")
                return

            for moduleName, newValue in state_changes.iteritems():
                if newValue is not None:
                    logger.debug("statest::set Module ({moduleName}) changes state value to: {newValue}",
                                 moduleName=moduleName, newValue=newValue)
                    value = newValue
                    break

            self.__States[key] = {
                'value': value,
                'updated': int(time()),
            }
            self._Statistics.increment("lib.states.set.new", bucket_time=60, anon=True)
            self.__set_history(key, self.__States[key]['value'], self.__States[key]['updated'])
        self.check_trigger(key, value)

    def set_live(self, key, callback, arguments={}):
        """
        Set a live state. This is a state that will call a function for each request of the value.

        :param key:
        :param callback:
        :param arguments:
        :return:
        """
        # Not implemented yet. Considerations: blocking calls.
        pass

    def __set_history(self, key, value, updated):
        data = {'value' : value, 'updated' : updated}
#        print "saving state history: %s:%s" % (key, value)
        if key in self.__History:
            self.__History[key].appendleft(data)
#            print "appending: %s" % self.__History[key]
        else:
            self.__History[key] = deque([data], self.MAX_HISTORY)

    def get_history(self, key, position=1):
        """
        Returns a previous version of the state. Returns a dictionary with "value" and "updated" inside. See
        :py:func:`history_length` to deterine how many entries there are. Max of MAX_HISTORY (currently 100).

        :param key: Name of the state to get.
        :param position: How far back to go. 0 is current, 1 is previous, etc.
        :return:
        """
        if key in self.__States:
            if key in self.__History:
                if position == -1:  # Lets return all the history
                    return self.__History[key]
                if len(self.__History[key]) < position:
                    raise YomboStateNotFound("History doesn't exist. Only %s entries exist. %s" % len(self.__History[key]))
                return self.__History[key][position]
            else:
                raise YomboStateNotFound("Cannot get state history, does not exist: %s" % key)
        else:
            raise YomboStateNotFound("Cannot get state: %s not found" % key)

    def history_length(self, key):
        """
        Returns how many records a given state (key) has.

        :param key: Name of the state to check.
        :return: How many records there are for a given state.
        :rtype: int
        """
        if key in self.__States:
            if key in self.__History:
                return len(self.__History[key])
            else:
                raise YomboStateNotFound("Cannot get state history, no history for: %s" % key)
        else:
            raise YomboStateNotFound("Cannot get state: %s not found" % key)

    def delete(self, key):
        """
        Deletes a status (key).
        YomboStateNotFound if state not found.

        :param key: Name of the state to delete.
        :return: None
        :rtype: None
        """
        if key in self.__States:
            del self.__States[key]
        else:
            raise YomboStateNotFound("Cannot delete state: %s not found" % key)
        return None


    # The remaining functions implement automation hooks. These should not be called by anything other than the
    # automation library!

    def check_trigger(self, key, value):
        """
        Called by the states.set function when a new value is set. It asks the automation library if this key is
        trigger, and if so, fire any rules.

        True - Rules fired, fale - no rules fired.
        """
        if self._loaded:
            results = self.automation.triggers_check('states', key, value)

    def States_automation_source_list(self, **kwargs):
        """
        hook_automation_source_list called by the automation library to get a list of possible sources.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'states',
              'validate_source_callback': self.states_validate_source_callback,  # function to call to validate a trigger
              'add_trigger_callback': self.states_add_trigger_callback,  # function to call to add a trigger
              'get_value_callback': self.states_get_value_callback,  # get a value
            }
         ]

    def states_validate_source_callback(self, rule, portion, **kwargs):
        """
        A callback to check if a provided source is valid before being added as a possible source.

        :param rule: The potential rule being added.
        :param portion: Dictionary containg everything in the portion of rule being fired. Includes source, filter, etc.
        :return:
        """
        if all( required in portion['source'] for required in ['platform', 'name']):
            return True
        raise YomboWarning("Source doesn't have required parameters: platform, name",
                101, 'states_validate_source_callback', 'states')

    def states_add_trigger_callback(self, rule, **kwargs):
        """
        Called to add a trigger.  We simply use the automation library for the heavy lifting.

        :param rule: The potential rule being added.
        :param kwargs: None
        :return:
        """
        self.automation.triggers_add(rule['rule_id'], 'states', rule['trigger']['source']['name'])

    def states_get_value_callback(self, rule, portion, **kwargs):
        """
        A callback to the value for platform "states". We simply just do a get based on key_name.

        :param rule: The potential rule being added.
        :param portion: Dictionary containg everything in the portion of rule being fired. Includes source, filter, etc.
        :return:
        """
        return self.get(portion['source']['name'])

    def States_automation_action_list(self, **kwargs):
        """
        hook_automation_action_list called by the automation library to list possible actions this module can
        perform.

        This implementation allows autoamtion rules set easily set Atom values.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'states',
              'validate_action_callback': self.states_validate_action_callback,  # function to call to validate an action is possible.
              'do_action_callback': self.states_do_action_callback  # function to be called to perform an action
            }
         ]

    def states_validate_action_callback(self, rule, action, **kwargs):
        """
        A callback to check if a provided action is valid before being added as a possible action.

        :param rule: The potential rule being added.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        if 'value' not in action:
            raise YomboWarning("In states_validate_action_callback: action is required to have 'value', so I know what to set.",
                               101, 'states_validate_action_callback', 'states')

    def states_do_action_callback(self, rule, action, **kwargs):
        """
        A callback to perform an action.

        :param rule: The complete rule being fired.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        return self.set(action['name'], action['value'])
