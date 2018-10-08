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
}
