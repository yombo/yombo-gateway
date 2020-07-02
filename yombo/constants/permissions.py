"""
Constants for permissions library.
"""
AUTH_PLATFORM_ATOM = "yombo.lib.atom"
AUTH_PLATFORM_AUTHKEY = "yombo.lib.authkey"
AUTH_PLATFORM_AUTOMATION = "yombo.lib.automation"
AUTH_PLATFORM_CALLLATER = "yombo.lib.calllater"
AUTH_PLATFORM_CATEGORIES = "yombo.lib.categories"
AUTH_PLATFORM_CRONTAB = "yombo.lib.crontab"
AUTH_PLATFORM_COMMAND = "yombo.lib.command"
AUTH_PLATFORM_CONFIG = "yombo.lib.config"
AUTH_PLATFORM_DEBUG = "yombo.lib.debug"
AUTH_PLATFORM_DEVICE = "yombo.lib.device"
AUTH_PLATFORM_DEVICE_COMMAND = "yombo.lib.device_command"
AUTH_PLATFORM_DEVICE_COMMAND_INPUT = "yombo.lib.device_command_input"
AUTH_PLATFORM_DEVICE_STATE = "yombo.lib.device_state"
AUTH_PLATFORM_DEVICE_TYPE = "yombo.lib.device_type"
AUTH_PLATFORM_DEVICE_TYPE_COMMAND = "yombo.lib.device_type_command"
AUTH_PLATFORM_DISCOVERY = "yombo.lib.discovery"
AUTH_PLATFORM_EVENTS = "yombo.lib.events"
AUTH_PLATFORM_GATEWAY = "yombo.lib.gateway"
AUTH_PLATFORM_GPG = "yombo.lib.gpg"
AUTH_PLATFORM_INPUT_TYPE = "yombo.lib.input_type"
AUTH_PLATFORM_INTENT = "yombo.lib.intent"
AUTH_PLATFORM_LOCATION = "yombo.lib.location"
AUTH_PLATFORM_MODULE = "yombo.lib.module"
AUTH_PLATFORM_MODULE_DEVICE_TYPE = "yombo.lib.module_device_type"
AUTH_PLATFORM_MQTT = "yombo.lib.mqtt"
AUTH_PLATFORM_MQTTUSERS = "yombo.lib.mqttusers"
AUTH_PLATFORM_MQTTYOMBO = "yombo.lib.mqttyombo"
AUTH_PLATFORM_NODE = "yombo.lib.node"
AUTH_PLATFORM_NOTIFICATION = "yombo.lib.notification"
AUTH_PLATFORM_PERMISSION = "yombo.lib.permission"
AUTH_PLATFORM_ROLE = "yombo.lib.role"
AUTH_PLATFORM_SCENE = "yombo.lib.scene"
AUTH_PLATFORM_STATE = "yombo.lib.state"
AUTH_PLATFORM_STATISTIC = "yombo.lib.statistic"
AUTH_PLATFORM_STORAGE = "yombo.lib.storage"
AUTH_PLATFORM_SYSTEM_SETTING = "yombo.lib.system_setting"
AUTH_PLATFORM_SYSTEM_OPTION = "yombo.lib.system_options"
AUTH_PLATFORM_TASK = "yombo.lib.task"
AUTH_PLATFORM_TIME = "yombo.lib.times"
AUTH_PLATFORM_USER = "yombo.lib.user"
AUTH_PLATFORM_VARIABLE_DATA = "yombo.lib.variable_data"
AUTH_PLATFORM_VARIABLE_FIELDS = "yombo.lib.variable_fields"
AUTH_PLATFORM_VARIABLE_GROUPS = "yombo.lib.variable_groups"
AUTH_PLATFORM_WEBSESSION = "yombo.lib.websession"
AUTH_PLATFORM_WEBSTREAM = "yombo.webstream"
AUTH_PLATFORM_WEBLOG = "yombo.lib.weblog"
AUTH_PLATFORM_WILDCARD = "yombo.lib.*"

ACTIONS_ATOM = {"possible": ["view"],
                "user": ["view"]}
ACTIONS_AUTHKEY = {"possible": ["create", "modify", "enable", "disable", "remove", "view"],
                   "user": []}
ACTIONS_CALLLATER = {"possible": ["create", "view", "cancel", "modify"],
                     "user": []}
ACTIONS_CATEGORIES = {"possible": ["view"],
                     "user": []}
ACTIONS_COMMAND = {"possible": ["create", "modify", "remove", "view"],
                   "user": ["view"]}
ACTIONS_CONFIG = {"possible": ["create", "modify", "view"],
                  "user": []}
