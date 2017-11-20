# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_good, return_not_found, return_error, return_unauthorized
from yombo.utils import epoch_to_string, bytes_to_unicode

def route_api_v1_device(webapp):
    with webapp.subroute("/api/v1") as webapp:


        @webapp.route('/device', methods=['GET'])
        @require_auth(api=True)
        def apiv1_device_get(webinterface, request, session):
            return return_good(request, payload=webinterface._Devices.full_list_devices())

        @webapp.route('/device/<string:device_id>/command/<string:command_id>', methods=['GET', 'POST'])
        @require_auth(api=True)
        def apiv1_device_command_get_post(webinterface, request, session, device_id, command_id):
            json_output = bytes_to_unicode(request.args.get('json_output', ["{}"])[0])
            # print("json_output  %s" % json_output)
            # print("json_output type: %s" % type(json_output))
            json_output = json.loads(json_output)
            inputs = json_output.get('inputs', {})

            if device_id in webinterface._Devices:
                device = webinterface._Devices[device_id]
            else:
                return return_not_found(request, 'device not found')

            try:
                device.command(
                    cmd=command_id,
                    requested_by={
                        'user_id': session['auth_id'],
                        'component': 'yombo.gateway.lib.WebInterface.api_v1.devices_get',
                        'gateway': webinterface.gateway_id()
                    },
                    inputs=inputs,
                    )
                a = return_good(request, 'Command executed.')
                request.setHeader('Content-Type', 'application/json')
                return json.dumps(a)
            except KeyError as e:
                return return_not_found(request, 'Error with command: %s' % e)