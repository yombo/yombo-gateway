# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/modules/devices/>`_

The device class is responsible for managing a single device.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from __future__ import print_function
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

from time import time

# Import Yombo libraries
from yombo.core.log import get_logger
logger = get_logger('library.devices.device_request')

class Device_Request(object):
    """
    A class that manages requests for a given device. This class is instantiated by the
    device class. Librarys and modules can use this instance to get the details of a given
    request.
    """

    def __init__(self, request, device):
        """
        Get the instance setup.

        :param request: Basic details about the request to get started.
        :param Device: A pointer to the device instance.
        """
        self.device = device
        self.request_id = request['request_id']
        self.sent_time = request['sent_time']
        self.command = request['command']
        self.history = request['history']
        self.requested_by = request['requested_by']
        self.status = None
        self.sent_time = None
        self.received_time = None
        self.pending_time = None
        self.finished_time = None
        self.message = None
        self.set_status('new')

    def set_sent_time(self, sent_time=None):
        if sent_time is None:
            sent_time = time()
        self.sent_time = sent_time
        self.status = 'sent'
        self.history.append((sent_time, 'sent'))

    def set_received_time(self, finished_time=None):
        if finished_time is None:
            finished_time = time()
        self.finished_time = finished_time
        self.status = 'failed'
        self.history.append((finished_time, 'failed'))

    def set_pending_time(self, pending_time=None):
        if pending_time is None:
            pending_time = time()
        self.pending_time = pending_time
        self.status = 'pending'
        self.history.append((pending_time, 'pending'))

    def set_finished_time(self, finished_time=None):
        if finished_time is None:
            finished_time = time()
        self.finished_time = finished_time
        self.status = 'done'
        self.history.append((finished_time, 'done'))

    def set_failed_time(self, finished_time=None):
        if finished_time is None:
            finished_time = time()
        self.finished_time = finished_time
        self.status = 'failed'
        self.history.append((finished_time, 'failed'))

    def set_status(self, status):
        self.status = status
        self.history.append((time(), status))

    def set_message(self, message):
        self.message = message
        self.history.append((time(), message))
