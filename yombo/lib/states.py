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
     raining = self._States['weather__raining']
   except:
     raining = None

   if raining is not True:
       # turn on sprinklers

   try:
     jeffIsHome = self._States['user_jeff_location']
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
   else:
     try:
       self._States.set_set_password('weather_is_cloudy', 'mySecretPassword123')  # set a write protect password
     except:
       pass  # unable to set write password? Who cares.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from collections import deque
from time import time

# Import Yombo libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboStateNoAccess, YomboStateNotFound
from yombo.core.log import getLogger
from yombo.utils.sqldict import SQLDict
from yombo.core.library import YomboLibrary

logger = getLogger("library.YomboStates")

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
        self.__History = yield SQLDict(self, 'History')
#        logger.info("Recovered YomboStates: {states}", states=self.__States)

    def _load_(self):
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

    def __repr__(self):
        states = {}
        for key, state in self.__States.iteritems():
            if state['readKey'] is not None:
                state['readKey'] = True
            if state['writeKey'] is not None:
                state['writeKey'] = True
            states[key] = state
        return states

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

    def get(self, key=None, password=None):
        """
        Get the value of a given state (key). If a password is required and not provided, returns YomboStateNoAccess.

        :param key: Name of state to check.
        :param password: Optional - Only required if state has a read password. See :py:func:`has_set_password`
        :return: Value of state
        """
#        logger.info("States: {state}", state=self.__States)
#        logger.info("State pass: {password}", key=key, password=password)
        if key is None:
            results = {}
            for item in self.__States:
                if self.__States[item]['readKey'] is None:
                    results[item] = self.__States[item]['value']
            return results

        if key in self.__States:
            if self.__States[key]['readKey'] is not None:
                if password is None:
                    raise YomboStateNoAccess("State is read protected with password. Use self.__States.get(key, password) to read.")
                elif self.__States[key]['readKey'] != password:
                    raise YomboStateNoAccess("State read password is invalid.")
#            logger.info("State get2: {key}  value: {value}", key=key, value=self.__States[key]['value'])
            return self.__States[key]['value']
        else:
            return None

    def set(self, key, value, password=None):
        """
        Set the value of a given state (key). If a password is required and not provided, returns YomboStateNoAccess.

        :param key: Name of state to set.
        :param value: Value to set state to. Can be string, list, or dictionary.
        :param password: Optional - Only required if state has a write password. See :py:func:`has_get_password`
        :return: Value of state
        """

