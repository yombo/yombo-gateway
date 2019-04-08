import json
from marshmallow import Schema, fields, EXCLUDE, pre_load, post_load


class YomboSchemaBase(Schema):
    class Meta:
        unknown = EXCLUDE
        ordered = True


class AuthKeysSchema(YomboSchemaBase):
    id = fields.String(required=True)
    label = fields.String(required=True)
    description = fields.String(required=True)
    enabled = fields.Integer(required=True)
    roles = fields.String(allow_none=True)
    auth_data = fields.String(required=True)
    created_by = fields.String(required=True)
    created_by_type = fields.String(required=True)
    created_at = fields.String(required=True)
    last_access_at = fields.Integer(required=True)
    updated_at = fields.Integer(required=True)


class CategoriesSchema(YomboSchemaBase):
    id = fields.String(required=True)
    parent_id = fields.String(required=True)
    category_type = fields.String(required=True)
    machine_label = fields.String(required=True)
    label = fields.String(required=True)
    description = fields.String(allow_none=True)
    status = fields.Integer(required=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(required=True)


class CommandsSchema(YomboSchemaBase):
    # class Meta:
        # fields = ("name", "email", "created_at", "uppername")
        # ordered = True

    id = fields.String(required=True)
    voice_cmd = fields.String(allow_none=True)
    machine_label = fields.String(required=True)
    label = fields.String(required=True)
    description = fields.String(allow_none=True)
    public = fields.Integer(required=True)
    status = fields.Integer(required=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(required=True)


class DevicesSchema(YomboSchemaBase):
    id = fields.String(required=True)
    gateway_id = fields.String(required=True)
    user_id = fields.String(required=True)
    device_type_id = fields.String(required=True)
    machine_label = fields.String(required=True)
    label = fields.String(required=True)
    description = fields.String(allow_none=True)
    location_id = fields.String(required=True)
    area_id = fields.String(required=True)
    notes = fields.String(allow_none=True)
    attributes = fields.String(allow_none=True)
    intent_allow = fields.Integer(allow_none=True)
    intent_text = fields.String(allow_none=True)
    pin_code = fields.String(allow_none=True)
    pin_required = fields.Integer(required=True)
    pin_timeout = fields.Integer(allow_none=True)
    statistic_label = fields.String(allow_none=True)
    statistic_lifetime = fields.Integer(allow_none=True)
    statistic_type = fields.String(allow_none=True)
    statistic_bucket_size = fields.Integer(allow_none=True)
    energy_type = fields.String(allow_none=True)
    energy_tracker_source = fields.String(allow_none=True)
    energy_tracker_device = fields.String(allow_none=True)
    energy_map = fields.Dict(allow_none=True)
    controllable = fields.Integer(allow_none=True)
    allow_direct_control = fields.Integer(allow_none=True)
    status = fields.Integer(required=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(required=True)

    @pre_load
    def pre_load_defaults(self, in_data):
        """
        Sets the defaults. Also, converts the energy map from whatever (string, json, dict) to a dictionary.
        :param in_data:
        :return:
        """
        if 'energy_map' in in_data:
            if isinstance(in_data["energy_map"], str):
                try:
                    in_data["energy_map"] = json.loads(in_data["energy_map"])
                except:
                    in_data["energy_map"] = {}

            if isinstance(in_data["energy_map"], dict) is False:
                in_data["energy_map"] = {}
        else:
            in_data["energy_map"] = {}

        if 'statistic_lifetime' in in_data:
            if in_data["statistic_lifetime"] is None:
                in_data["statistic_lifetime"] = 0
        else:
            in_data["statistic_lifetime"] = 0

        if 'pin_timeout' in in_data:
            if in_data["pin_timeout"] is None:
                in_data["pin_timeout"] = 0
        else:
            in_data["pin_timeout"] = 0

        if 'controllable' in in_data:
            if in_data["controllable"] is None:
                in_data["controllable"] = 1
        else:
            in_data["controllable"] = 1

        if 'allow_direct_control' in in_data:
            if in_data["allow_direct_control"] is None:
                in_data["allow_direct_control"] = 1
        else:
            in_data["allow_direct_control"] = 1

        return in_data

    @post_load()
    def post_load_fixes(self, data):
        """
        Convert energy_map to a json from a dictionary.

        :param data:
        :return:
        """
        data['energy_map'] = json.dumps(data['energy_map'])
        return data


class DeviceCommandInputsSchema(YomboSchemaBase):
    id = fields.String(required=True)
    device_type_id = fields.String(required=True)
    command_id = fields.String(required=True)
    input_type_id = fields.String(required=True)
    machine_label = fields.String(required=True)
    label = fields.String(required=True)
    live_update = fields.Integer(required=True)
    live_update = fields.Integer(required=True)
    value_required = fields.Integer(required=True)
    value_max = fields.Integer(required=True)
    value_min = fields.Integer(required=True)
    value_casing = fields.String(required=True)
    encryption = fields.String(required=True)
    notes = fields.String(allow_none=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(required=True)


class DeviceTypesSchema(YomboSchemaBase):
    id = fields.String(required=True)
    category_id = fields.String(required=True)
    machine_label = fields.String(required=True)
    label = fields.String(required=True)
    description = fields.String(allow_none=True)
    platform = fields.String(allow_none=True)
    public = fields.Integer(required=True)
    status = fields.Integer(required=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(required=True)


class DeviceTypeCommandsSchema(YomboSchemaBase):
    id = fields.String(required=True)
    device_type_id = fields.String(required=True)
    command_id = fields.String(required=True)
    created_at = fields.Integer(required=True)


class GatewaysSchema(YomboSchemaBase):
    id = fields.String(required=True)
    is_master = fields.Integer(required=True)
    master_gateway_id = fields.String(required=True)
    machine_label = fields.String(required=True)
    label = fields.String(required=True)
    description = fields.String(allow_none=True)
    user_id = fields.String(required=True)
    mqtt_auth = fields.String(allow_none=True)
    mqtt_auth_next = fields.String(allow_none=True)
    mqtt_auth_last_rotate_at = fields.String(allow_none=True)
    internal_ipv4 = fields.String(allow_none=True)
    external_ipv4 = fields.String(allow_none=True)
    internal_ipv6 = fields.String(allow_none=True)
    external_ipv6 = fields.String(allow_none=True)
    internal_http_port = fields.Integer(allow_none=True)
    external_http_port = fields.Integer(allow_none=True)
    internal_http_secure_port = fields.Integer(allow_none=True)
    external_http_secure_port = fields.Integer(allow_none=True)
    internal_mqtt = fields.Integer(allow_none=True)
    internal_mqtt_le = fields.Integer(allow_none=True)
    internal_mqtt_ss = fields.Integer(allow_none=True)
    internal_mqtt_ws = fields.Integer(allow_none=True)
    internal_mqtt_ws_le = fields.Integer(allow_none=True)
    internal_mqtt_ws_ss = fields.Integer(allow_none=True)
    external_mqtt = fields.Integer(allow_none=True)
    external_mqtt_le = fields.Integer(allow_none=True)
    external_mqtt_ss = fields.Integer(allow_none=True)
    external_mqtt_ws = fields.Integer(allow_none=True)
    external_mqtt_ws_le = fields.Integer(allow_none=True)
    external_mqtt_ws_ss = fields.Integer(allow_none=True)
    dns_name = fields.String(allow_none=True)
    status = fields.Integer(required=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(required=True)


class InputTypesSchema(YomboSchemaBase):
    id = fields.String(required=True)
    category_id = fields.String(required=True)
    machine_label = fields.String(required=True)
    label = fields.String(required=True)
    description = fields.String(allow_none=True)
    public = fields.Integer(required=True)
    status = fields.Integer(required=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(required=True)


class LocationsSchema(YomboSchemaBase):
    id = fields.String(required=True)
    location_type = fields.String(required=True)
    user_id = fields.String(required=True)
    machine_label = fields.String(required=True)
    label = fields.String(required=True)
    description = fields.String(allow_none=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(required=True)


class ModulesSchema(YomboSchemaBase):
    id = fields.String(required=True)
    user_id = fields.String(required=True)
    module_type = fields.String(required=True)
    machine_label = fields.String(required=True)
    label = fields.String(required=True)
    description = fields.String(allow_none=True)
    short_description = fields.String(required=True)
    medium_description = fields.String(required=True)
    medium_description_html = fields.String(required=True)
    description_html = fields.String(required=True)
    see_also = fields.String(allow_none=True)
    repository_link = fields.String(allow_none=True)
    issue_tracker_link = fields.String(allow_none=True)
    install_count = fields.Integer(required=True)
    doc_link = fields.String(allow_none=True)
    git_link = fields.String(allow_none=True)
    git_auto_approve = fields.Integer(required=True)
    install_branch = fields.String(required=True)
    require_approved = fields.Integer(required=True)
    public = fields.Integer(required=True)
    status = fields.Integer(required=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(required=True)


class ModuleCommitsSchema(YomboSchemaBase):
    id = fields.String(required=True)
    module_id = fields.String(required=True)
    branch = fields.String(required=True)
    commit = fields.String(required=True)
    committed_at = fields.Integer(required=True)
    approved = fields.Integer(allow_none=True)
    created_at = fields.Integer(required=True)


class ModuleDeviceTypesSchema(YomboSchemaBase):
    id = fields.String(required=True)
    module_id = fields.String(required=True)
    device_type_id = fields.String(required=True)
    created_at = fields.Integer(required=True)


class NodesSchema(YomboSchemaBase):
    id = fields.String(required=True)
    parent_id = fields.String(allow_none=True)
    gateway_id = fields.String(allow_none=True)
    node_type = fields.String(required=True)
    weight = fields.Integer(required=True)
    machine_label = fields.String(allow_none=True)
    label = fields.String(allow_none=True)
    always_load = fields.Integer(allow_none=True)
    destination = fields.String(allow_none=True)
    data = fields.String(allow_none=True)
    data_content_type = fields.String(required=True)
    status = fields.Integer(required=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(required=True)


class UsersSchema(YomboSchemaBase):
    id = fields.String(required=True)
    user_id = fields.String(required=True)
    email = fields.String(required=True)
    name = fields.String(required=True)
    access_code_digits = fields.String(allow_none=True)
    access_code_string = fields.String(allow_none=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(required=True)


class VariableDataSchema(YomboSchemaBase):
    id = fields.String(required=True)
    user_id = fields.String(required=True)
    gateway_id = fields.String(required=True)
    variable_field_id = fields.String(required=True)
    variable_relation_id = fields.String(required=True)
    variable_relation_type = fields.String(required=True)
    data = fields.String(required=True)
    data_weight = fields.Integer(required=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(required=True)


class VariableFieldsSchema(YomboSchemaBase):
    id = fields.String(required=True)
    user_id = fields.String(required=True)
    variable_group_id = fields.String(required=True)
    field_machine_label = fields.String(required=True)
    field_label = fields.String(required=True)
    field_description = fields.String(required=True)
    field_help_text = fields.String(required=True)
    field_weight = fields.Integer(required=True)
    value_required = fields.Integer(required=True)
    value_max = fields.Integer(allow_none=True)
    value_min = fields.Integer(allow_none=True)
    value_casing = fields.String(required=True)
    encryption = fields.String(required=True)
    input_type_id = fields.String(required=True)
    default_value = fields.String(required=True)
    field_help_text = fields.String(required=True)
    multiple = fields.Integer(required=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(required=True)


class VariableGroupsSchema(YomboSchemaBase):
    id = fields.String(required=True)
    group_relation_id = fields.String(required=True)
    group_relation_type = fields.String(required=True)
    group_machine_label = fields.String(required=True)
    group_label = fields.String(required=True)
    group_description = fields.String(required=True)
    group_relation_id = fields.String(required=True)
    group_weight = fields.Integer(required=True)
    status = fields.Integer(required=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(required=True)
