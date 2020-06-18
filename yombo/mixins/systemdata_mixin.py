# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Mixin class for for atoms and states. These two libraries perform nearly the same function,
but with different data sets.

.. seealso::

   This mixin in used by the following libraries:

   * :doc:`Atoms </lib/atoms>`
   * :doc:`States </lib/states>`

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/mixins/systemdata_mixin.html>`_
"""
# Import python libraries
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import SENTINEL
from yombo.core.exceptions import YomboWarning, YomboHookStopProcessing
from yombo.utils import pattern_search, is_true_false, get_yombo_instance_type
from yombo.utils.caller import caller_string
import yombo.utils.converters as converters
from yombo.utils.hookinvoke import global_invoke_all

# RANDOM_DEFAULT_STRING = "Oaj(EpC~`c5Z!;DL%^%MSL6'>Pp3>$2`*p&U;Xo(:~,LNQ-(e;hq5k,UW%n8Uf=tN#{#G/DXTb,aUblCz*"
# SENTINEL = object()


class SystemDataChildMixin:
    """
    Used for individual state or atom instances.
    """
    def load_attribute_values_pre_process(self, incoming: dict) -> None:
        if "gateway_id" not in incoming:
            incoming["gateway_id"] = self._gateway_id

    def sync_allowed(self):
        """
        We only save local atoms that are local, or cluster, or global.
        :return:
        """
        if self.gateway_id in (self._gateway_id, "cluster", "global"):
            return True
        return False


