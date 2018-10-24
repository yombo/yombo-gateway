"""
frg Constants for events library.
"""
SYSTEM_EVENT_TYPES = {
    'auth': {
        'denied': {
            'description': "Authentication request failed",
            'attributes': (
                'platform',
                'item',
                'action',
            ),
            'expires': 90,  # save events for 90 days
        },
        'accepted': {
            'description': "Authentication request allowed",
            'attributes': (
                'platform',
                'item',
                'action',
            ),
            'expires': 90,  # save events for 90 days
        },
    },
    'amqp': {
        'new': {
            'description': "New AMQP client created, but not connected yet.",
            'attributes': (
                'client_id',
                'host',
                'port',
                'username',
                'ssl',
            ),
            'expires': 90,  # save events for 90 days
        },
        'connected': {
            'description': "AMQP connection made.",
            'attributes': (
                'client_id',
            ),
            'expires': 90,  # save events for 90 days
        },
        'disconnected': {
            'description': "AMQP disconnected.",
            'attributes': (
                'client_id',
                'reason',
            ),
            'expires': 90,  # save events for 90 days
        },
    },
    'localdb': {
        'cleaning': {
            'description': "Tracks database cleaning events.",
            'attributes': (
                'action',
                'duration',
            ),
            'expires': 30,  # save events for 90 days
        },
        'connected': {
            'description': "SQLite connection details.",
            'attributes': (
                'start_schema_version',
                'last_schema_version',
            ),
            'expires': 30,  # save events for 90 days
        },
        'dbbackup': {
            'description': "Tracks database backup events.",
            'attributes': (
                'duration',
            ),
            'expires': 30,  # save events for 90 days
        },
    },
    'pip': {
        'installed': {
            'description': "Python package installed",
            'attributes': (
                'name',
                'version',
                'duration',
            ),
            'expires': 360,  # save events for 90 days
        },
        'not_found': {
            'description': "Python package not found, but was required..",
            'attributes': (
                'package_name',
            ),
            'expires': 360,  # save events for 90 days
        },
        'update_needed': {
            'description': "When a python package is old and about to updated.",
            'attributes': (
                'package_name',
                'current',
                'requested',
            ),
            'expires': 360,  # save events for 90 days
        },
    },
    'sslcerts': {
        'generate_new': {
            'description': "Generated a TLS certificate.",
            'attributes': (
                'name',
                'cn',
                'san',
                'duration',
                '',
            ),
            'expires': 360,  # save events for 90 days
        },
    },
}
