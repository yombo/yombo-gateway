# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This handler library is responsible for handling control messages received from amqpyombo library.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/handler/amqpcontrol.py>`_
"""
# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

# Import twisted libraries

# Import 3rd party extensions

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger('library.handler.amqpcontrol')


class AmqpControlHandler(YomboLibrary):
    """
    Handles interactions with Yombo servers through the AMQP library.
    """

    def __init__(self, amqpyombo):
        """
        Loads various variables and calls :py:meth:connect() when it's ready.

        :return:
        """
        self.parent = amqpyombo
        self._Devices = self.parent._Devices

    def process_control(self, msg, headers):
        request = msg['request']
        # print request
        device_id = request['device']['id']

        if device_id in self._Devices:
            device = self._Devices[request['device']['id']]
            device.do_command(request['command']['id'])