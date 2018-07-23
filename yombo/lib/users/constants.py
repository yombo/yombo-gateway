"""
Constants for users.
"""
SYSTEM_ROLES = {
    'admin': {
        'label': 'Administrators',
        'description': 'Full access to everything.',
        'permissions': [
            {
                'path': '*:*',
                'action': '*',
                'access': 'allow',
            }
        ]
    },
    'everyone': {
        'label': 'Everyone',
        'description': 'Everyone belongs to this role.',
        'permissions': [],
    },
    'general_users': {
        'label': 'General Users',
        'description': 'Given to most users so they can control all devices. Specific devices can be blocked at the device level. This role also grants views to states, atoms, and other low level items.',
        'permissions': [
            {
                'path': 'atom:*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'path': 'automation:*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'path': 'device:*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'path': 'device:*',
                'action': 'control',
                'access': 'allow',
            },
            {
                'path': 'gateway:*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'path': 'location:*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'path': 'module:*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'path': 'notifications_view:*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'path': 'panel_view:*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'path': 'scene:*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'path': 'state:*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'path': 'statistic:*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'path': 'user:*',
                'action': 'view',
                'access': 'allow',
            },
        ]
    },
    'viewers': {
        'label': 'Viewers',
        'description': 'Can view anything within the system.',
        'permissions': [
            {
                'path': '*:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'apiauth_view': {
        'label': 'API Auth - View',
        'description': 'View configured API Auth keys.',
        'permissions': [
            {
                'path': 'apiauth:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'apiauth_edit': {
        'label': 'API Auth - Edit',
        'description': 'Edit configured API Auth keys.',
        'permissions': [
            {
                'path': 'apiauth:*',
                'action': 'edit',
                'access': 'allow',
            },
            {
                'path': 'apiauth:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'apiauth_add': {
        'label': 'API Auth - Add',
        'description': 'Add new API Auth keys.',
        'permissions': [
            {
                'path': 'apiauth:*',
                'action': 'add',
                'access': 'allow',
            }
        ]
    },
    'apiauth_delete': {
        'label': 'API Auth - Delete',
        'description': 'Delete API Auth keys.',
        'permissions': [
            {
                'path': 'apiauth:*',
                'action': 'delete',
                'access': 'allow',
            },
            {
                'path': 'apiauth:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'apiauth_admin': {
        'label': 'API Auth - Administrator',
        'description': 'Full access to API Auth keys.',
        'permissions': [
            {
                'path': 'apiauth:*',
                'action': '*',
                'access': 'allow',
            }
        ]
    },
    'atoms_view': {
        'label': 'Atoms - View',
        'description': 'View system defined atoms.',
        'permissions': [
            {
                'path': 'atom:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'automation_view': {
        'label': 'Automation Rules - View',
        'description': 'View configured automation rules.',
        'permissions': [
            {
                'path': 'automation:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'automation_edit': {
        'label': 'Automation Rules - Edit',
        'description': 'Edit configured automation rules.',
        'permissions': [
            {
                'path': 'automation:*',
                'action': 'edit',
                'access': 'allow',
            },
            {
                'path': 'automation:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'automation_add': {
        'label': 'Automation Rules - Add',
        'description': 'Add new automation rules.',
        'permissions': [
            {
                'path': 'automation:*',
                'action': 'add',
                'access': 'allow',
            }
        ]
    },
    'automation_delete': {
        'label': 'Automation Rules - Delete',
        'description': 'Delete configured automation rules.',
        'permissions': [
            {
                'path': 'automation:*',
                'action': 'delete',
                'access': 'allow',
            },
            {
                'path': 'automation:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'automation_start': {
        'label': 'Automation Rules - Start',
        'description': 'Start configured automation rules.',
        'permissions': [
            {
                'path': 'automation:*',
                'action': 'start',
                'access': 'allow',
            },
            {
                'path': 'automation:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'automation_stop': {
        'label': 'Automation Rules - Stop',
        'description': 'Stop configured automation rules.',
        'permissions': [
            {
                'path': 'automation:*',
                'action': 'stop',
                'access': 'allow',
            },
            {
                'path': 'automation:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'automation_enable': {
        'label': 'Automation Rules - Enable',
        'description': 'Enable configured automation rules.',
        'permissions': [
            {
                'path': 'automation:*',
                'action': 'enable',
                'access': 'allow',
            },
            {
                'path': 'automation:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'automation_disable': {
        'label': 'Automation Rules - Disable',
        'description': 'Start configured automation rules.',
        'permissions': [
            {
                'path': 'automation:*',
                'action': 'disable',
                'access': 'allow',
            },
            {
                'path': 'automation:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'automation_admin': {
        'label': 'Automation Rules - Administrator',
        'description': 'Full control over automation rules.',
        'permissions': [
            {
                'path': 'automation:*',
                'action': '*',
                'access': 'allow',
            }
        ]
    },
    'devices_view': {
        'label': 'Devices - View',
        'description': 'Able to view devices.',
        'permissions': [
            {
                'path': 'device:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'devices_edit': {
        'label': 'Devices - Edit',
        'description': 'Able to edit devices.',
        'permissions': [
            {
                'path': 'device:*',
                'action': 'edit',
                'access': 'allow',
            },
            {
                'path': 'device:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'devices_delete': {
        'label': 'Devices - Delete',
        'description': 'Able to delete devices.',
        'permissions': [
            {
                'path': 'device:*',
                'action': 'delete',
                'access': 'allow',
            },
            {
                'path': 'device:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'devices_add': {
        'label': 'Devices - Add',
        'description': 'Able to add new devices.',
        'permissions': [
            {
                'path': 'device:*',
                'action': 'add',
                'access': 'allow',
            }
        ]
    },
    'devices_control': {
        'label': 'Devices - Control',
        'description': 'Able to control devices.',
        'permissions': [
            {
                'path': 'device:*',
                'action': 'control',
                'access': 'allow',
            },
            {
                'path': 'device:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'devices_enable': {
        'label': 'Devices - Control',
        'description': 'Able to enable devices.',
        'permissions': [
            {
                'path': 'device:*',
                'action': 'enable',
                'access': 'allow',
            },
            {
                'path': 'device:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'devices_disable': {
        'label': 'Devices - Enable',
        'description': 'Able to disable devices.',
        'permissions': [
            {
                'path': 'device:*',
                'action': 'disable',
                'access': 'allow',
            },
            {
                'path': 'device:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'devices_admin': {
        'label': 'Devices - Administrator',
        'description': 'Full access to devices. This includes edit, add, delete, view, and control.',
        'permissions': [
            {
                'path': 'device:*',
                'action': '*',
                'access': 'allow',
            }
        ]
    },
    'device_commands_view': {
        'label': 'Device Commands - View',
        'description': 'Able to view device commands.',
        'permissions': [
            {
                'path': 'device_command:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'gateways_view': {
        'label': 'Gateways - View',
        'description': 'View configured gateways within the cluster.',
        'permissions': [
            {
                'path': 'gateway:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'locations_view': {
        'label': 'Locations - View',
        'description': 'View configured locations.',
        'permissions': [
            {
                'path': 'location:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'locations_edit': {
        'label': 'Locations - Edit',
        'description': 'Edit configured locations.',
        'permissions': [
            {
                'path': 'location:*',
                'action': 'edit',
                'access': 'allow',
            },
            {
                'path': 'location:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'locations_add': {
        'label': 'Locations - Add',
        'description': 'Add new locations.',
        'permissions': [
            {
                'path': 'location:*',
                'action': 'add',
                'access': 'allow',
            },
            {
                'path': 'location:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'locations_delete': {
        'label': 'Locations - Delete',
        'description': 'Delete configured locations.',
        'permissions': [
            {
                'path': 'location:*',
                'action': 'delete',
                'access': 'allow',
            },
            {
                'path': 'location:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'locations_admin': {
        'label': 'Locations - Administrator',
        'description': 'Full access to the location administration.',
        'permissions': [
            {
                'path': 'location:*',
                'action': '*',
                'access': 'allow',
            }
        ]
    },
    'modules_view': {
        'label': 'Modules - View',
        'description': 'View configured modules.',
        'permissions': [
            {
                'path': 'module:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'modules_edit': {
        'label': 'Modules - Edit',
        'description': 'Edit configured modules.',
        'permissions': [
            {
                'path': 'module:*',
                'action': 'edit',
                'access': 'allow',
            },
            {
                'path': 'module:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'modules_add': {
        'label': 'Modules - Add',
        'description': 'Add new modules.',
        'permissions': [
            {
                'path': 'module:*',
                'action': 'add',
                'access': 'allow',
            },
            {
                'path': 'module:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'modules_delete': {
        'label': 'Modules - Delete',
        'description': 'Delete configured modules.',
        'permissions': [
            {
                'path': 'module:*',
                'action': 'delete',
                'access': 'allow',
            },
            {
                'path': 'module:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'modules_enable': {
        'label': 'Modules - Enable',
        'description': 'Enable configured modules.',
        'permissions': [
            {
                'path': 'module:*',
                'action': 'enable',
                'access': 'allow',
            },
            {
                'path': 'module:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'modules_disable': {
        'label': 'Modules - Disable',
        'description': 'Disable configured modules.',
        'permissions': [
            {
                'path': 'module:*',
                'action': 'disable',
                'access': 'allow',
            },
            {
                'path': 'module:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'modules_admin': {
        'label': 'Modules - Administrator',
        'description': 'Full control over modules.',
        'permissions': [
            {
                'path': 'module:*',
                'action': '*',
                'access': 'allow',
            }
        ]
    },
    'notifications_view': {
        'label': 'Notifications - View',
        'description': 'View notifications.',
        'permissions': [
            {
                'path': 'notification:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'notifications_delete': {
        'label': 'Notifications - Delete',
        'description': 'Delete notifications.',
        'permissions': [
            {
                'path': 'notification:*',
                'action': 'delete',
                'access': 'allow',
            },
            {
                'path': 'notification:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'panel_view': {
        'label': 'Panel - View',
        'description': 'View panel.',
        'permissions': [
            {
                'path': 'panel:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'scenes_view': {
        'label': 'Scenes - View',
        'description': 'View configured scenes.',
        'permissions': [
            {
                'path': 'scene:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'scenes_edit': {
        'label': 'Scenes - Edit',
        'description': 'Edit configured scenes.',
        'permissions': [
            {
                'path': 'scene:*',
                'action': 'edit',
                'access': 'allow',
            },
            {
                'path': 'scene:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'scenes_add': {
        'label': 'Scenes - Add',
        'description': 'Add new scenes.',
        'permissions': [
            {
                'path': 'scene:*',
                'action': 'add',
                'access': 'allow',
            }
        ]
    },
    'scenes_delete': {
        'label': 'Scenes - Delete',
        'description': 'Delete configured scenes.',
        'permissions': [
            {
                'path': 'scene:*',
                'action': 'delete',
                'access': 'allow',
            },
            {
                'path': 'scene:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'scenes_start': {
        'label': 'Scenes - Start',
        'description': 'Start configured scenes.',
        'permissions': [
            {
                'path': 'scene:*',
                'action': 'start',
                'access': 'allow',
            },
            {
                'path': 'scene:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'scenes_stop': {
        'label': 'Scenes - Stop',
        'description': 'Stop configured scenes.',
        'permissions': [
            {
                'path': 'scene:*',
                'action': 'stop',
                'access': 'allow',
            },
            {
                'path': 'scene:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'scenes_enable': {
        'label': 'Scenes - Enable',
        'description': 'Enable configured scenes.',
        'permissions': [
            {
                'path': 'scene:*',
                'action': 'enable',
                'access': 'allow',
            },
            {
                'path': 'scene:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'scenes_disable': {
        'label': 'Scenes - Disable',
        'description': 'Disable configured scenes.',
        'permissions': [
            {
                'path': 'scene:*',
                'action': 'disable',
                'access': 'allow',
            },
            {
                'path': 'scene:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'scenes_admin': {
        'label': 'Scenes - Administrator',
        'description': 'Full control over modules.',
        'permissions': [
            {
                'path': 'scene:*',
                'action': '*',
                'access': 'allow',
            }
        ]
    },
    'states_view': {
        'label': 'States - View',
        'description': 'View system states.',
        'permissions': [
            {
                'path': 'state:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'statistics_view': {
        'label': 'Statistics - View',
        'description': 'View statistics.',
        'permissions': [
            {
                'path': 'statistic:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'system_option_backup': {
        'label': 'System option - backup',
        'description': 'Allow user to backup the system.',
        'permissions': [
            {
                'path': 'system_options:*',
                'action': 'backup',
                'access': 'allow',
            }
        ]
    },
    'system_option_control': {
        'label': 'System option - control',
        'description': 'Allow user to shutdown or restart the gateway software.',
        'permissions': [
            {
                'path': 'system_options:*',
                'action': 'control',
                'access': 'allow',
            }
        ]
    },
    'system_option_status': {
        'label': 'System option - status',
        'description': 'View various system status pages.',
        'permissions': [
            {
                'path': 'system_options:*',
                'action': 'status',
                'access': 'allow',
            }
        ]
    },
    'system_option_stream': {
        'label': 'System option - stream',
        'description': 'Allow to connection to the system event stream. This permits live access to nearly any system even change.',
        'permissions': [
            {
                'path': 'system_options:*',
                'action': 'stream',
                'access': 'allow',
            }
        ]
    },
    'system_option_mqtt': {
        'label': 'System option - mqtt',
        'description': 'Allows connections to the MQTT broker.',
        'permissions': [
            {
                'path': 'system_options:*',
                'action': 'mqtt',
                'access': 'allow',
            }
        ]
    },
    'system_settings_view': {
        'label': 'System settings - View',
        'description': 'View any system settings. Use caution, it can review various details about the installation.',
        'permissions': [
            {
                'path': 'system_setting:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'system_settings_edit': {
        'label': 'System settings - Edit',
        'description': 'Edit any system settings. Use caution, people can break things easily.',
        'permissions': [
            {
                'path': 'system_setting:*',
                'action': 'edit',
                'access': 'allow',
            }
        ]
    },
    'users_view': {
        'label': 'Users - View',
        'description': 'View configured users.',
        'permissions': [
            {
                'path': 'user:*',
                'action': 'view',
                'access': 'allow',
            }
        ]
    },
    'users_edit': {
        'label': 'Users - Edit',
        'description': 'Edit configured users.',
        'permissions': [
            {
                'path': 'user:*',
                'action': 'edit',
                'access': 'allow',
            }
        ]
    },
    'users_add': {
        'label': 'Users - Add',
        'description': 'Add new users.',
        'permissions': [
            {
                'path': 'user:*',
                'action': 'add',
                'access': 'allow',
            }
        ]
    },
    'users_delete': {
        'label': 'Users - Delete',
        'description': 'Delete configured users.',
        'permissions': [
            {
                'path': 'user:*',
                'action': 'delete',
                'access': 'allow',
            }
        ]
    },
    'users_admin': {
        'label': 'Users - Administrator',
        'description': 'Full access to the user administration.',
        'permissions': [
            {
                'path': 'user:*',
                'action': '*',
                'access': 'allow',
            }
        ]
    },
}
