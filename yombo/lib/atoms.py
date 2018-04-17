# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For developer documentation, see: `Atoms @ Module Development <https://yombo.net/docs/libraries/atoms>`_

.. seealso::

   The :doc:`States library </lib/states>` is used to store states that change.

Atoms provide non-changing information about the environment the gateway is running in as well as about the
Yombo Gateway software. Atoms are generally immutable, however, if the system state changes and is detected, the
atom should also be updated.

For dynamically changing data, use :py:mod:`States <yombo.lib.states>`.

**Usage**:

.. code-block:: python

   if self._Atom['os'] != None:
       logger.debug("Running on operating system: {operatingsystem}", operatingsystem=self._Atom['os'])

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/atoms.html>`_
"""
# Import python libraries
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from os.path import dirname, abspath
import platform
import re
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboHookStopProcessing
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.utils

SUPPORTED_DISTS = platform._supported_dists + ('arch', 'mageia', 'meego', 'vmware', 'bluewhite64',
                     'slamd64', 'ovs', 'system', 'mint', 'oracle')
logger = get_logger("library.atoms")

_REPLACE_LINUX_RE = re.compile(r'linux', re.IGNORECASE)

_MAP_OS_NAME = {
    'redhatente': 'RedHat',
    'gentoobase': 'Gentoo',
    'archarm': 'Arch ARM',
    'arch': 'Arch',
    'debian': 'Debian',
    'debiangnu/': 'Debian',
    'raspbiangn': 'Raspbian',
    'fedoraremi': 'Fedora',
    'amazonami': 'Amazon',
    'alt': 'ALT',
    'enterprise': 'OEL',
    'oracleserv': 'OEL',
    'cloudserve': 'CloudLinux',
    'pidora': 'Fedora',
    'scientific': 'ScientificLinux',
    'synology': 'Synology',
    'nilrt': 'NILinuxRT',
    'manjaro': 'Manjaro',
    'antergos': 'Antergos',
    'sles': 'SUSE',
}

_MAP_OS_FAMILY = {
    'ALT': 'RedHat',
    'Amazon': 'RedHat',
    'Antergos': 'Arch',
    'Arch ARM': 'Arch',
    'Bluewhite64': 'Bluewhite',
    'CentOS': 'RedHat',
    'CloudLinux': 'RedHat',
    'Devuan': 'Debian',
    'ESXi': 'VMWare',
    'Fedora': 'RedHat',
    'GCEL': 'Debian',
    'GoOSe': 'RedHat',
    'Linaro': 'Debian',
    'Mandrake': 'Mandriva',
    'Manjaro': 'Arch',
    'Mint': 'Debian',
    'NILinuxRT': 'NILinuxRT',
    'OpenIndiana': 'Solaris',
    'OpenIndiana Development': 'Solaris',
    'OpenSolaris': 'Solaris',
    'OpenSolaris Development': 'Solaris',
    'OEL': 'RedHat',
    'OVS': 'RedHat',
    'Raspbian': 'Debian',
    'Scientific': 'RedHat',
    'ScientificLinux': 'RedHat',
    'Slamd64': 'Slackware',
    'SLED': 'Suse',
    'SLES': 'Suse',
    'SmartOS': 'Solaris',
    'Solaris': 'Solaris',
    'SUSE': 'Suse',
    'SUSE Enterprise Server': 'Suse',
    'SUSE  Enterprise Server': 'Suse',
    'Trisquel': 'Debian',
    'Ubuntu': 'Debian',
    'VMWareESX': 'VMWare',
    'XCP': 'RedHat',
    'XenServer': 'RedHat',
    'antiX': 'Debian',
    'elementary OS': 'Debian',
    'openSUSE': 'Suse',
    'openSUSE Leap': 'Suse',
    'openSUSE Tumbleweed': 'Suse',
}


class Atoms(YomboLibrary):
    """
    Provides information about the system environment and yombo gateway.
    """
    def __contains__(self, atom_requested):
        """
        Checks to if a provided atom exists.

            >>> if 'cpu.count' in self._Atoms:
            >>>    print("The system has {0} cpus. ".format(self._Atoms['cpu.count']))

        :raises YomboWarning: Raised when request is malformed.
        :param atom_requested: The atom key to search for.
        :type atom_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(atom_requested)
            return True
        except Exception as e:
            return False

    def __getitem__(self, atom_requested):
        """
        Attempts to find the atom requested.

            >>> system_cpus = self._Atoms['cpu.count']

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param atom_requested: The atom key to search for.
        :type atom_requested: string
        :return: The value assigned to the atom.
        :rtype: mixed
        """
        return self.get(atom_requested)

    def __setitem__(self, atom_requested, value):
        """
        Sets an atom value..

            >>> system_cpus = self._Atoms['cpu.count'] = 4

        :raises YomboWarning: Raised when request is malformed.
        :param atom_requested: The atom key to replace the value for.
        :type atom_requested: string
        :param value: New value to set.
        :type value: mixed
        """
        return self.set(atom_requested, value)

    def __delitem__(self, atom_requested):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter atoms. """
        return self.__Atoms[self.gateway_id].__iter__()

    def __len__(self):
        """
        Returns an int of the number of atoms defined.

        :return: The number of atoms defined.
        :rtype: int
        """
        return len(self.__Atoms[self.gateway_id])

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo atoms library"

    def keys(self, gateway_id=None):
        """
        Returns the keys of the atoms that are defined.

        :return: A list of atoms defined. 
        :rtype: list
        """
        if gateway_id is None:
            gateway_id = self.gateway_id

        if gateway_id not in self.__Atoms:
            return []
        return list(self.__Atoms[gateway_id].keys())

    def items(self, gateway_id=None):
        """
        Gets a list of tuples representing the atoms defined.

        :return: A list of tuples.
        :rtype: list
        """
        if gateway_id is None:
            gateway_id = self.gateway_id

        if gateway_id not in self.__Atoms:
            return []
        return list(self.__Atoms[gateway_id].items())

    def values(self, gateway_id=None):
        """
        Gets a list of atom values
        :return: list
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        if gateway_id not in self.__Atoms:
            return []
        return list(self.__Atoms[gateway_id].values())

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Sets up the atom library and files basic atoms values about the system.

        :return: None
        """
        self.library_state = 1
        # self.gateway_id = 'local'
        self.gateway_id = self._Configs.get('core', 'gwid', 'local', False)
        self._loaded = False
        self.__Atoms = {self.gateway_id: {}}
        # if 'local' not in self.__Atoms:
        #     self.__Atoms['local'] = {}
        self.os_data()

        self.triggers = {}
        # self._Automation = self._Libraries['automation']
        self.set('yombo.path', dirname(dirname(dirname(abspath(__file__)))) )
        logger.debug("Calling GPG init_from_config...")
        yield self._GPG._init_from_atoms_()


    def _load_(self, **kwargs):
        self._loaded = True
        self.library_state = 2
        self.set('running_since', time())
        self.set('is_master', self._Configs.get('core', 'is_master', True, False))
        self.set('master_gateway', self._Configs.get('core', 'master_gateway', None, False))
        self._loaded = True

    def _start_(self, **kwargs):
        self.library_state = 3

    def exists(self, key, gateway_id=None):
        """
        Checks if a given state exists. Returns true or false.

        :param key: Name of state to check.
        :return: If state exists:
        :rtype: Bool
        """
        if gateway_id is None:
            gateway_id = self.gateway_id

        if key in self.__Atoms[gateway_id]:
            return True
        return False

    def get_last_update(self, key):
        """
        Get the time() the key was created or last updated.

        :param key: Name of atom to check.
        :return: Time() of last update
        :rtype: float
        """
        if key in self.__Atoms:
            return self.__Atoms[key]['updated_at']
        else:
            raise KeyError("Cannot get state time: %s not found" % key)

    def get_atoms(self, gateway_id=None):
        """
        Shouldn't really be used. Just returns a _copy_ of all the atoms.

        :return: A dictionary containing all atoms.
        :rtype: dict
        """
        if gateway_id is None:
            return self.__Atoms.copy()
        if gateway_id in self.__Atoms:
            return self.__Atoms[gateway_id].copy()
        else:
            return {}

    def get(self, atom_requested, human=None, full=None, gateway_id=None):
        """
        Get the value of a given atom (key).

        :raises KeyError: Raised when request is not found.
        :param atom_requested: Name of atom to retrieve.
        :type atom_requested: string
        :return: Value of the atom
        :rtype: mixed
        """
        # logger.debug('atoms:get: {atom_requested}', atom_requested=atom_requested)
        if gateway_id is None:
            gateway_id = self.gateway_id

        self._Statistics.increment("lib.atoms.get", bucket_size=15, anon=True)
        search_chars = ['#', '+']
        if any(s in atom_requested for s in search_chars):
            if gateway_id not in self.__Atoms:
                return {}
            results = yombo.utils.pattern_search(atom_requested, self.__Atoms[gateway_id])
            if len(results) > 1:
                values = {}
                # print("atoms: %s" % self.__Atoms[gateway_id])
                for item in results:
                    values[item] = self.__Atoms[gateway_id][item]
                return values
            else:
                raise KeyError("Searched for atom, none found: %s" % atom_requested)

        if human is True:
            return self.__Atoms[gateway_id][atom_requested]['value_human']
        elif full is True:
            return self.__Atoms[gateway_id][atom_requested]
        else:
            return self.__Atoms[gateway_id][atom_requested]['value']

    @inlineCallbacks
    def set(self, key, value, value_type=None, gateway_id=None, human_value=None):
        """
        Get the value of a given atom (key).

        **Hooks called**:

        * _atoms_set_ : Sends kwargs 'key', and 'value'. *key* is the name of the atom being set and *value* is
          the new value to set.

        :raises YomboWarning: Raised when request is malformed.
        :param key: Name of atom to set.
        :type key: string
        :param value: Value to set the atom to.
        :type value: mixed
        :return: Value of atom
        :rtype: mixed
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        # logger.debug('atoms:set: {gateway_id}: {key} = {value}', gateway_id=gateway_id, key=key, value=value)

        if gateway_id not in self.__Atoms:
            self.__Atoms[gateway_id] = {}

        search_chars = ['#', '+']
        if any(s in key for s in search_chars):
            raise YomboWarning("state keys cannot have # or + in them, reserved for searching.")

        if key in self.__Atoms[gateway_id]:
            is_new = False
            # If state is already set to value, we don't do anything.
            self.__Atoms[gateway_id][key]['updated_at'] = int(round(time()))
            if human_value is not None:
                self.__Atoms[gateway_id][key]['value_human'] = human_value
            if self.__Atoms[gateway_id][key]['value'] == value:
                return
            self._Statistics.increment("lib.atoms.set.update", bucket_size=60, anon=True)
        else:
            is_new = True
            self.__Atoms[gateway_id][key] = {
                'gateway_id': gateway_id,
                'created_at': int(time()),
                'updated_at': int(time()),
            }
            self._Statistics.increment("lib.atoms.set.new", bucket_size=60, anon=True)


        self.__Atoms[gateway_id][key]['value'] = value
        if is_new is True or value_type is not None:
            self.__Atoms[gateway_id][key]['value_type'] = value_type

        if human_value is not None:
            self.__Atoms[gateway_id][key]['value_human'] = human_value
        else:
            self.__Atoms[gateway_id][key]['value_human'] = self.convert_to_human(value, value_type)

        # Call any hooks
        yield yombo.utils.global_invoke_all('_atoms_set_',
                                            called_by=self,
                                            key=key,
                                            value=value,
                                            value_full=self.__Atoms[gateway_id][key],
                                            gateway_id=gateway_id
                                            )

    @inlineCallbacks
    def set_from_gateway_communications(self, key, values):
        """
        Used by the gateway coms (mqtt) system to set atom values.
        :param key:
        :param values:
        :return:
        """
        gateway_id = values['gateway_id']
        if gateway_id == self.gateway_id:
            return
        if gateway_id not in self.__Atoms:
            self.__Atoms[gateway_id] = {}
        self.__Atoms[values['gateway_id']][key] = {
            'gateway_id': values['gateway_id'],
            'value': values['value'],
            'value_human': values['value_human'],
            'value_type': values['value_type'],
            'created_at': values['created_at'],
            'updated_at': values['updated_at'],
        }
        yield yombo.utils.global_invoke_all('_atoms_set_',
                                            called_by=self,
                                            key=key,
                                            value=value,
                                            value_full=self.__Atoms[gateway_id][key],
                                            gateway_id=gateway_id
                                            )

    def convert_to_human(self, value, value_type):
        if value_type == 'bool':
            results = yombo.utils.is_true_false(value)
            if results is not None:
                return results
            else:
                return value

        elif value_type == 'epoch':
            return yombo.utils.epoch_to_string(value)
        else:
            return value

        # if gateway_id is None:
        #     gateway_id = self.gateway_id
        # if gateway_id != self.gateway_id:
        #     raise YomboWarning("Cannot set atom value for another gateway.")
        #
        # search_chars = ['#', '+']
        # if any(s in key for s in search_chars):
        #     raise YomboWarning("atom keys cannot have # or + in them, reserved for searching.")
        #
        # # Call any hooks
        # already_set = False
        # if self.library_state >= 2:  # but only if we are not during init.
        #     try:
        #         atom_changes = yield yombo.utils.global_invoke_all(
        #             '_atoms_preset_',
        #             called_by = self,
        #             **{'keys': key, 'value': value, 'new': key in self.__Atoms})
        #     except YomboHookStopProcessing as e:
        #         logger.warning("Not saving atom '{state}'. Resource '{resource}' raised' YomboHookStopProcessing exception.",
        #                        state=key, resource=e.by_who)
        #         returnValue(None)
        #     for moduleName, newValue in atom_changes.items():
        #         if newValue is not None:
        #             logger.debug("atoms::set Module ({moduleName}) changes atom value to: {newValue}",
        #                          moduleName=moduleName, newValue=newValue)
        #             self.__Atoms['key'] = newValue
        #             already_set = True
        #             break
        #
        # self._Statistics.increment("lib.atoms.set", bucket_size=15, anon=True)
        # if not already_set:
        #    self.__Atoms[key]= value
        #
        # if self.library_state >= 2:  # but only if we are not during init.
        #     # Call any hooks
        #     try:
        #         state_changes = yield yombo.utils.global_invoke_all('_atoms_set_',
        #                                                             called_by=self,
        #                                                             **{'key': key, 'value': value})
        #     except YomboHookStopProcessing:
        #         pass
        #

    def os_data(self):
        """
        Sets atoms concerning the operating system.

        :return: None
        """
        atoms = {}
        (atoms['kernel'],atoms['system.name'],atoms['kernel.release'], version,
         atoms['cpu.arch'], _) = platform.uname()

        atoms['cpu.count'] = 0
        atoms['mem.total'] = 0
        atoms['mem.sizing'] = 'medium'
        atoms['os.family'] = 'Unknown'
        if HAS_PSUTIL:
            atoms['cpu.count'] = psutil.cpu_count()
            memory = psutil.virtual_memory()
            atoms['mem.total'] = memory.total
        if memory.total < 261939712:
            atoms['mem.sizing'] = 'x_small'
        elif memory.total < 523879424:
            atoms['mem.sizing'] = 'small'
        elif memory.total < 1047758848:
            atoms['mem.sizing'] = 'medium'
        elif memory.total < 2095517696:
            atoms['mem.sizing'] = 'large'
        elif memory.total < 4191035392:
            atoms['mem.sizing'] = 'x_large'
        else:
            atoms['mem.sizing'] = 'xx_large'

        if yombo.utils.is_windows():
            atoms['os'] = 'Windows'
            atoms['os.family'] = 'Windows'
        elif yombo.utils.is_linux():
            atoms['os'] = 'Linux'
            atoms['os.family'] = 'Linux'

            (osname, osrelease, oscodename) = \
                [x.strip('"').strip("'") for x in
                 # distro.linux_distribution(full_distribution_name=False)
                 platform.linux_distribution(supported_dists=SUPPORTED_DISTS)]

            if 'os.fullname' not in atoms:
                atoms['os.fullname'] = osname.strip()
            if 'os.release' not in atoms:
                atoms['os.release'] = osrelease.strip()
            atoms['os.codename'] = oscodename.strip()

            distroname = _REPLACE_LINUX_RE.sub('', atoms['os.fullname']).strip()
            # return the first ten characters with no spaces, lowercased
            shortname = distroname.replace(' ', '').lower()[:10]
            # this maps the long names from the /etc/DISTRO-release files to the
            # traditional short names that Salt has used.
            atoms['os'] = _MAP_OS_NAME.get(shortname, distroname)

        elif atoms['kernel'] == 'Darwin':
            atoms['os'] = 'Mac'
            atoms['os.family'] = 'Darwin'
        elif atoms['kernel'] == 'SunOS':
            atoms['os'] = 'SunOS'
            atoms['os.family'] = 'Solaris'
        else:
            atoms['os'] = atoms['kernel']

        for name, value in atoms.items():
            self.set(name, value)
        return atoms
