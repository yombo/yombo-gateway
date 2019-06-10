# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `Input Types @ Library Documentation <https://yombo.net/docs/libraries/input_types>`_

This library maintains a list of all available input types. The input types (plural) is a wrapper class and contains all
the individual input type classes.

The input type (singular) class represents one input type.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/inputtypes.html>`_
"""
import collections
from functools import reduce
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.mixins.library_db_model_mixin import LibraryDBModelMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.core.log import get_logger
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.inputtypes")

BASE_INPUT_TYPE_PLATFORMS = {
    "yombo.lib.inputtypes.automation_addresses": ["X10_Address", "X10_House", "X10_Unit", "Insteon_Address"],
    "yombo.lib.inputtypes.basic_addresses": ["Email", "YomboUsername", "URI", "URL"],
    "yombo.lib.inputtypes.basic_types": ["_Any", "_Bool", "_Checkbox", "_Float", "Filename", "_Integer", "_None",
                                         "Number", "Password", "Percent", "_String"],
    "yombo.lib.inputtypes.ip_address": ["IP_Address", "IP_Address_Public", "IP_Address_Private", "IPv4_Address",
                                        "IPv4_Address_Public", "IPv4_Address_Private", "IPv6_Address",
                                        "IPv6_Address_Public", "IPv6_Address_Private"],
    "yombo.lib.inputtypes.latin_alphabet": ["Latin_Alphabet", "Latin_Alphanumeric"],
    "yombo.lib.inputtypes.yombo_items": ["Yombo_Command", "Yombo_Device_Type", "Yombo_Module",
                                         "Yombo_Device"],
}

class InputTypes(YomboLibrary, LibraryDBModelMixin, LibrarySearchMixin):
    """
    Manages all input types available for input types.

    All modules already have a predefined reference to this library as
    `self._InputTypes`. All documentation will reference this use case.
    """
    input_types = {}
    platforms = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_load_hook_prefix = "input_type"
    _class_storage_load_db_class = None
    _class_storage_attribute_name = "input_types"
    _class_storage_search_fields = [
        "input_type_id", "machine_label", "label", "category_id", "description"
    ]
    _class_storage_sort_key = "machine_label"

    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.load_platforms(BASE_INPUT_TYPE_PLATFORMS)

    @inlineCallbacks
    def _load_(self, **kwargs):
        """
        Loads all input types from DB to various arrays for quick lookup.
        """
        yield self._class_storage_load_from_database()

    def _class_storage_get_instance_model(self, incoming):
        """
        Return the correct class to use to create individual input types.

        This is called by _class_storage_load_db_items_to_memory

        :param incoming:
        :return:
        """
        # print(f"input typoe: {incoming['machine_label']}")
        if incoming["machine_label"] in self.platforms:
            return self.platforms[incoming["machine_label"]]
        else:
            return self.platforms["any"]

    def load_platforms(self, platforms):
        """
        Load the platforms and prep them for usage.

        :param platforms: 
        :return: 
        """
        for path, items in platforms.items():
            for item in items:
                item_key = item.lower()
                if item_key.startswith("_"):
                    item_key = item_key[1:]

                module_root = __import__(path, globals(), locals(), [], 0)
                module_tail = reduce(lambda p1, p2: getattr(p1, p2), [module_root, ] + path.split(".")[1:])
                klass = getattr(module_tail, item)
                if not isinstance(klass, collections.Callable):
                    logger.warn("Unable to load input type platform '{name}', it's not callable.", name=item)
                    continue
                self.platforms[item_key] = klass

    def check(self, input_type_requested, value, **kwargs):
        input_type_platform = self.get(input_type_requested)
        # print("validator: %s" % validator)
        return input_type_platform.validate(value, **kwargs)
