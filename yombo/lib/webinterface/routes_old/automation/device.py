# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the device handling for /automation sub directory.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.19.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/routes/automation.py>`_
"""
import json

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.routes.automation.device")


def route_automation_device(webapp):
    with webapp.subroute("/automation") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/automation/index", "Automation Rule")

        @webapp.route("/<string:rule_id>/set_trigger_device", methods=["GET"])
        @require_auth()
        def page_automation_trigger_set_device_get(webinterface, request, session, rule_id):
            session.has_access("automation", rule_id, "edit", raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/automation/index")
            rule_id = rule.rule_id
            device_machine_label = ""

            trigger_data = rule.data["trigger"]
            if trigger_data["trigger_type"] == "device":
                if "device_machine_label" in trigger_data:
                    device_machine_label = trigger_data["device_machine_label"]

            data = {
                "trigger_type": "device",
                "device_machine_label": webinterface.request_get_default(request, "device_machine_label", device_machine_label),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/automation/{rule_id}/details", rule.label)
            webinterface.add_breadcrumb(request, f"/automation/{rule_id}/add_trigger_device", "Set trigger: device")
            return page_automation_trigger_set_device_form(webinterface, request, session, rule, data)

        @webapp.route("/<string:rule_id>/set_trigger_device", methods=["POST"])
        @require_auth()
        def page_automation_trigger_set_device_post(webinterface, request, session, rule_id):
            session.has_access("automation", rule_id, "edit", raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/automation/index")
            rule_id = rule.rule_id

            trigger_data = rule.data["trigger"]
            if trigger_data["trigger_type"] == "device":
                print("getting data from array")
                if "device_machine_label" in trigger_data:
                    device_machine_label = trigger_data["device_machine_label"]

            data = {
                "trigger_type": "device",
                "device_machine_label": webinterface.request_get_default(request,
                                                                         "device_machine_label",
                                                                         "device_machine_label"),
            }

            if data["device_machine_label"] == "":
                webinterface.add_alert("Must enter a device machine label.", "warning")
                return page_automation_trigger_set_device_form(webinterface, request, session, rule, data)

            try:
                webinterface._Automation.set_rule_trigger(rule_id, **data)
            except YomboWarning as e:
                webinterface.add_alert(f"Cannot add device to automation. {e.message}", "warning")
                return page_automation_trigger_set_device_form(webinterface, request, session, rule, data)

            webinterface.add_alert("Set device trigger to automation rule.")
            return webinterface.redirect(request, f"/automation/{rule_id}/details")

        def page_automation_trigger_set_device_form(webinterface, request, session, rule, data):
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/automation/form_trigger_device.html")

            return page.render(alerts=webinterface.get_alerts(),
                               rule=rule,
                               data=data,
                               )

        @webapp.route("/<string:rule_id>/add_action_device", methods=["GET"])
        @require_auth()
        def page_automation_action_device_add_get(webinterface, request, session, rule_id):
            session.has_access("automation", rule_id, "edit", raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/automation/index")
            rule_id = rule.rule_id

            data = {
                "action_id": None,
                "action_type": "device",
                "device_machine_label": webinterface.request_get_default(request, "device_machine_label", ""),
                "command_machine_label": webinterface.request_get_default(request, "command_machine_label", ""),
                "inputs": webinterface.request_get_default(request, "inputs", ""),
                "weight": int(webinterface.request_get_default(
                    request, "weight", (len(webinterface._Automation.get_action_items(rule_id)) + 1) * 10)),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/automation/{rule_id}/details", rule.label)
            webinterface.add_breadcrumb(request, f"/automation/{rule_id}/add_device", "Add action: Device")
            return page_automation_action_form_device(webinterface, request, session, rule, data, "add",
                                           "Add device to automation rule")

        @webapp.route("/<string:rule_id>/add_action_device", methods=["POST"])
        @require_auth()
        def page_automation_action_device_add_post(webinterface, request, session, rule_id):
            session.has_access("automation", rule_id, "edit", raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/automation/index")
            rule_id = rule.rule_id

            try:
                incoming_data = json.loads(webinterface.request_get_default(request, "json_output", "{}"))
            except Exception as e:
                webinterface.add_alert("Error decoding request data.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/add_device")
            keep_attributes = ["device_machine_label", "command_machine_label", "inputs", "weight"]
            data = {k: incoming_data[k] for k in keep_attributes if k in incoming_data}
            data["action_type"] = "device"
            if "device_machine_label" not in data:
                webinterface.add_alert("device_machine_label information is missing.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/add_device")
            try:
                device = webinterface._Devices[data["device_machine_label"]]
            except Exception as e:
                webinterface.add_alert("Device could not be found.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/add_device")

            if "command_machine_label" not in data:
                webinterface.add_alert("Command ID information is missing.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/add_device")
            try:
                command = webinterface._Commands[data["command_machine_label"]]
            except Exception as e:
                webinterface.add_alert("Device could not be found.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/add_device")

            if "inputs" not in data:
                data["inputs"] = {}

            if "weight" not in data:
                data["weight"] = 40000
            else:
                try:
                    data["weight"] = int(data["weight"])
                except Exception as e:
                    webinterface.add_alert("Weight must be a whole number.", "warning")
                    return webinterface.redirect(request, f"/automation/{rule_id}/add_device")

            # TODO: handle encrypted input values....

            try:
                webinterface._Automation.add_action_item(rule_id, **data)
            except YomboWarning as e:
                webinterface.add_alert(f"Cannot add device to automation rule. {e.message}", "warning")
                return page_automation_action_form_device(webinterface, request, session, rule, data, "add",
                                               "Add device to automation rule")

            webinterface.add_alert("Added device action to automation rule.")
            return webinterface.redirect(request, f"/automation/{rule.rule_id}/details")

        @webapp.route("/<string:rule_id>/edit_action_device/<string:action_id>", methods=["GET"])
        @require_auth()
        def page_automation_action_device_edit_get(webinterface, request, session, rule_id, action_id):
            session.has_access("automation", rule_id, "edit", raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/automation/index")
            rule_id = rule.rule_id

            try:
                action = webinterface._Automation.get_action_items(rule_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Requested action id could not be located.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/details")
            if action["action_type"] != "device":
                webinterface.add_alert("Requested action type is invalid.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/details")

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/automation/{rule_id}/details", rule.label)
            webinterface.add_breadcrumb(request, f"/automation/{rule_id}/edit_device", "Edit action: Device")
            return page_automation_action_form_device(webinterface, request, session, rule, action, "edit",
                                           "Edit automation rule action: Device")

        @webapp.route("/<string:rule_id>/edit_action_device/<string:action_id>", methods=["POST"])
        @require_auth()
        def page_automation_action_device_edit_post(webinterface, request, session, rule_id, action_id):
            session.has_access("automation", rule_id, "edit", raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/automation/index")
            rule_id = rule.rule_id

            try:
                action = webinterface._Automation.get_action_items(rule_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Requested action id could not be located.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/details")
            if action["action_type"] != "device":
                webinterface.add_alert("Requested action type is invalid.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/details")

            try:
                incoming_data = json.loads(webinterface.request_get_default(request, "json_output", "{}"))
            except Exception as e:
                webinterface.add_alert("Error decoding request data.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/add_device")
            keep_attributes = ["device_machine_label", "command_machine_label", "inputs", "weight"]
            data = {k: incoming_data[k] for k in keep_attributes if k in incoming_data}
            data["action_type"] = "device"

            if "device_machine_label" not in data:
                webinterface.add_alert("device_machine_label information is missing.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/add_device")
            try:
                device = webinterface._Devices[data["device_machine_label"]]
            except Exception as e:
                webinterface.add_alert("Device could not be found.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/add_device")

            if "command_machine_label" not in data:
                webinterface.add_alert("Command ID information is missing.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/add_device")
            try:
                command = webinterface._Commands[data["command_machine_label"]]
            except Exception as e:
                webinterface.add_alert("Device could not be found.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/add_device")

            if "inputs" not in data:
                data["inputs"] = {}

            if "weight" not in data:
                data["weight"] = 40000
            else:
                try:
                    data["weight"] = int(data["weight"])
                except Exception as e:
                    webinterface.add_alert("Weight must be a whole number.", "warning")
                    return webinterface.redirect(request, f"/automation/{rule_id}/add_device")
            if "rule_id" in data:
                del data["rule_id"]
            if "action_id" in data:
                del data["action_id"]

            # TODO: handle encrypted input values....

            try:
                webinterface._Automation.edit_action_item(rule_id, action_id, **data)
            except YomboWarning as e:
                webinterface.add_alert(f"Cannot edit device within automation rule. {e.message}", "warning")
                return page_automation_action_form_device(webinterface, request, session, rule, data, "add",
                                               "Add device to automation rule")

            webinterface.add_alert("Added device action to automation rule.")
            return webinterface.redirect(request, f"/automation/{rule_id}/details")

        def page_automation_action_form_device(webinterface, request, session, rule, data, action_type, header_label):
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/automation/form_action_device.html")

            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               rule=rule,
                               data=data,
                               action_type=action_type,
                               )

        @webapp.route("/<string:rule_id>/delete_action_device/<string:action_id>", methods=["GET"])
        @require_auth()
        def page_automation_action_device_delete_get(webinterface, request, session, rule_id, action_id):
            session.has_access("automation", rule_id, "edit", raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/automation/index")
            rule_id = rule.rule_id

            try:
                action = webinterface._Automation.get_action_items(rule_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Requested action id could not be located.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/details")
            if action["action_type"] != "device":
                webinterface.add_alert("Requested action type is invalid.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/details")

            page = webinterface.get_template(
                request,
                webinterface.wi_dir + "/pages/automation/delete_action_device.html"
            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/automation/{rule_id}/details", rule.label)
            webinterface.add_breadcrumb(request, f"/automation/{rule_id}/delete_device", "Delete action: Device")
            return page.render(alerts=webinterface.get_alerts(),
                               rule=rule,
                               action=action,
                               action_id=action_id,
                               )

        @webapp.route("/<string:rule_id>/delete_action_device/<string:action_id>", methods=["POST"])
        @require_auth()
        def page_automation_action_device_delete_post(webinterface, request, session, rule_id, action_id):
            session.has_access("automation", rule_id, "edit", raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/automation/index")
            rule_id = rule.rule_id

            try:
                action = webinterface._Automation.get_action_items(rule_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Requested action id could not be located.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/details")
            if action["action_type"] != "device":
                webinterface.add_alert("Requested action type is invalid.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/details")

            try:
                confirm = request.args.get("confirm")[0]
            except:
                webinterface.add_alert("Must enter 'delete' in the confirmation box to "
                                       "delete the device from the automation rule.", "warning")
                return webinterface.redirect(request,
                                             f"/automation/{rule_id}/delete_device/{action_id}")

            if confirm != "delete":
                webinterface.add_alert("Must enter 'delete' in the confirmation box to "
                                       "delete the device from the automation rule.", "warning")
                return webinterface.redirect(request,
                                             f"/automation/{rule_id}/delete_device/{action_id}")

            try:
                webinterface._Automation.delete_action_item(rule_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert(f"Cannot delete device from automation rule. {e.message}", "warning")
                return webinterface.redirect(request, "/automation/index")

            webinterface.add_alert("Deleted device action for automation rule.")
            return webinterface.redirect(request, f"/automation/{rule_id}/details")
