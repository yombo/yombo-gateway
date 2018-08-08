# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_good, return_not_found, return_error, return_unauthorized, args_to_dict
from yombo.utils.converters import epoch_to_string

def route_api_v1_device_command(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route('/device_command/<string:device_command_id>', methods=['GET'])
        @require_auth(api=True)
        def apiv1_device_do_command_get_post(webinterface, request, session, device_command_id):
            session.has_access('device_command', device_command_id, 'view', raise_error=True)
            if device_command_id in webinterface._Devices.device_commands:
                device_command = webinterface._Devices.device_commands[device_command_id]
                return return_good(
                    request,
                    payload=device_command.asdict()
                )

            return return_not_found(request, 'Error with device command id: %s' % device_command_id)
