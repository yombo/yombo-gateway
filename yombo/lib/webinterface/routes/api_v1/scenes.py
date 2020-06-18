from yombo.classes.jsonapi import JSONApi
from yombo.constants.permissions import AUTH_PLATFORM_SCENE
from yombo.lib.webinterface.auth import get_session


def route_api_v1_scenes(webapp):
    with webapp.subroute("/api/v1") as webapp:
        pass
        # @webapp.route("/scenes", methods=["GET"])
        # @get_session(auth_required=True, api=True)
        # def apiv1_scenes_get(webinterface, request, session):
        #     """ Gets the system scenes. """
        #     session.is_allowed(AUTH_PLATFORM_SCENE, "view")
        #     return webinterface.render_api(request,
        #                                    data=JSONApi(webinterface._Scenes.get_all()),
        #                                    data_type="scenes",
        #                                    )
        #
        # @webapp.route("/scenes/<string:scene_id>", methods=["GET"])
        # @get_session(auth_required=True, api=True)
        # def apiv1_scenes_byid_get(webinterface, request, session, rule_id):
        #     """ Get a single scene by it's ID. """
        #     webinterface._Validate.id_string(rule_id)
        #     session.is_allowed(AUTH_PLATFORM_SCENE, "view", rule_id)
        #     return webinterface.render_api(request,
        #                                    data=JSONApi(webinterface._Scenes.get_all()),
        #                                    data_type="rules",
        #                                    attributes=webinterface._Scenes.get(rule_id)
        #                                    )

        # @webapp.route("/device_inputs", methods=["GET"])
        # @get_session(auth_required=True, api=True)
        # def apiv1_scenes_device_inputs_index(webinterface, request, session):
        #     webinterface._Validate.id_string(rule_id)
        #     session.is_allowed(AUTH_PLATFORM_SCENE, "edit", rule_id)
        #     session.has_access("scene", "*", "view", raise_error=True)
        #
        #     def local_error(message):
        #         return f"<tr><td colspan=4>{message}</td><tr>\n"
        #
        #     try:
        #         scene_id = request.args.get("scene_id")[0]
        #     except Exception:
        #         return local_error("The 'scene_id' is required.")
        #     try:
        #         scene = webinterface._Scenes[scene_id]
        #     except Exception:
        #         return local_error("The 'scene_id' cannot be found.")
        #
        #     action_id = is_none(request.args.get("action_id", [None])[0])
        #     if action_id is None:
        #         action_details = None
        #     else:
        #         try:
        #             action_details = webinterface._Scenes.get_action_items(scene_id, action_id)
        #         except Exception as e:
        #             return local_error("The 'itemid' cannot be found.")
        #
        #     try:
        #         device_machine_label = request.args.get("device_machine_label")[0]
        #     except Exception:
        #         return local_error("The 'device_machine_label' is required.")
        #     try:
        #         device = webinterface._Devices[device_machine_label]
        #     except Exception as e:
        #         return local_error("The 'deviceid' cannot be found.")
        #
        #     try:
        #         command_machine_label = request.args.get("command_machine_label")[0]
        #     except Exception:
        #         return local_error("The 'command_machine_label' is required.")
        #     try:
        #         command = webinterface._Commands[command_machine_label]
        #     except Exception:
        #         return local_error("The 'command_machine_label' cannot be found.")
        #
        #     available_commands = device.available_commands()
        #
        #     if command.command_id not in available_commands:
        #         return local_error("Command ID is not valid for this device.")
        #     inputs = available_commands[command.command_id]["inputs"]
        #
        #     page = webinterface.get_template(request, webinterface.wi_dir + "/pages/scenes/form_device_inputs.html")
        #     return page.render(
        #         alerts=session.get_alerts(),
        #         inputs=inputs,
        #         action_details=action_details,
        #         )