class SystemDataParentMixin:
    """
    Mixing for Atoms and States libraries. This handles the bulk of the processing, including getting and setting
    values.
    """
    _storage_pickled_fields: ClassVar[Dict[str, str]] = {"value": "msgpack"}  # preserve int/string/dict/etc.

    def __delitem__(self, item_requested):
        """
        Attempts to delete the system data item.

            >>> del self._States["module.local.name.hi"]

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param item_requested: The data item key to search for.
        :type item_requested: string
        :return: The value assigned to the data item.
        :rtype: mixed
        """
        return self.delete(item_requested)

    def __getitem__(self, item_requested: str):
        """
        Looks for the atom/state and returns it's value, not the instance. Use get() for additional features.

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when the requested item is not found.
        :param item_requested: The id, label, or machine_label, or other attribute to search for.
        :return: Returns the instance requested.
        """
        return self.get(item_requested, instance=False)

    def __len__(self):
        """
        Returns an int of the number of data items defined.

        :return: The number of data items defined.
        :rtype: int
        """
        return len(getattr(self, self._storage_attribute_name)[self._gateway_id])

    def keys(self, gateway_id=None):
        """
        Returns the keys of the data items that are defined.

        :return: A list of data items defined.
        :rtype: list
        """
        if gateway_id is None:
            gateway_id = self._gateway_id
        if gateway_id not in getattr(self, self._storage_attribute_name):
            return []
        return getattr(self, self._storage_attribute_name)[gateway_id].keys()

    def items(self, gateway_id=None):
        """
        Gets a list of tuples representing the data items defined.

        :return: A list of tuples.
        :rtype: list
        """
        if gateway_id is None:
            gateway_id = self._gateway_id
        if gateway_id not in getattr(self, self._storage_attribute_name):
            return []
        return getattr(self, self._storage_attribute_name)[gateway_id].items()

    def values(self, gateway_id=None):
        """
        Gets a list of data item values
        :return: list
        """
        if gateway_id is None:
            gateway_id = self._gateway_id
        if gateway_id not in getattr(self, self._storage_attribute_name):
            return []
        return getattr(self, self._storage_attribute_name)[gateway_id].values()

    def sorted(self, gateway_id: Optional[str] = None, key: Optional[str] = None) -> dict:
        """
        Returns an dict of the data items sorted by name. Default: machine_label

        :param gateway_id: The gateway to get the data items for, default is the local gateway.
        :param key: Key to sort by, default 'machine_label'.
        :return: All data items, sorted by data item name.
        """
        if gateway_id is None:
            gateway_id = self._gateway_id

        if key is None:
            key = self._storage_attribute_sort_key

        items_to_sort = getattr(self, self._storage_attribute_name)[gateway_id]
        return dict(sorted(iter(items_to_sort.items()), key=lambda i: getattr(i[1], key)))

    @inlineCallbacks
    def update(self, requested_item, data, request_context: Optional[str] = None,
               authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None,
               **kwargs):
        """
        Updates the requested data.

        :param requested_item:
        :param data:
        :param kwargs:
        :return:
        """
        # print(f"update: data: {data}")
        # print(f"authentication: {authentication}")
        item = self.get(requested_item, instance=True)
        args = {
            "key": getattr(item, self._storage_primary_field_name),
            "value": data["value"],
        }
        # print(f"systemdata_mixin: item: {item} - {item.__dict__}")
        allowed_args = ["value_human", "value_type"]
        for arg in allowed_args:
            if arg in kwargs:
                args[arg] = kwargs[arg]
        args["request_context"] = request_context
        args["authentication"] = authentication
        yield self.set_yield(**args)
        return item

    def get_last_update(self, key, gateway_id=None):
        """
        Get the time() the data item was created or last updated.

        :param key: Name of data item to check.
        :return: Time() of last update
        :rtype: float
        """
        data = getattr(self, self._storage_attribute_name)
        if gateway_id is None:
            gateway_id = self._gateway_id
        if key in data[gateway_id]:
            return data[gateway_id][key]["created_at"]
        else:
            raise KeyError(f"Cannot get {self._storage_label_name} time: {key} not found")

    # def get_all(self, gateway_id=None, filters=None):
    #     """
    #     Shouldn"t really be used. Just returns a _copy_ of all the data items.
    #
    #     :return: A dictionary containing all data items.
    #     :rtype: dict
    #     """
    #     results = []
    #
    #
    #     data = getattr(self, self._storage_attribute_name)
    #     if gateway_id is None:
    #         return data.copy()
    #     if gateway_id in data:
    #         return data[gateway_id].copy()
    #     else:
    #         return {}

    def get(self, item_requested: str, default: Optional[Any] = SENTINEL, gateway_id: Optional[str] = None,
            instance: Optional[bool] = None):
        """
        Get the value of a given data item (key).

        :raises KeyError: Raised when request is not found.
        :param item_requested: Name of data item to retrieve.
        :param default: Default value to return in a data instance if the requested item is missing.
        :param gateway_id: The gateway_id to reference.
        :param instance: If True, returns the object (atom/state), versus just the value.
        """
        if gateway_id is None or gateway_id.lower() == 'self':
            gateway_id = self._gateway_id

        # if self._Loader.operating_mode != "run":
        #     gateway_id = self._gateway_id

        data = getattr(self, self._storage_attribute_name)

        if gateway_id not in data:
            raise KeyError(f"gateway_id '{gateway_id}' not found in '{self._storage_attribute_name}'")

        self._Statistics.increment(f"lib.{self._storage_attribute_name}.get", bucket_size=15, anon=True)
        if any(s in item_requested for s in ["#", "+"]):
            if gateway_id not in data:
                return {}
            results = pattern_search(item_requested, data[gateway_id])
            if len(results) > 1:
                values = {}
                for item in results:
                    if instance is True:
                        values[item] = data[gateway_id][item]
                    else:
                        values[item] = data[gateway_id][item].value
                return values
            else:
                raise KeyError(f"Searched for {self._storage_attribute_name}, none found: {item_requested}")

        if item_requested in data[gateway_id]:
            data[gateway_id][item_requested]. update({"last_access_at": int(time())})
            if instance is True:
                return data[gateway_id][item_requested]
            else:
                return data[gateway_id][item_requested].value
        elif default is SENTINEL:
            raise KeyError(f"'{item_requested}' not found in '{self._storage_label_name}'")
        else:
            if instance is True:
                raise KeyError(f"'{item_requested}' not found in '{self._storage_label_name}',"
                               f" cannot return instance using a default value.")
            else:
                return default

    def set(self, key, value, value_human=None, value_type=None, gateway_id=None,
            request_by: Optional[str] = None, request_by_type: Optional[str] = None,
            request_context: Optional[str] = None,
            authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None,
            created_at: Optional[int] = None, updated_at: Optional[int] = None):
        """
        Set the value of a given data item.

        Note: This function calls set_yield. If an atom/state needs to be set immediately, use:  yield set_yield()

        **Hooks called**:

        * _atoms_set_ / _states_set_: Sends kwargs "key", and "value". *key* is the name of the data item being set
           and *value* is the new value to set.

        :raises YomboWarning: Raised when request is malformed.
        :param key: Name of data item to set.
        :type key: string
        :param value: The value to set
        :type value: mixed
        :param value_human: What to display to mere mortals.
        :type value_human: mixed
        :param value_type: Data type to help with display formatting. Should be: str, dict, list, int, float, epoch
        :type value_type: string
        :param gateway_id: Gateway ID this item belongs to, defaults to local gateway.
        :type gateway_id: string
        :param request_by: Who created the Authkey. "alexamodule"
        :param request_by_type: What type of item created it: "module"
        :param request_context: Some additional information about where the request comes from.
        :param authentication: An auth item such as a websession or authkey.
        :param created_at: Change the default created_at, typically used internally.
        :type created_at: int
        :param updated_at: Change the default updated_at, typically used internally.
        :type updated_at: int
        :return: Data item instance
        :rtype: instance
        """
        reactor.callLater(0.0001, self.set_yield, key, value, value_human=value_human, value_type=value_type,
                          gateway_id=gateway_id, request_by=request_by, request_by_type=request_by_type,
                          request_context=request_context, authentication=authentication, created_at=created_at,
                          updated_at=updated_at)

    @inlineCallbacks
    def set_yield(self, key, value, value_human=None, value_type=None, gateway_id=None,
                  request_by: Optional[str] = None, request_by_type: Optional[str] = None,
                  request_context: Optional[str] = None,
                  authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None,
                  created_at: Optional[int] = None, updated_at: Optional[int] = None,
                  dont_save: Optional[bool] = None):
        """
        Get the value of a given data item.

        **Hooks called**:

        * _atoms_set_ / _states_set_: Sends kwargs "key", and "value". *key* is the name of the data item being set
           and *value* is the new value to set.

        :raises YomboWarning: Raised when request is malformed.
        :param key: Name of data item to set.
        :type key: string
        :param value: The value to set
        :type value: mixed
        :param value_human: What to display to mere mortals.
        :type value_human: mixed
        :param value_type: Data type to help with display formatting. Should be: str, dict, list, int, float, epoch
        :type value_type: string
        :param gateway_id: Gateway ID this item belongs to, defaults to local gateway.
        :type gateway_id: string
        :param request_by: Who created the Authkey. "alexamodule"
        :param request_by_type: What type of item created it: "module"
        :param request_context: Some additional information about where the request comes from.
        :param authentication: An auth item such as a websession or authkey.
        :param created_at: Change the default created_at, typically used internally.
        :type created_at: int
        :param updated_at: Change the default updated_at, typically used internally.
        :type updated_at: int
        :return: Data item instance
        :rtype: instance
        """
        search_chars = ["#", "+"]
        if any(s in key for s in search_chars):
            raise YomboWarning("data item keys cannot have # or + in them, reserved for searching.")

        if gateway_id is None:
            gateway_id = self._gateway_id
        # self.logger.debug("systemdatamixin:set: {gateway_id}: {key} = {value}", gateway_id=gateway_id, key=key, value=value)

        if self._Loader.operating_mode != "run":
            gateway_id = self._gateway_id

        data = getattr(self, self._storage_attribute_name)

        if gateway_id not in data:
            data[gateway_id] = {}

        if updated_at is None:
            updated_at = int(time())
        if created_at is None:
            created_at = int(time())

        if isinstance(request_context, str):
            request_context = request_context
        else:
            source_type, request_context = get_yombo_instance_type(request_context)
        if request_context is None:
            request_context = caller_string()

        try:
            request_by, request_by_type = self._Permissions.request_by_info(
                authentication=authentication, request_by=request_by, request_by_type=request_by_type,
                default=self._Users.system_user)
        except YomboWarning:
            print("System data accepted a value without any authentication information.")

        if value_human is None:
            value_human = self.convert_to_human(value, value_type)

        if self._Loader.run_phase[1] >= 6000 and dont_save is not True:
            try:
                yield global_invoke_all(f"_{self._storage_attribute_name}_preset_",
                                        called_by=self,
                                        arguments={
                                            "key": key,
                                            "value": value,
                                            "value_type": value_type,
                                            "value_human": value_human,
                                            "gateway_id": gateway_id,
                                            "request_context": request_context,
                                            },
                                        stop_on_error=True,
                                        )

            except YomboHookStopProcessing as e:
                self.logger.warn("Not saving data item '{key}'. Resource '{resource}' raised' YomboHookStopProcessing exception.",
                                 key=key, resource=e.by_who)
                return None

        if value_type == "str":
            value_type = "string"
        if value_type == "boolean":
            value_type = "bool"

        if key in data[gateway_id]:
            save_data = {}
            if value_type is not None and data[gateway_id][key].value_type != value_type:
                save_data["value_type"] = value_type
            # If data item is already set to value, we don't do anything.
            if data[gateway_id][key].value == value:
                return
            save_data["updated_at"] = updated_at
            self._Statistics.increment(f"lib.{self._storage_attribute_name}.update", bucket_size=60, anon=True)
            save_data["request_context"] = request_context
            save_data["value"] = value
            save_data["value_human"] = value_human
            data[gateway_id][key].update(save_data)
        else:
            new_instance = yield self.load_an_item_to_memory({
                "id": key,
                "gateway_id": gateway_id,
                "value": value,
                "value_human": value_human,
                "value_type": value_type,
                "request_by": request_by,
                "request_by_type": request_by_type,
                "request_context": request_context,
                "last_access_at": None,
                "created_at": created_at,
                "updated_at": updated_at,
                },
                save_into_storage=False
            )
            if dont_save is not True:
                data[gateway_id][key] = new_instance
                self._Statistics.increment(f"lib.{self._storage_attribute_name}.new", bucket_size=60, anon=True)

        if dont_save is not True:
            self._Events.new(self._storage_attribute_name, "set", (key, value, value_human, value_type, gateway_id,
                                                                   request_context))

        # Call any hooks
        if self._Loader.run_phase[1] >= 6000 and dont_save is not True:
            yield global_invoke_all(f"_{self._storage_attribute_name}_set_",
                                    called_by=self,
                                    arguments={
                                        "item": data[gateway_id][key],
                                        "key": key,
                                        "gateway_id": gateway_id,
                                        "request_context": request_context,
                                        }
                                    )

    def change_gateway_id(self, old, new):
        """ Moves data from an old gateway_id to a new one. """
        print(f"change_gateway_id: {old} -> {new}")
        data = getattr(self, self._storage_attribute_name)
        data[new] = data[old]
        del data[old]

    def save_an_item_to_memory(self, storage, instance, item_id):
        """
        Called by library_db_parent_mixin::do_load_an_item_to_memory to save an item into the storage.

        :param storage:
        :param instance:
        :param item_id:
        :return:
        """
        storage[instance.gateway_id][item_id] = instance

    @inlineCallbacks
    def set_from_gateway_communications(self, key, data, request_context):
        """
        Used by the gateway coms (mqtt) system to set data values.

        :param key:
        :param values:
        :return:
        """
        gateway_id = data["gateway_id"]
        if gateway_id == self._gateway_id:
            return
        yield self.set(key, data["value"], value_type=data["value_type"], gateway_id=data["gateway_id"],
                       value_human=data["value_human"], request_context=request_context, created_at=data["created_at"],
                       updated_at=data["updated_at"])

    def convert_to_human(self, value, value_type):
        """
        Convert various value types to a more human friendly display.

        :param value:
        :param value_type:
        :return:
        """
        if value_type == "bool":
            results = is_true_false(value)
            if results is not None:
                return results
            else:
                return value
        elif value_type == "epoch":
            return converters.epoch_to_string(value)
        else:
            return value

    @inlineCallbacks
    def get_history(self, key, offset=None, limit=None, gateway_id=None):
        """
        Returns a previous version of the state. Returns a dictionary with "value" and "updated" inside. See
        :py:func:`history_length` to deterine how many entries there are..

        :param key: Name of the state to get.
        :param offset: How far back to go. 0 is current, 1 is previous, etc.
        :param limit: How many records to provide
        :param gateway_id: Gateway ID to get stats for.
        :return:
        """
        if gateway_id is None:
            gateway_id = self._gateway_id

        if offset is None:
            offset = 1
        if limit is None:
            limit = 1
        results = yield self._LocalDB.get_system_data_history(self._storage_attribute_name,
                                                              key, limit, offset, gateway_id=gateway_id)
        if len(results) >= 1:
            return results
        else:
            return

    @inlineCallbacks
    def history_length(self, key):
        """
        Returns how many records a given state (key) has.

        :param key: Name of the state to check.
        :return: How many records there are for a given state.
        :rtype: int
        """
        results = yield self._LocalDB.get_system_data_count(self._storage_attribute_name, key)
        return results

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
            gateway_id = self._gateway_id

        if key in self.states:
            del self.states[gateway_id][key]
        else:
            raise KeyError(f"Cannot delete state: {key} not found")
        return None

    def _get_storage_data(self):
        return getattr(self, self._storage_attribute_name)[self._gateway_id]
