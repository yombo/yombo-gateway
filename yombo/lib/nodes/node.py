# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Nodes @ Library Documentation <https://yombo.net/docs/libraries/nodes>`_

Nodes store generic information and are used to store information that doesn't need specific database needs.

**Besure to double check if the function being used returns a deferred. Many times, the node may be in the
database and needs to be retrieved using a Deferred.**

Nodes differ from SQLDict in that Nodes can be managed by the Yombo API, while SQLDict is only used
for local data.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2017-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/nodes/node.html>`_
"""
from copy import deepcopy
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin

logger = get_logger("library.node")


class Node(Entity, LibraryDBChildMixin):
    """
    A class to manage a single node.

    :ivar node_id: (string) The unique ID.
    :ivar label: (string) Human label
    :ivar machine_label: (string) A non-changable machine label.
    :ivar category_id: (string) Reference category id.
    :ivar input_regex: (string) A regex to validate if user input is valid or not.
    :ivar always_load: (int) 1 if this item is loaded at startup, otherwise 0.
    :ivar status: (int) 0 - disabled, 1 - enabled, 2 - deleted
    :ivar public: (int) 0 - private, 1 - public pending approval, 2 - public
    :ivar created_at: (int) EPOCH time when created
    :ivar updated_at: (int) EPOCH time when last updated
    """
    _sync_to_api: ClassVar[bool] = True
    _Entity_type: ClassVar[str] = "Node"
    _Entity_label_attribute: ClassVar[str] = "node_id"

