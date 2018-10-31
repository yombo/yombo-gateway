
CONFIG_ITEM_MAP = {
    'devices': 'gateway_devices'
}

CONFIG_ITEMS = {
    'categories': {
        'dbclass': "Category",
        'table': "categories",
        'library': None,
        'functions': {
            # 'process': "enable_command",
            # 'enabled': "enable_device",
            # 'disabled': "disable_device",
            # 'deleted': "delete_device",
        },
        'purgeable': False,
        'map': {  # api name : database field name
            'id': 'id',
            'category_type': 'category_type',
            'machine_label': 'machine_label',
            'label': 'label',
            'description': 'description',
            'status': 'status',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
            # '': '',
        }
    },

    'gateway_cluster': {
        'dbclass': "Gateway",
        'table': "gateways",
        'library': "gateways",
        'functions': {
            # 'process': "enable_command",
            # 'enabled': "enable_device",
            # 'disabled': "disable_device",
            # 'deleted': "delete_device",
        },
        'purgeable': False,
        'map': {  # api name : database field name
            'id': 'id',
            'is_master': 'is_master',
            'master_gateway': 'master_gateway_id',
            'machine_label': 'machine_label',
            'label': 'label',
            'description': 'description',
            'mqtt_auth': 'mqtt_auth',
            'mqtt_auth_prev': 'mqtt_auth_prev',
            'mqtt_auth_next': 'mqtt_auth_next',
            'mqtt_auth_last_rotate': 'mqtt_auth_last_rotate',
            'fqdn': 'fqdn',
            'internal_ipv4': 'internal_ipv4',
            'external_ipv4': 'external_ipv4',
            'internal_ipv6': 'internal_ipv6',
            'external_ipv6': 'external_ipv6',
            'internal_port': 'internal_port',
            'external_port': 'external_port',
            'internal_secure_port': 'internal_secure_port',
            'external_secure_port': 'external_secure_port',
            'internal_mqtt': 'internal_mqtt',
            'internal_mqtt_le': 'internal_mqtt_le',
            'internal_mqtt_ss': 'internal_mqtt_ss',
            'internal_mqtt_ws': 'internal_mqtt_ws',
            'internal_mqtt_ws_le': 'internal_mqtt_ws_le',
            'internal_mqtt_ws_ss': 'internal_mqtt_ws_ss',
            'externalmqtt': 'externalmqtt',
            'externalmqtt_le': 'externalmqtt_le',
            'externalmqtt_ss': 'externalmqtt_ss',
            'externalmqtt_ws': 'externalmqtt_ws',
            'externalmqtt_ws_le': 'externalmqtt_ws_le',
            'externalmqtt_ws_ss': 'externalmqtt_ws_ss',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
        }
    },
    'gateway_dns_name': {
        'dbclass': "none",
        'table': "none",
        'library': None,
        'functions': {
        },
        'purgeable': False,
        'map': {  # api name : database field name
        }
    },

    'gateway_commands': {
        'dbclass': "Command",
        'table': "commands",
        'library': "commands",
        'functions': {
            # 'process': "enable_command",
            # 'enabled': "enable_device",
            # 'disabled': "disable_device",
            # 'deleted': "delete_device",
        },
        'purgeable': False,
        'map': {  # api name : database field name
            'id': 'id',
            'machine_label': 'machine_label',
            'voice_cmd': 'voice_cmd',
            'label': 'label',
            'description': 'description',
            'always_load': 'always_load',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
            'status': 'status',
            'public': 'public',
        }
    },

    'gateway_devices': {
        'dbclass': "Device",
        'table': "devices",
        'library': "devices",
        'functions': {
            # 'enabled': "enable_device",
            # 'disabled': "disable_device",
            # 'deleted': "delete_device",
        },
        'purgeable': True,
        'map': {  # api name : database field name
            'id': 'id',
            'gateway_id': 'gateway_id',
            'area_id': 'area_id',
            'location_id': 'location_id',
            'machine_label': 'machine_label',
            'label': 'label',
            'notes': 'notes',
            'attributes': 'attributes',
            'description': 'description',
            'gateway_id': 'gateway_id',
            'device_type_id': 'device_type_id',
            'intent_allow': 'intent_allow',
            'intent_text': 'intent_text',
            'pin_code': 'pin_code',
            'pin_required': 'pin_required',
            'pin_timeout': 'pin_timeout',
            'statistic_label': 'statistic_label',
            'statistic_lifetime': 'statistic_lifetime',
            'statistic_type': 'statistic_type',
            'statistic_bucket_size': 'statistic_bucket_size',
            'data': 'data',
            'energy_type': 'energy_type',
            'energy_tracker_source': 'energy_tracker_source',
            'energy_tracker_device': 'energy_tracker_device',
            'energy_map': 'energy_map',
            'controllable': 'controllable',
            'allow_direct_control': 'allow_direct_control',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
            'status': 'status',
        }
    },

    'gateway_device_command_inputs': {
        'dbclass': "DeviceCommandInput",
        'table': "device_command_inputs",
        'library': None,
        'functions': {
            # 'enabled': "enable_device",
            # 'disabled': "disable_device",
            # 'deleted': "delete_device",
        },
        'purgeable': False,
        'map': {  # api name : database field name
            'id': 'id',
            'category_id': 'category_id',
            'device_type_id': 'device_type_id',
            'command_id': 'command_id',
            'input_type_id': 'input_type_id',
            'machine_label': 'machine_label',
            'label': 'label',
            'live_update': 'live_update',
            'value_required': 'value_required',
            'value_max': 'value_max',
            'value_min': 'value_min',
            'value_casing': 'value_casing',
            'encryption': 'encryption',
            'notes': 'notes',
            'always_load': 'always_load',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
        }
    },

    'gateway_locations': {
        'dbclass': "Location",
        'table': "locations",
        'library': None,
        'functions': {
            # 'enabled': "enable_device",
            # 'disabled': "disable_device",
            # 'deleted': "delete_device",
        },
        'purgeable': False,
        'map': {  # api name : database field name
            'id': 'id',
            'machine_label': 'machine_label',
            'label': 'label',
            'description': 'description',
            'public': 'public',
            'status': 'status',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
        }
    },

    'gateway_device_types': {
        'dbclass': "DeviceType",
        'table': "device_types",
        'library': "devicestypes",
        'functions': {
            # 'enabled': "enable_device",
            # 'disabled': "disable_device",
            # 'deleted': "delete_device",
        },
        'purgeable': False,
        'map': {  # api name : database field name
            'id': 'id',
            'category_id': 'category_id',
            'platform': 'platform',
            'machine_label': 'machine_label',
            'label': 'label',
            'description': 'description',
            'always_load': 'always_load',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
            'public': 'public',
            'status': 'status',
        }
    },

    'gateway_device_type_commands': {
        'dbclass': "DeviceTypeCommand",
        'table': "device_type_commands",
        'library': None,
        'functions': {
            # 'enabled': "enable_device",
            # 'disabled': "disable_device",
            # 'deleted': "delete_device",
        },
        'purgeable': False,
        'map': {  # api name : database field name
            'id': 'id',
            'device_type_id': 'device_type_id',
            'command_id': 'command_id',
            'created_at': 'created_at',
        }
    },

    'gateway_input_types': {
        'dbclass': "InputType",
        'table': "input_types",
        'library': "inputtypes",
        'functions': {
            # 'enabled': "enable_device",
            # 'disabled': "disable_device",
            # 'deleted': "delete_device",
        },
        'purgeable': False,
        'map': {  # api name : database field name
            'id': 'id',
            'category_id': 'category_id',
            'machine_label': 'machine_label',
            'label': 'label',
            'description': 'description',
            'platform': 'platform',
            'always_load': 'always_load',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
            'public': 'public',
            'status': 'status',
        }
    },

    'gateway_modules': {
        'dbclass': "Modules",
        'table': "modules",
        'library': "modules",
        'functions': {
            # 'enabled': "enable_command",
            # 'disabled': "enable_command",
            # 'deleted': "enable_command",
        },
        'purgeable': True,
        'map': {  # api name : database field name
            'module_id': 'id',
            'gateway_id': 'gateway_id',
            'machine_label': 'machine_label',
            'module_type': 'module_type',
            'label': 'label',
            'short_description': 'short_description',
            'medium_description': 'medium_description',
            'description': 'description',
            'medium_description_html': 'medium_description_html',
            'description_html': 'description_html',
            'see_also': 'see_also',
            'repository_link': 'repository_link',
            'issue_tracker_link': 'issue_tracker_link',
            'install_count': 'install_count',
            'doc_link': 'doc_link',
            'git_link': 'git_link',
            'prod_branch': 'prod_branch',
            'dev_branch': 'dev_branch',
            'prod_version': 'prod_version',
            'dev_version': 'dev_version',
            'install_branch': 'install_branch',
            'always_load': 'always_load',
            'public': 'public',
            'status': 'status',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
        }
    },

    'gateway_configs': {},  # Processed with it's own catch.

    'gateway_users': {
        'dbclass': "Users",
        'table': "users",
        'library': None,
        'functions': {
        },
        'purgeable': True,
        'map': {  # api name : database field name
            'user_id': 'id',
            'email': 'email',
            'name': 'name',
            'access_code_digits': 'access_code_digits',
            'access_code_string': 'access_code_string',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
        }
    },

    'module_device_type': {
        'dbclass': "ModuleDeviceTypes",
        'table': "module_device_types",
        'library': None,
        'functions': {
            # 'enabled': "enable_device",
            # 'disabled': "disable_device",
            # 'deleted': "delete_device",
        },
        'purgeable': False,
        'map': {  # api name : database field name
            'id': 'id',
            'module_id': 'module_id',
            'device_type_id': 'device_type_id',
            'created_at': 'created_at',
        }
    },

    'gateway_nodes': {
        'dbclass': "Node",
        'table': "nodes",
        'library': None,
        'functions': {
            # 'enabled': "enable_device",
            # 'disabled': "disable_device",
            # 'deleted': "delete_device",
        },
        'purgeable': True,
        'map': {  # api name : database field name
            'id': 'id',
            'parent_id': 'parent_id',
            'node_id': 'node_id',
            'gateway_id': 'gateway_id',
            'node_type': 'node_type',
            'weight': 'weight',
            'label': 'label',
            'machine_label': 'machine_label',
            'always_load': 'always_load',
            'destination': 'destination',
            'data': 'data',
            'data_content_type': 'data_content_type',
            'status': 'status',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
        }
    },

    'variable_groups': {
        'dbclass': "VariableGroups",
        'table': "variable_groups",
        'library': "configuration",
        'functions': {
        },
        'purgeable': False,
        'map': {  # api name : database field name
            'id': 'id',
            'relation_id': 'group_relation_id',
            'relation_type': 'group_relation_type',
            'group_machine_label': 'group_machine_label',
            'group_label': 'group_label',
            'group_description': 'group_description',
            'group_weight': 'group_weight',
            'status': 'status',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
        }
    },

    'variable_fields': {
        'dbclass': "VariableFields",
        'table': "variable_fields",
        'library': "configuration",
        'functions': {
        },
        'purgeable': False,
        'map': {  # api name : database field name
            'id': 'id',
            'group_id': 'group_id',
            'field_machine_label': 'field_machine_label',
            'field_label': 'field_label',
            'field_description': 'field_description',
            'field_weight': 'field_weight',
            'value_required': 'value_required',
            'value_max': 'value_max',
            'value_min': 'value_min',
            'value_casing': 'value_casing',
            'encryption': 'encryption',
            'input_type_id': 'input_type_id',
            'default_value': 'default_value',
            'field_help_text': 'field_help_text',
            'multiple': 'multiple',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
        }
    },

    'variable_data': {
        'dbclass': "VariableData",
        'table': "variable_data",
        'library': "configuration",
        'functions': {
        },
        'purgeable': True,
        'map': {  # api name : database field name
            'id': 'id',
            'gateway_id': 'gateway_id',
            'field_id': 'field_id',
            'relation_id': 'data_relation_id',
            'relation_type': 'data_relation_type',
            'data': 'data',
            'data_weight': 'data_weight',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
        }
    },
}