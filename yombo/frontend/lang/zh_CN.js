export default {
  "commands": {
    "close": {
      "description": "Close something.",
      "label": "关"
    }
  },
  "config": {
    "config_item": {
      "amqpyombo": {
        "port": "The AQMP port that Yombo AQMP connects to."
      },
      "amqpyombo:hostname": "AMQP Yombo server name to connect to.",
      "core": {
        "default_lang": "The default system language.",
        "environment": "Which environment this system connects to. One of: production, staging, development.",
        "externalipaddress": "Current external IP address, what the internet sees.",
        "first_run": "Used to help determine if this is the first time the gateway as run.",
        "gwhash": "The secret key of the gateway. Used by the gateway to authenticate to the server.",
        "gwid": "An ID that identifies this gateway to anyone. Notice: This ID change.",
        "gwuuid": "The ID of the gateway. Should not give this out freely, but not a secret.",
        "internalipaddress": "Current internal IP address, what the local network sees.",
        "module_domain": "A domain which the modules should be downloaded from."
      },
      "gpg": {
        "keyid": "GPG Key ID. This should be used by other devices wishing to send this gateway secrets. Or used to store secrets in the database."
      },
      "localize": {
        "hashes": "Store hasing information on the locale files. Used to determine if locale files need to be rebuilt."
      },
      "location": {
        "elevation": "Elevation of the gateway, in feet.",
        "latitude": "Latitude of the gateway.",
        "longitude": "Longitude of the gateway."
      },
      "mqtt": {
        "client_enabled": "When True, allows client connections to be made externally.",
        "server_allow_anonymous": "Allow un-authenticated users. To add users, edit the yombo.ini file, add useds to 'mtqq_users' section.",
        "server_enabled": "When True, starts the MQTT broker.",
        "server_listen_ip": "The IP address to bind to. For security reasons, the default only allows connections from the local machine. Change to the IP address of the local machine or network card to allow from only that network card. Or, us '0.0.0.0 to allow from all network sources.",
        "server_listen_port": "MQTT Non-secure (non-ssl) port to listen on. 0 = disabled.  Use non-secure port only when connecting to the local machine. Using the non-secure port for local connections reduces load on CPU for low-powered devices.",
        "server_listen_port_le_ssl": "MQTT Lets encrypt cert port.",
        "server_listen_port_ss_ssl": "MQTT Self-Signed cert port.",
        "server_listen_port_websockets": "WS port to listen on.",
        "server_listen_port_websockets_le_ssl": "WSS Lets Encrypt secure port.",
        "server_listen_port_websockets_ss_ssl": "WSS Self-Signed cert secure port.",
        "server_max_connections": "Max connections allowed on the MQTT broker. Sets 'max_connections' for the MQTT broker configs.",
        "server_timeout_disconnect_delay": "MQTT broker timeout disconnect. Sets 'timeout_disconnect_delay' for the MQTT broker configs.",
        "yombo_mqtt_password": "Yombo's mqtt password. You shouldn't use this password so it can be easily rotated."
      },
      "sqldict": {
        "save_interval": "How many seconds between saving the dictionaries to SQL."
      },
      "statistics": {
        "anonymous": "Allow collection of anaonymous statistics. If enabled, will allow upload regardless of 'upload' enabled for private statistics.",
        "averages_bucket_duration": "How minutes of information to collect for average based time buckets.",
        "averages_bucket_life_daily": "How many days to history to keep daily resolution statistics for average collections.",
        "averages_bucket_life_full": "How many days of history to keep full detailed statistics for average collections.",
        "averages_bucket_life_hourly": "How many days to history to keep hourly resolution statistics for average collections.",
        "averages_bucket_life_qtr_hour": "How many days of history to keep 15 minute resolution statistics for average collections.",
        "count_bucket_duration": "How minutes of information to collect for count based time buckets.",
        "count_bucket_life_daily": "How many days to history to keep daily resolution statistics for basic counters.",
        "count_bucket_life_full": "How many days of history to keep full detailed statistics for basic counters.",
        "count_bucket_life_hourly": "How many days to history to keep hourly resolution statistics for basic counters.",
        "count_bucket_life_qtr_hour": "How many days of history to keep 15 minute resolution statistics for basic counters.",
        "datapoint_bucket_life_daily": "How many days to history to keep daily averaged statistics for specific datapoints.",
        "datapoint_bucket_life_full": "How many days of history to keep full detailed statistics for specific datapoints.",
        "datapoint_bucket_life_hourly": "How many days to history to keep hourly averaged statistics for specific datapoints.",
        "datapoint_bucket_life_qtr_hour": "How many days of history to keep 15 minute averaged statistics for specific datapoints.",
        "enabled": "Enable or disable entire library. When disabled, calls still work, nothing actually done.",
        "time_between_saves": "Seconds between datasaves. Stats are collected and processed in memory memeory before being dumped. Longer is better for averages, but at a risk to dataloss.",
        "time_between_saves_averages": "For averages, how many seconds between data saves from memory to disk. Longer is better for averages, but at a risk to dataloss.",
        "upload": "Allow uploading of statistics to Yombo servers"
      },
      "times": {
        "twilighthorizon": "How many degrees below the horizon must the sun be before it's considered dark. Civil = -6, Nautical = -12, Astronomical = -18"
      },
      "webinterface": {
        "auth_pin_totp": "When using TOTP for additional security, it's token is stored here.",
        "cookie_session": "Name of the cookie used in browsers.",
        "enabled": "If True (or: on, 1), then the web interface will be started."
      },
      "yomboapi": {
        "allow_system_session": "Allows the gateway to store admin credentials in a hashed form to make calls on behalf of itself. This allows the gateway make changes to various items without admin input.",
        "api_key": "API密钥在提出请求时使用。注意：该键将旋转以防止滥用。",
        "baseurl": "URL to prepend requests to.",
        "contenttype": "Sets the header of Content-Type in the request to Yombo API system",
        "sessionid_id": "When allow_system_session is true, this is used for logging into the API.",
        "sessionid_key": "当allow_system_session为true时，这用于登录到API。"
      }
    },
    "config_section": {
      "amqpyombo": "Items specific to the AMQPYombo library.",
      "core": "Core components of the gateway. Required items needed to run ths system, most with no defaults",
      "localize": "Items specific to the localize library.",
      "location": "Location information about the gateway. Used for calculating light\/dark, sunrise, etc.",
      "logging": "Allows fine grained control of console logging. See https:\/\/yombo.net\/docs\/gateway\/logging for details.",
      "mqtt": "Items specific to the statistics library.",
      "rbac_roles": "Role Based Access Control - User roles. Stores user create roles here. These fields are not meant to be directly edited.",
      "rbac_user_roles": "Role Based Access Control - Roles and device permissions for users. These fields are not meant to be directly edited.",
      "sqldict": "Specific items relating to the SQLDict library.",
      "sslcerts": "Stores some SSL certificate information here. Primary storage location is the database.",
      "statistics": "Items specific to the statistics library.",
      "system_modules": "Controls where system modules are loaded or not.",
      "times": "Items specific to the times library.",
      "webinterface": "Web interface configuration.",
      "yomboapi": "API related items for communicating with remote Yombo API system."
    }
  },
  "device_platform": {
    "alarm_control_panel": "Alarm control panel",
    "calendar": "Calendar",
    "camera": "Camera",
    "climate": "Climate",
    "configurator": "Configurator",
    "conversation": "Conversation",
    "cover": "Cover",
    "device_tracker": "Device tracker",
    "digital_sensor": "Digital sensor",
    "fan": "Fan",
    "group": "Group",
    "history_graph": "History graph",
    "image_processing": "Image processing",
    "light": "Light",
    "lock": "Lock",
    "mailbox": "Mailbox",
    "media_player": "Media player",
    "notify": "Notify",
    "plant": "Plant",
    "proximity": "Proximity",
    "remote": "Remote",
    "scene": "Scene",
    "script": "Script",
    "sensor": "Sensor",
    "sun": "Sun",
    "switch": "Switch",
    "updater": "Updater",
    "weblink": "Weblink"
  },
  "lib": {
    "atom": {
      "cpu.count": "Number of CPUs (cores) gateway has.",
      "mem.total": "Total memory on gateway.",
      "os": "Operating system type.",
      "os.codename": "OS Codename.",
      "os.family": "Family OS belongs to.",
      "os.fullname": "Fullname of the OS platform.",
      "os.kernel": "System kernel information."
    },
    "configs": {
      "yombo.ini": {
        "about": "This file stores configuration information about the gateway.",
        "dont_edit": "WARNING: Do not edit this file while the gateway is running, any changes will be lost.",
        "still_running": "It appears the Yombo gateway still running. All changes will be lost!",
        "still_running_pid": "Yombo process id (PID): {number}"
      }
    },
    "state": {
      "amqp.amqpyombo.state": "如果连接则为真，如果连接未完全建立，则为假。",
      "is.dark": "True if it's dark. The sun is below 'twilighthorizon'.",
      "is.dawn": "True is sun is rising and above 'twilighthorizon', but below horizon.",
      "is.day": "True if it's daytime. Day time is when sun is above horizon.",
      "is.dusk": "True is sun is setting and above 'twilighthorizon', but below horizon.",
      "is.light": "True if it's light. This includes sun above 'twilighthorizon' and includes sun above horizon.",
      "is.night": "True if it's dark. Night time is when sun is below horizon.",
      "is.twilight": "True if it's twilight. Sun his below horizon, but less then 'twilighthorizon' below the horizon.",
      "loader.operating_mode": "The mode the system is in. One of: first_run, config, run",
      "localize.default_language": "Default language system is currently set to.",
      "next.moonrise": "When the next moon rise is.",
      "next.moonset": "When the next moon set is.",
      "next.sunrise": "When the next time sun is at the horizon, and rising.",
      "next.sunset": "When the next time sun is at the horizon, and setting."
    }
  },
  "lokalise.po.header": "\"MIME-Version: 1.0\\n\"\n\"Content-Type: text\/plain; charset=UTF-8\\n\"\n\"Content-Transfer-Encoding: 8bit\\n\"\n\"X-Generator: lokalise.co\\n\"\n\"Project-Id-Version: Yombo Frontend\\n\"\n\"Report-Msgid-Bugs-To: translate@yombo.net\\n\"\n\"POT-Creation-Date: 2016-10-28 17:12-0400\\n\"\n\"Last-Translator: Mitch Schwenk <translate@yombo.net>\\n\"\n\"Language: en\\n\"\n\"Plural-Forms: nplurals=2; plural=(n!=1);\\n\"",
  "panel": {
    "calendar": "Calendar",
    "config": "Configuration",
    "dev-events": "Events",
    "dev-info": "Info",
    "dev-mqtt": "MQTT",
    "dev-services": "Services",
    "dev-states": "States",
    "dev-templates": "Templates",
    "history": "History",
    "logbook": "Logbook",
    "mailbox": "Mailbox",
    "map": "Map",
    "shopping_list": "Shopping list",
    "states": "Overview"
  },
  "state": {
    "alarm_control_panel": {
      "armed": "Armed",
      "armed_away": "Armed away",
      "armed_custom_bypass": "Armed custom bypass",
      "armed_home": "Armed home",
      "armed_night": "Armed night",
      "arming": "Arming",
      "disarmed": "Disarmed",
      "disarming": "Disarming",
      "pending": "Pending",
      "triggered": "Triggered"
    },
    "automation": {
      "off": "Off",
      "on": "On"
    },
    "calendar": {
      "off": "Off",
      "on": "On"
    },
    "camera": {
      "idle": "Idle",
      "recording": "Recording",
      "streaming": "Streaming"
    },
    "climate": {
      "auto": "Auto",
      "cool": "Cool",
      "cool_1": "Cool stage 1",
      "dry": "Dry",
      "eco": "Eco",
      "electric": "Electric",
      "fan_only": "Fan only",
      "gas": "Gas",
      "heat": "Heat",
      "heat_1": "Heat stage 1",
      "heat_2": "Heat stage 2",
      "heat_3": "Heat stage 3",
      "heat_pump": "Heat pump",
      "high_demand": "High demand",
      "idle": "Idle",
      "off": "Off",
      "on": "On",
      "performance": "Performance"
    },
    "cover": {
      "closed": "Closed",
      "closing": "Closing",
      "open": "Open",
      "opening": "Opening",
      "stopped": "Stopped"
    },
    "default": {
      "off": "关闭",
      "on": "开启",
      "open": "开启",
      "opening": "正在打开",
      "running": "Running",
      "stopped": "已停止",
      "unavailable": "不可用",
      "unknown": "Unknown"
    },
    "device_tracker": {
      "home": "Home",
      "not_home": "Away"
    },
    "digital_sensor": {
      "battery": {
        "off": "Normal",
        "on": "Low"
      },
      "cold": {
        "off": "Off",
        "on": "Cold"
      },
      "connectivity": {
        "off": "Disconnected",
        "on": "Connected"
      },
      "default": {
        "off": "Off",
        "on": "Off"
      },
      "door": {
        "off": "Closed",
        "on": "Open"
      },
      "garage_door": {
        "off": "Closed",
        "on": "Open"
      },
      "gas": {
        "off": "Clear",
        "on": "Detected"
      },
      "heat": {
        "off": "Off",
        "on": "Hot"
      },
      "lock": {
        "off": "Locked",
        "on": "Unlocked"
      },
      "moisture": {
        "off": "Dry",
        "on": "Wet"
      },
      "motion": {
        "off": "Off",
        "on": "On"
      },
      "occupancy": {
        "off": "Off",
        "on": "On"
      },
      "opening": {
        "off": "Closed",
        "on": "Open"
      },
      "presence": {
        "off": "Away",
        "on": "Home"
      },
      "problem": {
        "off": "OK",
        "on": "Problem"
      },
      "safety": {
        "off": "Safe",
        "on": "Unsafe"
      },
      "smoke": {
        "off": "Off",
        "on": "On"
      },
      "sound": {
        "off": "Off",
        "on": "On"
      },
      "vibration": {
        "off": "Off",
        "on": "On"
      },
      "window": {
        "off": "Closed",
        "on": "Open"
      }
    },
    "fan": {
      "off": "Off",
      "on": "On"
    },
    "group": {
      "closed": "Closed",
      "closing": "Closing",
      "home": "Home",
      "locked": "Locked",
      "not_home": "Away",
      "off": "Off",
      "ok": "Ok",
      "on": "On",
      "open": "Open",
      "opening": "Opening",
      "problem": "Problem",
      "stopped": "Stopped",
      "unlocked": "Unlocked"
    },
    "light": {
      "off": "Off",
      "on": "On"
    },
    "lock": {
      "locked": "Locked",
      "unlocked": "Unlocked"
    },
    "media_player": {
      "idle": "Idle",
      "off": "Off",
      "on": "On",
      "paused": "Paused",
      "playing": "Playing",
      "standby": "Standby"
    },
    "plant": {
      "ok": "Off",
      "problem": "On"
    },
    "remote": {
      "off": "Off",
      "on": "On"
    },
    "scene": {
      "scening": "Scening"
    },
    "script": {
      "off": "Off",
      "on": "On"
    },
    "sensor": {
      "off": "Off",
      "on": "On"
    },
    "sun": {
      "above_horizon": "Above horizon",
      "below_horizon": "Below horizon"
    },
    "switch": {
      "off": "Off",
      "on": "ON"
    },
    "weather": {
      "clear_night": "Clear, night",
      "cloudy": "Cloudy",
      "fog": "Fog",
      "hail": "Hail",
      "lightning": "Lightning",
      "lightning_rainy": "Lightning, rainy",
      "partlycloudy": "Partly cloudy",
      "pouring": "Pouring",
      "rainy": "Rainy",
      "snowy": "Snowy",
      "snowy_rainy": "Snowy, rainy",
      "sunny": "Sunny",
      "windy": "Windy",
      "windy_variant": "Windy"
    },
    "zwave": {
      "default": {
        "dead": "Dead",
        "initializing": "Initializing",
        "ready": "Ready",
        "sleeping": "Sleeping"
      },
      "query_stage": {
        "dead": "Dead ({query_stage})",
        "initializing": "Initializing ({query_stage})"
      }
    }
  },
  "system": {
    "current_language": "中文 (Simplified)"
  },
  "ui": {
    "alerts": {
      "devices": {
        "invalid_fan_direction": "Invalid fan direction.",
        "invalid_fan_speed": "Invalid fan speed."
      },
      "messages": {
        "none": "No alerts"
      }
    },
    "card": {
      "alarm_control_panel": {
        "arm_away": "离家警戒",
        "arm_home": "在家警戒",
        "clear_code": "Clear",
        "code": "Code",
        "disarm": "Disarm",
        "title": "Alarm Panel"
      },
      "automation": {
        "last_triggered": "Last triggered",
        "title": "Automation",
        "trigger": "Trigger"
      },
      "camera": {
        "not_available": "Image not available"
      },
      "climate": {
        "aux_heat": "Aux heat",
        "away_mode": "Away mode",
        "currently": "Currently",
        "fan_mode": "Fan mode",
        "on_off": "On \/ off",
        "operation": "Operation",
        "swing_mode": "Swing mode",
        "target_humidity": "Target humidity",
        "target_temperature": "Target temperature"
      },
      "cover": {
        "position": "Position",
        "tilt_position": "Tilt position"
      },
      "fan": {
        "direction": "Direction",
        "oscillate": "Oscillate",
        "speed": "Speed"
      },
      "light": {
        "brightness": "Brightness",
        "color_temperature": "Color temperature",
        "effect": "Effect",
        "white_value": "White value"
      },
      "lock": {
        "code": "Code",
        "lock": "Lock",
        "unlock": "Unlock"
      },
      "media_player": {
        "sound_mode": "Sound mode",
        "source": "Source",
        "text_to_speak": "Text to speak"
      },
      "persistent_notification": {
        "dismiss": "Dismiss"
      },
      "scene": {
        "activate": "Activate"
      },
      "script": {
        "execute": "Execute"
      },
      "weather": {
        "attributes": {
          "air_pressure": "Air pressure",
          "humidity": "Humidity",
          "temperature": "Temperature",
          "visibility": "Visibility",
          "wind_speed": "Wind speed"
        },
        "forecast": "Forecast"
      }
    },
    "cardinal_direction": {
      "e": "E",
      "ene": "ENE",
      "ese": "ESE",
      "n": "N",
      "ne": "NE",
      "nne": "NNE",
      "nnw": "NNW",
      "nw": "NW",
      "s": "S",
      "se": "SE",
      "sse": "SSE",
      "ssw": "SSW",
      "sw": "SW",
      "w": "W",
      "wnw": "WNW",
      "wsw": "WSW"
    },
    "common": {
      "add": "Add",
      "allow": "Allow",
      "cancel": "Cancel",
      "close": "Close",
      "current_language": "Current Language",
      "deleted": "Deleted",
      "deny": "Deny",
      "disable": "禁用",
      "disabled": "Disabled",
      "discovered": "Discovered",
      "documentation": "Documentation",
      "edit": "Edit",
      "email": "E-Mail",
      "enable": "启用",
      "enabled": "启用",
      "info": "Info",
      "list": "List",
      "loading": "Loading",
      "name": "Name",
      "none": "没有",
      "number_devices_on": "There is {num} device turned on|There are {num} devices turned on",
      "private": "Private",
      "public": "Public",
      "public_pending": "Public pending",
      "restart": "Restart",
      "roles": "Roles",
      "rules": "Rules",
      "save": "Save",
      "shutdown": "Shutdown",
      "users": "Users"
    },
    "common:enable": "Enable",
    "form": {
      "login": {
        "log_in": "Log in",
        "password": "Password",
        "remember": "Remember"
      }
    },
    "greeting": {
      "welcome": "欢迎"
    },
    "header": {
      "basic_information": "Basic Information"
    },
    "label": {
      "modules": "Modules",
      "states": "States"
    },
    "messages": {
      "rate_limit_exceeded": "Too many attempts, try again later."
    },
    "misc": {
      "allowed_next_change": "Allowed next change",
      "current_fqdn": "Current FQDN",
      "current_sub_domain": "Current Sub-domain",
      "current_top_level_domain": "Current Domain"
    },
    "navigation": {
      "about": "关于",
      "add": "加",
      "api_auth": "API Auth",
      "atoms": "Atoms",
      "automation": "自动化",
      "backup": "备份",
      "basic_settings": "Basic Settings",
      "control": "Control",
      "control_tower": "控制塔",
      "crontab": "CronTab",
      "dashboard": "仪表板",
      "debug": "Debug",
      "delayed_commands": "Delayed Commands",
      "developer_tools": "Developer tools",
      "device_commands": "Device Commands",
      "devices": "Devices",
      "discovery": "Discovery",
      "dns": "DNS",
      "encryption": "Encryption",
      "encryption_keys": "Encryption Keys",
      "events": "Events",
      "frontend_settings": "Frontend Settings",
      "gateways": "Gateways",
      "general": "General",
      "home": "Home",
      "http_event_stream": "HTTP Event Stream",
      "info": "Info",
      "intents": "Intents",
      "lang": "Lang",
      "language": "Language",
      "list": "List",
      "locations": "Locations",
      "lockscreen": "Lock Screen",
      "logout": "Logout",
      "module_settings": "Module Settings",
      "modules": "Modules",
      "monitor": "Monitor",
      "more": "More",
      "overview": "Overview",
      "panel": "Panel",
      "permissions": "Permissions",
      "restart_gateway": "Restart Gateway",
      "roles": "Roles",
      "rules": "Rules",
      "scenes": "Scenes",
      "send": "Send",
      "settings": "Settings",
      "states": "States",
      "statistics": "Statistics",
      "status": "Status",
      "storage": "Storage",
      "system": "System",
      "system_settings": "System Settings",
      "users": "Users",
      "web_logs": "Web Logs",
      "yombo_ini": "Yombo.ini"
    },
    "notifications": {
      "warning": "Warning"
    },
    "pages": {
      "home": {
        "controltower": "Additionally, use the {controltower} as a control display for all your automation devices.",
        "dashboard": "Use the {dashboard} to manage the gateway, including any automation devices, rules, and scenes.",
        "welcome": "Welcome to the Yombo Gateway Frontend."
      }
    },
    "relative_time": {
      "future": "In {time}",
      "never": "Never",
      "past": "{time} ago"
    },
    "user": {
      "log_out": "Log out",
      "profile": "User profile"
    }
  }
}