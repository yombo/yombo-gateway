# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `MQTTUsers @ Library Documentation <https://yombo.net/docs/libraries/mqttusers>`_

Manages user accounts that can access the mqtt broker.

.. note::

   This is a placeholder library and is not functionally complete!

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/mqttusers.html>`_
"""
from passlib.hash import argon2, bcrypt
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor, threads


# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import MQTTUserSchema
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin

logger = get_logger("library.mqttusers")


class MQTTUser(Entity, LibraryDBChildMixin):
    """
    Represents a single mqtt user.
    Topics value:
        { topic_name: [access_values]}

    Example:
    topics = {
        "topic/here/+": ['read', 'write']
        "another/topic": ['read']
    }
    """
    _Entity_type: ClassVar[str] = "MQTTUser"
    _Entity_label_attribute: ClassVar[str] = "machine_label"


class MQTTUsers(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages users that are allowed to access the MQTT broker.
    """
    mqtt_users: ClassVar[dict] = {}

    _storage_primary_field_name: ClassVar[str] = "mqttuser_id"
    _storage_attribute_name: ClassVar[str] = "mqtt_users"
    _storage_label_name: ClassVar[str] = "mqtt_users"
    _storage_class_reference: ClassVar = MQTTUser
    _storage_schema: ClassVar = MQTTUserSchema()
    _storage_pickled_fields: ClassVar[Dict[str, str]] = {"topics": "msgpack"}
    _storage_search_fields: ClassVar[str] = [
        "mqttuser_id", "machine_label", "description",
    ]
    _storage_attribute_sort_key: ClassVar[str] = "machine_label"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Loads mqtt users from the database and imports them.
        """
        yield self.load_from_database()
