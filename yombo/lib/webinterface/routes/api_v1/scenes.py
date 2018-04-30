# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_not_found, return_error
from yombo.utils import is_none

def route_api_v1_scene(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route('/scene/device_inputs', methods=['GET'])
        @require_auth(api=True)
        def apiv1_scenes_device_inputs_index(webinterface, request, session):
            def local_error(message):
                return "<tr><td colspan=4>%s</td><tr>\n" % message

            try:
                scene_id = request.args.get('scene_id')[0]
            except Exception:
                return local_error("The 'scene_id' is required.")
            try:
                scene = webinterface._Scenes[scene_id]
            except Exception:
                return local_error("The 'scene_id' cannot be found.")

            action_id = is_none(request.args.get('action_id', [None])[0])
            if action_id is None:
                action_details = None
            else:
                try:
                    action_details = webinterface._Scenes.get_action_items(scene_id, action_id)
                except Exception as e:
                    return local_error("The 'itemid' cannot be found.")

            try:
                device_machine_label = request.args.get('device_machine_label')[0]
            except Exception:
                return local_error("The 'device_machine_label' is required.")
            try:
                device = webinterface._Devices[device_machine_label]
            except Exception as e:
                return local_error("The 'deviceid' cannot be found.")

            try:
                command_machine_label = request.args.get('command_machine_label')[0]
            except Exception:
                return local_error("The 'command_machine_label' is required.")
            try:
                command = webinterface._Commands[command_machine_label]
            except Exception:
                return local_error("The 'command_machine_label' cannot be found.")

            available_commands = device.available_commands()

            if command.command_id not in available_commands:
                return local_error("Command ID is not valid for this device.")
            inputs = available_commands[command.command_id]['inputs']

            page = webinterface.get_template(request, webinterface._dir + 'pages/scenes/form_device_inputs.html')
            return page.render(
                alerts=webinterface.get_alerts(),
                inputs=inputs,
                action_details=action_details,
                )

        # @webapp.route('/scene/inputs', methods=['GET'])
        # @require_auth(api=True)
        # def apiv1_scenes_inputs_index(webinterface, request, session):
        #     """
        #     Gets input data for a given sceneid, device
        #     :param webinterface:
        #     :param request:
        #     :param session:
        #     :return:
        #     """
        #     try:
        #         device_id = request.args.get('deviceid')[0]
        #     except Exception:
        #         return return_error(request, "'deviceid' required.")
        #     try:
        #         device = webinterface._Devices[device_id]
        #     except Exception as e:
        #         return return_error(request, "'deviceid' cannot be found.")
        #     try:
        #         command_id = request.args.get('commandid')[0]
        #     except Exception:
        #         return return_error(request, "'commandid' required.")
        #     try:
        #         command = webinterface._Commands[command_id]
        #     except Exception:
        #         return return_error(request, "'commandid' cannot be found.")
        #
        #     try:
        #         scene_id = request.args.get('sceneid')[0]
        #     except Exception:
        #         return return_error(request, "'sceneid' required.")
        #     try:
        #         scene = webinterface._Scenes[scene_id]
        #     except Exception:
        #         return return_error(request, "'sceneid' cannot be found.")
        #
        #     available_commands = device.available_commands()
        #     command_inputs = available_commands[command_id]['inputs']
        #     items = webinterface._Scenes.get_action_items(scene_id)
        #     data = command_inputs
        #     # data = {
        #     #     'total': results['content']['pages']['total_items'],
        #     #     'rows': results['data'],
        #     # }
        #     request.setHeader('Content-Type', 'application/json')
        #     return json.dumps(data)
