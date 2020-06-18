# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Module Core @ Module Development <https://yombo.net/docs/core/schemas>`_

Helps to ensure that inputs into libraries, and other places, are properly formatted.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/schemas.html>`_
"""
import simplejson as json
from marshmallow import Schema, fields, EXCLUDE, pre_load, post_load, validates_schema
from marshmallow.exceptions import ValidationError
from marshmallow.validate import Range, Length, ContainsOnly
from time import time
from typing import ClassVar
import string

from yombo.constants.authkeys import AUTHKEY_ID_LENGTH, AUTHKEY_ID_LENGTH_FULL
from yombo.constants.discovery import DISCOVERY_ID_LENGTH
from yombo.constants.device_states import DEVICESTATE_ID_LENGTH
from yombo.constants.locations import LOCATION_ID_LENGTH
from yombo.constants.roles import ROLE_ID_LENGTH
from yombo.core.entity import Entity

from yombo.utils import random_string

ALPHANUMERIC = string.ascii_letters + string.digits


def ID_VALIDATOR(min=None, max=None, length=None):
    if isinstance(length, int):
        return [Length(equal=length), ContainsOnly(ALPHANUMERIC)]
    if min is None:
        min = 20
    if max is None:
        max = 38
    return None
    return [Length(min=min, max=max), ContainsOnly(ALPHANUMERIC)]


def MACHINE_LABEL_VALIDATOR(min=None, max=None):
    if min is None:
        min = 3
    if max is None:
        max = 256
    return None
    return [Length(min=min, max=max), ContainsOnly(ALPHANUMERIC + "_")]


def PUBLIC_VALIDATOR(min=None, max=None):
    if min is None:
        min = 0
    if max is None:
        max = 2
    return None
    return [Range(min=min, max=max)]


def TIME_AT_VALIDATOR(min=None, max=None):
    if min is None:
        min = 0
    if max is None:
        max = 2147483647  # Unix Y2k 2038 issue
    return None
    return [Range(min=min, max=max), ContainsOnly(ALPHANUMERIC)]


def STATUS_VALIDATOR(min=None, max=None):
    if min is None:
        min = 0
    if max is None:
        max = 2
    return None
    return [Range(min=min, max=max)]


class YomboSchemaBase(Entity, Schema):
    """
    Add standardized processing to various schemas.
    """
    _Entity_type: ClassVar[str] = "Yombo schema base"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(None, *args, **kwargs)

    class Meta:
        unknown = EXCLUDE
        ordered = True
        additional = ("_meta", "_options")

    _fake_data = fields.Boolean(load_only=True, required=False, allow_none=True)
    _validate_general = True
    _id_length = None
    _timestamp_accuracy = None

    @pre_load(pass_many=False)
    def preprocess_general(self, incoming, **kwargs):
        """
        A simple function to validate common attributes. This will applied to all schemas, unless
        "_validate_general" is False.

        :param incoming:
        :return:
        """
        if self._validate_general is False:
            return
        if hasattr(self, "preprocess_start"):
            self.preprocess_start(incoming)
        if isinstance(self._id_length, int):
            self.ensure_has_id(incoming)
        if isinstance(self._timestamp_accuracy, int):
            self.ensure_has_timestamps(incoming)
        if hasattr(self, "preprocess_finish"):
            self.preprocess_finish(incoming)
        return incoming

    def ensure_has_id(self, incoming: dict) -> None:
        """ Ensures the item has an id, if it doesn't, create one. """
        if ("id" not in incoming or incoming["id"] is None) and "id" in self.declared_fields:
            if self._id_length is None:
                raise ValidationError("Item has no ID, and cannot be generated.")
            incoming["id"] = random_string(length=self._id_length)

    def ensure_has_timestamps(self, incoming: dict) -> None:
        """ Ensure the the item has the proper time stamps. """

        if "created_at" not in incoming and "created_at" in self.declared_fields:
            incoming["created_at"] = self.generate_timestamp()
        if "updated_at" not in incoming and "updated_at" in self.declared_fields:
            incoming["updated_at"] = self.generate_timestamp()

    def generate_timestamp(self):
        if self._timestamp_accuracy == 0:
            return int(time())
        else:
            return round(time(), self._timestamp_accuracy)


class AtomSchema(YomboSchemaBase):
    _id_length = None
    _timestamp_accuracy = 0

    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR(min=2, max=256))
    gateway_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    value = fields.Field(required=True, allow_none=True)
    value_human = fields.Field(required=True, allow_none=True)
    value_type = fields.String(required=True, allow_none=True, validate=Length(max=8192))
    request_by = fields.String(required=True, allow_none=False, validate=Length(min=0, max=43))
    request_by_type = fields.String(required=True, allow_none=False, validate=Length(min=0, max=32))
    request_context = fields.String(required=True, allow_none=False, validate=Length(min=0, max=1024))
    last_access_at = fields.Integer(required=False, allow_none=True, validate=TIME_AT_VALIDATOR())
    created_at = fields.Integer(required=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=False, validate=TIME_AT_VALIDATOR())

    def preprocess_start(self, incoming: dict) -> None:
        """
        Set last access at to current time if empty.
        
        :param incoming: 
        :return: 
        """
        if "last_access_at" not in incoming:
            incoming["last_access_at"] = None

    @validates_schema
    def validate_value(self, incoming, **kwargs):
        if incoming["value"] is None:
            return
        # isinstance(incoming["value"], bytes) or \
        if isinstance(incoming["value"], str) or \
                isinstance(incoming["value"], int) or \
                isinstance(incoming["value"], float):
            return
        else:
            print(f"schema, atom, value type: {type(incoming['value'])} - {incoming['value']}")
            raise ValidationError("Atom value must be a string, float, or integer.",
                                  field_name="value",
                                  data=incoming["value"])
        if len(incoming["value"]) > 8192:
            raise ValidationError("Atom value length must be less than 8192.",
                                  field_name="value",
                                  data=incoming["value"])

    @validates_schema
    def validate_value_human(self, incoming, **kwargs):
        if incoming["value_human"] is None:
            return
        if isinstance(incoming["value_human"], int) or isinstance(incoming["value_human"], float):
            incoming["value_human"] = str(incoming["value_human"])
        if isinstance(incoming["value_human"], str) is False:
            # print(f'incoming["value_human"]: {type(incoming["value_human"])} - {incoming["value_human"]}')
            raise ValidationError("Atom value_human must be a string, float, or integer.",
                                  field_name="value_human",
                                  data=incoming["value_human"])
        # print(f"checking incoming lenght: {incoming}")
        if len(incoming["value_human"]) > 8192:
            raise ValidationError("Atom value_human length must be less than 8192.",
                                  field_name="value_human",
                                  data=incoming["value_human"])

class AuthKeySchema(YomboSchemaBase):
    _id_length = AUTHKEY_ID_LENGTH
    _timestamp_accuracy = 0
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    auth_key_id_full = fields.String(required=False, allow_none=True, validate=ID_VALIDATOR(max=100))
    preserve_key = fields.Boolean(required=False, allow_none=True)
    machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR(max=256))
    label = fields.String(required=False, allow_none=True, validate=Length(min=3, max=256))
    description = fields.String(required=False, allow_none=True, validate=Length(max=256))
    roles = fields.List(fields.Field(), required=True, allow_none=False, validate=Length(max=10000))
    request_by = fields.String(required=True, allow_none=False, validate=Length(max=43))
    request_by_type = fields.String(required=True, allow_none=False, validate=Length(max=32))
    request_context = fields.String(required=True, allow_none=False, validate=Length(max=256))
    expired_at = fields.Integer(allow_none=True, validate=TIME_AT_VALIDATOR())
    last_access_at = fields.Integer(required=False, allow_none=True, validate=TIME_AT_VALIDATOR())
    status = fields.Integer(required=True, allow_none=False, validate=STATUS_VALIDATOR())
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())

    def preprocess_start(self, incoming):
        """
        Sets the defaults.
        
        :param incoming:
        :return:
        """
        if "preserve_key" not in incoming or incoming["preserve_key"] is None:
            incoming["preserve_key"] = True

        if "status" not in incoming or incoming["status"] is None:
            incoming["status"] = 1
        if isinstance(incoming["status"], int) is False or incoming["status"] < 0 or incoming["status"] > 2:
            raise ValidationError("'status' must be an integer ranging from 0 to 2.")

        if "id" not in incoming:
            auth_key_id_full = random_string(length=AUTHKEY_ID_LENGTH_FULL)
            auth_key_id = self._Hash.sha256_compact(auth_key_id_full)
            incoming["id"] = auth_key_id
            if incoming["preserve_key"] is True:
                incoming["auth_key_id_full"] = auth_key_id_full
            else:
                incoming["auth_key_id_full"] = None

        if "auth_key_id_full" not in incoming:
            incoming["auth_key_id_full"] = None
        if "label" not in incoming or incoming["label"] is None:
            incoming["label"] = incoming["machine_label"]
        if "description" not in incoming or incoming["description"] is None:
            incoming["description"] = incoming["label"]
        if "roles" not in incoming or incoming["roles"] is None:
            incoming["roles"] = []
        if "last_access_at" not in incoming:
            incoming["last_access_at"] = int(time())
        if "expired_at" not in incoming:
            incoming["expired_at"] = None
        if "scope" not in incoming:
            incoming["scope"] = "local"


class CategorySchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    category_parent_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    category_type = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR())
    label = fields.String(required=True, allow_none=False, validate=Length(min=3, max=128))
    description = fields.String(allow_none=True, validate=Length(max=16777215))
    status = fields.Integer(required=True, allow_none=False, validate=STATUS_VALIDATOR())
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class CommandSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    user_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    original_user_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR(max=128))
    label = fields.String(required=True, allow_none=False, validate=Length(min=2, max=128))
    description = fields.String(allow_none=True, validate=Length(min=3, max=8192))
    public = fields.Integer(required=True, allow_none=False, validate=PUBLIC_VALIDATOR())
    status = fields.Integer(required=True, allow_none=False, validate=STATUS_VALIDATOR())
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class ConfigSchema(YomboSchemaBase):
    config = fields.String(required=True, allow_none=False)
    value = fields.Raw(allow_none=True)
    value_type = fields.String(required=True, allow_none=False)
    fetches = fields.Integer(required=True, allow_none=False)
    writes = fields.Integer(required=True, allow_none=False)
    device_command_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    checksum = fields.Integer(required=True, allow_none=False)
    source = fields.String(required=True, allow_none=False)
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class CronTabSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    minute = fields.Integer(required=True, allow_none=False, validate=Range(min=0, max=59))
    hour = fields.Integer(required=True, allow_none=False, validate=Range(min=0, max=23))
    day = fields.Integer(required=True, allow_none=False, validate=Range(min=1, max=31))
    month = fields.Integer(required=True, allow_none=False, validate=Range(min=1, max=12))
    dow = fields.Integer(required=True, allow_none=False, validate=Range(min=0, max=6))
    machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR())
    label = fields.String(required=True, allow_none=False, validate=Length(min=3, max=128))
    enabled = fields.Integer(required=True, allow_none=False, validate=Range(min=0, max=2))
    args = fields.String(allow_none=True, validate=Length(max=16777215))
    kwargs = fields.String(allow_none=True, validate=Length(max=16777215))
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class DeviceSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    gateway_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    user_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    device_type_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR())
    label = fields.String(required=True, allow_none=False, validate=Length(min=3, max=128))
    description = fields.String(allow_none=True, validate=Length(min=0, max=258))
    location_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    area_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    notes = fields.String(allow_none=True, validate=Length(max=16777215))
    attributes = fields.String(allow_none=True, validate=Length(max=1024))
    intent_allow = fields.Bool(allow_none=True)
    intent_text = fields.String(allow_none=True, validate=Length(max=1024))
    pin_code = fields.String(allow_none=True, validate=Length(max=1024))
    pin_required = fields.Bool(required=True, allow_none=False)
    pin_timeout = fields.Integer(allow_none=True, validate=Range(min=0, max=4294967295))
    statistic_label = fields.String(allow_none=True, validate=Length(max=256))
    statistic_lifetime = fields.Integer(allow_none=True, validate=Range(max=16777215))
    statistic_type = fields.String(allow_none=True, validate=Length(max=256))
    statistic_bucket_size = fields.Integer(allow_none=True, validate=Range(max=16777215))
    energy_type = fields.String(allow_none=True, validate=Length(max=256))
    energy_tracker_source_type = fields.String(allow_none=True, validate=Length(max=256))
    energy_tracker_source_id = fields.String(allow_none=True, validate=Length(max=256))
    energy_map = fields.Dict(allow_none=True)
    scene_controllable = fields.Bool(allow_none=True)
    allow_direct_control = fields.Bool(allow_none=True)
    status = fields.Integer(required=True, allow_none=False, validate=STATUS_VALIDATOR())
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    # Extra fields
    energy_tracker_source_id = fields.String(allow_none=True)

    def preprocess_start(self, incoming):
        """
        Sets the defaults. Also, converts the energy map from whatever (string, json, dict) to a dictionary.
        :param incoming:
        :return:
        """
        new_map = {"0.0": "0", "1.0": "0"}
        if "energy_map" in incoming:
            if isinstance(incoming["energy_map"], str):
                if len(incoming["energy_map"]) > 65534:
                    raise ValidationError("Must be smaller than 65534",
                                          field_name="energy_map",
                                          data=incoming["energy_map"])
                try:
                    incoming["energy_map"] = json.loads(incoming["energy_map"])
                except:
                    incoming["energy_map"] = new_map

            if isinstance(incoming["energy_map"], dict) is False:
                incoming["energy_map"] = new_map
        else:
            incoming["energy_map"] = new_map

        if "statistic_lifetime" in incoming:
            if incoming["statistic_lifetime"] is None:
                incoming["statistic_lifetime"] = 0
        else:
            incoming["statistic_lifetime"] = 0

        if "pin_timeout" in incoming:
            if incoming["pin_timeout"] is None:
                incoming["pin_timeout"] = 0
        else:
            incoming["pin_timeout"] = 0

        if "scene_controllable" in incoming:
            if incoming["scene_controllable"] is None:
                incoming["scene_controllable"] = 1
        else:
            incoming["scene_controllable"] = 1

        if "allow_direct_control" in incoming:
            if incoming["allow_direct_control"] is None:
                incoming["allow_direct_control"] = 1
        else:
            incoming["allow_direct_control"] = 1

    @post_load()
    def post_load_fixes(self, data, **kwargs):
        """
        Convert energy_map to a json from a dictionary.

        :param data:
        :return:
        """
        if isinstance(data["energy_map"], str):
            try:
                data["energy_map"] = json.loads(data["energy_map"])
            except Exception:
                data["energy_map"] = {"0.0": "0", "1.0": "0"}
        return data


class DeviceCommandInputSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    device_type_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    command_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    input_type_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR())
    label = fields.String(required=True, allow_none=False, validate=Length(min=2, max=128))
    live_update = fields.Bool(required=True, allow_none=False)
    value_required = fields.Bool(required=True, allow_none=False)
    value_max = fields.Integer(required=True, allow_none=False, validate=Range(min=0, max=65534))
    value_min = fields.Integer(required=True, allow_none=False, validate=Range(min=0, max=65534))
    value_casing = fields.String(required=True, allow_none=False, validate=Length(min=0, max=30))
    encryption = fields.String(required=True, allow_none=False, validate=Length(min=0, max=30))
    notes = fields.String(allow_none=True, validate=Length(min=0, max=2048))
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class DeviceCommandSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    persistent_request_id = fields.String(required=False, allow_none=True, validate=ID_VALIDATOR())
    gateway_id = fields.String(required=False, allow_none=True, validate=ID_VALIDATOR())
    device_id = fields.String(required=False, allow_none=True, validate=ID_VALIDATOR())
    device = fields.Field(required=False, allow_none=True, load_only=True)
    command_id = fields.String(required=False, allow_none=True, validate=ID_VALIDATOR())
    command = fields.Field(required=False, allow_none=True, load_only=True)
    inputs = fields.Dict(required=False, allow_none=True)
    created_at = fields.Number(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    broadcast_at = fields.Number(required=False, allow_none=True, validate=TIME_AT_VALIDATOR())
    accepted_at = fields.Number(required=False, allow_none=True, validate=TIME_AT_VALIDATOR())
    sent_at = fields.Number(required=False, allow_none=True, validate=TIME_AT_VALIDATOR())
    received_at = fields.Number(required=False, allow_none=True, validate=TIME_AT_VALIDATOR())
    pending_at = fields.Number(required=False, allow_none=True, validate=TIME_AT_VALIDATOR())
    finished_at = fields.Number(required=False, allow_none=True, validate=TIME_AT_VALIDATOR())
    not_before_at = fields.Number(required=False, allow_none=True, validate=TIME_AT_VALIDATOR())
    not_after_at = fields.Number(required=False, allow_none=True, validate=TIME_AT_VALIDATOR())
    history = fields.String(required=True, allow_none=False, validate=Length(min=0, max=65534))
    status = fields.String(required=True, allow_none=False, validate=STATUS_VALIDATOR())
    request_by = fields.String(required=True, allow_none=False, validate=Length(min=0, max=43))
    request_by_type = fields.String(required=True, allow_none=False, validate=Length(min=0, max=32))
    request_context = fields.String(required=True, allow_none=False, validate=Length(min=0, max=1024))
    idempotence = fields.String(allow_none=True, validate=Length(min=10, max=64))
    uploaded = fields.Bool(required=True, allow_none=False)
    uploadable = fields.Bool(required=True, allow_none=False)

    # Dumps (read-only)
    status_id = fields.Integer(dump_only=True)
    history = fields.Dict(dump_only=True)

    @validates_schema
    def validate_device_command(self, incoming, **kwargs):
        if ("device_id" in incoming is False and incoming["device_id"] is None) and \
                ("device" in incoming is False and incoming["device"] is None):
            raise ValidationError("Must supply either a device or device_id.",
                                  field_name="device_id",
                                  data=incoming["device_id"])
        if ("command_id" in incoming is False and incoming["command_id"] is None) and \
                ("command" in incoming is False and incoming["command"] is None):
            raise ValidationError("Must supply either a command or command_id.",
                                  field_name="device_id",
                                  data=incoming["device_id"])


class DeviceStateSchema(YomboSchemaBase):
    _id_length = DEVICESTATE_ID_LENGTH
    _timestamp_accuracy = 0

    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    gateway_id = fields.String(allow_none=True, validate=ID_VALIDATOR())
    device_id = fields.String(required=False, allow_none=True, validate=ID_VALIDATOR())
    device = fields.Field(required=False, allow_none=True, load_only=True)
    command_id = fields.String(required=False, allow_none=True, validate=ID_VALIDATOR())
    command = fields.Field(required=False, allow_none=True, load_only=True)
    device_command_id = fields.String(required=False, allow_none=True, validate=ID_VALIDATOR())
    device_command = fields.Field(required=False, allow_none=True, load_only=True)
    energy_usage = fields.Number(required=True, allow_none=False, validate=Range(min=-2147483647, max=2147483646))
    energy_type = fields.String(required=True, allow_none=False, validate=Length(min=0, max=64))
    human_state = fields.String(required=True, allow_none=False, validate=Length(min=0, max=1024))
    human_message = fields.String(required=True, allow_none=False, validate=Length(min=0, max=2048))
    machine_state_extra = fields.Dict(required=False, allow_none=True)
    machine_state = fields.Field(required=False, allow_none=True)
    request_by = fields.String(allow_none=True, validate=Length(min=0, max=43))
    request_by_type = fields.String(allow_none=True, validate=Length(min=0, max=32))
    request_context = fields.String(allow_none=True, validate=Length(min=0, max=256))
    uploaded = fields.Bool(required=True, allow_none=False)
    uploadable = fields.Bool(required=True, allow_none=False)
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())

    @validates_schema
    def validate_device_state(self, incoming, **kwargs):
        if ("device_id" in incoming is False and incoming["device_id"] is None) and \
                ("device" in incoming is False and incoming["device"] is None):
            raise ValidationError("Must supply either a device or device_id.",
                                  field_name="device_id",
                                  data=incoming["device_id"])


class DeviceTypeSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    user_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    original_user_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    category_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR())
    label = fields.String(required=True, allow_none=False, validate=Length(min=3, max=128))
    description = fields.String(allow_none=True, validate=Length(min=0, max=8192))
    platform = fields.String(allow_none=True, validate=Length(min=0, max=256))
    public = fields.Integer(required=True, allow_none=False, validate=PUBLIC_VALIDATOR())
    status = fields.Integer(required=True, allow_none=False, validate=STATUS_VALIDATOR())
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    # Set while loading
    is_usable = fields.Bool(required=False, allow_none=True)

class DeviceTypeCommandSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    device_type_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    command_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class DiscoverySchema(YomboSchemaBase):
    _id_length = DISCOVERY_ID_LENGTH
    _timestamp_accuracy = 0

    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    gateway_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    device_id = fields.String(required=False, allow_none=True, validate=ID_VALIDATOR())
    device_type_id = fields.String(required=False, allow_none=True, validate=ID_VALIDATOR())
    # device_type = fields.String(required=False, allow_none=True)
    discovered_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    last_seen_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    mfr = fields.String(required=True, allow_none=False, validate=Length(min=0, max=128))
    model = fields.String(required=True, allow_none=False, validate=Length(min=0, max=128))
    serial = fields.String(required=True, allow_none=False, validate=Length(min=0, max=128))
    label = fields.String(required=True, allow_none=True, validate=Length(min=0, max=256))
    machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR())
    description = fields.String(required=True, allow_none=False, validate=Length(min=0, max=1024))
    variables = fields.Dict(required=True, allow_none=True, validate=Length(max=15000))
    request_context = fields.String(required=True, allow_none=False, validate=Length(min=0, max=256))
    status = fields.Integer(required=True, allow_none=True, validate=STATUS_VALIDATOR())
    created_at = fields.Integer(required=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=False, validate=TIME_AT_VALIDATOR())

    @validates_schema
    def validate_device_type(self, incoming, **kwargs):
        if ("device_type_id" in incoming is False and incoming["device_type_id"] is None) and \
                ("device_type" in incoming is False and incoming["device_type"] is None):
            raise ValidationError(f"Must supply either a device_type_id or device_type: "
                                  f"{incoming['machine_label']} - {incoming['label']}")

    def preprocess_start(self, incoming: dict) -> None:
        """
        Set last access at to current time if empty.

        :param incoming:
        :return:
        """
        if "last_access_at" not in incoming or incoming["last_access_at"] is None:
            incoming["last_access_at"] = None
        else:
            incoming["last_access_at"] = int(incoming["last_access_at"])

        if "discovered_at" not in incoming or incoming["discovered_at"] is None:
            incoming["discovered_at"] = int(time())
        else:
            incoming["discovered_at"] = int(incoming["discovered_at"])

        if "last_seen_at" not in incoming or incoming["last_seen_at"] is None:
            incoming["last_seen_at"] = int(time())
        else:
            incoming["last_seen_at"] = int(incoming["last_seen_at"])

        if "created_at" not in incoming or incoming["created_at"] is None:
            incoming["created_at"] = int(time())
        else:
            incoming["created_at"] = int(incoming["created_at"])

        if "updated_at" not in incoming or incoming["updated_at"] is None:
            incoming["updated_at"] = int(time())
        else:
            incoming["updated_at"] = int(incoming["updated_at"])

        if "status" not in incoming or incoming["status"] is None:
            incoming["status"] = 1
        else:
            incoming["status"] = int(incoming["status"])


class GatewaySchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR())
    label = fields.String(required=True, allow_none=False, validate=Length(min=0, max=256))
    description = fields.String(allow_none=True, validate=Length(min=0, max=8192))
    user_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    mqtt_auth = fields.String(allow_none=True, validate=Length(min=0, max=128))
    mqtt_auth_next = fields.String(allow_none=True, validate=Length(min=0, max=128))
    mqtt_auth_last_rotate_at = fields.Integer(allow_none=True, validate=TIME_AT_VALIDATOR())
    internal_ipv4 = fields.String(allow_none=True, validate=Length(min=0, max=64))
    external_ipv4 = fields.String(allow_none=True, validate=Length(min=0, max=64))
    internal_ipv6 = fields.String(allow_none=True, validate=Length(min=0, max=64))
    external_ipv6 = fields.String(allow_none=True, validate=Length(min=0, max=64))
    internal_http_port = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    external_http_port = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    internal_http_secure_port = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    external_http_secure_port = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    internal_mqtt = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    internal_mqtt_le = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    internal_mqtt_ss = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    internal_mqtt_ws = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    internal_mqtt_ws_le = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    internal_mqtt_ws_ss = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    external_mqtt = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    external_mqtt_le = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    external_mqtt_ss = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    external_mqtt_ws = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    external_mqtt_ws_le = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    external_mqtt_ws_ss = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    is_master = fields.Boolean(required=True, allow_none=False)
    master_gateway_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    dns_name = fields.String(allow_none=True, validate=Length(min=0, max=256))
    status = fields.Integer(required=True, allow_none=False, validate=STATUS_VALIDATOR())
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())

    # Dump only items
    com_status = fields.String(dump_only=True)
    version = fields.String(dump_only=True)
    ping_request_id = fields.String(dump_only=True)
    ping_request_at = fields.Number(dump_only=True)
    ping_response_at = fields.Number(dump_only=True)
    ping_time_offset = fields.Number(dump_only=True)
    ping_roundtrip = fields.Number(dump_only=True)


class GPGKeyUIDSchema(Schema):
    name = fields.String(required=True)
    comment = fields.String(required=True)
    email = fields.String(required=True)
    endpoint_id = fields.String(required=True)
    endpoint_type = fields.String(required=True)
    original = fields.String(required=True)


class GPGKeySchema(YomboSchemaBase):
    trust = fields.String(required=True, allow_none=False)
    length = fields.Integer(required=True, allow_none=False)
    algo = fields.Integer(required=True, allow_none=False)
    keyid = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    date = fields.Integer(required=True, allow_none=False)
    expires = fields.Integer(required=True, allow_none=False)
    ownertrust = fields.String(required=True, allow_none=False)
    uids = fields.List(fields.Nested(GPGKeyUIDSchema), required=True, allow_none=False)
    sigs = fields.List(fields.String(), required=True, allow_none=False)
    subkeys = fields.List(fields.Field(), required=True, allow_none=False)
    fingerprint = fields.String(required=True, allow_none=False)
    has_private = fields.Boolean(required=True, allow_none=False)
    publickey = fields.String(required=True, allow_none=False)
    passphrase = fields.String(required=True, allow_none=True, load_only=True)
    uid_endpoint_id = fields.String(required=True, allow_none=True)
    uid_endpoint_type = fields.String(required=True, allow_none=True)


class InputTypeSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    user_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    original_user_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    category_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR())
    label = fields.String(required=True, allow_none=False, validate=Length(min=0, max=128))
    description = fields.String(allow_none=True, validate=Length(min=0, max=2048))
    public = fields.Integer(required=True, allow_none=False, validate=PUBLIC_VALIDATOR())
    status = fields.Integer(required=True, allow_none=False, validate=STATUS_VALIDATOR())
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    # Set while loading
    is_usable = fields.Bool(required=False, allow_none=True)


class LocationSchema(YomboSchemaBase):
    _id_length = LOCATION_ID_LENGTH

    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    user_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    location_type = fields.String(required=True, allow_none=False, validate=Length(min=2, max=32))
    machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR())
    label = fields.String(required=True, allow_none=False, validate=Length(min=0, max=256))
    description = fields.String(allow_none=True, validate=Length(min=0, max=2048))
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class ModuleSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    user_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    original_user_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    module_type = fields.String(required=True, allow_none=False, validate=Length(min=0, max=32))
    machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR())
    label = fields.String(required=True, allow_none=False, validate=Length(min=0, max=256))
    description = fields.String(allow_none=True, validate=Length(min=0, max=15000))
    short_description = fields.String(required=True, allow_none=False, validate=Length(min=0, max=256))
    medium_description = fields.String(required=True, allow_none=False, validate=Length(min=0, max=4096))
    medium_description_html = fields.String(required=True, allow_none=False, validate=Length(min=0, max=5120))
    description_html = fields.String(required=True, allow_none=False, validate=Length(min=0, max=65534))
    see_also = fields.String(allow_none=True, validate=Length(min=0, max=65534))
    repository_link = fields.String(allow_none=True, validate=Length(min=0, max=256))
    issue_tracker_link = fields.String(allow_none=True, validate=Length(min=0, max=256))
    install_count = fields.Integer(required=True, allow_none=False, validate=Range(min=0, max=4294967295))
    doc_link = fields.String(allow_none=True, validate=Length(min=0, max=256))
    git_link = fields.String(allow_none=True, validate=Length(min=0, max=256))
    git_auto_approve = fields.Bool(required=True, allow_none=False)
    install_branch = fields.String(required=True, allow_none=False, validate=Length(min=0, max=64))
    require_approved = fields.Bool(required=True, allow_none=False)
    public = fields.Integer(required=True, allow_none=False, validate=PUBLIC_VALIDATOR())
    status = fields.Integer(required=True, allow_none=False, validate=STATUS_VALIDATOR())
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class ModuleCommitSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    module_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    branch = fields.String(required=True, allow_none=False, validate=Length(min=0, max=128))
    commit = fields.String(required=True, allow_none=False, validate=Length(min=0, max=256))
    committed_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    approved = fields.Bool(allow_none=True)
    approved_at = fields.Integer(allow_none=True, validate=TIME_AT_VALIDATOR())
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class ModuleDeviceTypeSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    module_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    device_type_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class MQTTUserSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR())
    password = fields.String(required=True, allow_none=False, validate=Length(min=0, max=100))
    description = fields.String(required=True, allow_none=False, validate=Length(min=0, max=512))
    topics = fields.Dict(required=True, allow_none=False, validate=Length(min=0, max=15000))
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class NodeSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    node_parent_id = fields.String(allow_none=True, validate=ID_VALIDATOR())
    gateway_id = fields.String(allow_none=True, validate=ID_VALIDATOR())
    node_type = fields.String(required=True, allow_none=False, validate=Length(min=0, max=128))
    weight = fields.Integer(required=True, allow_none=False, validate=Range(min=-32767, max=32767))
    machine_label = fields.String(allow_none=True, validate=MACHINE_LABEL_VALIDATOR())
    label = fields.String(allow_none=True, validate=Length(min=0, max=256))
    always_load = fields.Bool(allow_none=True)
    destination = fields.String(allow_none=True, validate=Length(min=0, max=100))
    data = fields.Field(allow_none=True, validate=Length(min=0, max=65534))
    data_content_type = fields.String(required=True, allow_none=False, validate=Length(min=0, max=35))
    status = fields.Integer(required=True, allow_none=False, validate=STATUS_VALIDATOR())
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class PermissionSchema(YomboSchemaBase):
    _timestamp_accuracy = 0

    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    attach_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    attach_type = fields.String(required=True, allow_none=False, validate=Length(min=0, max=256))
    machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR())
    label = fields.String(required=True, allow_none=False, validate=Length(min=0, max=256))
    description = fields.String(required=True, allow_none=False, validate=Length(min=0, max=2048))
    policy = fields.String(required=True, allow_none=False, validate=Length(min=0, max=16384))
    request_by = fields.String(required=True, allow_none=False, validate=Length(min=0, max=43))
    request_by_type = fields.String(required=True, allow_none=False, validate=Length(min=0, max=32))
    request_context = fields.String(required=True, allow_none=False, validate=Length(min=0, max=256))
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class RoleSchema(YomboSchemaBase):
    _id_length = ROLE_ID_LENGTH
    _timestamp_accuracy = 0

    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR())
    label = fields.String(required=False, allow_none=False, validate=Length(min=0, max=256))
    description = fields.String(required=False, allow_none=True, validate=Length(min=0, max=1024))
    request_by = fields.String(required=True, allow_none=False, validate=Length(min=0, max=43))
    request_by_type = fields.String(required=True, allow_none=False, validate=Length(min=0, max=32))
    request_context = fields.String(required=True, allow_none=False, validate=Length(min=0, max=256))
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class SQLDictSchema(YomboSchemaBase):
    _timestamp_accuracy = 0

    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    component = fields.String(required=True, allow_none=False, validate=Length(min=0, max=128))
    dict_name = fields.String(required=True, allow_none=False, validate=Length(min=0, max=128))
    dict_data = fields.Dict(required=True, allow_none=False, validate=Length(min=0, max=65537))
    seralizer = fields.Field(load_only=True)
    unseralizer = fields.Field(load_only=True)
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class StateSchema(YomboSchemaBase):
    _timestamp_accuracy = 0

    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR(min=2, max=256))
    gateway_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    value = fields.Field(required=True, allow_none=True)
    value_human = fields.Field(required=True, allow_none=True)
    value_type = fields.String(required=True, allow_none=True, validate=Length(max=8192))
    request_by = fields.String(required=True, allow_none=False, validate=Length(min=0, max=43))
    request_by_type = fields.String(required=True, allow_none=False, validate=Length(min=0, max=32))
    request_context = fields.String(required=True, allow_none=False, validate=Length(min=0, max=1024))
    last_access_at = fields.Integer(required=False, allow_none=True, validate=TIME_AT_VALIDATOR())
    created_at = fields.Integer(required=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=False, validate=TIME_AT_VALIDATOR())

    def preprocess_start(self, incoming: dict) -> None:
        """
        Set last access at to current time if empty.

        :param incoming:
        :return:
        """
        if "last_access_at" not in incoming:
            incoming["last_access_at"] = None

    @validates_schema
    def validate_value(self, incoming, **kwargs):
        if incoming["value"] is None:
            return
        if isinstance(incoming["value"], int) or isinstance(incoming["value"], float):
            # incoming["value"] = str(incoming["value"])
            return
        if isinstance(incoming["value"], str) is False:
            print(f'incoming["value"]: {type(incoming["value"])} - {incoming["value"]}')
            raise ValidationError("State value must be a string, float, or integer.",
                                  field_name="value",
                                  data=incoming["value"])
        if len(incoming["value"]) > 8192:
            raise ValidationError("State value length must be less than 8192.",
                                  field_name="value",
                                  data=incoming["value"])

    @validates_schema
    def validate_value_human(self, incoming, **kwargs):
        if incoming["value_human"] is None:
            return
        if isinstance(incoming["value_human"], int) or isinstance(incoming["value_human"], float):
            incoming["value_human"] = str(incoming["value_human"])
            return
        if isinstance(incoming["value_human"], str) is False:
            print(f'incoming["value_human"]: {type(incoming["value_human"])} - {incoming["value_human"]}')
            raise ValidationError("State value_human must be a string, float, or integer.",
                                  field_name="value_human",
                                  data=incoming["value_human"])
        if len(incoming["value_human"]) > 8192:
            raise ValidationError("State value_human length must be less than 8192.",
                                  field_name="value_human",
                                  data=incoming["value_human"])


class StorageSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    gateway_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    scheme = fields.String(allow_none=True, validate=Length(max=32))
    username = fields.String(allow_none=True, validate=Length(max=64))
    password = fields.String(required=True, allow_none=False, validate=Length(max=64))
    netloc = fields.String(required=True, allow_none=False, validate=Length(max=32))
    port = fields.Integer(allow_none=True, validate=Range(min=30, max=65535))
    path = fields.String(allow_none=True, validate=Length(max=256))
    params = fields.String(allow_none=True, validate=Length(max=2048))
    query = fields.String(allow_none=True, validate=Length(max=2048))
    fragment = fields.String(allow_none=True, validate=Length(max=2048))
    mangle_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    expires = fields.Integer(required=True, allow_none=False, validate=Range(min=0, max=65535))
    public = fields.String(required=True, allow_none=False, validate=Length(max=65534))
    internal_url = fields.String(required=True, allow_none=False, validate=Length(max=2048))
    external_url = fields.String(required=True, allow_none=False, validate=Length(max=2048))
    internal_thumb_url = fields.String(required=True, allow_none=False, validate=Length(max=2048))
    external_thumb_url = fields.String(required=True, allow_none=False, validate=Length(max=2048))
    content_type = fields.String(required=True, allow_none=False, validate=Length(max=2048))
    charset = fields.String(required=True, allow_none=False, validate=Length(max=2048))
    size = fields.Integer(required=True, allow_none=False, validate=Range(min=0, max=65535))
    file_path = fields.String(required=True, allow_none=False, validate=Length(max=2048))
    file_path_thumb = fields.String(required=True, allow_none=False, validate=Length(max=2048))
    variables = fields.String(required=True, allow_none=False, validate=Length(max=10000))
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class UserSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    gateway_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    email = fields.String(required=True, allow_none=False, validate=Length(min=0, max=255))
    name = fields.String(required=True, allow_none=False, validate=Length(min=0, max=255))
    access_code_string = fields.String(allow_none=True, validate=Length(min=0, max=32))
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class VariableDataSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    user_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    gateway_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    variable_field_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    variable_relation_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    variable_relation_type = fields.String(required=True, allow_none=False, validate=Length(min=0, max=255))
    data = fields.String(required=True, allow_none=False, validate=Length(min=0, max=16777214))
    data_content_type = fields.String(required=True, allow_none=False, validate=Length(min=0, max=35))
    data_weight = fields.Integer(required=True, allow_none=False, validate=Range(min=-32767, max=32767))
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class VariableFieldSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    user_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    variable_group_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    field_machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR())
    field_label = fields.String(required=True, allow_none=False, validate=Length(min=3, max=256))
    field_description = fields.String(required=True, allow_none=False, validate=Length(min=0, max=1024))
    field_weight = fields.Integer(required=True, allow_none=False, validate=Range(min=-32767, max=32767))
    value_required = fields.Bool(required=True, allow_none=False)
    value_max = fields.Integer(allow_none=True, validate=Range(min=-8388608, max=8388607))
    value_min = fields.Integer(allow_none=True, validate=Range(min=-8388608, max=8388607))
    value_casing = fields.String(required=True, allow_none=False, validate=Length(min=0, max=60))
    encryption = fields.String(required=True, allow_none=False, validate=Length(min=0, max=60))
    input_type_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    default_value = fields.String(required=True, allow_none=False, validate=Length(min=0, max=1000))
    field_help_text = fields.String(required=True, allow_none=False, validate=Length(min=0, max=4000))
    multiple = fields.Bool(required=True, allow_none=False)
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class VariableGroupSchema(YomboSchemaBase):
    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    group_relation_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    group_relation_type = fields.String(required=True, allow_none=False, validate=Length(min=0, max=60))
    group_machine_label = fields.String(required=True, allow_none=False, validate=MACHINE_LABEL_VALIDATOR())
    group_label = fields.String(required=True, allow_none=False, validate=Length(min=0, max=256))
    group_description = fields.String(required=True, allow_none=False, validate=Length(min=0, max=1024))
    group_relation_id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    group_weight = fields.Integer(required=True, allow_none=False, validate=Range(min=-32767, max=32767))
    status = fields.Integer(required=True, allow_none=False, validate=STATUS_VALIDATOR())
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())


class WebSessionSchema(YomboSchemaBase):
    _timestamp_accuracy = 0

    id = fields.String(required=True, allow_none=False, validate=ID_VALIDATOR())
    user_id = fields.String(allow_none=True, validate=ID_VALIDATOR())
    auth_at = fields.Integer(allow_none=True, validate=TIME_AT_VALIDATOR())
    auth_data = fields.Dict(required=True, allow_none=False, validate=Length(min=0, max=5000))
    refresh_token = fields.Raw(allow_none=True, validate=Length(min=0, max=500))
    access_token = fields.Raw(allow_none=True, validate=Length(min=0, max=250))
    refresh_token_expires_at = fields.Integer(allow_none=True, validate=TIME_AT_VALIDATOR())
    access_token_expires_at = fields.Integer(allow_none=True, validate=TIME_AT_VALIDATOR())
    status = fields.Integer(allow_none=True, validate=STATUS_VALIDATOR())
    last_access_at = fields.Integer(allow_none=True, validate=TIME_AT_VALIDATOR())
    created_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())
    updated_at = fields.Integer(required=True, allow_none=False, validate=TIME_AT_VALIDATOR())

    def preprocess_start(self, incoming: dict) -> None:
        """
        Setup some defaults.

        :param incoming:
        :return:
        """
        if "auth_data" not in incoming or incoming["auth_data"] is None:
            incoming["auth_data"] = {}
        if "last_access_at" not in incoming or incoming["last_access_at"] is None:
            incoming["last_access_at"] = int(time())
        if "status" not in incoming or incoming["status"] is None:
            incoming["status"] = 1
