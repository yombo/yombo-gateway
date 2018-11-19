"""
Constants for users library.
"""

AUTH_PLATFORM_ATOM = "atom"
AUTH_PLATFORM_AUTHKEY = "authkey"
AUTH_PLATFORM_AUTOMATION = "automation"
AUTH_PLATFORM_CALLLATER = "calllater"
AUTH_PLATFORM_CRONTAB = "crontab"
AUTH_PLATFORM_DEBUG = "debug"
AUTH_PLATFORM_DEVICE = "device"
AUTH_PLATFORM_DEVICE_COMMAND = "device_command"
AUTH_PLATFORM_EVENTS = "events"
AUTH_PLATFORM_GATEWAY = "gateway"
AUTH_PLATFORM_INTENT = "intent"
AUTH_PLATFORM_LOCATION = "location"
AUTH_PLATFORM_MODULE = "module"
AUTH_PLATFORM_NOTIFICATION = "notification"
AUTH_PLATFORM_PANEL = "panel"
AUTH_PLATFORM_ROLE = "role"
AUTH_PLATFORM_SCENE = "scene"
AUTH_PLATFORM_STATE = "state"
AUTH_PLATFORM_STATISTIC = "statistic"
AUTH_PLATFORM_SYSTEM_SETTING = "system_setting"
AUTH_PLATFORM_SYSTEM_OPTION = "system_options"
AUTH_PLATFORM_TASKS = "tasks"
AUTH_PLATFORM_USER = "user"
AUTH_PLATFORM_WEBSESSION = "websession"
AUTH_PLATFORM_WEBLOGS = "weblogs"
AUTH_PLATFORM_WILDCARD = "*"

ITEMIZED_AUTH_PLATFORMS = AUTH_PLATFORM_AUTOMATION, AUTH_PLATFORM_DEVICE, AUTH_PLATFORM_SCENE

ACTIONS_ATOM = ("view", "edit", "enable", "disable")
ACTIONS_AUTHKEY = ("add", "view", "edit", "enable", "disable", "remove")
ACTIONS_AUTOMATION = ("add", "view", "edit", "start", "stop", "enable", "disable", "remove")
ACTIONS_CALLLATER = ("view",)
ACTIONS_CRONTAB = ("add", "view", "edit", "enable", "disable")
ACTIONS_DEBUG = ("cache", "view", "commands", "device_types", "libraries", "modules", "nodes", "sslcerts", "statistics",
                 "requirements", "crontab", "locales", "event_types")
ACTIONS_DEVICE = ("add", "view", "control", "edit", "enable", "disable", "remove")
ACTIONS_DEVICE_COMMAND = ("view", "remove")
ACTIONS_EVENTS = ("view",)
ACTIONS_GATEWAY = ("add", "view", "edit", "enable", "disable", "remove")
ACTIONS_INTENT = ("add", "view", "edit", "remove")
ACTIONS_LOCATION = ("add", "view", "edit", "remove")
ACTIONS_MODULE = ("add", "view", "edit", "enable", "disable", "remove")
ACTIONS_NOTIFICATION = ("view", "remove")
ACTIONS_PANEL = ("view",)
ACTIONS_ROLE = ("add", "view", "edit", "remove")
ACTIONS_SCENE = ("add", "view", "start", "stop", "edit", "enable", "disable", "remove")
ACTIONS_STATE = ("view",)
ACTIONS_STATISTIC = ("view",)
ACTIONS_SYSTEM_SETTING = ("view", "edit")
ACTIONS_SYSTEM_OPTION = ("view", "backup", "control", "status", "stream", "mqtt")
ACTIONS_TASKS = ("view",)
ACTIONS_USER = ("add", "view", "edit", "remove")
ACTIONS_WEBLOGS = ("view",)
ACTIONS_WEBSESSION = ("view",)
ACTIONS_WILDCARD = ()

