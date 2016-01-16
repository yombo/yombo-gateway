"""
Yombo comes with an interface to derive information about the underlying system. This is called
the atoms interface and provides the Yombo Gateway with various information. Libraries and modules
can extend atoms. For dynamically changing data, use States.

Atoms are relatively static, although if a change is detected, the atom should be updated as
needed. For example, if the IP address changes, the atom data should be refreshed.

If a request atom doesn't exist, a value of None will be returned instead of an exception.

*Usage**:

.. code-block:: python

   if self._Atom['os'] != None:
       logger.debug("Running on operating system: {operatingsystem}", operatingsystem=self._Atom['os'])

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
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
from collections import deque
from time import time

from yombo.core.log import getLogger
from yombo.core.library import YomboLibrary
import yombo.utils

logger = getLogger("library.Atoms")

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
        pass

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
        if key in self.__Atoms:
            return True
        return False

    def get(self, key=None):
        if key is None:
            return self.__Atoms
        keys = key.split(':')
        return yombo.utils.dict_get_value(self.__Atoms, keys)

    def set(self, key, value):
        keys = key.split(':')
        yombo.utils.dict_set_value(self.__Atoms, keys, value)
        self.check_trigger(key, keys, value)

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
            atoms['mem_total'] = memory['total']

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

    def check_trigger(self, key, keys, value):
        """
        Checks if a trigger should be fired.
        """
        results = self.automation.track_trigger_check_triggers('atoms', key, value)
        if results != False:
            logger.info("I have a match! {results}", results=results)
            self.automation.track_trigger_basic_do_actions(results)
        else:
            logger.info("trigger didn't match any trigger filters")

    def Atoms_automation_source_list(self, **kwargs):
        """
        hook_automation_source_list called by the automation library to get a list of possible sources and triggers.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'atom',
              'add_trigger_callback': self.add_trigger_callback,  # function to call to add a trigger
              'validate_callback': self.automation_source_validate,  # function to call to validate a trigger
              'get_value_callback': self.automation_get_value,  # get a value
            }
         ]

    def add_trigger_callback(self, rule, **kwargs):
        """
        Called to add a trigger.

        :param kwargs: None
        :return:
        """
        self.automation.track_trigger_basic_add(rule['rule_id'], 'atoms', rule['trigger']['source']['name'])

    def automation_source_validate(self, rule, **kwargs):
        """
        A callback to check if a provided trigger is valid before being added.

        :param kwargs: None
        :return:
        """
        trigger = rule['trigger']['source']
        if all( required in trigger for required in ['platform', 'name']):
            return True
        return False

    def automation_get_value(self, rule, key_name, **kwargs):
        return self.get(key_name)

    def Atoms_automation_condjjition_check(self, rule, **kwargs):
        """
        A callback to check if a provided condition is valid before an action is triggered.

        :param kwargs: None
        :return:
        """
        condition_type = 'and'
        if 'condition_type' in rule:
            condition_type = rule['condition_type']

#        platform = kwargs['platform']
        conditions = kwargs['conditions']
        results = []
        for condition in conditions:
            keys = condition['name'].split(':')
            if yombo.utils.dict_has_value(self.__Atoms, keys, condition['value']):
                results.append(True)
            else:
                results.append(False)

        if condition_type == 'and':
            return all(results)
        else:
            return any(results)

    def Atoms_automation_action_list(self, **kwargs):
        """
        hook_automation_action_list called by the automation library to list possible actions.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'atom',
              'validation_callback': self.automation_action_validation,  # function to call to validate an action is possible.
              'do_action_callback': self.automation_do_action  # function to be called to perform an action
            }
         ]

    def automation_action_validation(self, rule, **kwargs):
        """
        A callback to check if a provided action is valid before being added as a possible action.

        :param kwargs: None
        :return:
        """
        item = kwargs['item']
        action = rule['condition'][item]

        if action['platform'] == 'call_function':
            if 'component_callback' in action:
                if not callable(action['component_callback']):
                    logger.warn("Rule '{rule_name}' is not callable by reference: 'component_callback': {callback}", rule_name=rule['name'], callback=action['component_callback'])
                    return False
                else:
                    rule['action'][item]['_my_callback'] = action['component_callback']
            else:
                if all( required in action for required in ['component_type', 'component_name', 'component_function']):
                    if action['component_type'] == 'library':
                        if action['component_name'] not in self._Libraries:
                            return False
                        if hasattr(self._Libraries[action['component_name']], action['component_function']):
                            method = getattr(self._Libraries[action['component_name']], action['component_function'])
                            if not callable(method):
                                logger.warn("Rule '{rule_name}' is not callable by name: 'component_type, component_name, component_function'", rule_name=rule['name'])
                                return False
                            else:
                                rule['action'][item]['_my_callback'] = method
                    elif action['component_type'] == 'module':
                        if action['component_name'] not in self._Modules:
                            return False
                        if hasattr(self._Modules[action['component_name']], action['component_function']):
                            method = getattr(self._Modules[action['component_name']], action['component_function'])
                            if not callable(method):
                                logger.warn("Rule '{rule_name}' is not callable by name: 'component_type, component_name, component_function'", rule_name=rule['name'])
                                return False
                            else:
                                rule['action'][item]['_my_callback'] = method
                    else:
                        logger.warn("Rule() '{rule_name}' doesn't have a valid component_type: ", rule_name=rule['name'])
                        return False

                else:
                    logger.warn("Rule '{rule_name}' needs either 'component_callback' or 'component_type, component_name, component_function'", rule_name=rule['name'])
                    return False
        else:
            logger.warn("Rule '{rule_name}' doesn't have a valid 'call_function' configuration", rule_name=rule['name'])
            return False
#        logger.warn("saving rule: {rule}", rule=rule)
        return True


#        platform = kwargs['platform']
        actions = kwargs['actions']
        for action in actions:
            if all( required in action for required in ['name', 'value']):
                keys = action['name'].split(':')
                if not yombo.utils.dict_has_key(self.__Atoms, keys):
                    return False
            else:
                return False
        return True

    def automation_do_action(self, rule, **kwargs):
        """
        A callback to perform an action.

        :param kwargs: None
        :return:
        """
        actions = rule['actions']
        for action in actions:
            keys = deque(action['name'].split(':'))
            yombo.utils.dict_set_value(self.__Atoms, keys, action['value'])
