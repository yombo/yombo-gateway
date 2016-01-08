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
import sys

from platform import _supported_dists
_supported_dists += ('arch', 'mageia', 'meego', 'vmware', 'bluewhite64',
                     'slamd64', 'ovs', 'system', 'mint', 'oracle')
from collections import deque
from time import time

from yombo.core.log import getLogger
from yombo.core.library import YomboLibrary
logger = getLogger("library.YomboStates")

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
        self._ModDescription = "Yombo States API"
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "https://yombo.net"
        self.__Atoms = {}
        self.__Atoms.update(self.os_data())

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
        if key in self.__Atoms:
            return self.__Atoms[key]
        else:
            return None

    def set(self, key, value):
        self.__Atoms[key] = value

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

        if is_windows():
            atoms['os'] = 'Windows'
            atoms['os_family'] = 'Windows'
        elif is_linux():
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


def is_freebsd():
        """
        Returns if the host is linus or not
        """
        return sys.platform.startswith('freebsd')


def is_linux():
        """
        Returns if the host is linus or not
        """
        return sys.platform.startswith('linux')


def is_windows():
        """
        Returns if the host is windows or not
        """
        return sys.platform.startswith('win')