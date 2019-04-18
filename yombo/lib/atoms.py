# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * End user documentation: `Atoms @ User Documentation <https://yombo.net/docs/gateway/web_interface/atoms>`_
  * For library documentation, see: `Atoms @ Library Documentation <https://yombo.net/docs/libraries/atoms>`_

.. seealso::

   The :doc:`States library </lib/states>` is used to store items whose data changes.

Atoms provide non-changing information about the environment the gateway is running in as well as about the
Yombo Gateway software. Atoms are generally immutable, however, if the system state changes and is detected, the
atom should also be updated.

For dynamically changing data, use :py:mod:`States <yombo.lib.states>`.

**Usage**:

.. code-block:: python

   if self._Atom["os"] != None:
       logger.debug("Running on operating system: {operatingsystem}", operatingsystem=self._Atom["os"])

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/atoms.html>`_
"""
# Import python libraries
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from collections import OrderedDict
import os
import platform
import re
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
import yombo.core.settings as settings
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.utils
import yombo.utils.converters as converters

SUPPORTED_DISTS = platform._supported_dists + ("arch", "mageia", "meego", "vmware", "bluewhite64",
                     "slamd64", "ovs", "system", "mint", "oracle")
logger = get_logger("library.atoms")

_REPLACE_LINUX_RE = re.compile(r"linux", re.IGNORECASE)

_MAP_OS_NAME = {
    "redhatente": "RedHat",
    "gentoobase": "Gentoo",
    "archarm": "Arch ARM",
    "arch": "Arch",
    "debian": "Debian",
    "debiangnu/": "Debian",
    "raspbiangn": "Raspbian",
    "fedoraremi": "Fedora",
    "amazonami": "Amazon",
    "alt": "ALT",
    "enterprise": "OEL",
    "oracleserv": "OEL",
    "cloudserve": "CloudLinux",
    "pidora": "Fedora",
    "scientific": "ScientificLinux",
    "synology": "Synology",
    "nilrt": "NILinuxRT",
    "manjaro": "Manjaro",
    "antergos": "Antergos",
    "sles": "SUSE",
}

_MAP_OS_FAMILY = {
    "ALT": "RedHat",
    "Amazon": "RedHat",
    "Antergos": "Arch",
    "Arch ARM": "Arch",
    "Bluewhite64": "Bluewhite",
    "CentOS": "RedHat",
    "CloudLinux": "RedHat",
    "Devuan": "Debian",
    "ESXi": "VMWare",
    "Fedora": "RedHat",
    "GCEL": "Debian",
    "GoOSe": "RedHat",
    "Linaro": "Debian",
    "Mandrake": "Mandriva",
    "Manjaro": "Arch",
    "Mint": "Debian",
    "NILinuxRT": "NILinuxRT",
    "OpenIndiana": "Solaris",
    "OpenIndiana Development": "Solaris",
    "OpenSolaris": "Solaris",
    "OpenSolaris Development": "Solaris",
    "OEL": "RedHat",
    "OVS": "RedHat",
    "Raspbian": "Debian",
    "Scientific": "RedHat",
    "ScientificLinux": "RedHat",
    "Slamd64": "Slackware",
    "SLED": "Suse",
    "SLES": "Suse",
    "SmartOS": "Solaris",
    "Solaris": "Solaris",
    "SUSE": "Suse",
    "SUSE Enterprise Server": "Suse",
    "SUSE  Enterprise Server": "Suse",
    "Trisquel": "Debian",
    "Ubuntu": "Debian",
    "VMWareESX": "VMWare",
    "XCP": "RedHat",
    "XenServer": "RedHat",
    "antiX": "Debian",
    "elementary OS": "Debian",
    "openSUSE": "Suse",
    "openSUSE Leap": "Suse",
    "openSUSE Tumbleweed": "Suse",
}


class Atoms(YomboLibrary):
    """
    Provides information about the system environment and yombo gateway.
    """
    def __contains__(self, atom_requested):
        """
        Checks to if a provided atom exists.

            >>> if "cpu.count" in self._Atoms:
            >>>    print("The system has {0} cpus. ".format(self._Atoms["cpu.count"]))

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

            >>> system_cpus = self._Atoms["cpu.count"]

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

            >>> system_cpus = self._Atoms["cpu.count"] = 4

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
        return self.atoms[self.gateway_id].__iter__()

    def __len__(self):
        """
        Returns an int of the number of atoms defined.

        :return: The number of atoms defined.
        :rtype: int
        """
        return len(self.atoms[self.gateway_id])

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

        if gateway_id not in self.atoms:
            return []
        return list(self.atoms[gateway_id].keys())

    def items(self, gateway_id=None):
        """
        Gets a list of tuples representing the atoms defined.

        :return: A list of tuples.
        :rtype: list
        """
        if gateway_id is None:
            gateway_id = self.gateway_id

        if gateway_id not in self.atoms:
            return []
        return list(self.atoms[gateway_id].items())

    def values(self, gateway_id=None):
        """
        Gets a list of atom values
        :return: list
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        if gateway_id not in self.atoms:
            return []
        return list(self.atoms[gateway_id].values())

    def sorted(self, gateway_id):
        """
        Returns an OrderedDict of the atoms sorted by name.

        :param gateway_id: The gateway to get the atoms for, default is the local gateway.
        :type gateway_id: str
        :return: All atoms, sorted by atom name.
        :rtype: OrderedDict
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        return OrderedDict(sorted(self.atoms[gateway_id]))

    def _init_(self, **kwargs):
        """
        Sets up the atom library and files basic atoms values about the system.

        :return: None
        """
        self.library_state = 1
        # self.gateway_id = "local"
        self.gateway_id = self._Configs.get("core", "gwid", "local", False)
        self._loaded = False
        self.atoms = {self.gateway_id: {}}
        # if "local" not in self.atoms:
        #     self.atoms["local"] = {}
        self.os_data()

        self.triggers = {}
        # self._Automation = self._Libraries["automation"]
        self.set("working_dir", settings.arguments["working_dir"], source=self)
        self.set("app_dir", settings.arguments["app_dir"], source=self)

    def _load_(self, **kwargs):
        self._loaded = True
        self.library_state = 2
        self.set("running_since", time(), source=self)
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

        if key in self.atoms[gateway_id]:
            return True
        return False

    def get_last_update(self, key):
        """
        Get the time() the key was created or last updated.

        :param key: Name of atom to check.
        :return: Time() of last update
        :rtype: float
        """
        if key in self.atoms:
            return self.atoms[key]["updated_at"]
        else:
            raise KeyError(f"Cannot get state time: {key} not found")

    def get_copy(self, gateway_id=None):
        """
        Shouldn"t really be used. Just returns a _copy_ of all the atoms.

        :return: A dictionary containing all atoms.
        :rtype: dict
        """
        if gateway_id is None:
            return self.atoms.copy()
        if gateway_id in self.atoms:
            return self.atoms[gateway_id].copy()
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
        # logger.debug("atoms:get: {atom_requested}", atom_requested=atom_requested)
        if gateway_id is None:
            gateway_id = self.gateway_id

        self._Statistics.increment("lib.atoms.get", bucket_size=15, anon=True)
        search_chars = ["#", "+"]
        if any(s in atom_requested for s in search_chars):
            if gateway_id not in self.atoms:
                return {}
            results = yombo.utils.pattern_search(atom_requested, self.atoms[gateway_id])
            if len(results) > 1:
                values = {}
                for item in results:
                    if human is True:
                        values[item] = self.atoms[gateway_id][item]["value_human"]
                    elif full is True:
                        values[item] = self.atoms[gateway_id][item]
                    else:
                        values[item] = self.atoms[gateway_id][item]["value"]
                return values
            else:
                raise KeyError(f"Searched for atom, none found: {atom_requested}")

        if human is True:
            return self.atoms[gateway_id][atom_requested]["value_human"]
        elif full is True:
            return self.atoms[gateway_id][atom_requested]
        else:
            return self.atoms[gateway_id][atom_requested]["value"]

    @inlineCallbacks
    def set(self, key, value, value_type=None, gateway_id=None, human_value=None, source=None):
        """
        Get the value of a given atom (key).

        **Hooks called**:

        * _atoms_set_ : Sends kwargs "key", and "value". *key* is the name of the atom being set and *value* is
          the new value to set.

        :raises YomboWarning: Raised when request is malformed.
        :param key: Name of atom to set.
        :type key: string
        :param value: Value to set the atom to.
        :type value: mixed
        :param value_type: Data type to help with display formatting. Should be: str, dict, list, int, float, epoch
        :type value_type: string
        :param gateway_id: Gateway ID this atom belongs to, defaults to local gateway.
        :type gateway_id: string
        :param human_value: What to display to mere mortals.
        :type human_value: mixed
        :param source: Reference to the library or module settings this atom.
        :type source: object
        :return: Value of atom
        :rtype: mixed
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        # logger.debug("atoms:set: {gateway_id}: {key} = {value}", gateway_id=gateway_id, key=key, value=value)

        if gateway_id not in self.atoms:
            self.atoms[gateway_id] = {}

        source_type, source_label = yombo.utils.get_yombo_instance_type(source)

        search_chars = ["#", "+"]
        if any(s in key for s in search_chars):
            raise YomboWarning("state keys cannot have # or + in them, reserved for searching.")

        if key in self.atoms[gateway_id]:
            is_new = False
            # If state is already set to value, we don't do anything.
            self.atoms[gateway_id][key]["updated_at"] = int(round(time()))
            if human_value is not None:
                self.atoms[gateway_id][key]["value_human"] = human_value
            if self.atoms[gateway_id][key]["value"] == value:
                return
            self._Statistics.increment("lib.atoms.set.update", bucket_size=60, anon=True)
        else:
            is_new = True
            self.atoms[gateway_id][key] = {
                "gateway_id": gateway_id,
                "created_at": int(time()),
                "updated_at": int(time()),
            }
            self._Statistics.increment("lib.atoms.set.new", bucket_size=60, anon=True)

        self.atoms[gateway_id][key]["source"] = source_label

        self.atoms[gateway_id][key]["value"] = value
        if is_new is True or value_type is not None:
            self.atoms[gateway_id][key]["value_type"] = value_type

        if human_value is not None:
            self.atoms[gateway_id][key]["value_human"] = human_value
        else:
            self.atoms[gateway_id][key]["value_human"] = self.convert_to_human(value, value_type)

        # Call any hooks
        yield yombo.utils.global_invoke_all("_atoms_set_",
                                            called_by=self,
                                            key=key,
                                            value=value,
                                            value_type=value_type,
                                            value_full=self.atoms[gateway_id][key],
                                            gateway_id=gateway_id,
                                            source=source,
                                            source_label=source_label,
                                            )

    @inlineCallbacks
    def set_from_gateway_communications(self, key, data, source):
        """
        Used by the gateway coms (mqtt) system to set atom values.
        :param key:
        :param values:
        :return:
        """
        gateway_id = data["gateway_id"]
        if gateway_id == self.gateway_id:
            return
        if gateway_id not in self.atoms:
            self.atoms[gateway_id] = {}
        source_type, source_label = yombo.utils.get_yombo_instance_type(source)
        self.atoms[data["gateway_id"]][key] = {
            "gateway_id": data["gateway_id"],
            "value": data["value"],
            "value_human": data["value_human"],
            "value_type": data["value_type"],
            "source": source_label,
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
        }

        yield yombo.utils.global_invoke_all("_atoms_set_",
                                            called_by=self,
                                            key=key,
                                            value=data["value"],
                                            value_type=data["value_type"],
                                            value_full=self.atoms[gateway_id][key],
                                            gateway_id=gateway_id,
                                            source=source,
                                            source_label=source_label,
                                            )

    def convert_to_human(self, value, value_type):
        """
        Convert various value types to a more human friendly display.
        :param value:
        :param value_type:
        :return:
        """
        if value_type == "bool":
            results = yombo.utils.is_true_false(value)
            if results is not None:
                return results
            else:
                return value

        elif value_type == "epoch":
            return converters.epoch_to_string(value)
        else:
            return value

    def os_data(self):
        """
        Sets atoms concerning the operating system.

        :return: None
        """
        atoms = {}
        atoms["pid"] = os.getpid()
        (atoms["kernel"], atoms["system.name"], atoms["kernel.release"], version,
         atoms["cpu.arch"], _) = platform.uname()
        atoms["python.version"] = platform.python_version()
        atoms["python.build"] = platform.python_build()[0]
        atoms["cpu.count"] = 0
        atoms["mem.total"] = 0
        atoms["mem.sizing"] = "medium"
        atoms["os.family"] = "Unknown"
        if HAS_PSUTIL:
            atoms["cpu.count"] = psutil.cpu_count()
            memory = psutil.virtual_memory()
            atoms["mem.total"] = memory.total
        if memory.total < 550502400:  # less then 525mb
            atoms["mem.sizing"] = "x_small"
        elif memory.total < 1101004800:  # less then 1050mb
            atoms["mem.sizing"] = "small"
        elif memory.total < 1651507200:  # less then 1575mb
            atoms["mem.sizing"] = "medium"
        elif memory.total < 2202009600:  # less than 2100mb
            atoms["mem.sizing"] = "large"
        elif memory.total < 4404019200:  # less than 4200mb
            atoms["mem.sizing"] = "x_large"
        else:                            # more than 4200mb
            atoms["mem.sizing"] = "xx_large"

        if yombo.utils.is_windows():
            atoms["os"] = "Windows"
            atoms["os.family"] = "Windows"
        elif yombo.utils.is_linux():
            atoms["os"] = "Linux"
            atoms["os.family"] = "Linux"

            (osname, osrelease, oscodename) = \
                [x.strip(""").strip(""") for x in
                 # distro.linux_distribution(full_distribution_name=False)
                 platform.linux_distribution(supported_dists=SUPPORTED_DISTS)]

            if "os.fullname" not in atoms:
                atoms["os.fullname"] = osname.strip()
            if "os.release" not in atoms:
                atoms["os.release"] = osrelease.strip()
            atoms["os.codename"] = oscodename.strip()

            distroname = _REPLACE_LINUX_RE.sub("", atoms["os.fullname"]).strip()
            # return the first ten characters with no spaces, lowercased
            shortname = distroname.replace(" ", "").lower()[:10]
            # this maps the long names from the /etc/DISTRO-release files to the
            # traditional short names that Salt has used.
            atoms["os"] = _MAP_OS_NAME.get(shortname, distroname)

        elif atoms["kernel"] == "Darwin":
            atoms["os"] = "Mac"
            atoms["os.family"] = "Darwin"
        elif atoms["kernel"] == "SunOS":
            atoms["os"] = "SunOS"
            atoms["os.family"] = "Solaris"
        else:
            atoms["os"] = atoms["kernel"]

        for name, value in atoms.items():
            self.set(name, value, source=self)
        return atoms
