"""
frg Constants for events library.
"""
SYSTEM_EVENT_TYPES = {
    "amqp": {
        "new": {
            "description": "New AMQP client created, but not connected yet.",
            "attributes": (
                "client_id",
                "host",
                "port",
                "username",
                "ssl",
            ),
            "expires": 2160,  # save events for 90 days
        },
        "connected": {
            "description": "AMQP connection made.",
            "attributes": (
                "client_id",
            ),
            "expires": 2160,  # save events for 90 days
        },
        "disconnected": {
            "description": "AMQP disconnected.",
            "attributes": (
                "client_id",
                "reason",
            ),
            "expires": 2160,  # save events for 90 days
        },
    },
    "atoms": {
        "set": {
            "description": "Set an atom",
            "attributes": (
                "name",
                "value",
                "value_human",
                "value_type",
                "gateway_id",
                "source",
            ),
            "expires": 8760,  # 365 days
        },
    },
    "auth": {
        "denied": {
            "description": "Authentication request failed",
            "attributes": (
                "platform",
                "item",
                "action",
            ),
            "expires": 2160,  # save events for 90 days
        },
        "accepted": {
            "description": "Authentication request allowed",
            "attributes": (
                "platform",
                "item",
                "action",
            ),
            "expires": 2160,  # save events for 90 days
        },
    },
    "authkey": {
        "new": {
            "description": "AuthKey created",
            "attributes": (
                "label",
                "description",
                "requested_by",
                "requested_by_type",
                "requested_context",
            ),
            "expires": 43800,  # save events for 5 years
        },
        "modified": {
            "description": "Modified key",
            "attributes": (
                "label",
                "description",
                "requested_by",
                "requested_by_type",
                "requested_context",
            ),
            "expires": 43800,  # save events for 5 years
        },
        "rotated": {
            "description": "Rotated key for security.",
            "attributes": (
                "requested_by",
                "requested_by_type",
                "requested_context",
            ),
            "expires": 43800,  # save events for 5 years
        },
        "removed": {
            "description": "AuthKey was removed",
            "attributes": (
                "requested_by",
                "requested_by_type",
                "requested_context",
            ),
            "expires": 43800,  # save events for 90 days
        },
    },
    "localdb": {
        "cleaning": {
            "description": "Tracks database cleaning events.",
            "attributes": (
                "action",
                "duration",
            ),
            "expires": 720,  # save events for 30 days
        },
        "connected": {
            "description": "SQLite connection details.",
            "attributes": (
                "start_schema_version",
                "last_schema_version",
            ),
            "expires": 720,  # save events for 30 days
        },
        "dbbackup": {
            "description": "Tracks database backup events.",
            "attributes": (
                "duration",
            ),
            "expires": 720,  # save events for 30 days
        },
    },
    "pip": {
        "installed": {
            "description": "Python package installed",
            "attributes": (
                "name",
                "version",
                "duration",
            ),
            "expires": 8760,  # 365 days
        },
        "not_found": {
            "description": "Python package not found, but was required..",
            "attributes": (
                "package_name",
            ),
            "expires": 8760,  # 365 days
        },
        "update_needed": {
            "description": "When a python package is old and about to updated.",
            "attributes": (
                "package_name",
                "current",
                "requested",
            ),
            "expires": 8760,  # 365 days
        },
    },
    "sslcerts": {
        "generate_new": {
            "description": "Generated a TLS certificate.",
            "attributes": (
                "name",
                "cn",
                "san",
                "duration",
            ),
            "expires": 8760,  # 365 days
        },
    },
    "states": {
        "set": {
            "description": "Set a state",
            "attributes": (
                "name",
                "value",
                "value_human",
                "value_type",
                "gateway_id",
                "source",
            ),
            "expires": 8760,  # 365 days
        },
    },

}
