from yombo.lib.webinterface.auth import require_auth
from yombo.utils import is_none

def route_api_v1_automation(webapp):
    with webapp.subroute("/api/wi") as webapp:

        @webapp.route("/automation/device_inputs", methods=["GET"])
        @require_auth(api=True)
        def apiv1_automations_device_inputs_index(webinterface, request, session):
            session.has_access("automation", "*", "view")
            def local_error(message):
                return f"<tr><td colspan=4>message</td><tr>\n"

            try:
                rule_id = request.args.get("rule_id")[0]
                rule_id = webinterface._Validate.id_string(rule_id)
            except Exception:
                return local_error("The 'rule_id' is required.")
            try:
                rule = webinterface._Automation[rule_id]
            except Exception:
                return local_error("The 'rule_id' cannot be found.")

            action_id = is_none(request.args.get("action_id", [None])[0])
            if action_id is None:
                action_details = None
            else:
                try:
                    action_details = webinterface._Automation.get_action_items(rule_id, action_id)
                except Exception as e:
                    return local_error("The 'action_id' cannot be found.")

            try:
                device_machine_label = request.args.get("device_machine_label")[0]
            except Exception:
                return local_error("The 'device_machine_label' is required.")
            try:
                device = webinterface._Devices[device_machine_label]
            except Exception as e:
                return local_error("The 'device_machine_label' cannot be found.")

            try:
                command_machine_label = request.args.get("command_machine_label")[0]
            except Exception:
                return local_error("The 'command_machine_label' is required.")
            try:
                command = webinterface._Commands[command_machine_label]
            except Exception:
                return local_error("The 'command_machine_label' cannot be found.")

            available_commands = device.available_commands()

            if command.command_id not in available_commands:
                return local_error("Command ID is not valid for this device.")
            inputs = available_commands[command.command_id]["inputs"]

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/automation/form_action_device_inputs.html")
            return page.render(
                alerts=webinterface.get_alerts(),
                inputs=inputs,
                action_details=action_details,
                )
