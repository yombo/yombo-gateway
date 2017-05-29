# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For developer documentation, see: `Atoms @ Module Development <https://yombo.net/docs/modules/atoms/>`_

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
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/atoms.py>`_
"""
# Import python libraries
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

import platform
from os.path import dirname, abspath
import re
from platform import _supported_dists
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, returnValue

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboHookStopProcessing
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.utils

_supported_dists += ('arch', 'mageia', 'meego', 'vmware', 'bluewhite64',
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
        if atom_requested in self.__Atoms:
            return True
        else:
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
        return self.__Atoms.__iter__()

    def __len__(self):
        """
        Returns an int of the number of atoms defined.

        :return: The number of atoms defined.
        :rtype: int
        """
        return len(self.__Atoms)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo atoms library"

    def keys(self):
        """
        Returns the keys of the atoms that are defined.

        :return: A list of atoms defined. 
        :rtype: list
        """
        return list(self.__Atoms.keys())

    def items(self):
        """
        Gets a list of tuples representing the atoms defined.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.__Atoms.items())

    def iteritems(self):
        return iter(self.__Atoms.items())

    def iterkeys(self):
        return iter(self.__Atoms.keys())

    def itervalues(self):
        return iter(self.__Atoms.values())

    def values(self):
        return list(self.__Atoms.values())

    def _init_(self, **kwargs):
        """
        Sets up the atom library and files basic atoms values about the system.

        :return: None
        """
        self.library_state = 1
        self.__Atoms = {}
        self.__Atoms.update(self.os_data())

        self.triggers = {}
        self._Automation = self._Libraries['automation']
        self._loaded = False
        self.set('loader.operation_mode', 'run')
        self.set('yombo.path', dirname(dirname(dirname(abspath(__file__)))) )

    def _load_(self, **kwargs):
        self.library_state = 2
        self.set('running_since', time())
        self._loaded = True

    def _start_(self, **kwargs):
        self.library_state = 3

    def get_atoms(self):
        """
        Shouldn't really be used. Just returns a _copy_ of all the atoms.

        :return: A dictionary containing all atoms.
        :rtype: dict
        """
        return self.__Atoms.copy()

    def get(self, atom_requested):
        """
        Get the value of a given atom (key).

        :raises KeyError: Raised when request is not found.
        :param atom_requested: Name of atom to retrieve.
        :type atom_requested: string
        :return: Value of the atom
        :rtype: mixed
        """
        logger.debug('atoms:get: {atom_requested}', atom_requested=atom_requested)

        self._Statistics.increment("lib.atoms.get", bucket_size=15, anon=True)

        search_chars = ['#', '+']
        if any(s in atom_requested for s in search_chars):
            results = yombo.utils.pattern_search(atom_requested, self.__Atoms)
            if len(results) > 1:
                values = {}
                for item in results:
                    values[item] = self.__Atoms[item]
                return values
            else:
                raise KeyError("Searched for atom, none found: %s" % atom_requested)

        # print "atoms: %s" % self.__Atoms
        return self.__Atoms[atom_requested]

    @inlineCallbacks
    def set(self, key, value):
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
        logger.debug('atoms:set: {key} = {value}', key=key, value=value)

        search_chars = ['#', '+']
        if any(s in key for s in search_chars):
            raise YomboWarning("atom keys cannot have # or + in them, reserved for searching.")

        # Call any hooks
        already_set = False
        if self.library_state >= 2:  # but only if we are not during init.
            try:
                atom_changes = yield yombo.utils.global_invoke_all(
                    '_atoms_preset_',
                    called_by = self,
                    **{'keys': key, 'value': value, 'new': key in self.__Atoms})
            except YomboHookStopProcessing as e:
                logger.warning("Not saving atom '{state}'. Resource '{resource}' raised' YomboHookStopProcessing exception.",
                               state=key, resource=e.by_who)
                returnValue(None)
            for moduleName, newValue in atom_changes.items():
                if newValue is not None:
                    logger.debug("atoms::set Module ({moduleName}) changes atom value to: {newValue}",
                                 moduleName=moduleName, newValue=newValue)
                    self.__Atoms['key'] = newValue
                    already_set = True
                    break

        self._Statistics.increment("lib.atoms.set", bucket_size=15, anon=True)
        if not already_set:
           self.__Atoms[key]= value

        if self.library_state >= 2:  # but only if we are not during init.
            # Call any hooks
            try:
                state_changes = yield yombo.utils.global_invoke_all('_atoms_set_',
                                                                    called_by=self,
                                                                    **{'key': key, 'value': value})
            except YomboHookStopProcessing:
                pass

        self.check_trigger(key, value)

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
        atoms['os.family'] = 'Unknown'
        if HAS_PSUTIL:
            atoms['cpu.count'] = psutil.cpu_count()
            memory = psutil.virtual_memory()
            atoms['mem.total'] = memory.total

        if yombo.utils.is_windows():
            atoms['os'] = 'Windows'
            atoms['os.family'] = 'Windows'
        elif yombo.utils.is_linux():
            atoms['os'] = 'Linux'
            atoms['os.family'] = 'Linux'

            (osname, osrelease, oscodename) = \
                [x.strip('"').strip("'") for x in
                 platform.linux_distribution(supported_dists=_supported_dists)]

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

        return atoms

    ##############################################################################################################
    # The remaining functions implement automation hooks. These should not be called by anything other than the  #
    # automation library!                                                                                        #
    ##############################################################################################################

    def check_trigger(self, key, value):
        """
        .. note::

          Should only be called by the automation system.

        Called by the atoms.set function when a new value is set. It asks the automation library if this key is
        trigger, and if so, fire any rules.

        True - Rules fired, fale - no rules fired.
        """
        if self._loaded:
            results = self._Automation.triggers_check('atoms', key, value)

    def _automation_source_list_(self, **kwargs):
        """
        .. note::

          Should only be called by the automation system.

        hook_automation_source_list called by the automation library to get a list of possible sources.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'atoms',
              'description': 'Allows atoms to be used as a source (trigger).',
              'validate_source_callback': self.atoms_validate_source_callback,  # function to call to validate a trigger
              'add_trigger_callback': self.atoms_add_trigger_callback,  # function to call to add a trigger
              'get_value_callback': self.atoms_get_value_callback,  # get a value
              'field_details': [
                  {
                  'label': 'name',
                  'description': 'The name of the atom to monitor.',
                  'required': True
                  }
              ]            }
         ]

    def atoms_validate_source_callback(self, rule, portion, **kwargs):
        """
        .. note::

          Should only be called by the automation system.

        A callback to check if a provided source is valid before being added as a possible source.

        :param rule: The potential rule being added.
        :param portion: Dictionary containg everything in the portion of rule being fired. Includes source, filter, etc.
        :return:
        """
        if all( required in portion['source'] for required in ['platform', 'name']):
            return True
        raise YomboWarning("Source doesn't have required parameters: platform, name",
                           101, 'atoms_validate_source_callback', 'atoms')

    def atoms_add_trigger_callback(self, rule, **kwargs):
        """
        .. note::

          Should only be called by the automation system.

        Called to add a trigger.  We simply use the automation library for the heavy lifting.

        :param rule: The potential rule being added.
        :param kwargs: None
        :return:
        """
        self._Automation.triggers_add(rule['rule_id'], 'atoms', rule['trigger']['source']['name'])

    def atoms_get_value_callback(self, rule, portion, **kwargs):
        """
        .. note::

          Should only be called by the automation system.

        A callback to the value for platform "atom". We simply just do a get based on key_name.

        :param rule: The potential rule being added.
        :param portion: Dictionary containg everything in the portion of rule being fired. Includes source, filter, etc.
        :return:
        """
        return self.get(portion['source']['name'])

    def _automation_action_list_(self, **kwargs):
        """
        .. note::

          Should only be called by the automation system.

        hook_automation_action_list called by the automation library to list possible actions this module can
        perform.

        This implementation allows automation rules set easily set Atom values.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'atom',
              'description': 'Allows atoms to be changed as an action.',
              'validate_action_callback': self.atoms_validate_action_callback,  # function to call to validate an action is possible.
              'do_action_callback': self.atoms_do_action_callback,  # function to be called to perform an action
              'field_details': [
                  {
                  'label': 'name',
                  'description': 'The name of the atom to change.',
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

    def atoms_validate_action_callback(self, rule, action, **kwargs):
        """
        .. note::

          Should only be called by the automation system.

        A callback to check if a provided action is valid before being added as a possible action.

        :param rule: The potential rule being added.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        if 'value' not in action:
            raise YomboWarning("In atoms_validate_action_callback: action is required to have 'value', so I know what to set.",
                               101, 'atoms_validate_action_callback', 'atoms')

    def atoms_do_action_callback(self, rule, action, **kwargs):
        """
        .. note::

          Should only be called by the automation system.

        A callback to perform an action.

        :param rule: The complete rule being fired.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        return self.set(action['name'], action['value'])
