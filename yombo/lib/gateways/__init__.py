# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * End user documentation: `Gateways @ User Documentation <https://yombo.net/docs/gateway/web_interface/gateways>`_
  * For library documentation, see: `Gateways @ Library Documentation <https://yombo.net/docs/libraries/gateways>`_

Tracks gateway details for the local gateway and any member gateways within the current cluster.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.14.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/gateways.html>`_
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import VERSION
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.lib.gateways.gateway import Gateway
from yombo.utils import do_search_instance, global_invoke_all
from yombo.utils.decorators import deprecated

logger = get_logger('library.gateways')

class Gateways(YomboLibrary):
    """
    Manages information about gateways.
    """
    library_phase = 0

    @property
    def local(self):
        return self.gateways[self.gateway_id()]

    @local.setter
    def local(self, val):
        return

    @property
    def local_id(self):
        return self.gateway_id()

    @local.setter
    def local_id(self, val):
        return

    @property
    def master_id(self):
        if self.master_gateway_id() is None:
            return self.local_id
        return self.master_gateway_id()

    @master_id.setter
    def master_id(self, val):
        return

    @property
    def master(self):
        if self.master_gateway_id() is None:
            return self.gateways[self.gateway_id()]
        return self.gateways[self.master_gateway_id()]

    @master.setter
    def master(self, val):
        return


    def __contains__(self, gateway_requested):
        """
        .. note:: The gateway must be enabled to be found using this method.

        Checks to if a provided gateway ID or machine_label exists.

            >>> if '0kas02j1zss349k1' in self._Gateways:

        or:

            >>> if 'some_gateway_name' in self._Gateways:

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param gateway_requested: The gateway id or machine_label to search for.
        :type gateway_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get_meta(gateway_requested)
            return True
        except:
            return False

    def __getitem__(self, gateway_requested):
        """
        .. note:: The gateway must be enabled to be found using this method.

        Attempts to find the device requested using a couple of methods.

            >>> gateway = self._Gateways['0kas02j1zss349k1']  #by uuid

        or:

            >>> gateway = self._Gateways['alpnum']  #by name

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param gateway_requested: The gateway ID or machine_label to search for.
        :type gateway_requested: string
        :return: A pointer to the device type instance.
        :rtype: instance
        """
        return self.get_meta(gateway_requested)

    def __setitem__(self, **kwargs):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, **kwargs):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter device types. """
        return self.device_types.__iter__()

    def __len__(self):
        """
        Returns an int of the number of device types configured.

        :return: The number of gateways configured.
        :rtype: int
        """
        return len(self.gateways)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo gateway library"

    def keys(self):
        """
        Returns the keys (device type ID's) that are configured.

        :return: A list of device type IDs. 
        :rtype: list
        """
        return list(self.gateways.keys())

    def items(self):
        """
        Gets a list of tuples representing the device types configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.gateways.items())

    def values(self):
        return list(self.gateways.values())

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.library_phase = 1
        self.gateways = {}
        self.gateway_status = yield self._SQLDict.get(self, "gateway_status")
        self.gateway_id = self._Configs.gateway_id
        self.is_master = self._Configs.is_master
        self.master_gateway_id = self._Configs.master_gateway_id

        self.gateway_search_attributes = ['gateway_id', 'gateway_id', 'label', 'machine_label', 'status']
        if self._Loader.operating_mode != 'run':
            self.import_gateway({
                'id': 'local',
                'is_master': True,
                'master_gateway_id': '',
                'machine_label': 'local',
                'label': 'Local',
                'description': 'Local',
                'fqdn': '127.0.0.1',
                'version': VERSION,
            })
        self.import_gateway({
            'id': 'cluster',
            'is_master': False,
            'master_gateway_id': '',
            'machine_label': 'cluster',
            'label': 'Cluster',
            'description': 'All gateways in a cluster.',
            'fqdn': '127.0.0.1',
            'version': VERSION,
        })
        yield self._load_gateways_from_database()

    def _start_(self, **kwargs):
        self.library_phase = 3
        if self._Loader.operating_mode != 'run':
            return

    def _started_(self, **kwargs):
        self.library_phase = 4
        if self._Loader.operating_mode != 'run':
            return

    def _stop_(self, **kwargs):
        """
        Cleans up any pending deferreds.
        """
        if hasattr(self, 'load_deferred'):
            if self.load_deferred is not None and self.load_deferred.called is False:
                self.load_deferred.callback(1)  # if we don't check for this, we can't stop!

    @inlineCallbacks
    def _load_gateways_from_database(self):
        """
        Loads gateways from database and sends them to
        :py:meth:`import_gateway <Gateways.import_gateway>`

        This can be triggered either on system startup or when new/updated gateways have been saved to the
        database and we need to refresh existing gateways.
        """
        gateways = yield self._LocalDB.get_gateways()
        for a_gateway in gateways:
            self.import_gateway(a_gateway)

    def import_gateway(self, gateway, test_gateway=False):
        """
        Add a new gateways to memory or update an existing gateways.

        **Hooks called**:

        * _gateway_before_load_ : If added, sends gateway dictionary as 'gateway'
        * _gateway_before_update_ : If updated, sends gateway dictionary as 'gateway'
        * _gateway_loaded_ : If added, send the gateway instance as 'gateway'
        * _gateway_updated_ : If updated, send the gateway instance as 'gateway'

        :param gateway: A dictionary of items required to either setup a new gateway or update an existing one.
        :type input: dict
        :param test_gateway: Used for unit testing.
        :type test_gateway: bool
        :returns: Pointer to new input. Only used during unittest
        """
        # logger.debug("importing gateway: {gateway}", gateway=gateway)

        gateway_id = gateway["id"]
        if gateway_id == self.gateway_id():
            gateway['version'] = VERSION
        global_invoke_all('_gateways_before_import_',
                          called_by=self,
                          gateway_id=gateway_id,
                          gateway=gateway,
                          )
        if gateway_id not in self.gateways:
            global_invoke_all('_gateway_before_load_',
                              called_by=self,
                              gateway_id=gateway_id,
                              gateway=gateway,
                              )
            self.gateways[gateway_id] = Gateway(self, gateway)
            global_invoke_all('_gateway_loaded_',
                              called_by=self,
                              gateway_id=gateway_id,
                              gateway=self.gateways[gateway_id],
                              )
        elif gateway_id not in self.gateways:
            global_invoke_all('_gateway_before_update_',
                              called_by=self,
                              gateway_id=gateway_id,
                              gateway=self.gateways[gateway_id],
                              )
            self.gateways[gateway_id].update_attributes(gateway)
            global_invoke_all('_gateway_updated_',
                              called_by=self,
                              gateway_id=gateway_id,
                              gateway=self.gateways[gateway_id],
                              )

    @deprecated(deprecated_in="0.21.0", removed_in="0.22.0",
                current_version=VERSION,
                details="Use the 'local' property instead.")
    def get_local(self):
        return self.gateways[self.gateway_id()]

    @deprecated(deprecated_in="0.21.0", removed_in="0.22.0",
                current_version=VERSION,
                details="Use the 'local_id' property instead.")
    def get_local_id(self):
        """
        For future...
        :return:
        """
        return self.gateway_id()


    def get_gateways(self):
        """
        Returns a copy of the gateways list.
        :return:
        """
        return self.gateways.copy()

    def get_meta(self, gateway_requested, gateway=None, limiter=None, status=None):
        """
        Performs the actual search.

        .. note::

           Can use the built in methods below or use get_meta/get to include 'gateway_type' limiter:

            >>> self._Gateways['13ase45']

        or:

            >>> self._Gateways['numeric']

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param gateway_requested: The gateway ID or gateway label to search for.
        :type gateway_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the gateway to check for.
        :type status: int
        :return: Pointer to requested gateway.
        :rtype: dict
        """
        if limiter is None:
            limiter = .89

        if limiter > .99999999:
            limiter = .99
        elif limiter < .10:
            limiter = .10

        if status is None:
            status = 1

        if gateway_requested in self.gateways:
            item = self.gateways[gateway_requested]
            # if item.status != status:
            #     raise KeyError("Requested gateway found, but has invalid status: %s" % item.status)
            return item
        else:
            attrs = [
                {
                    'field': 'gateway_id',
                    'value': gateway_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'machine_label',
                    'value': gateway_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'label',
                    'value': gateway_requested,
                    'limiter': limiter,
                }
            ]
            try:
                # logger.debug("Get is about to call search...: %s" % gateway_requested)
                # found, key, item, ratio, others = self._search(attrs, operation="highest")
                found, key, item, ratio, others = do_search_instance(attrs, self.gateways,
                                                                     self.gateway_search_attributes,
                                                                     limiter=limiter,
                                                                     operation="highest")
                # logger.debug("found gateway by search: others: {others}", others=others)
                if found:
                    return item
                raise KeyError("Gateway not found: %s" % gateway_requested)
            except YomboWarning as e:
                raise KeyError('Searched for %s, but had problems: %s' % (gateway_requested, e))

    def get(self, gateway_requested, limiter=None, status=None):
        """
        Returns a deferred! Looking for a gateway id in memory.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find devices:

            >>> self._Gateways['13ase45']

        or:

            >>> self._Gateways['numeric']

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param gateway_requested: The gateway ID or gateway label to search for.
        :type gateway_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the gateway to check for.
        :type status: int
        :return: Pointer to requested gateway.
        :rtype: dict
        """
        try:
            gateway = self.get_meta(gateway_requested, limiter, status)
        except Exception as e:
            logger.warn("Unable to find requested gateway: {gateway}.  Reason: {e}", gateway=gateway_requested, e=e)
            raise YomboWarning("Cannot find requested gateway...")
        return gateway

    def search(self, criteria):
        """
        Search for gateways based on a dictionary of key=value pairs.

        :param criteria:
        :return:
        """
        results = {}
        for gateway_id, gateway in self.gateways.items():
            for key, value in criteria.items():
                if key not in self.gateway_search_attributes:
                    continue
                if value == getattr(gateway, key):
                    results[gateway_id] = gateway
        return results

    @inlineCallbacks
    def add_gateway(self, api_data, source=None, **kwargs):
        """
        Add a new gateway. Updates Yombo servers and creates a new entry locally.

        :param api_data:
        :param kwargs:
        :return:
        """
        if 'gateway_id' not in api_data:
            api_data['gateway_id'] = self.gateway_id()

        if api_data['machine_label'].lower() == 'cluster':
            return {
                'status': 'failed',
                'msg': "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
                'apimsg': "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
                'apimsghtml': "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
            }
        if api_data['label'].lower() == 'cluster':
            return {
                'status': 'failed',
                'msg': "Couldn't add gateway: label cannot be 'cluster' or 'all'",
                'apimsg': "Couldn't add gateway: label cannot be 'cluster' or 'all'",
                'apimsghtml': "Couldn't add gateway: label cannot be 'cluster' or 'all'",
            }
        if source != 'amqp':
            try:
                if 'session' in kwargs:
                    session = kwargs['session']
                else:
                    session = None

                gateway_results = yield self._YomboAPI.request('POST', '/v1/gateway',
                                                               api_data,
                                                               session=session)
            except YomboWarning as e:
                return {
                    'status': 'failed',
                    'msg': "Couldn't add gateway: %s" % e.message,
                    'apimsg': "Couldn't add gateway: %s" % e.message,
                    'apimsghtml': "Couldn't add gateway: %s" % e.html_message,
                }
            gateway_id = gateway_results['data']['id']

        new_gateway = gateway_results['data']
        self.import_gateway(new_gateway)
        return {
            'status': 'success',
            'msg': "Gateway added.",
            'gateway_id': gateway_id,
        }

    @inlineCallbacks
    def edit_gateway(self, gateway_id, api_data, called_from_gateway=None, source=None, **kwargs):
        """
        Edit a gateway at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        if api_data['machine_label'].lower() == 'cluster':
            return {
                'status': 'failed',
                'msg': "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
                'apimsg': "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
                'apimsghtml': "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
            }
        if api_data['label'].lower() == 'cluster':
            return {
                'status': 'failed',
                'msg': "Couldn't add gateway: label cannot be 'cluster' or 'all'",
                'apimsg': "Couldn't add gateway: label cannot be 'cluster' or 'all'",
                'apimsghtml': "Couldn't add gateway: label cannot be 'cluster' or 'all'",
            }
        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            gateway_results = yield self._YomboAPI.request('PATCH', '/v1/gateway/%s' % (gateway_id),
                                                           api_data,
                                                           session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't edit gateway: %s" % e.message,
                'apimsg': "Couldn't edit gateway: %s" % e.message,
                'apimsghtml': "Couldn't edit gateway: %s" % e.html_message,
            }

        gateway = self.gateways[gateway_id]
        if called_from_gateway is not True:
            gateway.update_attributes(api_data)
            gateway.save_to_db()

        return {
            'status': 'success',
            'msg': "Device type edited.",
            'gateway_id': gateway_results['data']['id'],
        }

    @inlineCallbacks
    def delete_gateway(self, gateway_id, **kwargs):
        """
        Delete a gateway at the Yombo server level, not at the local gateway level.

        :param gateway_id: The gateway ID to delete.
        :param kwargs:
        :return:
        """
        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            yield self._YomboAPI.request('DELETE', '/v1/gateway/%s' % gateway_id,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't delete gateway: %s" % e.message,
                'apimsg': "Couldn't delete gateway: %s" % e.message,
                'apimsghtml': "Couldn't delete gateway: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Gateway deleted.",
            'gateway_id': gateway_id,
        }

    @inlineCallbacks
    def enable_gateway(self, gateway_id, **kwargs):
        """
        Enable a gateway at the Yombo server level, not at the local gateway level.

        :param gateway_id: The gateway ID to enable.
        :param kwargs:
        :return:
        """
        api_data = {
            'status': 1,
        }

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            yield self._YomboAPI.request('PATCH', '/v1/gateway/%s' % gateway_id,
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't enable gateway: %s" % e.message,
                'apimsg': "Couldn't enable gateway: %s" % e.message,
                'apimsghtml': "Couldn't enable gateway: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Gateway enabled.",
            'gateway_id': gateway_id,
        }

    @inlineCallbacks
    def disable_gateway(self, gateway_id, **kwargs):
        """
        Enable a gateway at the Yombo server level, not at the local gateway level.

        :param gateway_id: The gateway ID to disable.
        :param kwargs:
        :return:
        """
        api_data = {
            'status': 0,
        }

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            yield self._YomboAPI.request('PATCH', '/v1/gateway/%s' % gateway_id,
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't disable gateway: %s" % e.message,
                'apimsg': "Couldn't disable gateway: %s" % e.message,
                'apimsghtml': "Couldn't disable gateway: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Gateway disabled.",
            'gateway_id': gateway_id,
        }

    def full_list_gateways(self):
        """
        Return a list of dictionaries representing all known commands to this gateway.
        :return:
        """
        items = []
        for gateway_id, gateway in self.gateways.items():
            if gateway.machine_label in ('cluster', 'all'):
                continue
            items.append(gateway.asdict())
        return items
