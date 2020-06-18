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

:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/inputtypes/__init__.html>`_
"""
from collections import Callable
from functools import reduce
from pyclbr import readmodule
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.schemas import InputTypeSchema
from yombo.lib.inputtypes.input_type import InputType
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.core.log import get_logger

logger = get_logger("library.inputtypes")


class InputTypes(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages all input types available for input types.

    All modules already have a predefined reference to this library as
    `self._InputTypes`. All documentation will reference this use case.
    """
    input_types: dict = {}
    platforms: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "input_type_id"

    _storage_attribute_name: ClassVar[str] = "input_types"
    _storage_label_name: ClassVar[str] = "input_type"
    _storage_class_reference: ClassVar = None
    _storage_schema: ClassVar = InputTypeSchema()
    _storage_search_fields: ClassVar[List[str]] = [
        "input_type_id", "machine_label", "label", "category_id", "description"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "created_at"
    _storage_attribute_sort_key_order: ClassVar[str] = "desc"
    _storage_primary_field_name_extra: ClassVar[list] = ["is_usable"]

    @inlineCallbacks
    def _init_(self, **kwargs) -> None:
        """
        Setups up the basic framework. Loads the system input type classes.
        """
        # load base input type.
        # self.load_platforms({"yombo.lib.inputtypes.input_type": ["InputType"]})
        classes = yield self._Files.extract_classes_from_files("yombo/lib/inputtypes/input_type.py")
        self.platforms.update(classes)

        # load system input types
        files = yield self._Files.search_path_for_files("yombo/lib/inputtypes/platforms/*.py")
        # print(f"input types - files, system: {files}")
        classes = yield self._Files.extract_classes_from_files(files)
        # print(f"input types - classes, system: {classes}")
        self.platforms.update(classes)

        # load module input types
        files = yield self._Modules.search_modules_for_files("inputtypes/*.py")
        classes = yield self._Files.extract_classes_from_files(files)
        self.platforms.update(classes)
        self.platforms = dict((k.lower(), v) for k, v in self.platforms.items())

        yield self.load_from_database()  # have to load after we have all input type platforms.

    def load_an_item_to_memory_pre_check(self, incoming, load_source):
        """ Checks if the given input item should be loaded into memory. """
        platform = incoming["machine_label"].replace("_", "")
        incoming["is_usable"] = True
        if platform not in self.platforms:
            incoming["is_usable"] = False
            raise YomboWarning(f"Input type platform not found: {platform}")

    def _storage_class_reference_getter(self, incoming: dict) -> Type[InputType]:
        """
        Return the correct class to use to create individual input types.

        This is called by load_an_item_to_memory

        :param incoming:
        :return:
        """
        if incoming["machine_label"] in self.platforms:
            return self.platforms[incoming["machine_label"].replace("_", "")]
        else:
            return InputType

    def check(self, input_type_requested, value, **kwargs):
        input_type_platform = self.get(input_type_requested)
        # print("validator: %s" % validator)
        return input_type_platform.validate(value, **kwargs)