AUTH_PLATFORMS = {
    AUTH_PLATFORM_ATOM: {"actions": ACTIONS_ATOM},
    AUTH_PLATFORM_AUTHKEY: {"actions": ACTIONS_AUTHKEY},
    AUTH_PLATFORM_AUTOMATION: {"actions": ACTIONS_AUTOMATION},
    AUTH_PLATFORM_CALLLATER: {"actions": ACTIONS_CALLLATER},
    AUTH_PLATFORM_CRONTAB: {"actions": ACTIONS_CRONTAB},
    AUTH_PLATFORM_DEBUG: {"actions": ACTIONS_DEBUG},
    AUTH_PLATFORM_DEVICE: {"actions": ACTIONS_DEVICE},
    AUTH_PLATFORM_DEVICE_COMMAND: {"actions": ACTIONS_DEVICE_COMMAND},
    AUTH_PLATFORM_EVENTS: {"actions": ACTIONS_EVENTS},
    AUTH_PLATFORM_GATEWAY: {"actions": ACTIONS_GATEWAY},
    AUTH_PLATFORM_INTENT: {"actions": ACTIONS_INTENT},
    AUTH_PLATFORM_LOCATION: {"actions": ACTIONS_LOCATION},
    AUTH_PLATFORM_MODULE: {"actions": ACTIONS_MODULE},
    AUTH_PLATFORM_NOTIFICATION: {"actions": ACTIONS_NOTIFICATION},
    AUTH_PLATFORM_PANEL: {"actions": ACTIONS_PANEL},
    AUTH_PLATFORM_ROLE: {"actions": ACTIONS_ROLE},
    AUTH_PLATFORM_SCENE: {"actions": ACTIONS_SCENE},
    AUTH_PLATFORM_STATE: {"actions": ACTIONS_STATE},
    AUTH_PLATFORM_STATISTIC: {"actions": ACTIONS_STATISTIC},
    AUTH_PLATFORM_SYSTEM_SETTING: {"actions": ACTIONS_SYSTEM_SETTING},
    AUTH_PLATFORM_SYSTEM_OPTION: {"actions": ACTIONS_SYSTEM_OPTION},
    AUTH_PLATFORM_TASKS: {"actions": ACTIONS_TASKS},
    AUTH_PLATFORM_USER: {"actions": ACTIONS_USER},
    AUTH_PLATFORM_WEBLOGS: {"actions": ACTIONS_WEBLOGS},
    AUTH_PLATFORM_WEBSESSION: {"actions": ACTIONS_WEBSESSION},
    AUTH_PLATFORM_WILDCARD: {"actions": ACTIONS_WILDCARD},
}

