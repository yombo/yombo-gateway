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
}
