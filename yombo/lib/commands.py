# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `Commands @ Library Documentation <https://yombo.net/docs/libraries/commands>`_

This library maintains a list of all available commands. The commands (plural) is a wrapper class and contains all
the individual command classes.

The command (singular) class represents one command.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/commands.html>`_
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.classes.fuzzysearch import FuzzySearch
from yombo.core.entity import Entity
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.sync_to_everywhere_mixin import SyncToEverywhereMixin
from yombo.mixins.library_db_model_mixin import LibraryDBModelMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin

logger = get_logger("library.commands")


class Command(Entity, LibraryDBChildMixin, SyncToEverywhereMixin):
    """
    A command is represented by this class is returned to callers of the
    :py:meth:`get() <Commands.get>` or :py:meth:`__getitem__() <Commands.__getitem__>` functions.
    """
    _primary_column = "command_id"  # Used by mixins

    def __init__(self, parent, incoming, source=None):
        """
        Setup the command object using information passed in.

        :param incoming: A command containing required items to setup.
        :type incoming: dict
        :return: None
        """
        self._Entity_type = "Command"
        self._Entity_label_attribute = "machine_label"
        super().__init__(parent)
        self._setup_class_model(incoming, source=source)


class Commands(YomboLibrary, LibraryDBModelMixin, LibrarySearchMixin):
    """
    Manages all commands available for devices.

    All modules already have a predefined reference to this library as
    `self._Commands`. All documentation will reference this use case.
    """
    commands = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_load_hook_prefix = "command"
    _class_storage_load_db_class = Command
    _class_storage_attribute_name = "commands"
    _class_storage_search_fields = [
        "command_id", "label", "machine_label", "description", "voice_cmd",
    ]
    _class_storage_sort_key = "machine_label"

    def _init_(self, **kwargs):
        """
        Setups up the basic framework.

        """
        self.__yombocommandsByVoice = FuzzySearch(None, .92)

    @inlineCallbacks
    def _load_(self, **kwargs):
        """
        Loads commands from the database and imports them.
        """
        yield self._class_storage_load_from_database()

    def _clear_(self, **kwargs):
        """
        Clear all devices. Should only be called by the loader module
        during a reconfiguration event. B{Do not call this function!}
        """
        self.__yombocommandsByVoice.clear()

    def _reload_(self):
        self._load_()
