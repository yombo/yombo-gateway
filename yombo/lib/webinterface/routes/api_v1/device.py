# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_good, return_not_found, return_error, return_unauthorized, args_to_dict
from yombo.utils import epoch_to_string, bytes_to_unicode, sleep

def route_api_v1_device(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route('/device', methods=['GET'])
        @require_auth(api=True)
        def apiv1_device_get(webinterface, request, session):
            return return_good(
                request,
                payload=webinterface._Devices.full_list_devices(),
            )

        @webapp.route('/device/<string:device_id>', methods=['GET'])
        @require_auth(api=True)
        def apiv1_device_details_get(webinterface, request, session, device_id):
            arguments = args_to_dict(request.args)

            if device_id in webinterface._Devices:
                device = webinterface._Devices[device_id]
            else:
                return return_not_found(request, 'device not found')

            payload = device.asdict()
            if 'item' in arguments:
                payload = payload[arguments['item']]
            return return_good(
                request,
                payload=payload
            )

        @webapp.route('/device/<string:device_id>/command/<string:command_id>', methods=['GET', 'POST'])
        @require_auth(api=True)
        @inlineCallbacks
        def apiv1_device_command_get_post(webinterface, request, session, device_id, command_id):
            try:
                wait_time = float(request.args.get('_wait')[0])
            except:
                wait_time = 2

            arguments = args_to_dict(request.args)

            if 'inputs' in arguments:
                inputs = arguments['inputs']
            else:
                inputs = None
            if device_id in webinterface._Devices:
                device = webinterface._Devices[device_id]
            else:
                return return_not_found(request, 'device not found')
            # print("inputs: %s" % inputs)
            try:
                request_id = device.command(
                    cmd=command_id,
                    requested_by={
                        'user_id': session.user_id,
                        'component': 'yombo.gateway.lib.webinterface.routes.api_v1.devices.device_command',
                        'gateway': webinterface.gateway_id()
                    },
                    inputs=inputs,
                    )
            except KeyError as e:
                return return_not_found(request, 'Error with command: %s' % e)

            DC = webinterface._Devices.device_commands[request_id]
            if wait_time > 0:
                exit_while = False
                start_time = time()
                while(start_time > (time() - wait_time) and exit_while is False):
                    yield sleep(.075)
                    if DC.status_id >= 100:
                        exit_while = True
            return return_good(
                request,
                payload={
                    'device_command_id': request_id,
                    'device_command': DC.asdict(),
                }
            )