SYSTEM_ROLES = {
    "admin": {
        "label": "Administrators",
        "description": "Full access to everything.",
        "permissions": [
            {
                "platform": "*",
                "item": "*",
                "action": "*",
                "access": "allow",
            }
        ]
    },
    "everyone": {
        "label": "Everyone",
        "description": "Everyone belongs to this role.",
        "permissions": [],
    },
    "general_users": {
        "label": "General Users",
        "description": "Given to most users so they can control all devices. "
                       "Specific devices can be blocked at the device level. "
                       "This role also grants views to states, atoms, and other low level items.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_ATOM,
                "item": "*",
                "action": "view",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_CRONTAB,
                "item": "*",
                "action": "view",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_DEVICE,
                "item": "*",
                "action": "view",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_DEVICE,
                "item": "*",
                "action": "control",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_GATEWAY,
                "item": "*",
                "action": "view",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_LOCATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_MODULE,
                "item": "*",
                "action": "view",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_NOTIFICATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_PANEL,
                "item": "*",
                "action": "view",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "view",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_STATE,
                "item": "*",
                "action": "view",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_STATISTIC,
                "item": "*",
                "action": "view",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_USER,
                "item": "*",
                "action": "view",
                "access": "allow",
            },
        ]
    },
    "viewers": {
        "label": "Viewers",
        "description": "Can view anything within the system.",
        "permissions": [
            {
                "platform": "*",
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "authkey_view": {
        "label": "Auth Key - View",
        "description": "View configured Auth Keys.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_AUTHKEY,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "authkey_edit": {
        "label": "Auth Key - Edit",
        "description": "Edit configured Auth Keys.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_AUTHKEY,
                "item": "*",
                "action": "edit",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_AUTHKEY,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "authkey_add": {
        "label": "Auth Key - Add",
        "description": "Add new Auth Keys.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_AUTHKEY,
                "item": "*",
                "action": "add",
                "access": "allow",
            }
        ]
    },
    "authkey_remove": {
        "label": "Auth Key - Delete",
        "description": "Delete Auth Keys.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_AUTHKEY,
                "item": "*",
                "action": "remove",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_AUTHKEY,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "authkey_admin": {
        "label": "Auth Key - Administrator",
        "description": "Full access to Auth Keys.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_AUTHKEY,
                "item": "*",
                "action": "*",
                "access": "allow",
            }
        ]
    },
    "atoms_view": {
        "label": "Atoms - View",
        "description": "View system defined atoms.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_ATOM,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "automation_view": {
        "label": "Automation Rules - View",
        "description": "View configured automation rules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "automation_edit": {
        "label": "Automation Rules - Edit",
        "description": "Edit configured automation rules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "edit",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "automation_add": {
        "label": "Automation Rules - Add",
        "description": "Add new automation rules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "add",
                "access": "allow",
            }
        ]
    },
    "automation_remove": {
        "label": "Automation Rules - Delete",
        "description": "Delete configured automation rules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "remove",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "automation_start": {
        "label": "Automation Rules - Start",
        "description": "Start configured automation rules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "start",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "automation_stop": {
        "label": "Automation Rules - Stop",
        "description": "Stop configured automation rules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "stop",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "automation_enable": {
        "label": "Automation Rules - Enable",
        "description": "Enable configured automation rules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "enable",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "automation_disable": {
        "label": "Automation Rules - Disable",
        "description": "Start configured automation rules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "disable",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "automation_admin": {
        "label": "Automation Rules - Administrator",
        "description": "Full control over automation rules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_AUTOMATION,
                "item": "*",
                "action": "*",
                "access": "allow",
            }
        ]
    },
    "calllater_view": {
        "label": "Call later - View call later items",
        "description": "Allow user to the view call later items.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_CALLLATER,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "crontab_add": {
        "label": "Crontab - Add",
        "description": "Able to add crontabs.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_CRONTAB,
                "item": "*",
                "action": "add",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_CRONTAB,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "crontab_edit": {
        "label": "Crontab - Edit",
        "description": "Able to edit crontabs.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_CRONTAB,
                "item": "*",
                "action": "edit",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_CRONTAB,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "crontab_disable": {
        "label": "Crontab - Disable",
        "description": "Able to disable crontabs.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_CRONTAB,
                "item": "*",
                "action": "disable",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_CRONTAB,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "crontab_enable": {
        "label": "Crontab - Enable",
        "description": "Able to enable crontabs.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_CRONTAB,
                "item": "*",
                "action": "enable",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_CRONTAB,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "devices_view": {
        "label": "Devices - View",
        "description": "Able to view devices.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_DEVICE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "devices_edit": {
        "label": "Devices - Edit",
        "description": "Able to edit devices.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_DEVICE,
                "item": "*",
                "action": "edit",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_DEVICE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "devices_remove": {
        "label": "Devices - Delete",
        "description": "Able to remove devices.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_DEVICE,
                "item": "*",
                "action": "remove",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_DEVICE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "devices_add": {
        "label": "Devices - Add",
        "description": "Able to add new devices.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_DEVICE,
                "item": "*",
                "action": "add",
                "access": "allow",
            }
        ]
    },
    "devices_control": {
        "label": "Devices - Control",
        "description": "Able to control devices.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_DEVICE,
                "item": "*",
                "action": "control",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_DEVICE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "devices_enable": {
        "label": "Devices - Enable",
        "description": "Able to enable devices.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_DEVICE,
                "item": "*",
                "action": "enable",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_DEVICE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "devices_disable": {
        "label": "Devices - Enable",
        "description": "Able to disable devices.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_DEVICE,
                "item": "*",
                "action": "disable",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_DEVICE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "devices_admin": {
        "label": "Devices - Administrator",
        "description": "Full access to devices. This includes edit, add, remove, view, and control.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_DEVICE,
                "item": "*",
                "action": "*",
                "access": "allow",
            }
        ]
    },
    "device_commands_view": {
        "label": "Device Commands - View",
        "description": "Able to view device commands.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_DEVICE_COMMAND,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "events_view": {
        "label": "Events - View",
        "description": "View system event log.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_EVENTS,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "gateways_view": {
        "label": "Gateways - View",
        "description": "View configured gateways within the cluster.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_GATEWAY,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "locations_view": {
        "label": "Locations - View",
        "description": "View configured locations.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_LOCATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "locations_edit": {
        "label": "Locations - Edit",
        "description": "Edit configured locations.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_LOCATION,
                "item": "*",
                "action": "edit",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_LOCATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "locations_add": {
        "label": "Locations - Add",
        "description": "Add new locations.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_LOCATION,
                "item": "*",
                "action": "add",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_LOCATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "locations_remove": {
        "label": "Locations - Delete",
        "description": "Delete configured locations.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_LOCATION,
                "item": "*",
                "action": "remove",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_LOCATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "locations_admin": {
        "label": "Locations - Administrator",
        "description": "Full access to the location administration.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_LOCATION,
                "item": "*",
                "action": "*",
                "access": "allow",
            }
        ]
    },
    "modules_view": {
        "label": "Modules - View",
        "description": "View configured modules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_MODULE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "modules_edit": {
        "label": "Modules - Edit",
        "description": "Edit configured modules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_MODULE,
                "item": "*",
                "action": "edit",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_MODULE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "modules_add": {
        "label": "Modules - Add",
        "description": "Add new modules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_MODULE,
                "item": "*",
                "action": "add",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_MODULE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "modules_remove": {
        "label": "Modules - Delete",
        "description": "Delete configured modules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_MODULE,
                "item": "*",
                "action": "remove",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_MODULE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "modules_enable": {
        "label": "Modules - Enable",
        "description": "Enable configured modules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_MODULE,
                "item": "*",
                "action": "enable",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_MODULE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "modules_disable": {
        "label": "Modules - Disable",
        "description": "Disable configured modules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_MODULE,
                "item": "*",
                "action": "disable",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_MODULE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "modules_admin": {
        "label": "Modules - Administrator",
        "description": "Full control over modules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_MODULE,
                "item": "*",
                "action": "*",
                "access": "allow",
            }
        ]
    },
    "notifications_view": {
        "label": "Notifications - View",
        "description": "View notification.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_NOTIFICATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "notifications_remove": {
        "label": "Notifications - Delete",
        "description": "Delete notifications.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_NOTIFICATION,
                "item": "*",
                "action": "remove",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_NOTIFICATION,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "panel_view": {
        "label": "Panel - View",
        "description": "View panel.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_PANEL,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "scenes_view": {
        "label": "Scenes - View",
        "description": "View configured scenes.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "scenes_edit": {
        "label": "Scenes - Edit",
        "description": "Edit configured scenes.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "edit",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "scenes_add": {
        "label": "Scenes - Add",
        "description": "Add new scenes.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "add",
                "access": "allow",
            }
        ]
    },
    "scenes_remove": {
        "label": "Scenes - Delete",
        "description": "Delete configured scenes.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "remove",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "scenes_start": {
        "label": "Scenes - Start",
        "description": "Start configured scenes.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "start",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "scenes_stop": {
        "label": "Scenes - Stop",
        "description": "Stop configured scenes.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "stop",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "scenes_enable": {
        "label": "Scenes - Enable",
        "description": "Enable configured scenes.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "enable",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "scenes_disable": {
        "label": "Scenes - Disable",
        "description": "Disable configured scenes.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "disable",
                "access": "allow",
            },
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "scenes_admin": {
        "label": "Scenes - Administrator",
        "description": "Full control over modules.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SCENE,
                "item": "*",
                "action": "*",
                "access": "allow",
            }
        ]
    },
    "states_view": {
        "label": "States - View",
        "description": "View system states.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_STATE,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "statistics_view": {
        "label": "Statistics - View",
        "description": "View statistics.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_STATISTIC,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "system_option_backup": {
        "label": "System option - backup",
        "description": "Allow user to backup the system.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SYSTEM_OPTION,
                "item": "*",
                "action": "backup",
                "access": "allow",
            }
        ]
    },
    "system_option_control": {
        "label": "System option - control",
        "description": "Allow user to shutdown or restart the gateway software.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SYSTEM_OPTION,
                "item": "*",
                "action": "control",
                "access": "allow",
            }
        ]
    },
    "system_option_status": {
        "label": "System option - status",
        "description": "View various system status pages.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SYSTEM_OPTION,
                "item": "*",
                "action": "status",
                "access": "allow",
            }
        ]
    },
    "system_option_stream": {
        "label": "System option - stream",
        "description": "Allow to connection to the system event stream. "
                       "This permits live access to nearly any system even change.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SYSTEM_OPTION,
                "item": "*",
                "action": "stream",
                "access": "allow",
            }
        ]
    },
    "system_option_mqtt": {
        "label": "System option - mqtt",
        "description": "Allows connections to the MQTT broker.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SYSTEM_OPTION,
                "item": "*",
                "action": "mqtt",
                "access": "allow",
            }
        ]
    },
    "system_settings_view": {
        "label": "System settings - View",
        "description": "View any system settings. Use caution, it can review various details about the installation.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SYSTEM_SETTING,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "system_settings_edit": {
        "label": "System settings - Edit",
        "description": "Edit any system settings. Use caution, people can break things easily.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_SYSTEM_SETTING,
                "item": "*",
                "action": "edit",
                "access": "allow",
            }
        ]
    },
    "tasks_view": {
        "label": "Tasks - View Tasks",
        "description": "Allow user to view tasks.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_TASKS,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "users_view": {
        "label": "Users - View",
        "description": "View configured users.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_USER,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
    "users_edit": {
        "label": "Users - Edit",
        "description": "Edit configured users.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_USER,
                "item": "*",
                "action": "edit",
                "access": "allow",
            }
        ]
    },
    "users_add": {
        "label": "Users - Add",
        "description": "Add new users.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_USER,
                "item": "*",
                "action": "add",
                "access": "allow",
            }
        ]
    },
    "users_remove": {
        "label": "Users - Delete",
        "description": "Delete configured users.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_USER,
                "item": "*",
                "action": "remove",
                "access": "allow",
            }
        ]
    },
    "users_admin": {
        "label": "Users - Administrator",
        "description": "Full access to the user administration.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_USER,
                "item": "*",
                "action": "*",
                "access": "allow",
            }
        ]
    },
    "weblogs_view": {
        "label": "WebLogs - View",
        "description": "View web interface logs.",
        "permissions": [
            {
                "platform": AUTH_PLATFORM_WEBLOGS,
                "item": "*",
                "action": "view",
                "access": "allow",
            }
        ]
    },
}
