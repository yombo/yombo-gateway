# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `Commands @ Library Documentation <https://yombo.net/docs/libraries/commands>`_

This library maintains a list of all available commands. The commands (plural) is a wrapper class and contains all
the individual command classes.

The command (singular) class represents one command.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/commands.html>`_
"""
from typing import ClassVar

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import CommandSchema
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin

logger = get_logger("library.commands")


class Command(Entity, LibraryDBChildMixin):
    """
    A command is represented by this class is returned to callers of the
    :py:meth:`get() <Commands.get>` or :py:meth:`__getitem__() <Commands.__getitem__>` functions.
    """
    _Entity_type: ClassVar[str] = "Command"
    _Entity_label_attribute: ClassVar[str] = "machine_label"


class Commands(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages all commands available for devices.

    All modules already have a predefined reference to this library as
    `self._Commands`. All documentation will reference this use case.
    """
    commands: ClassVar[dict] = {}

    _storage_primary_field_name: ClassVar[str] = "command_id"
    _storage_attribute_name: ClassVar[str] = "commands"
    _storage_label_name: ClassVar[str] = "command"
    _storage_class_reference: ClassVar = Command
    _storage_schema: ClassVar = CommandSchema()
    _storage_search_fields: ClassVar[str] = [
        "command_id", "label", "machine_label", "description",
    ]
    _storage_attribute_sort_key: ClassVar[str] = "machine_label"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Loads commands from the database and imports them.
        """
        yield self.load_from_database()
