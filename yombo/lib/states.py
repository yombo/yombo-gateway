"""
The states interface provides a common method to share automation states. States can include any
arbitrary information. This can include weather events such as isRaining, sprinklersOn, isAlarmArmed,
etc.

Yombo does not specify any naming standards and is left to the module developer. Developers should
take care not to overwrite another state. To prevent states from accidently overridden, a write
password can be set. This should help prevent another module modifying a state that it shouldn't
be modifying. For example, a module that manages sprinklers can set a write password.

A reference is added to every module and library and can be accessed as: "self.__States"

Loose guidelines:

All variables should start with the the type of state being stored, such as: weather, alarm, garagedoor, etc.

* Don't use multiple states when one is good enough. Below, there is "houseIsWholeHouseFanOn" and
  "houseStateWholeHouseFan". This is redundant, just use one.
* True/False values should start with "Is", such as: weatherIsRaining=True, alarmIsRinging=False,
  houseIsOccupied=True, GarageDoorIsAllClosed=True, houseIsWholeHouseFanOn=False
  * Don't use "True" or "False", use True or False.
  * When practical, don't use 1 or 0, use True or False.
* Items holding the status of state, should simply add 'State': alarmState="Disarmed",
  houseStateWholeHouseFan="Low", houseState="Occupied"
* Items holding multiple values should be stored within a dict, even though a list
  would work. This allows quick upserts:
  garageDoorDict = {1: 'Closed', 2:'Open'}
  garageDoorDict[4] = "Open"
* Don't set any values to None or "None". If None is needed, simply delete the state.

*Usage**:

.. code-block:: python

   try:
     raining = self._States['weatherIsRaining']
   except:
     raining = None

   if raining is not True:
       # turn on sprinklers

   try:
     jeffIsHome = self._States['JeffIsHome']
   except:
     jeffIsHome = None

   if jeffIsHome is True:
       # turn on HVAC
   elif jeffIsHome is false:
       # turn off HVAC
   else:
       # we don't know if Jeff is home or not, leave HVAC alone

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
from collections import deque
from time import time

from yombo.core.exceptions import YomboStateNoAccess, YomboStateNotFound
from yombo.core.log import getLogger
from yombo.core.sqldict import SQLDict
from yombo.core.library import YomboLibrary
logger = getLogger("library.YomboStates")

class States(YomboLibrary, object):
    """
    Provides a base API to store common states among libraries and modules.
    """
    def _init_(self, loader):
        self._ModDescription = "Yombo States API"
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "https://yombo.net"
        self.automation = self._Libraries['automation']

        self.__States = {}
        self.__History = SQLDict(self, 'History')
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
        if key in self.__States:
            return True
        return False

    def __str__(self):
        return "member of Test"

    def __repr__(self):
        return "member of Test"

    def exists(self, key):
        if key in self.__States:
            return True
        return False

    def getTime(self, key):
        if key in self.__States:
            return self.__States[key]['updated']
        else:
            raise YomboStateNotFound("Cannot get state time: %s not found" % key)

    def get(self, key=None, password=None):
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
#        logger.info("State set: {key} = {value}  pass: {password}", key=key, value=value, password=password)
        if key in self.__States:
            if self.__States[key]['writeKey'] is not None:
                if password is None:
                    raise YomboStateNoAccess("State is write protected with password. Use set(key, value, password) to write/update.")
                elif self.__States[key]['writeKey'] != password:
                    raise YomboStateNoAccess("State write password is invalid.")
            self.__States[key]['value'] = value
            self.__States[key]['updated'] = time()
            self.__setHistory(key, self.__States[key]['value'], self.__States[key]['updated'])
        else:
            self.__States[key] = {
                'value' : value,
                'updated' : int(time()),
                'readKey' : None,
                'writeKey' : password
            }
            self.__setHistory(key, self.__States[key]['value'], self.__States[key]['updated'])
        self.check_trigger(key, value)

    def __setHistory(self, key, value, updated):
        data = {'value' : value, 'updated' : updated}
        if key in self.__History:
            self.__History[key].appendleft(data)
        else:
            self.__History[key] = deque([data], 50)

    def getHistory(self, key, position=1, password=None):
        if key in self.__States:
            if self.__States[key]['readKey'] is not None:
                if password is None:
                    raise YomboStateNoAccess("State is read protected with password. Use self.__States.getHistory(key, position, password) to read.")
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

    def delete(self, key, password=None):
        if key in self.__States:
            if self.__States[key]['writeKey'] is not None:
                if password is None:
                    raise YomboStateNoAccess("State is write protected with password. Use delete(key, password) to delete.")
                elif self.__States[key]['writeKey'] != password:
                    raise YomboStateNoAccess("State write password is invalid.")
                del self.__States[key]

    def setReadPassword(self, key, password):
        if key not in self.__States:
            YomboStateNotFound("Key: %s not found." % key)
        if self.__States[key]['readKey'] is not None:
            YomboStateNotFound("State read password is already set.  Use unsetReadPassword(key, password)")
        self.__States[key]['readKey'] = password

    def unsetReadPassword(self, key, password):
        if key not in self.__States:
            YomboStateNotFound("Key: %s not found." % key)
        if self.__States[key]['readKey'] is None or self.__States[key]['readKey'] == password:
            self.__States[key]['readKey'] = None
        else:
            YomboStateNotFound("Invalid state read password supplied.")

    def setWritePassword(self, key, password):
        if key not in self.__States:
            YomboStateNotFound("Key: %s not found." % key)
        if self.__States[key]['writeKey'] is not None:
            YomboStateNotFound("State write password is already set.  Use unsetWritePassword(key, password)")
        self.__States[key]['writeKey'] = password

    def unsetWritePassword(self, key, password):
        if key not in self.__States:
            YomboStateNotFound("Key: %s not found." % key)
        if self.__States[key]['writeKey'] is None or self.__States[key]['writeKey'] == password:
            self.__States[key]['writeKey'] = None
        else:
            YomboStateNotFound("Invalid state write password supplied.")

    def check_trigger(self, key, value):
        """
        Called when a an State value is changed. Checks if a trigger should be fired. Uses the automation helper
        function for the heavy lifting.
        """
        results = self.automation.track_trigger_check_triggers('states', key, value)
        if results != False:
            logger.debug("I have a match! {results}", results=results)
            self.automation.track_trigger_basic_do_actions(results)
        else:
            logger.debug("trigger didn't match any trigger filters")

    def States_automation_source_list(self, **kwargs):
        """
        hook_automation_source_list called by the automation library to get a list of possible sources.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'states',
              'add_trigger_callback': self.states_add_trigger_callback,  # function to call to add a trigger
              'validate_callback': self.states_validate_callback,  # function to call to validate a trigger
              'get_value_callback': self.states_get_value_callback,  # get a value
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

    def states_validate_callback(self, rule, **kwargs):
        """
        A callback to check if a provided source is valid before being added as a possible source.

        :param kwargs: None
        :return:
        """
        if all( required in rule['trigger']['source'] for required in ['platform', 'name']):
            return True
        return False

    def states_get_value_callback(self, rule, key_name, **kwargs):
        """
        A callback to the value for platform "atom". We simply just do a get based on key_name.

        :param rule: The potential rule being added.
        :param key_name: The atom key we'll get get the value.
        :param kwargs: None
        :return:
        """
        return self.get(key_name)