ACTIONS_CRONTAB = {"possible": ["create", "disable", "enable", "modify", "view", "remove"],
                   "user": ["view"]}
ACTIONS_DEBUG = {"possible": ["cache", "commands", "crontab", "device_types", "index", "libraries", "modules", "mqtt",
                              "nodes", "sslcerts", "statistics", "requirements", "", "locales", "event_types",
                              "sqldicts"],
                 "user": []}
ACTIONS_DEVICE = {"possible": ["create", "control", "enable", "disable", "modify", "remove", "view"],
                  "user": ["view"]}
ACTIONS_DEVICE_COMMAND = {"possible": ["create", "modify", "remove", "view"],
                          "user": ["view"]}
ACTIONS_DEVICE_COMMAND_INPUT = {"possible": ["create", "modify", "remove", "view"],
                                "user": ["view"]}
ACTIONS_DEVICE_STATE = {"possible": ["remove", "view"],
                        "user": ["view"]}
ACTIONS_DEVICE_TYPE = {"possible": ["create", "modify", "remove", "view"],
                       "user": ["view"]}
ACTIONS_DEVICE_TYPE_COMMAND = {"possible": ["create", "modify", "remove", "view"],
                               "user": ["view"]}
ACTIONS_DISCOVERY = {"possible": ["create", "edit", "view"],
                     "user": ["view"]}
ACTIONS_EVENTS = {"possible": ["view"],
                  "user": []}
ACTIONS_GATEWAY = {"possible": ["create", "enable", "disable", "modify", "remove", "view"],
                   "user": ["view"]}
ACTIONS_GPG = {"possible": ["modify", "view"],
               "user": []}
ACTIONS_INPUT_TYPE = {"possible": ["create", "modify", "remove", "view"],
                      "user": ["view"]}
ACTIONS_INTENT = {"possible": ["modify", "remove", "view"],
                  "user": ["view"]}
ACTIONS_LOCATION = {"possible": ["create", "modify", "remove", "view"],
                    "user": ["view"]}
ACTIONS_MODULE = {"possible": ["create", "enable", "disable", "modify", "remove", "view"],
                  "user": ["view"]}
ACTIONS_MODULE_DEVICE_TYPE = {"possible": ["create", "modify", "remove", "view"],
                              "user": ["view"]}
ACTIONS_MQTT = {"possible": ["view", "publish"],
                "user": []}
ACTIONS_MQTTUSERS = {"possible": ["create", "modify", "remove", "view"],
                     "user": []}
ACTIONS_MQTTYOMBO = {"possible": ["view"],
                     "user": []}
ACTIONS_NODE = {"possible": ["create", "modify", "remove", "view"],
                "user": ["view"]}
ACTIONS_NOTIFICATION = {"possible": ["view", "remove"],
                        "user": ["view"]}
ACTIONS_PERMISSION = {"possible": ["create", "modify", "remove", "view"],
                      "user": []}
ACTIONS_ROLE = {"possible": ["create", "modify", "remove", "view"],
                "user": ["view"]}
ACTIONS_SCENE = {"possible": ["create", "enable", "disable", "modify", "start", "stop", "remove", "view"],
                 "user": ["view"]}
ACTIONS_STATE = {"possible": ["create", "modify", "remove", "view"],
                 "user": ["view"]}
ACTIONS_STATISTIC = {"possible": ["view"],
                     "user": ["view"]}
ACTIONS_STORAGE = {"possible": ["create", "modify", "remove", "view"],
                   "user": ["view"]}
ACTIONS_SYSTEM_SETTING = {"possible": ["create", "modify", "remove", "view"],
                          "user": []}
ACTIONS_SYSTEM_OPTION = {"possible": ["backup", "debug", "control", "info", "mqtt", "status", "stream", "weblogs",
                                      "view"],
                         "user": []}
ACTIONS_TASK = {"possible": ["create", "modify", "remove", "view"],
                "user": ["view"]}
ACTIONS_TIME = {"possible": ["view"],
                "user": ["view"]}
ACTIONS_USER = {"possible": ["create", "modify", "remove", "view"],
                "user": []}
ACTIONS_VARIABLE_DATA = {"possible": ["create", "modify", "remove", "view"],
                         "user": []}
ACTIONS_VARIABLE_FIELDS = {"possible": ["create", "modify", "remove", "view"],
                           "user": []}
ACTIONS_VARIABLE_GROUPS = {"possible": ["create", "modify", "remove", "view"],
                           "user": []}
ACTIONS_WEBLOG = {"possible": ["view"],
                  "user": []}
