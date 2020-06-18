# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `Commands @ Library Documentation <https://yombo.net/docs/libraries/modules_installed>`_

A very simple library to track which modules are installed, it's install branch and commit. Primarily used
for interfacing with the database.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/modulesinstalled.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin

logger = get_logger("library.modules_installed")


class ModuleInstalledItem(Entity, LibraryDBChildMixin):
    """
    Represent a single module installed data item.
    """
    _Entity_type: ClassVar[str] = "Module Installed"
    _Entity_label_attribute: ClassVar[str] = "module_id"


class ModulesInstalled(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages tracking module installed data.

    All modules already have a predefined reference to this library as
    `self._Commands`. All documentation will reference this use case.
    """
    modules_installed: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "module_installed_id"
    _storage_attribute_name: ClassVar[str] = "modules_installed"
    _storage_label_name: ClassVar[str] = "module_installed"
    _storage_class_reference: ClassVar = ModuleInstalledItem
    _storage_search_fields: ClassVar[str] = [
        "module_installed_id", "installed_branch", "installed_commit"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "module_installed_id"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Loads all modules installed data.
        """
        yield self.load_from_database()
