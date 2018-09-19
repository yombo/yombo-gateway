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
        },
        'accepted': {
            'description': "Authentication request allowed",
            'attributes': (
                'platform',
                'item',
                'action',
            ),
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
        },
        'connected': {
            'description': "AMQP connection made.",
            'attributes': (
                'client_id',
            ),
        },
        'disconnected': {
            'description': "AMQP disconnected.",
            'attributes': (
                'client_id',
                'reason',
            ),
        },
    },
}
