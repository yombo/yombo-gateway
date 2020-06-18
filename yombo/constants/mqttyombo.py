"""
Constants for mqttyombo library.
"""
MQTT_PROTOCOL_VERSION = "4"

SUBSCRIPTION_IDS = {
    1000: "atoms",
    1100: "device_command",
    1200: "device_command_status",
    1300: "device_state",
    1400: "notification_add",
    1401: "notification_delete",
    1402: "notification_updated",
    1500: "states",
    2000: "online",
    2100: "offline",
    2200: "ping",
}

SUBSCRIPTION_NAMES = {
    "atoms": 1000,
    "device_command": 1100,
    "device_command_status": 1200,
    "device_state": 1300,
    "notification_add": 1400,
    "notification_delete": 1401,
    "notification_updated": 1402,
    "states": 1500,
    "online": 2000,
    "offline": 2100,
    "ping": 2200,
}

