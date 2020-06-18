"""
Various constants used for the system data handler library.

The constant values are not fully documented here, see the
`constants source code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/systemdatahandler/constants.py>`_
for a full list.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/systemdatahandler/constants.py>`_
"""

CONFIG_ITEM_MAP = {
    "devices": "gateway_devices"
}

CONFIG_ITEMS = {
    "categories": {
        "dbclass": "Category",
        "schemaclass": "CategorySchema",
        "table": "categories",
        "library": "categories",
        "functions": {
            # "process": "enable_command",
            # "enabled": "enable_device",
            # "disabled": "disable_device",
            # "deleted": "delete_device",
        },
        "purgeable": False,
        "map": {  # api name : database field name
            "id": "id",
            "category_parent_id": "category_parent_id",
            "category_type": "category_type",
            "machine_label": "machine_label",
            "label": "label",
            "description": "description",
            "status": "status",
            "created_at": "created_at",
            "updated_at": "updated_at",
            # "": "",
        }
    },

    "commands": {
        "dbclass": "Command",
        "schemaclass": "CommandSchema",
        "table": "commands",
        "library": "commands",
        "functions": {
            # "process": "enable_command",
            # "enabled": "enable_device",
            # "disabled": "disable_device",
            # "deleted": "delete_device",
        },
        "purgeable": False,
        "map": {  # api name : database field name
            "id": "id",
            "user_id": "user_id",
            "original_user_id": "original_user_id",
            "machine_label": "machine_label",
            "label": "label",
            "description": "description",
            "public": "public",
            "status": "status",
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
    },

    "devices": {
        "dbclass": "Device",
        "schemaclass": "DeviceSchema",
        "table": "devices",
        "library": "devices",
        "functions": {
            # "enabled": "enable_device",
            # "disabled": "disable_device",
            # "deleted": "delete_device",
        },
        "purgeable": True,
        "map": {  # api name : database field name
            "id": "id",
            "gateway_id": "gateway_id",
            "user_id": "user_id",
            "device_type_id": "device_type_id",
            "machine_label": "machine_label",
            "label": "label",
            "description": "description",
            "location_id": "location_id",
            "area_id": "area_id",
            "notes": "notes",
            "attributes": "attributes",
            "intent_allow": "intent_allow",
            "intent_text": "intent_text",
            "pin_code": "pin_code",
            "pin_required": "pin_required",
            "pin_timeout": "pin_timeout",
            "statistic_label": "statistic_label",
            "statistic_lifetime": "statistic_lifetime",
            "statistic_type": "statistic_type",
            "statistic_bucket_size": "statistic_bucket_size",
            "energy_type": "energy_type",
            "energy_tracker_source_type": "energy_tracker_source_type",
            "energy_tracker_source_id": "energy_tracker_source_id",
            "energy_map": "energy_map",
            "scene_controllable": "scene_controllable",
            "allow_direct_control": "allow_direct_control",
            "status": "status",
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
    },

    "device_command_inputs": {
        "dbclass": "DeviceCommandInput",
        "schemaclass": "DeviceCommandInputSchema",
        "table": "device_command_inputs",
        "library": None,
        "functions": {
            # "enabled": "enable_device",
            # "disabled": "disable_device",
            # "deleted": "delete_device",
        },
        "purgeable": False,
        "map": {  # api name : database field name
            "id": "id",
            "device_type_id": "device_type_id",
            "command_id": "command_id",
            "input_type_id": "input_type_id",
            "machine_label": "machine_label",
            "label": "label",
            "live_update": "live_update",
            "value_required": "value_required",
            "value_max": "value_max",
            "value_min": "value_min",
            "value_casing": "value_casing",
            "encryption": "encryption",
            "notes": "notes",
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
    },

    "device_types": {
        "dbclass": "DeviceType",
        "schemaclass": "DeviceTypeSchema",
        "table": "device_types",
        "library": "devicestypes",
        "functions": {
            # "enabled": "enable_device",
            # "disabled": "disable_device",
            # "deleted": "delete_device",
        },
        "purgeable": False,
        "map": {  # api name : database field name
            "id": "id",
            "user_id": "user_id",
            "original_user_id": "original_user_id",
            "category_id": "category_id",
            "machine_label": "machine_label",
            "label": "label",
            "description": "description",
            "public": "public",
            "status": "status",
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
    },

    "device_type_commands": {
        "dbclass": "DeviceTypeCommand",
        "schemaclass": "DeviceTypeCommandSchema",
        "table": "device_type_commands",
        "library": None,
        "functions": {
            # "enabled": "enable_device",
            # "disabled": "disable_device",
            # "deleted": "delete_device",
        },
        "purgeable": False,
        "map": {  # api name : database field name
            "id": "id",
            "device_type_id": "device_type_id",
            "command_id": "command_id",
            "created_at": "created_at",
        }
    },
    "gateways": {
        "dbclass": "Gateway",
        "schemaclass": "GatewaySchema",
        "table": "gateways",
        "library": "gateways",
        "functions": {
            # "process": "enable_command",
            # "enabled": "enable_device",
            # "disabled": "disable_device",
            # "deleted": "delete_device",
        },
        "purgeable": False,
        "map": {  # api name : database field name
            "id": "id",
            "machine_label": "machine_label",
            "label": "label",
            "description": "description",
            "user_id": "user_id",
            "mqtt_auth": "mqtt_auth",
            "mqtt_auth_next": "mqtt_auth_next",
            "mqtt_auth_last_rotate_at": "mqtt_auth_last_rotate_at",
            "internal_ipv4": "internal_ipv4",
            "external_ipv4": "external_ipv4",
            "internal_ipv6": "internal_ipv6",
            "external_ipv6": "external_ipv6",
            "internal_http_port": "internal_http_port",
            "external_http_port": "external_http_port",
            "internal_http_secure_port": "internal_http_secure_port",
            "external_http_secure_port": "external_http_secure_port",
            "internal_mqtt": "internal_mqtt",
            "internal_mqtt_le": "internal_mqtt_le",
            "internal_mqtt_ss": "internal_mqtt_ss",
            "internal_mqtt_ws": "internal_mqtt_ws",
            "internal_mqtt_ws_le": "internal_mqtt_ws_le",
            "internal_mqtt_ws_ss": "internal_mqtt_ws_ss",
            "externalmqtt": "externalmqtt",
            "externalmqtt_le": "externalmqtt_le",
            "externalmqtt_ss": "externalmqtt_ss",
            "externalmqtt_ws": "externalmqtt_ws",
            "externalmqtt_ws_le": "externalmqtt_ws_le",
            "externalmqtt_ws_ss": "externalmqtt_ws_ss",
            "is_master": "is_master",
            "master_gateway_id": "master_gateway_id",
            "dns_name": "dns_name",
            "status": "status",
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
    },
    # "gateway_dns_name": {
    #     "dbclass": "none",
    #     "table": "none",
    #     "library": None,
    #     "functions": {
    #     },
    #     "purgeable": False,
    #     "map": {  # api name : database field name
    #     }
    # },

    "input_types": {
        "dbclass": "InputType",
        "schemaclass": "InputTypeSchema",
        "table": "input_types",
        "library": "inputtypes",
        "functions": {
            # "enabled": "enable_device",
            # "disabled": "disable_device",
            # "deleted": "delete_device",
        },
        "purgeable": False,
        "map": {  # api name : database field name
            "id": "id",
            "user_id": "user_id",
            "original_user_id": "original_user_id",
            "category_id": "category_id",
            "machine_label": "machine_label",
            "label": "label",
            "description": "description",
            "public": "public",
            "status": "status",
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
    },

    "locations": {
        "dbclass": "Location",
        "schemaclass": "LocationSchema",
        "table": "locations",
        "library": None,
        "functions": {
            # "enabled": "enable_device",
            # "disabled": "disable_device",
            # "deleted": "delete_device",
        },
        "purgeable": False,
        "map": {  # api name : database field name
            "id": "id",
            "user_id": "user_id",
            "location_type": "location_type",
            "machine_label": "machine_label",
            "label": "label",
            "description": "description",
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
    },

    "modules": {
        "dbclass": "Modules",
        "schemaclass": "ModuleSchema",
        "table": "modules",
        "library": "modules",
        "functions": {
            # "enabled": "enable_command",
            # "disabled": "enable_command",
            # "deleted": "enable_command",
        },
        "purgeable": True,
        "map": {  # api name : database field name
            "id": "id",
            "user_id": "user_id",
            "original_user_id": "original_user_id",
            "module_type": "module_type",
            "machine_label": "machine_label",
            "label": "label",
            "short_description": "short_description",
            "medium_description": "medium_description",
            "description": "description",
            "medium_description_html": "medium_description_html",
            "description_html": "description_html",
            "see_also": "see_also",
            "repository_link": "repository_link",
            "issue_tracker_link": "issue_tracker_link",
            "install_count": "install_count",
            "doc_link": "doc_link",
            "git_link": "git_link",
            "git_auto_approve": "git_auto_approve",
            "install_branch": "install_branch",
            "require_approved": "require_approved",
            "public": "public",
            "status": "status",
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
    },

    "module_commits": {
        "dbclass": "ModuleCommits",
        "schemaclass": "ModuleCommitSchema",
        "table": "module_commits",
        "library": "modules",
        "functions": {
            # "enabled": "enable_command",
            # "disabled": "enable_command",
            # "deleted": "enable_command",
        },
        "purgeable": True,
        "map": {  # api name : database field name
            "id": "id",
            "module_id": "module_id",
            "branch": "branch",
            "commit": "commit",
            "committed_at": "committed_at",
            "approved": "approved",
            "approved_at": "approved_at",
            "created_at": "created_at",
        }
    },

    "module_device_types": {
        "dbclass": "ModuleDeviceTypes",
        "schemaclass": "ModuleDeviceTypeSchema",
        "table": "module_device_types",
        "library": None,
        "functions": {
            # "enabled": "enable_device",
            # "disabled": "disable_device",
            # "deleted": "delete_device",
        },
        "purgeable": False,
        "map": {  # api name : database field name
            "id": "id",
            "module_id": "module_id",
            "device_type_id": "device_type_id",
            "created_at": "created_at",
        }
    },

    "nodes": {
        "dbclass": "Node",
        "schemaclass": "NodeSchema",
        "table": "nodes",
        "library": None,
        "functions": {
            # "enabled": "enable_device",
            # "disabled": "disable_device",
            # "deleted": "delete_device",
        },
        "purgeable": True,
        "map": {  # api name : database field name
            "id": "id",
            "node_parent_id": "node_parent_id",
            "node_id": "node_id",
            "gateway_id": "gateway_id",
            "node_type": "node_type",
            "weight": "weight",
            "label": "label",
            "machine_label": "machine_label",
            "always_load": "always_load",
            "destination": "destination",
            "data": "data",
            "data_content_type": "data_content_type",
            "status": "status",
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
    },

    "gateway_users": {
        "dbclass": "Users",
        "schemaclass": "UserSchema",
        "table": "users",
        "library": None,
        "functions": {
        },
        "purgeable": True,
        "map": {  # api name : database field name
            "user_id": "id",
            "gateway_id": "gateway_id",
            "email": "email",
            "name": "name",
            "access_code_string": "access_code_string",
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
    },

    "variable_groups": {
        "dbclass": "VariableGroups",
        "schemaclass": "VariableGroupSchema",
        "table": "variable_groups",
        "library": "configuration",
        "functions": {
        },
        "purgeable": False,
        "map": {  # api name : database field name
            "id": "id",
            "relation_id": "group_relation_id",
            "relation_type": "group_relation_type",
            "group_machine_label": "group_machine_label",
            "group_label": "group_label",
            "group_description": "group_description",
            "group_weight": "group_weight",
            "status": "status",
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
    },

    "variable_fields": {
        "dbclass": "VariableFields",
        "schemaclass": "VariableFieldSchema",
        "table": "variable_fields",
        "library": "configuration",
        "functions": {
        },
        "purgeable": False,
        "map": {  # api name : database field name
            "id": "id",
            "user_id": "user_id",
            "variable_group_id": "variable_group_id",
            "field_machine_label": "field_machine_label",
            "field_label": "field_label",
            "field_description": "field_description",
            "field_weight": "field_weight",
            "value_required": "value_required",
            "value_max": "value_max",
            "value_min": "value_min",
            "value_casing": "value_casing",
            "encryption": "encryption",
            "input_type_id": "input_type_id",
            "default_value": "default_value",
            "field_help_text": "field_help_text",
            "multiple": "multiple",
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
    },

    "variables": {
        "dbclass": "VariableData",
        "schemaclass": "VariableDataSchema",
        "table": "variable_data",
        "library": "configuration",
        "functions": {
        },
        "purgeable": True,
        "map": {  # api name : database field name
            "id": "id",
            "user_id": "user_id",
            "gateway_id": "gateway_id",
            "variable_field_id": "variable_field_id",
            "variable_relation_id": "variable_relation_id",
            "variable_relation_type": "variable_relation_type",
            "data": "data",
            "data_content_type": "data_content_type",
            "data_weight": "data_weight",
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
    },
}