# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For end-user documentation, see: `States @ Module Development <https://yombo.net/docs/modules/states/>`_

.. seealso::

   * The :doc:`Atoms library </lib/atoms>` is used to store static data about the environment.
   * The :doc:`MQTT library </lib/mqtt>` is used to allow IoT devices to interact with states.
   
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
from collections import OrderedDict, deque
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time
from functools import partial

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboHookStopProcessing
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
from yombo.utils import global_invoke_all, pattern_search, is_true_false, epoch_to_string, random_string,\
    random_int, get_nested_dict, set_nested_dict

logger = get_logger("library.states")

class States(YomboLibrary, object):
    """
    Provides a base API to store common states among libraries and modules.
    """
    MAX_HISTORY = 100
    gateway_id = 'local'

    def __contains__(self, state_requested):
        """
        Checks to if a provided state exists.

            >>> if 'is.light' in self._States:

        :raises YomboWarning: Raised when request is malformed.
        :param state_requested: The state key to search for.
        :type state_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(state_requested)
            return True
        except Exception as e:
            return False

    def __getitem__(self, state_requested):
        """
        Attempts to find the state requested.

            >>> state_value = self._States['is.light']  #by id

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param state_requested: The state key to search for.
        :type state_requested: string
        :return: The value assigned to the state.
        :rtype: mixed
        """
        return self.get(state_requested)

    def __setitem__(self, state_requested, value):
        """
        Sets a state.
        
        .. note:: If this is a new state, or you wish to set a human filter for the value, use
           :py:meth:`set <States.set>` method.

            >>> self._States['module.local.name.hi'] = 'somee value'

        :raises YomboWarning: Raised when request is malformed.
        :param state_requested: The state key to replace the value for.
        :type state_requested: string
        :param value: New value to set.
        :type value: mixed
        """
        return self.set(state_requested, value)

    def __delitem__(self, state_requested):
        """
        Attempts to delete the state.

            >>> del self._States['module.local.name.hi']

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param state_requested: The state key to search for.
        :type state_requested: string
        :return: The value assigned to the state.
        :rtype: mixed
        """
        return self.delete(state_requested)

    def __iter__(self):
        """ iter states. """
        return self.__States[self.gateway_id].__iter__()

    def __len__(self):
        """
        Returns an int of the number of states defined.

        :return: The number of states defined.
        :rtype: int
        """
        return len(self.__States[self.gateway_id])

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo states library"

    def keys(self, gateway_id=None):
        """
        Returns the keys of the states that are defined.

        :return: A list of states defined. 
        :rtype: list
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        if gateway_id not in self.__States:
            return []
        return list(self.__States[gateway_id].keys())

    def items(self, gateway_id=None):
        """
        Gets a list of tuples representing the states defined.

        :return: A list of tuples.
        :rtype: list
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        if gateway_id not in self.__States:
            return []
        return list(self.__States[gateway_id].items())

    def values(self, gateway_id=None):
        """
        Gets a list of state values
        :return: list
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        if gateway_id not in self.__States:
            return []
        return list(self.__States[gateway_id].values())

    def _init_(self, **kwargs):
        self.library_phase = 1
        self.gateway_id = self._Configs.get('core', 'gwid', 'local', False)
        self.__States = {self.gateway_id: {}}
        self.automation_startup_check = {}
        self.db_save_states_data = deque()
        self.db_save_states_loop = LoopingCall(self.db_save_states)
        self.db_save_states_loop.start(random_int(60, .10), False)  # clean the database every 6 hours.

    def _load_(self, **kwargs):
        self.library_phase = 2
        self.init_deferred = Deferred()
        self.load_states()
        return self.init_deferred

    def _start_(self, **kwargs):
        self.module_phase = 3
        self.clean_states_loop = LoopingCall(self.clean_states_table)
        self.clean_states_loop.start(random_int(60*60*6, .10))  # clean the database every 6 hours.

        if self._States['loader.operating_mode'] == 'run':
            self.mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming, client_id='Yombo-states-%s' %
                                                                                            self.gateway_id)
            self.mqtt.subscribe("yombo/states/+/get")
            self.mqtt.subscribe("yombo/states/+/get/+")
            self.mqtt.subscribe("yombo/states/+/set")
            self.mqtt.subscribe("yombo/states/+/set/+")

    def _started_(self, **kwargs):
        self.library_phase = 4

    def _stop_(self, **kwargs):
        if hasattr(self, 'load_deferred'):
            if self.init_deferred is not None and self.init_deferred.called is False:
                self.init_deferred.callback(1)  # if we don't check for this, we can't stop!

    @inlineCallbacks
    def _unload_(self, **kwargs):
        yield self.db_save_states()

    @inlineCallbacks
    def load_states(self):
        states = yield self._LocalDB.get_states()

        for state in states:
            if state['name'] not in self.__States[self.gateway_id]:
                self.__States[self.gateway_id][state['name']] = {
                    'gateway_id': state['gateway_id'],
                    'value': state['value'],
                    'value_human': self.convert_to_human(state['value'], state['value_type']),
                    'value_type': state['value_type'],
                    'live': state['live'],
                    'created_at': state['created_at'],
                    'updated_at': state['updated_at'],
                }
        self.init_deferred.callback(10)

    def clean_states_table(self):
        """
        Periodically called to remove old records.

        :return:
        """
        self._LocalDB.clean_states_table()

    # def __repr__(self):
    #     states = {}
    #     for key, state in self.__States.iteritems():
    #         if state['readKey'] is not None:
    #             state['readKey'] = True
    #         if state['writeKey'] is not None:
    #             state['writeKey'] = True
    #         states[key] = state
    #     return states

    def exists(self, key, gateway_id):
        """
        Checks if a given state exists. Returns true or false.

        :param key: Name of state to check.
        :return: If state exists:
        :rtype: Bool
        """
        if gateway_id is None:
            gateway_id = self.gateway_id

        if key in self.__States[gateway_id]:
            return True
        return False

    def get_last_update(self, key, gateway_id=None):
        """
        Get the time() the key was created or last updated.

        :param key: Name of state to check.
        :return: Time() of last update
        :rtype: float
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        if key in self.__States[gateway_id]:
            return self.__States[gateway_id][key]['created_at']
        else:
            raise KeyError("Cannot get state time: %s not found" % key)

    def get2(self, key, human=None, full=None, gateway_id=None, set=None, **kwargs):
        """
        Like :py:meth:`get() <get>` below, however, this returns a callable to retrieve the value instead of an actual
        value. The callable can also be used to set the value of the state too. See
        example for usage details.

        **Usage**:

        .. code-block:: python

           some_state = self._States.get2("some_state")
           logger.info("The state or some_state is: {state}", state=some_state()
           # set a new state value for 'some_state'.
           some_state(set="New label")

        .. versionadded:: 0.13.0

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param key: Name of state to get.
        :type key: string
        :param human: If true, returns a state for human consumption.
        :type human: bool
        :param full: If true, Returns all data about the state. If false, just the value.
        :type full: bool
        :return: Value of state
        """

        if set is not None:
            self.set(key, set, gateway_id=gateway_id, **kwargs)
            return set

        self.get(key, human, full, gateway_id=gateway_id)

        return partial(self.get, key, human, full, gateway_id=gateway_id)

    def get(self, key, human=None, full=None, gateway_id=None):
        """
        Get the value of a given state (key).

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param key: Name of state to get.
        :type key: string
        :param human: If true, returns a state for human consumption.
        :type human: bool
        :param full: If true, Returns all data about the state. If false, just the value.
        :type full: bool
        :return: Value of state
        """
        # logger.debug('states:get: {key} = {value}', key=key)
        if gateway_id is None:
            gateway_id = self.gateway_id

        self._Statistics.increment("lib.states.get", bucket_size=15, anon=True)
        search_chars = ['#', '+']
        if any(s in key for s in search_chars):
            if gateway_id not in self.__States:
                return {}
            results = pattern_search(key, self.__States[gateway_id])
            if len(results) > 1:
                values = {}
                for item in results:
                    values[item] = self.__States[gateway_id][item]
                return values
            else:
                raise KeyError("Searched for atoms, none found.")
        if human is True:
            return self.__States[gateway_id][key]['value_human']
        elif full is True:
            return self.__States[gateway_id][key]
        else:
            return self.__States[gateway_id][key]['value']

    def get_states(self, gateway_id=None):
        """
        Returns a copy of the active states.

        :param key: Name of state to check.
        :return: Value of state
        """
        if gateway_id is None:
            return self.__States.copy()
        if gateway_id is None:
            gateway_id = self.gateway_id
        if gateway_id in self.__States:
            return self.__States[gateway_id].copy()
        else:
            return {}

    @inlineCallbacks
    def set(self, key, value, value_type=None, function=None, arguments=None, gateway_id=None):
        """
        Set the value of a given state (key).

        **Hooks called**:

        * _states_set_ : Sends kwargs: *key* - The name of the state being set. *value* - The new value to set.

        :param key: Name of state to set.
        :param value: Value to set state to. Can be string, list, or dictionary.
        :param value_type: If set, allows a human filter to be applied for display.
        :param function: If this a living state, provide a function to be called to get value. Value will be used
          to set the initial value.
        :param arguments: kwarg (arguments) to send to function.
        :return: Value of state
        """
        # logger.debug("Saving state: {key} = {value}", key=key, value=value)
        if gateway_id is None:
            gateway_id = self.gateway_id

        search_chars = ['#', '+']
        if any(s in key for s in search_chars):
            raise YomboWarning("state keys cannot have # or + in them, reserved for searching.")

        if gateway_id not in self.__States:
            self.__States[gateway_id] = {}
        if key in self.__States[gateway_id]:
            is_new = False
            # If state is already set to value, we don't do anything.
            self.__States[gateway_id][key]['updated_at'] = int(round(time()))
            if self.__States[gateway_id][key]['value'] == value:
                return
            self._Statistics.increment("lib.states.set.update", bucket_size=60, anon=True)
        else:
            is_new = True
            self.__States[gateway_id][key] = {
                'gateway_id': gateway_id,
                'created_at': int(time()),
                'updated_at': int(time()),
                'live': False,
            }
            self._Statistics.increment("lib.states.set.new", bucket_size=60, anon=True)

        # Call any hooks
        try:
            state_changes = yield global_invoke_all('_states_preset_', **{'called_by': self,
                                                                          'key': key,
                                                                          'value': value,
                                                                          'gateway_id': gateway_id
                                                                          }
                                                    )
        except YomboHookStopProcessing as e:
            logger.warning("Not saving state '{state}'. Resource '{resource}' raised' YomboHookStopProcessing exception.",
                           state=key, resource=e.by_who)
            returnValue(None)

        self.__States[gateway_id][key]['value'] = value
        self.__States[gateway_id][key]['function'] = function
        self.__States[gateway_id][key]['arguments'] = arguments
        if is_new is True or value_type is not None:
            self.__States[gateway_id][key]['value_type'] = value_type
        if is_new is True or function is not None:
            if function is None:
                self.__States[gateway_id][key]['live'] = False
            else:
                self.__States[gateway_id][key]['live'] = True

        self.__States[gateway_id][key]['value_human'] = self.convert_to_human(value, value_type)

        # Call any hooks
        try:
            state_changes = yield global_invoke_all('_states_set_',
                                                    **{'called_by': self,
                                                       'key': key,
                                                       'value': value,
                                                       'value_full': self.__States[gateway_id][key],
                                                       'gateway_id': gateway_id})
        except YomboHookStopProcessing:
            pass


        if gateway_id == self.gateway_id:
            self.db_save_states_data.append((key, self.__States[gateway_id][key]))

        self.check_trigger(gateway_id, key, value)  # Check if any automation items need to fire!

    @inlineCallbacks
    def db_save_states(self):
        """
        Called periodically and on exit to save states to database.

        :return:
        """
        to_save = deque()

        while True:
            try:
                key, data = self.db_save_states_data.popleft()
                if data['live'] is True:
                    live = 1
                else:
                    live = 0

                od = OrderedDict()
                od['gateway_id'] = data['gateway_id']
                od['name'] = key
                od['value'] = data['value']
                od['value_type'] = data['value_type']
                od['live'] = live
                od['created_at'] = data['created_at']
                od['updated_at'] = data['updated_at']
                to_save.append(od)
            except IndexError:
                break
        if len(to_save) > 0:
            yield self._LocalDB.save_state_bulk(to_save)

    @inlineCallbacks
    def set_from_gateway_communications(self, key, values):
        """
        Used by the gateway coms (mqtt) system to set state values.
        :param key:
        :param values:
        :return:
        """
        gateway_id = values['gateway_id']
        if gateway_id == self.gateway_id:
            return
        if gateway_id not in self.__States:
            self.__States[gateway_id] = {}
        self.__States[values['gateway_id']][key] = {
            'gateway_id': values['gateway_id'],
            'value': values['value'],
            'value_human': values['value_human'],
            'value_type': values['value_type'],
            'live': False,
            'created_at': values['created_at'],
            'updated_at': values['updated_at'],
        }

        # Call any hooks
        try:
            yield global_invoke_all('_states_set_',
                                    **{'called_by': self,
                                       'key': key,
                                       'value': values['value'],
                                       'value_full': self.__States[gateway_id][key],
                                       'gateway_id': gateway_id,
                                       }
                                    )
        except YomboHookStopProcessing:
            pass

    def convert_to_human(self, value, value_type):
        if value_type == 'bool':
            results = is_true_false(value)
            if results is not None:
                return results
            else:
                return value

        elif value_type == 'epoch':
            return epoch_to_string(value)
        else:
            return value

    @inlineCallbacks
    def get_history(self, key, offset=None, limit=None, gateway_id=None):
        """
        Returns a previous version of the state. Returns a dictionary with "value" and "updated" inside. See
        :py:func:`history_length` to deterine how many entries there are. Max of MAX_HISTORY (currently 100).

        :param key: Name of the state to get.
        :param offset: How far back to go. 0 is current, 1 is previous, etc.
        :limit limit: How many records to provide
        :return:
        """
        if gateway_id is None:
            gateway_id = self.gateway_id

        if offset is None:
            offset = 1
        if limit is None:
            limit = 1
        results = yield self._LocalDB.get_state_history(key, limit, offset, gateway_id=gateway_id)
        if len(results) >= 1:
            returnValue(results)
        else:
            returnValue(None)

    def history_length(self, key):
        """
        Returns how many records a given state (key) has.

        :param key: Name of the state to check.
        :return: How many records there are for a given state.
        :rtype: int
        """
        results = yield self._LocalDB.get_state_count(key)
        returnValue(results)

    def delete(self, key, gateway_id=None):
        """
        Deletes a status (key).
        KeyError if state not found.

        :raises KeyError: Raised when request is not found.
        :param key: Name of the state to delete.
        :return: None
        :rtype: None
        """
        if gateway_id is None:
            gateway_id = self.gateway_id

        if key in self.__States:
            del self.__States[gateway_id][key]
        else:
            raise KeyError("Cannot delete state: %s not found" % key)
        return None

    def mqtt_incoming(self, topic, payload, qos, retain):
        """
        Processes incoming MQTT requests. See `MQTT @ Module Development <https://yombo.net/docs/modules/mqtt/>`_

        Examples:

        * /yombo/states/statename/get  - returns a json (preferred)
        * /yombo/states/statename/get abc1234 - returns a json, sends a message ID as a string for tracking
          * A message can only be returned with the above items, cannot be used when requesting a single value.
        * /yombo/states/statename/get/value - returns a string
        * /yombo/states/statename/get/value_type - returns a string
        * /yombo/states/statename/get/value_human - returns a string
        * /yombo/states/statesname/set {"value":"working","value_type":"string"}

        :param topic:
        :param payload:
        :param qos:
        :param retain:
        :return:
        """
        #getting
        #  0       1       2      3      optional payload, one of:
        # yombo/states/statename/get {value (default), value_type, value_human, all (response in json)}

        #setting
        #  0       1       2      3       payload
        # yombo/states/statename/set    new value
        payload = str(payload)

        parts = topic.split('/', 10)
        # print("Yombo States got this: %s / %s" % (topic, parts))
        # requested_state = urllib.unquote(parts[2])
        requested_state = parts[2].replace("$", ".")
        # requested_state = decoded_state.replace("_", " ")
        if len(parts) <= 3 or len(parts) > 5:
            logger.warn("States received an invalid MQTT topic, discarding. Too long or too short. '%s'" % topic)
            return

        if  parts[3] not in ('get', 'set'):
            # logger.warn("States received an invalid MQTT topic, discarding. Must have either 'set' or 'get'. '%s'" % topic)
            return


        if requested_state not in self.__States:
            self.mqtt.publish('yombo/states/%s/get_response' % parts[2], str('MQTT Error: state not found'))
            return

        state = self.__States[self.gateway_id][requested_state]

        if parts[3] == 'get':
            request_id = random_string(length=30)

            if len(payload) > 0:
                try:
                    payload = json.loads(payload)
                    if 'request_id' in payload:
                        if len(payload['request_id']) > 100:
                            self.mqtt.publish('yombo/states/%s/get_response' % parts[2],
                                              str('MQTT Error: request id too long'))
                            return
                except Exception:
                    pass

            if len(parts) == 4 or (len(parts) == 5 and payload == 'all'):
                response = {
                    'value': state['value'],
                    'value_type': state['value_type'],
                    'value_human': state['value_human'],
                    'request_id': request_id,
                }
                output = json.dumps(response, separators=(',', ':'))
                self.mqtt.publish('yombo/states/%s/get_response' % parts[2],
                                  str(output))
                return
            elif len(parts) == 5:

                if payload == '':
                    payload = 'value'
                if payload not in ('value', 'value_type', 'value_human'):
                    logger.warn(
                        "States received an invalid MQTT get request, invalid request type: '%s'" % payload)
                    return

                output = ""
                if payload == 'value':
                    if isinstance(state['value'], dict) or isinstance(state['value'], list):
                        output = json.dumps(state['value'], separators=(',', ':'))
                    else:
                        output = state['value']
                elif payload == 'value_type':
                    output = state['value_type']
                elif payload == 'value_human':
                    output = state['value_human']

                    self.mqtt.publish('yombo/states/%s/get_response/%s' % (parts[2], payload), str(output))
                return


        elif parts[3] == 'set':
            request_id = random_string(length=30)

            try:
                data = json.loads(payload)
                if 'request_id' in data:
                    request_id = data['request_id']

                if 'value' not in data:
                    self.mqtt.publish('yombo/states/%s/set_response' % parts[2],
                                      str(
                                          'invalid (%s): Payload must contain json with these: value, value_type, and request_id' % request_id)
                                      )

                for key in list(data.keys()):
                    if key not in ('value', 'value_type', 'request_id'):
                        self.mqtt.publish('yombo/states/%s/set_response' % parts[2],
                                          str(
                                              'invalid (%s): json contents can only contain value, value_type and request_id' %
                                              request_id)
                                          )

                if 'value_type' not in data:
                    data['value_type'] = None

                self.set(requested_state, data['value'], value_type=data['value_type'], function=None, arguments=None)
                return
            except Exception:
                self.mqtt.publish('yombo/states/%s/set_response' % parts[2],
                                  str(
                                      'invalid (%s): Payload must contain json with these: value, value_type, and request_id' % request_id)
                                  )
                return


    ##############################################################################################################
    # The remaining functions implement automation hooks. These should not be called by anything other than the  #
    # automation library!                                                                                        #
    #############################################################################################################

    def check_trigger(self, gateway_id, name, value):
        """
        Called by the states.set function when a new value is set. It asks the automation library if this key is
        trigger, and if so, fire any rules.

        True - Rules fired, fale - no rules fired.
        """
        logger.debug("check_trigger. {name} = {value}", name=name, value=value)
        if self.library_phase >= 2:
            logger.debug("check_trigger running... {name} = {value}", name=name, value=value)
            results = self._Automation.triggers_check(['states', gateway_id, name], value)

    def _automation_source_list_(self, **kwargs):
        """
        hook_automation_source_list called by the automation library to get a list of possible sources.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'states',
              'description': 'Allows states to be used as a source (trigger).',
              'validate_source_callback': self.states_validate_source_callback,  # function to call to validate a trigger
              'add_trigger_callback': self.states_add_trigger_callback,  # function to call to add a trigger
              'startup_trigger_callback': self.states_startup_trigger_callback,  # function to call to check all triggers
              'get_value_callback': self.states_get_value_callback,  # get a value
              'field_details': [
                  {
                  'label': 'name',
                  'description': 'The name of the state to monitor.',
                  'required': True
                  }
              ]
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
        if 'gateway_id' in rule['trigger']['source']:
            gateway_id = rule['trigger']['source']['gateway_id']
        else:
            gateway_id = self.gateway_id
        # if rule['run_on_start'] is True:

        keys = ['states', gateway_id, rule['trigger']['source']['name']]
        self._Automation.triggers_add(rule['rule_id'], keys)
        if 'run_on_start' in rule:
            keys = [gateway_id, rule['trigger']['source']['name']]
            set_nested_dict(self.automation_startup_check, keys, True)

        logger.debug("states_add_trigger_callback.automation_startup_check: {automation_startup_check}",
                     automation_startup_check=self.automation_startup_check)

    def states_startup_trigger_callback(self):
        """
        Called when automation rules are active. Check for any automation rules that are marked with run_on_start

        :return:
        """
        # logger.debug("states_startup_trigger_callback: {automation_startup_check}",
        #             automation_startup_check=self.automation_startup_check)
        for gateway_id, keys in self.automation_startup_check.items():
            # logger.debug("states_startup_trigger_callback keys: keys {keys}",
            #             keys=keys)
            for name, name_value in keys.items():
                # logger.debug("states_startup_trigger_callback keys: name {name} = {value}",
                #             name=name, value=name_value)
                if name_value is True:
                    try:
                        value = self.__States[gateway_id][name]['value']
                        # logger.debug("states_startup_trigger_callback state {name} = {value}", name=name, value=value)
                        self.check_trigger(gateway_id, name, value)
                    except Exception as e:
                        pass

    def states_get_value_callback(self, rule, portion, **kwargs):
        """
        A callback to the value for platform "states". We simply just do a get based on key_name.

        :param rule: The potential rule being added.
        :param portion: Dictionary containg everything in the portion of rule being fired. Includes source, filter, etc.
        :return:
        """
        if 'gateway_id' in rule['source']:
            gateway_id = rule['source']['gateway_id']
        else:
            gateway_id = self.gateway_id

        return self.get(rule['source']['name'], gateway_id=gateway_id)

    def _automation_action_list_(self, **kwargs):
        """
        hook_automation_action_list called by the automation library to list possible actions this module can
        perform.

        This implementation allows automation rules set easily set state values.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'states',
              'description': 'Allows states to be changed as an action.',
              'validate_action_callback': self.states_validate_action_callback,  # function to call to validate an action is possible.
              'do_action_callback': self.states_do_action_callback,  # function to be called to perform an action
              'field_details': [
                  {
                  'label': 'name',
                  'description': 'The name of the state to change.',
                  'required': True
                  },
                  {
                  'label': 'value',
                  'description': 'The value that should be set.',
                  'required': True
                  }
              ]
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
        if all( required in action for required in ['name', 'value']):
            return True
        raise YomboWarning("In states_validate_action_callback: action is required to have 'name' and 'value', so I know what to set.",
                           101, 'states_validate_action_callback', 'states')

    def states_do_action_callback(self, rule, action, **kwargs):
        """
        A callback to perform an action.

        :param rule: The complete rule being fired.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        logger.debug("Automation rule fired. Setting:  {name} = {value}", name=action['name'], value=action['value'])
        results = action['name'].split(":::")
        if len(results) == 1:
            gateway_id = self.gateway_id
            name = results[0]
        else:
            gateway_id = results[0]
            name = results[1]
        return self.set(name, action['value'], gateway_id=gateway_id)
