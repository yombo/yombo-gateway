# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * End user documentation: `Atoms @ User Documentation <https://yombo.net/docs/gateway/web_interface/atoms>`_
  * For library documentation, see: `Atoms @ Library Documentation <https://yombo.net/docs/libraries/atoms>`_

.. seealso::

   * The :doc:`States library </lib/states>` is used to store items whose data changes.
   * The :doc:`System Data Mixin </mixins/systemdata_mixin>` handles the bulk of the actions.

Atoms provide non-changing information about the environment the gateway is running in as well as about the
Yombo Gateway software. Atoms are generally immutable, however, if the system state changes and is detected, the
atom should also be updated.

For dynamically changing data, use :py:mod:`States <yombo.lib.states>`.

**Usage**:

.. code-block:: python

   if self._Atom["os"] != None:
       logger.debug("Running on operating system: {operatingsystem}", operatingsystem=self._Atom["os"])

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/atoms.html>`_
"""
# Import python libraries
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

import distro
import os
import platform
import sys
from time import time
from typing import ClassVar, List

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import AtomSchema
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.mixins.systemdata_mixin import SystemDataParentMixin, SystemDataChildMixin

logger = get_logger("library.atoms")

_MAP_OS_NAME = {
    "redhatente": "RedHat",
    "debian": "Debian",
}

_MAP_OS_FAMILY = {
    'Ubuntu': 'Debian',
    'Fedora': 'RedHat',
    'CentOS': 'RedHat',
    'GoOSe': 'RedHat',
    'Scientific': 'RedHat',
    'Amazon': 'RedHat',
    'CloudLinux': 'RedHat',
    'Mandrake': 'Mandriva',
    'ESXi': 'VMWare',
    'VMWareESX': 'VMWare',
    'Bluewhite64': 'Bluewhite',
    'Slamd64': 'Slackware',
    'OVS': 'Oracle',
    'OEL': 'Oracle',
    'SLES': 'Suse',
    'SLED': 'Suse',
    'openSUSE': 'Suse',
    'SUSE': 'Suse'
}
DEFAULT = object()


class Atom(Entity, LibraryDBChildMixin, SystemDataChildMixin):
    """
    Represents a single atom.
    """
    _Entity_type: ClassVar[str] = "Atom"
    _Entity_label_attribute: ClassVar[str] = "atom_id"


class Atoms(YomboLibrary, SystemDataParentMixin, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Provides information about the system environment and yombo gateway.
    """
    atoms: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "atom_id"
    _storage_label_name: ClassVar[str] = "atom"
    _storage_class_reference: ClassVar = Atom
    _storage_schema: ClassVar = AtomSchema()
    _storage_attribute_name: ClassVar[str] = "atoms"
    _storage_search_fields: ClassVar[List[str]] = [
        "atom_id", "value"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "atom_id"

    def __delitem__(self, state_requested: str) -> None:
        """
        Deleting atoms is not possible.
        """
        return

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Sets up the atom library and files basic atoms values about the system.

        :return: None
        """
        self.logger = logger
        self.atoms[self._gateway_id] = {}
        yield self.load_from_database()
        yield self.set_yield("app_dir", self._Configs.app_dir, value_type="string", request_context=self)
        yield self.set_yield("working_dir", self._Configs.working_dir, value_type="string", request_context=self)
        yield self.set_yield("gateway.running_since", time(), value_type="int", request_context=self)
        yield self.os_data()

    def os_data(self) -> None:
        """
        Sets atoms concerning the operating system.
        """
        os_platform = sys.platform
        self.set("gateway.pid", os.getpid(), value_type="int", request_context=self)
        (_, system_name, kernel_version, kernel_notes, cpu_arch, _) = platform.uname()
        self.set("hardware.cpu_arch", cpu_arch, value_type="string", request_context=self)
        self.set("system.name", system_name, value_type="string", request_context=self)
        self.set("os.type", os_platform, value_type="string", request_context=self)
        self.set("os.kernel_version", kernel_version, value_type="string", request_context=self)
        self.set("os.kernel_notes", kernel_notes, value_type="string", request_context=self)
        self.set("python.version", platform.python_version(), value_type="string", request_context=self)
        cpu_count = 1
        mem_total = 550502400
        mem_sizing = "small"
        os_family = "Unknown"
        if HAS_PSUTIL:
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            mem_total = memory.total
            if mem_total < 550502400:  # less then 525mb
                mem_sizing = "x_small"
            elif mem_total < 1101004800:  # less then 1050mb
                mem_sizing = "small"
            elif mem_total < 1651507200:  # less then 1575mb
                mem_sizing = "medium"
            elif mem_total < 2202009600:  # less than 2100mb
                mem_sizing = "large"
            elif mem_total < 4404019200:  # less than 4200mb
                mem_sizing = "x_large"
            else:                         # more than 4200mb
                mem_sizing = "xx_large"

        self.set("system.cpu_count", cpu_count, value_type="int", request_context=self)
        self.set("system.memory_total", mem_total, value_type="int", request_context=self)
        self.set("system.memory_sizing", mem_sizing, value_type="string", request_context=self)

        if os_platform == "Windows":
            self.set("os.family", "windows", value_type="string", request_context=self)
            self.set("os.distrofamily", "nt", value_type="string", request_context=self)
        elif os_platform == "Linux":
            self.set("os.family", "linux", value_type="string", request_context=self)
            (osname, osrelease, oscodename) = \
                [x.strip(""").strip(""") for x in
                 distro.linux_distribution()]
            self.set("os.release", osrelease.strip(), value_type="string", request_context=self)
            self.set("os.oscodename", oscodename.strip(), value_type="string", request_context=self)

            distroname = osname.lower().strip()
            self.set("os.distroname", distroname, value_type="string", request_context=self)
            shortname = distroname.replace(" ", "").lower()[:10]
            self.set("os.distrofamily", _MAP_OS_NAME.get(shortname, distroname), value_type="string", request_context=self)

        elif os_platform == "Darwin":
            self.set("os.family", "darwin", value_type="string", request_context=self)
            self.set("os.distrofamily", "darwin", value_type="string", request_context=self)
        elif os_platform == "SunOS":
            self.set("os.family", "solaris", value_type="string", request_context=self)
            self.set("os.distrofamily", "solaris", value_type="string", request_context=self)
        else:
            self.set("os.family", _MAP_OS_FAMILY.get(os_platform, os_platform),
                     value_type="string", request_context=self)
