# Import python libraries
from time import time

from twisted.internet.defer import inlineCallbacks

from yombo.classes.jsonapi import JSONApi
from yombo.constants.permissions import AUTH_PLATFORM_DEVICE, AUTH_PLATFORM_DEVICE_STATE
from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import get_session
from yombo.lib.webinterface.routes.api_v1.__init__ import return_not_found, return_error, request_args
from yombo.utils import sleep


def route_api_v1_devices(webapp):
    with webapp.subroute("/api/v1/lib") as webapp:

        @webapp.route("/devices/states", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_states_get(webinterface, request, session):
            """ Get all devices' state. """
            session.is_allowed(AUTH_PLATFORM_DEVICE_STATE, "view")
            devices = webinterface._Devices.devices
            states = []
            for device_id, device in devices.items():
                if device.status == 2:
                    continue
                states.append(device.state_all)
            return webinterface.render_api(request,
                                           data=JSONApi(states),
                                           data_type="device_states",
                                           )

        @webapp.route("/devices/<string:device_id>/states", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_states_details_get(webinterface, request, session, device_id):
            """ Gets a single device state. """
            webinterface._Validate.id_string(device_id)
            session.is_allowed(AUTH_PLATFORM_DEVICE_STATE, "view")
            device = webinterface._Devices.get(device_id)
            return webinterface.render_api(request,
                                           data=JSONApi(device.state_all),
                                           data_type="device_states",
                                           )

        @webapp.route("/devices/<string:device_id>/command/<string:command_id>", methods=["GET", "POST"])
        @get_session(auth_required=True, api=True)
        @inlineCallbacks
        def apiv1_devices_command_get_post(webinterface, request, session, device_id, command_id):
            webinterface._Validate.id_string(device_id)
            webinterface._Validate.id_string(command_id)
            session.is_allowed(AUTH_PLATFORM_DEVICE, "control", device_id)

            try:
                wait_time = float(request.args.get("_wait")[0])
            except:
                wait_time = 2

            print(f"rrequest.content.read(): {request.content.read()}")
            print(f"request.processed_body: {request.processed_body}")
            print(f"request.processed_body_encoding: {request.processed_body_encoding}")
            print(f"request.args: {request.args}")
            if request.processed_body is not None:
                arguments = request.processed_body
            else:
                arguments = request_args(request)

            pin_code = arguments.get("pin_code", None)
            delay = arguments.get("delay", None)
            max_delay = arguments.get("max_delay", None)
            not_before = arguments.get("not_before", None)
            not_after = arguments.get("not_after", None)
            inputs = arguments.get("inputs", None)

            if device_id in webinterface._Devices:
                device = webinterface._Devices[device_id]
            else:
                return return_not_found(request, "Device id not found")

            if command_id in webinterface._Commands:
                command = webinterface._Commands[command_id]
            else:
                return return_not_found(request, "Command id not found")
            print(f"device control, input: {inputs}")
            try:
                device_command_id = yield device.command(
                    command=command,
                    authentication=session,
                    pin=pin_code,
                    delay=delay,
                    max_delay=max_delay,
                    not_before=not_before,
                    not_after=not_after,
                    inputs=inputs,
                    request_context=f"api/v1:{request.getClientIP()}"
                    # idempotence=request.idempotence,
                )
            except KeyError as e:
                print(f"error with apiv1_device_command_get_post keyerror: {e}")
                return return_not_found(request, f"Error with command, it is not found: {e}")
            except YomboWarning as e:
                print(f"error with apiv1_device_command_get_post warning: {e}")
                return return_error(request, f"Error with command: {e}")

            DC = webinterface._DeviceCommands.device_commands[device_command_id]
            if wait_time > 0:
                exit_while = False
                start_time = time()
                while(start_time > (time() - wait_time) and exit_while is False):
                    yield sleep(.075)
                    if DC.status_id >= 100:
                        exit_while = True

            if len(device.state_history) > 0:
                status_current = device.state_history[0].to_dict(include_meta=False)
            else:
                status_current = None

            if len(device.state_history) > 1:
                status_previous = device.state_history[1].to_dict(include_meta=False)
            else:
                status_previous = None

            return webinterface.render_api(request,
                                           data=JSONApi(data={
                                               "type": device_command_id,
                                               "id": device_command_id,
                                               "attributes": {
                                                   "id": device_command_id,
                                                   "device_id": device.device_id,
                                                   "command_id": DC.command_id,
                                                   "device_command_id": device_command_id,
                                                   "device_command": DC.to_dict(include_meta=False),
                                                   "status_current": status_current,
                                                   "status_previous": status_previous,
                                                   }
                                               }),
                                           data_type="device_commands",
                                           )