#        logger.info("State set: {key} = {value}  pass: {password}", key=key, value=value, password=password)
        if key in self.__States:
            if self.__States[key]['writeKey'] is not None:
                if password is None:
                    raise YomboStateNoAccess("State is write protected with password. Use set(key, value, password) to write/update.")
                elif self.__States[key]['writeKey'] != password:
                    raise YomboStateNoAccess("State write password is invalid.")
            self.__States[key]['value'] = value
            self.__States[key]['updated'] = time()
            self.__set_history(key, self.__States[key]['value'], self.__States[key]['updated'])
        else:
            self.__States[key] = {
                'value': value,
                'updated': int(time()),
                'readKey': None,
                'writeKey': password
            }
            self.__set_history(key, self.__States[key]['value'], self.__States[key]['updated'])
        self.check_trigger(key, value)

    def __set_history(self, key, value, updated):
        data = {'value' : value, 'updated' : updated}
        if key in self.__History:
            self.__History[key].appendleft(data)
        else:
            self.__History[key] = deque([data], self.MAX_HISTORY)

    def get_history(self, key, position=1, password=None):
        """
        Returns a previous version of the state. Returns a dictionary with "value" and "updated" inside. See
        :py:func:`history_length` to deterine how many entries there are. Max of MAX_HISTORY (currently 100).

        :param key: Name of the state to get.
        :param position: How far back to go. 0 is current, 1 is previous, etc.
        :param password: Optional - Only required if state has a read password. See :py:func:`has_set_password`
        :return:
        """
        if key in self.__States:
            if self.__States[key]['readKey'] is not None:
                if password is None:
                    raise YomboStateNoAccess("State is read protected with password. Use self.__States.get_history(key, position, password) to read.")
                elif self.__States[key]['readKey'] != password:
                    raise YomboStateNoAccess("State read password is invalid.")
            if key in self.__History:
                if len(self.__History[key]) < position:
                    raise YomboStateNotFound("History doesn't exist. Only %s entries exist. %s" % len(self.__History[key]))
                return self.__History[key][position]
            else:
                raise YomboStateNotFound("Cannot get state history, does not exist: %s" % key)
        else:
            raise YomboStateNotFound("Cannot get state: %s not found" % key)

    def history_length(self, key, password=None):
        """
        Returns how many records a given state (key) has.

        :param key: Name of the state to check.
        :param password: Optional - Only required if state has a read password. See :py:func:`has_set_password`
        :return: How many records there are for a given state.
        :rtype: int
        """
        if key in self.__States:
            if self.__States[key]['readKey'] is not None:
                if password is None:
                    raise YomboStateNoAccess("State is read protected with password. Use self.__States.get_history(key, position, password) to read.")
                elif self.__States[key]['readKey'] != password:
                    raise YomboStateNoAccess("State read password is invalid.")
            if key in self.__History:
                return len(self.__History[key])
            else:
                raise YomboStateNotFound("Cannot get state history, no history for: %s" % key)
        else:
            raise YomboStateNotFound("Cannot get state: %s not found" % key)

    def has_get_password(self, key):
        """
        Checks if a password is required for 'get'.

        :param key: Name of the state to check.
        :return: True if a password exists.
        :rtype: bool
        """
        if key in self.__States:
            if self.__States[key]['readKey'] is None:
                return False
            else:
                return True
        else:
            raise YomboStateNotFound("Cannot get state: %s not found" % key)

    def has_set_password(self, key):
        """
        Checks if a password is required for 'set'.

        :param key: Name of the state to check.
        :return: True if a password exists.
        :rtype: bool
        """
        if key in self.__States:
            if self.__States[key]['writeKey'] is None:
                return False
            else:
                return True
        else:
            raise YomboStateNotFound("Cannot get state: %s not found" % key)

    def delete(self, key, password=None):
        """
        Deletes a status (key). Raises YomboStateNoAccess if write access password is required. Raises
        YomboStateNotFound if state not found.

        :param key: Name of the state to delete.
        :param password: Optional - Only required if state has a write password. See :py:func:`has_set_password`
        :return: None
        :rtype: None
        """
        if key in self.__States:
            if self.__States[key]['writeKey'] is not None:
                if password is None:
                    raise YomboStateNoAccess("State is write protected with password. Use delete(key, password) to delete.")
                elif self.__States[key]['writeKey'] != password:
                    raise YomboStateNoAccess("State write password is invalid.")
                del self.__States[key]
        else:
            raise YomboStateNotFound("Cannot delete state: %s not found" % key)
        return None

    def set_get_password(self, key, password):
        """
        Sets a get password for the given state (key).

        :param key: state to set password for
        :param password: new pasword
        :return: None
        """
        if key not in self.__States:
            YomboStateNotFound("Key: %s not found." % key)
        if self.__States[key]['readKey'] is not None:
            YomboStateNotFound("State read password is already set.  Use unset_read_password(key, password)")
        self.__States[key]['readKey'] = password
        return None

    def unset_get_password(self, key, password):
        """
        Remove a get password for the given state.

        :param key: state to remove password for
        :param password: Current password.
        :return: None
        """
        if key not in self.__States:
            YomboStateNotFound("Key: %s not found." % key)
        if self.__States[key]['readKey'] is None or self.__States[key]['readKey'] == password:
            self.__States[key]['readKey'] = None
        else:
            YomboStateNotFound("Invalid state read password supplied.")
        return None

    def set_set_password(self, key, password):
        """
        Sets a write (set) password for the given state.
        :param key: state to set write password
        :param password: new password
        :return: None
        """
        if key not in self.__States:
            YomboStateNotFound("Key: %s not found." % key)
        if self.__States[key]['writeKey'] is not None:
            YomboStateNotFound("State write password is already set.  Use unset_write_password(key, password)")
        self.__States[key]['writeKey'] = password
        return None

    def unset_set_password(self, key, password):
        """
        Remove a write password for the given state.

        :param key: state to remove write password
        :param password: current password
        :return: None
        """
        if key not in self.__States:
            YomboStateNotFound("Key: %s not found." % key)
        if self.__States[key]['writeKey'] is None or self.__States[key]['writeKey'] == password:
            self.__States[key]['writeKey'] = None
        else:
            YomboStateNotFound("Invalid state write password supplied.")
        return None

    # The remaining functions implement automation hooks. These should not be called by anything other than the
    # automation library!

    def check_trigger(self, key, value):
        """
        Not actually called by automation library, but it's used to send triggers to it.

        Called when a an State value is changed. Checks if a trigger should be fired. Uses the automation helper
        function for the heavy lifting.
        """
        results = self.automation.track_trigger_check_triggers('states', key, value)
        if results != False:
            logger.debug("I have a match! {results}", results=results)
            self.automation.track_trigger_basic_do_actions(results)
        else:
            logger.debug("trigger didn't match any trigger filters")

    def States_automation_trigger_list(self, **kwargs):
        """
        hook_automation_source_list called by the automation library to get a list of possible sources.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'states',
              'add_trigger_callback': self.states_add_trigger_callback,  # function to call to add a trigger
              'validate_callback': self.states_trigger_validate_callback,  # function to call to validate a trigger
              'get_value_callback': self.states_trigger_get_value_callback,  # get a value
            }
         ]

    def states_add_trigger_callback(self, rule, **kwargs):
        """
        Called to add a trigger.  We simply use the automation library for the heavy lifting.

        :param rule: The potential rule being added.
        :param kwargs: None
        :return:
        """
        self.automation.track_trigger_basic_add(rule['rule_id'], 'states', rule['trigger']['source']['name'])

    def states_trigger_validate_callback(self, rule, trigger, **kwargs):
        """
        A callback to check if a provided source is valid before being added as a possible source.

        :param kwargs: None
        :return:
        """
        if all( required in trigger['source'] for required in ['platform', 'name']):
            return True
        return False

    def states_trigger_get_value_callback(self, rule, source, **kwargs):
        """
        A callback to the value for platform "states". We simply just do a get based on key_name.

        :param rule: The potential rule being added.
        :param source: Dictionary containg everything that's in the 'source' section for trigger or condition
        :return:
        """
        key_name = source['name']
        if 'password' in source:
            return self.get(key_name, source['password'])
        else:
            return self.get(key_name)

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
              'validate_callback': self.states_action_validate_callback,  # function to call to validate an action is possible.
              'do_action_callback': self.states_do_action_callback  # function to be called to perform an action
            }
         ]

    def states_action_validate_callback(self, rule, action, **kwargs):
        """
        A callback to check if a provided action is valid before being added as a possible action.

        :param rule: The potential rule being added.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        print "################ in states_action_validate_callback"
        if key not in action:
            return False
        if value not in action:
            return False
        return True

    def states_do_action_callback(self, rule, action, **kwargs):
        """
        A callback to perform an action.

        :param rule: The complete rule being fired.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        key_name = source['name']
        if 'password' in source:
            return self.set(key_name, source['password'])
        else:
            return self.set(key_name)
