"""
.. rst-class:: floater

.. note::

  For more information see: `Atoms @ Projects.yombo.net <https://projects.yombo.net/projects/modules/wiki/Atoms>`_

Atoms provide an interface to derive information about the underlying system. Atoms are generally immutable, with
some exceptions such as IP address changes. Libraries and modules and get and set additional atoms as desired.

For dynamically changing data, use :py:mod:`yombo.lib.states`.

If a request atom doesn't exist, a value of None will be returned instead of an exception.

*Usage**:

.. code-block:: python

   if self._Atom['os'] != None:
       logger.debug("Running on operating system: {operatingsystem}", operatingsystem=self._Atom['os'])

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

import platform
import re

from platform import _supported_dists
_supported_dists += ('arch', 'mageia', 'meego', 'vmware', 'bluewhite64',
                     'slamd64', 'ovs', 'system', 'mint', 'oracle')
from time import time

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboHookStopProcessing
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.utils

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
    Provides the Atom information for modules and libraries to get more
    information about the underlying system.
    """
    def _init_(self):
        self.run_state = 1
        self.__Atoms = {}
        self.__Atoms.update(self.os_data())
        self.triggers = {}
        self.automation = self._Libraries['automation']
        self._loaded = False
        self.set('loader.operation_mode', 'run')

    def _load_(self):
        self.run_state = 2
        self.set('running_since', time())
        self._loaded = True

    def _start_(self):
        self.run_state = 3

    def _stop_(self):
        pass

    def _unload_(self):
        pass

    def __delitem__(self, key):
        if key in self.__Atoms:
            del self.__Atoms[key]

    def __getitem__(self, key):
        return self.get(key)

    def __len__(self):
        return len(self.__Atoms)

    def __setitem__(self, key, value):
        return self.set(key, value)

    def __contains__(self, key):
        return self.exists(key)

    def __str__(self):
        return self.__Atoms

    def _i18n_atoms_(self, **kwargs):
       return [
           {'cpu.count': {
               'en': 'Number of CPUs (cores) gateway has.',
               },
           },
           {'mem'
            'mem.total': {
               'en': 'Total memory on gateway.',
               },
           },
           { 'os': {
               'en': 'Operating system type.',
               },
           },
           { 'os.family': {
               'en': 'Which family the operating system belongs to.',
               },
           },
       ]

    def _statistics_lifetimes_(self, **kwargs):
        """
        We keep 10 days of max data, 30 days of hourly data, 1 of daily data
        """
        return {'name': 'lib.atoms.#', 'lifetimes': [11, 30, 365] } # we set full details for 11 days as an example/test

    def get_atoms(self):
        """
        Shouldn't really be used. Just returns a _copy_ of all the atoms.
        :return:
        """
        return self.__Atoms.copy()

    def exists(self, key):
        """
        Checks if a given atom exsist. Returns true or false.

        :param key: Name of state to check.
        :return: If state exists:
        :rtype: Bool
        """
        if key in self.__Atoms:
            return True
        return False

    def get(self, key=None):
        """
        Get the value of a given atom (key).

        :param key: Name of atom to check.
        :return: Value of atom
        """
        logger.debug('atoms:get: {key} = {value}', key=key)
        if key is None:
            raise YomboWarning("Key cannot be none")

        self._Statistics.increment("lib.atoms.get", bucket_time=15, anon=True)

        search_chars = ['#', '+']
        if any(s in key for s in search_chars):
            results = yombo.utils.pattern_search(key, self.__Atoms)
            if len(results) > 1:
                values = {}
                for item in results:
                    values[item] = self.__Atoms[item]
                return values
            else:
                raise KeyError("Searched for atoms, none found.")

        # print "atoms: %s" % self.__Atoms
        return self.__Atoms[key]

    def set(self, key, value):
        """
        Get the value of a given atom (key).

        **Hooks called**:

        * _atoms_set_ : Sends kwargs 'key', and 'value'. *key* is the name of the atom being set and *value* is
          the new value to set.

        :param key: Name of atom to set.
        :param value: Value to set the atom to.
        :return: Value of atom
        """
        logger.debug('atoms:set: {key} = {value}', key=key, value=value)

        search_chars = ['#', '+']
        if any(s in key for s in search_chars):
            raise YomboWarning("atom keys cannot have # or + in them, reserved for searching.")

        # Call any hooks
        already_set = False
        if self.run_state >= 2:  # but only if we are not during init.
            try:
                atom_changes = yombo.utils.global_invoke_all('_atoms_set_',
                                        **{'keys': key, 'value': value, 'new': key in self.__Atoms})
            except YomboHookStopProcessing:
                logger.warning("Stopping processing 'hook_atoms_set' due to YomboHookStopProcessing exception.")
                return
            for moduleName, newValue in atom_changes.iteritems():
                if newValue is not None:
                    logger.debug("atoms::set Module ({moduleName}) changes atom value to: {newValue}",
                                 moduleName=moduleName, newValue=newValue)
                    self.__Atoms['key'] = newValue
                    already_set = True
                    break

        self._Statistics.increment("lib.atoms.set", bucket_time=15, anon=True)
        if not already_set:
           self.__Atoms[key]= value

        self.check_trigger(key, value)

    def os_data(self):
        """
        Returns atoms about the operating system.
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
        Called by the atoms.set function when a new value is set. It asks the automation library if this key is
        trigger, and if so, fire any rules.

        True - Rules fired, fale - no rules fired.
        """
        if self._loaded:
            results = self.automation.triggers_check('atoms', key, value)

    def _automation_source_list_(self, **kwargs):
        """
        hook_automation_source_list called by the automation library to get a list of possible sources.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'atoms',
              'description': 'Allows states to be used as a source (trigger).',
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
        Called to add a trigger.  We simply use the automation library for the heavy lifting.
        Called to add a trigger.  We simply use the automation library for the heavy lifting.

        :param rule: The potential rule being added.
        :param kwargs: None
        :return:
        """
        self.automation.triggers_add(rule['rule_id'], 'atoms', rule['trigger']['source']['name'])

    def atoms_get_value_callback(self, rule, portion, **kwargs):
        """
        A callback to the value for platform "atom". We simply just do a get based on key_name.

        :param rule: The potential rule being added.
        :param portion: Dictionary containg everything in the portion of rule being fired. Includes source, filter, etc.
        :return:
        """
        return self.get(portion['source']['name'])

    def _automation_action_list_(self, **kwargs):
        """
        hook_automation_action_list called by the automation library to list possible actions this module can
        perform.

        This implementation allows autoamtion rules set easily set Atom values.

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
        A callback to perform an action.

        :param rule: The complete rule being fired.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        return self.set(action['name'], action['value'])