ACTIONS_WEBSESSION = {"possible": ["view"],
                      "user": []}
ACTIONS_WILDCARD = {"possible": ["*"],
                    "user": []}

# These are used to create permissions and by the api/generic_router to access the libraries. The leading
# underscore (_) is added here for convenience.
AUTH_PLATFORMS = {
    AUTH_PLATFORM_ATOM: {
        "actions": ACTIONS_ATOM,
        "resource_type": "library", "resource_name": "Atoms", "resource_label": "atoms"},
    AUTH_PLATFORM_AUTHKEY: {
        "actions": ACTIONS_AUTHKEY,
        "resource_type": "library", "resource_name": "AuthKeys", "resource_label": "authkeys"},
    AUTH_PLATFORM_CALLLATER: {
        "actions": ACTIONS_CALLLATER,
        "resource_type": "library", "resource_name": "CallLater", "resource_label": "calllater"},
    AUTH_PLATFORM_CATEGORIES: {
        "actions": ACTIONS_CATEGORIES,
        "resource_type": "library", "resource_name": "Categories", "resource_label": "categories"},
    AUTH_PLATFORM_COMMAND: {
        "actions": ACTIONS_COMMAND,
        "resource_type": "library", "resource_name": "Commands", "resource_label": "commands"},
    AUTH_PLATFORM_CONFIG: {
        "actions": ACTIONS_CONFIG,
        "resource_type": "library", "resource_name": "Configs", "resource_label": "configs"},
    AUTH_PLATFORM_CRONTAB: {
        "actions": ACTIONS_CRONTAB,
        "resource_type": "library", "resource_name": "CronTabs", "resource_label": "crontabs"},
    AUTH_PLATFORM_DEBUG: {
        "actions": ACTIONS_DEBUG,
        "resource_type": None, "resource_name": None, "resource_label": None},
    AUTH_PLATFORM_DEVICE: {
        "actions": ACTIONS_DEVICE,
        "resource_type": "library", "resource_name": "Devices", "resource_label": "devices"},
    AUTH_PLATFORM_DEVICE_COMMAND: {
        "actions": ACTIONS_DEVICE_COMMAND,
        "resource_type": "library", "resource_name": "DeviceCommands", "resource_label": "device_commands"},
    AUTH_PLATFORM_DEVICE_COMMAND_INPUT: {
        "actions": ACTIONS_DEVICE_COMMAND_INPUT,
        "resource_type": "library", "resource_name": "DeviceCommandInputs", "resource_label": "device_command_inputs"},
    AUTH_PLATFORM_DEVICE_STATE: {
        "actions": ACTIONS_DEVICE_STATE,
        "resource_type": "library", "resource_name": "DeviceStates", "resource_label": "device_states"},
    AUTH_PLATFORM_DEVICE_TYPE: {
        "actions": ACTIONS_DEVICE_TYPE,
        "resource_type": "library", "resource_name": "DeviceTypes", "resource_label": "device_types"},
    AUTH_PLATFORM_DEVICE_TYPE_COMMAND: {
        "actions": ACTIONS_DEVICE_TYPE_COMMAND,
        "resource_type": "library", "resource_name": "DeviceTypeCommands", "resource_label": "device_type_commands"},
    AUTH_PLATFORM_DISCOVERY: {
        "actions": ACTIONS_DISCOVERY,
        "resource_type": "library", "resource_name": "Discovery", "resource_label": "discovery"},
    AUTH_PLATFORM_EVENTS: {
        "actions": ACTIONS_EVENTS,
        "resource_type": "library", "resource_name": "Events", "resource_label": "events"},
    AUTH_PLATFORM_GATEWAY: {
        "actions": ACTIONS_GATEWAY,
        "resource_type": "library", "resource_name": "Gateways", "resource_label": "gateways"},
    AUTH_PLATFORM_GPG: {
        "actions": ACTIONS_GPG,
        "resource_type": "library", "resource_name": "GPG", "resource_label": "gpg_keys"},
    AUTH_PLATFORM_INPUT_TYPE: {
        "actions": ACTIONS_INPUT_TYPE,
        "resource_type": "library", "resource_name": "InputTypes", "resource_label": "input_types"},
    AUTH_PLATFORM_INTENT: {
        "actions": ACTIONS_INTENT,
        "resource_type": "library", "resource_name": "Intents", "resource_label": "intents"},
    AUTH_PLATFORM_LOCATION: {
        "actions": ACTIONS_LOCATION,
        "resource_type": "library", "resource_name": "Locations", "resource_label": "locations"},
    AUTH_PLATFORM_MODULE: {
        "actions": ACTIONS_MODULE,
        "resource_type": "library", "resource_name": "Modules", "resource_label": "modules"},
    AUTH_PLATFORM_MODULE_DEVICE_TYPE: {
        "actions": ACTIONS_MODULE_DEVICE_TYPE,
        "resource_type": "library", "resource_name": "ModuleDeviceTypes", "resource_label": "module_device_types"},
    AUTH_PLATFORM_MQTT: {
        "actions": ACTIONS_MQTT,
        "resource_type": "library", "resource_name": "MQTT", "resource_label": "mqtt"},
    AUTH_PLATFORM_MQTTUSERS: {
        "actions": ACTIONS_MQTTUSERS,
        "resource_type": "library", "resource_name": "MQTTUsers", "resource_label": "mqtt_users"},
    AUTH_PLATFORM_MQTTYOMBO: {
        "actions": ACTIONS_MQTTYOMBO,
        "resource_type": "library", "resource_name": "MQTTYombo", "resource_label": "mqtt_yombo"},
    AUTH_PLATFORM_NODE: {
        "actions": ACTIONS_NODE,
        "resource_type": "library", "resource_name": "Nodes", "resource_label": "nodes"},
    AUTH_PLATFORM_NOTIFICATION: {
        "actions": ACTIONS_NOTIFICATION,
        "resource_type": "library", "resource_name": "Notifications", "resource_label": "notifications"},
    AUTH_PLATFORM_PERMISSION: {
        "actions": ACTIONS_PERMISSION,
        "resource_type": "library", "resource_name": "Permissions", "resource_label": "permissions"},
    AUTH_PLATFORM_ROLE: {
        "actions": ACTIONS_ROLE,
        "resource_type": "library", "resource_name": "Roles", "resource_label": "roles"},
    AUTH_PLATFORM_SCENE: {
        "actions": ACTIONS_SCENE,
        "resource_type": "library", "resource_name": "Scenes", "resource_label": "scenes"},
    AUTH_PLATFORM_STATE: {
        "actions": ACTIONS_STATE,
        "resource_type": "library", "resource_name": "States", "resource_label": "states"},
    AUTH_PLATFORM_STATISTIC: {
        "actions": ACTIONS_STATISTIC,
        "resource_type": "library", "resource_name": "Statistics", "resource_label": "statistics"},
    AUTH_PLATFORM_STORAGE: {
        "actions": ACTIONS_STORAGE,
        "resource_type": "library", "resource_name": "Storage", "resource_label": "storage"},
    AUTH_PLATFORM_SYSTEM_SETTING: {
        "actions": ACTIONS_SYSTEM_SETTING,
        "resource_type": None, "resource_name": None, "resource_label": None},
    AUTH_PLATFORM_SYSTEM_OPTION: {
        "actions": ACTIONS_SYSTEM_OPTION,
        "resource_type": None, "resource_name": None, "resource_label": None},
    AUTH_PLATFORM_TASK: {
        "actions": ACTIONS_TASK,
        "resource_type": "library", "resource_name": "Tasks", "resource_label": "tasks"},
    AUTH_PLATFORM_TIME: {
        "actions": ACTIONS_TIME,
        "resource_type": "library", "resource_name": "Times", "resource_label": "times"},
    AUTH_PLATFORM_USER: {
        "actions": ACTIONS_USER,
        "resource_type": "library", "resource_name": "Users", "resource_label": "users"},
    AUTH_PLATFORM_VARIABLE_DATA: {
        "actions": ACTIONS_VARIABLE_DATA,
        "resource_type": "library", "resource_name": "VariableData", "resource_label": "variable_data"},
    AUTH_PLATFORM_VARIABLE_FIELDS: {
        "actions": ACTIONS_VARIABLE_FIELDS,
        "resource_type": "library", "resource_name": "VariableFields", "resource_label": "variable_fields"},
    AUTH_PLATFORM_VARIABLE_GROUPS: {
        "actions": ACTIONS_VARIABLE_GROUPS,
        "resource_type": "library", "resource_name": "VariableGroups", "resource_label": "variable_groups"},
    AUTH_PLATFORM_WEBLOG: {
        "actions": ACTIONS_WEBLOG,
        "resource_type": None, "resource_name": None, "resource_label": None},
    AUTH_PLATFORM_WEBSESSION: {
        "actions": ACTIONS_WEBSESSION,
        "resource_type": "library", "resource_name": "WebSessions", "resource_label": "web_sessions"},
    AUTH_PLATFORM_WILDCARD: {
        "actions": ACTIONS_WILDCARD,
        "resource_type": None, "resource_name": None, "resource_label": None},
}
