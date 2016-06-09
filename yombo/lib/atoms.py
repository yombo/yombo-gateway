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
from yombo.core.exceptions import YomboWarning
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
    def _init_(self, loader):
        self.loader = loader
        self.__Atoms = {}
        self.__Atoms.update(self.os_data())
        self.triggers = {}
        self.automation = self._Libraries['automation']

    def _load_(self):
        self.set('running_since', time())

    def _start_(self):
        pass

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

#    def __repr__(self):
#        return str(self.__Atoms)

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
        if key is None:
            return self.__Atoms
        keys = key.split(':')
        return yombo.utils.dict_get_value(self.__Atoms, keys)

    def set(self, key, value):
        """
        Get the value of a given atom (key).

        :param key: Name of atom to set.
        :param value: Value to set the atom to.
        :return: Value of atom
        """
        keys = key.split(':')

        # Call any hooks
        already_set = False
        atom_changes = yombo.utils.global_invoke_all('atoms_set', **{'keys': keys, 'value': value})
        for moduleName, newValue in atom_changes.iteritems():
            if newValue is not None:
                logger.debug("atoms::set Module ({moduleName}) changes atom value to: {newValue}", moduleName=moduleName, newValue=newValue)
                yombo.utils.dict_set_value(self.__Atoms, keys, newValue)
                already_set = True

        if not already_set:
            yombo.utils.dict_set_value(self.__Atoms, keys, value)

        self.check_trigger(key, value)

    def os_data(self):
        """
        Returns atoms about the operating system.
        """
        atoms = {}
        (atoms['kernel'],atoms['nodename'],atoms['kernelrelease'], version,
         atoms['cpuarch'], _) = platform.uname()

        atoms['cpu_count'] = 0
        atoms['mem_total'] = 0
        atoms['os_family'] = 'Unknown'
        if HAS_PSUTIL:
            atoms['cpu_count'] = psutil.cpu_count()
            memory = psutil.virtual_memory()
            atoms['mem_total'] = memory.total

        if yombo.utils.is_windows():
            atoms['os'] = 'Windows'
            atoms['os_family'] = 'Windows'
        elif yombo.utils.is_linux():
            atoms['os'] = 'Linux'
            atoms['os_family'] = 'Linux'

            (osname, osrelease, oscodename) = \
                [x.strip('"').strip("'") for x in
                 platform.linux_distribution(supported_dists=_supported_dists)]

            if 'osfullname' not in atoms:
                atoms['osfullname'] = osname.strip()
            if 'osrelease' not in atoms:
                atoms['osrelease'] = osrelease.strip()
            atoms['oscodename'] = oscodename.strip()

            distroname = _REPLACE_LINUX_RE.sub('', atoms['osfullname']).strip()
            # return the first ten characters with no spaces, lowercased
            shortname = distroname.replace(' ', '').lower()[:10]
            # this maps the long names from the /etc/DISTRO-release files to the
            # traditional short names that Salt has used.
            atoms['os'] = _MAP_OS_NAME.get(shortname, distroname)

        elif atoms['kernel'] == 'Darwin':
            atoms['os'] = 'Mac'
            atoms['os_family'] = 'Darwin'
        elif atoms['kernel'] == 'SunOS':
            atoms['os'] = 'SunOS'
            atoms['os_family'] = 'Solaris'
        else:
            atoms['os'] = atoms['kernel']

        return atoms

    # The remaining functions implement automation hooks. These should not be called by anything other than the
    # automation library!

    def check_trigger(self, key, value):
        """
        Called by the atoms.set function when a new value is set. It asks the automation library if this key is
        trigger, and if so, fire any rules.

        True - Rules fired, fale - no rules fired.
        """
        results = self.automation.triggers_check('atoms', key, value)

    def Atoms_automation_source_list(self, **kwargs):
        """
        hook_automation_source_list called by the automation library to get a list of possible sources.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'atoms',
              'validate_source_callback': self.atoms_validate_source_callback,  # function to call to validate a trigger
              'add_trigger_callback': self.atoms_add_trigger_callback,  # function to call to add a trigger
              'get_value_callback': self.atoms_get_value_callback,  # get a value
            }
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

    def Atoms_automation_action_list(self, **kwargs):
        """
        hook_automation_action_list called by the automation library to list possible actions this module can
        perform.

        This implementation allows autoamtion rules set easily set Atom values.

        :param kwargs: None
        :return:
        """
#        print "!@#!@#!@#!@#!@#!@#!@#!@#!@#!@#!@#!@#!@#!@#!@#!@#!@#!@#"
        return [
            { 'platform': 'atom',
              'validate_action_callback': self.atoms_validate_action_callback,  # function to call to validate an action is possible.
              'do_action_callback': self.atoms_do_action_callback  # function to be called to perform an action
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
        if 'value' not in action['argumments']:
            raise YomboWarning("In atoms_validate_action_callback: action is required to have 'value' within the arguments, so I know what to set.",
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
