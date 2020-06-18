"""
.. note::

  * For library documentation, see: `Categories @ Library Documentation <https://yombo.net/docs/libraries/categories>`_

This library maintains a list of all available categories. The categories (plural) is a wrapper class and contains all
the individual category classes.

The category (singular) class represents one category.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/categories.html>`_
"""
from typing import ClassVar

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin

logger = get_logger("library.categories")


class Category(Entity, LibraryDBChildMixin):
    """
    A command is represented by this class is returned to callers of the
    :py:meth:`get() <Commands.get>` or :py:meth:`__getitem__() <Commands.__getitem__>` functions.
    """
    _Entity_type: ClassVar[str] = "Category"
    _Entity_label_attribute: ClassVar[str] = "machine_label"


class Categories(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages all available categories for various items.

    All modules already have a predefined reference to this library as
    `self._Categories`. All documentation will reference this use case.
    """
    categories: ClassVar[dict] = {}

    _storage_primary_field_name: ClassVar[str] = "category_id"
    _storage_attribute_name: ClassVar[str] = "categories"
    _storage_label_name: ClassVar[str] = "category"
    _storage_class_reference: ClassVar = Category
    # _storage_schema: ClassVar = CategorySchema()
    _storage_search_fields: ClassVar[str] = [
        "category_id", "label", "machine_label",
    ]
    _storage_attribute_sort_key: ClassVar[str] = "machine_label"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Loads commands from the database and imports them.
        """
        yield self.load_from_database()
