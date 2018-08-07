"""
Constants for users.
"""
SYSTEM_ROLES = {
    'admin': {
        'label': 'Administrators',
        'description': 'Full access to everything.',
        'permissions': [
            {
                'platform': '*',
                'item': '*',
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
                'platform': 'atom',
                'item': '*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'platform': 'automation',
                'item': '*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'platform': 'device',
                'item': '*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'platform': 'device',
                'item': '*',
                'action': 'control',
                'access': 'allow',
            },
            {
                'platform': 'gateway',
                'item': '*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'platform': 'location',
                'item': '*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'platform': 'module',
                'item': '*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'platform': 'notifications',
                'item': '*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'platform': 'panel',
                'item': '*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'platform': 'scene',
                'item': '*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'platform': 'state',
                'item': '*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'platform': 'statistic',
                'item': '*',
                'action': 'view',
                'access': 'allow',
            },
            {
                'platform': 'user',
                'item': '*',
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
                'platform': '*',
                'item': '*',
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
                'platform': 'apiauth',
                'item': '*',
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
                'platform': 'apiauth',
                'item': '*',
                'action': 'edit',
                'access': 'allow',
            },
            {
                'platform': 'apiauth',
                'item': '*',
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
                'platform': 'apiauth',
                'item': '*',
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
                'platform': 'apiauth',
                'item': '*',
                'action': 'delete',
                'access': 'allow',
            },
            {
                'platform': 'apiauth',
                'item': '*',
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
                'platform': 'apiauth',
                'item': '*',
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
                'platform': 'atom',
                'item': '*',
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
                'platform': 'automation',
                'item': '*',
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
                'platform': 'automation',
                'item': '*',
                'action': 'edit',
                'access': 'allow',
            },
            {
                'platform': 'automation',
                'item': '*',
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
                'platform': 'automation',
                'item': '*',
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
                'platform': 'automation',
                'item': '*',
                'action': 'delete',
                'access': 'allow',
            },
            {
                'platform': 'automation',
                'item': '*',
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
                'platform': 'automation',
                'item': '*',
                'action': 'start',
                'access': 'allow',
            },
            {
                'platform': 'automation',
                'item': '*',
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
                'platform': 'automation',
                'item': '*',
                'action': 'stop',
                'access': 'allow',
            },
            {
                'platform': 'automation',
                'item': '*',
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
                'platform': 'automation',
                'item': '*',
                'action': 'enable',
                'access': 'allow',
            },
            {
                'platform': 'automation',
                'item': '*',
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
                'platform': 'automation',
                'item': '*',
                'action': 'disable',
                'access': 'allow',
            },
            {
                'platform': 'automation',
                'item': '*',
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
                'platform': 'automation',
                'item': '*',
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
                'platform': 'device',
                'item': '*',
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
                'platform': 'device',
                'item': '*',
                'action': 'edit',
                'access': 'allow',
            },
            {
                'platform': 'device',
                'item': '*',
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
                'platform': 'device',
                'item': '*',
                'action': 'delete',
                'access': 'allow',
            },
            {
                'platform': 'device',
                'item': '*',
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
                'platform': 'device',
                'item': '*',
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
                'platform': 'device',
                'item': '*',
                'action': 'control',
                'access': 'allow',
            },
            {
                'platform': 'device',
                'item': '*',
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
                'platform': 'device',
                'item': '*',
                'action': 'enable',
                'access': 'allow',
            },
            {
                'platform': 'device',
                'item': '*',
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
                'platform': 'device',
                'item': '*',
                'action': 'disable',
                'access': 'allow',
            },
            {
                'platform': 'device',
                'item': '*',
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
                'platform': 'device',
                'item': '*',
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
                'platform': 'device_command',
                'item': '*',
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
                'platform': 'gateway',
                'item': '*',
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
                'platform': 'location',
                'item': '*',
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
                'platform': 'location',
                'item': '*',
                'action': 'edit',
                'access': 'allow',
            },
            {
                'platform': 'location',
                'item': '*',
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
                'platform': 'location',
                'item': '*',
                'action': 'add',
                'access': 'allow',
            },
            {
                'platform': 'location',
                'item': '*',
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
                'platform': 'location',
                'item': '*',
                'action': 'delete',
                'access': 'allow',
            },
            {
                'platform': 'location',
                'item': '*',
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
                'platform': 'location',
                'item': '*',
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
                'platform': 'module',
                'item': '*',
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
                'platform': 'module',
                'item': '*',
                'action': 'edit',
                'access': 'allow',
            },
            {
                'platform': 'module',
                'item': '*',
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
                'platform': 'module',
                'item': '*',
                'action': 'add',
                'access': 'allow',
            },
            {
                'platform': 'module',
                'item': '*',
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
                'platform': 'module',
                'item': '*',
                'action': 'delete',
                'access': 'allow',
            },
            {
                'platform': 'module',
                'item': '*',
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
                'platform': 'module',
                'item': '*',
                'action': 'enable',
                'access': 'allow',
            },
            {
                'platform': 'module',
                'item': '*',
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
                'platform': 'module',
                'item': '*',
                'action': 'disable',
                'access': 'allow',
            },
            {
                'platform': 'module',
                'item': '*',
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
                'platform': 'module',
                'item': '*',
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
                'platform': 'notification',
                'item': '*',
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
                'platform': 'notification',
                'item': '*',
                'action': 'delete',
                'access': 'allow',
            },
            {
                'platform': 'notification',
                'item': '*',
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
                'platform': 'panel',
                'item': '*',
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
                'platform': 'scene',
                'item': '*',
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
                'platform': 'scene',
                'item': '*',
                'action': 'edit',
                'access': 'allow',
            },
            {
                'platform': 'scene',
                'item': '*',
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
                'platform': 'scene',
                'item': '*',
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
                'platform': 'scene',
                'item': '*',
                'action': 'delete',
                'access': 'allow',
            },
            {
                'platform': 'scene',
                'item': '*',
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
                'platform': 'scene',
                'item': '*',
                'action': 'start',
                'access': 'allow',
            },
            {
                'platform': 'scene',
                'item': '*',
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
                'platform': 'scene',
                'item': '*',
                'action': 'stop',
                'access': 'allow',
            },
            {
                'platform': 'scene',
                'item': '*',
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
                'platform': 'scene',
                'item': '*',
                'action': 'enable',
                'access': 'allow',
            },
            {
                'platform': 'scene',
                'item': '*',
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
                'platform': 'scene',
                'item': '*',
                'action': 'disable',
                'access': 'allow',
            },
            {
                'platform': 'scene',
                'item': '*',
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
                'platform': 'scene',
                'item': '*',
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
                'platform': 'state',
                'item': '*',
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
                'platform': 'statistic',
                'item': '*',
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
                'platform': 'system_options',
                'item': '*',
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
                'platform': 'system_options',
                'item': '*',
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
                'platform': 'system_options',
                'item': '*',
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
                'platform': 'system_options',
                'item': '*',
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
                'platform': 'system_options',
                'item': '*',
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
                'platform': 'system_setting',
                'item': '*',
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
                'platform': 'system_setting',
                'item': '*',
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
                'platform': 'user',
                'item': '*',
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
                'platform': 'user',
                'item': '*',
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
                'platform': 'user',
                'item': '*',
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
                'platform': 'user',
                'item': '*',
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
                'platform': 'user',
                'item': '*',
                'action': '*',
                'access': 'allow',
            }
        ]
    },
}
