# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the pause handling for /automation sub directory.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.19.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/routes/automation.py>`_
"""
# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.routes.automation.pause")


def route_automation_pause(webapp):
    with webapp.subroute("/automation") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/", "Home")
            webinterface.add_breadcrumb(request, "/automation/index", "Automation")

        @webapp.route("/<string:rule_id>/add_action_pause", methods=["GET"])
        @require_auth()
        def page_automation_action_pause_add_get(webinterface, request, session, rule_id):
            session.has_access("automation", rule_id, "edit", raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/automation/index")
            rule_id = rule.rule_id

            data = {
                "action_type": "pause",
                "duration": webinterface.request_get_default(request, "duration", 5),
                "weight": int(webinterface.request_get_default(
                    request, "weight", (len(webinterface._Automation.get_action_items(rule_id)) + 1) * 10)),
            }
            try:
                data["duration"] = float(data["duration"])
            except Exception as e:
                webinterface.add_alert("Duration must be an integer or float.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/details")

            try:
                data["weight"] = int(data["weight"])
            except Exception:
                webinterface.add_alert("Must enter a number for a weight.", "warning")
                return page_automation_action_form_pause(webinterface, request, session, rule, data, "add",
                                                         "Add a pause to automation rule")

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/automation/{rule_id}/details", rule.label)
            webinterface.add_breadcrumb(request, f"/automation/{rule_id}/add_pause", "Add action: Pause")
            return page_automation_action_form_pause(webinterface, request, session, rule, data, "add",
                                                     "Add a pause to automation rule")

        @webapp.route("/<string:rule_id>/add_action_pause", methods=["POST"])
        @require_auth()
        def page_automation_action_pause_add_post(webinterface, request, session, rule_id):
            session.has_access("automation", rule_id, "edit", raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/automation/index")
            rule_id = rule.rule_id

            data = {
                "action_type": "pause",
                "duration": webinterface.request_get_default(request, "duration", 5),
                "weight": int(webinterface.request_get_default(
                    request, "weight", (len(webinterface._Automation.get_action_items(rule_id)) + 1) * 10)),
            }
            try:
                data["duration"] = float(data["duration"])
            except Exception as e:
                webinterface.add_alert("Duration must be an integer or float.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/details")

            try:
                data["weight"] = int(data["weight"])
            except Exception:
                webinterface.add_alert("Must enter a number for a weight.", "warning")
                return page_automation_action_form_pause(webinterface, request, session, rule, data, "add",
                                                         "Add a pause to automation rule")

            try:
                webinterface._Automation.add_action_item(rule_id, **data)
            except YomboWarning as e:
                webinterface.add_alert(f"Cannot add pause to automation rule. {e.message}", "warning")
                return page_automation_action_form_pause(webinterface, request, session, rule, data, "add",
                                                         "Add a pause to automation rule")

            webinterface.add_alert("Added pause action to automation rule.")
            return webinterface.redirect(request, f"/automation/{rule_id}/details")

        @webapp.route("/<string:rule_id>/edit_action_pause/<string:action_id>", methods=["GET"])
        @require_auth()
        def page_automation_action_pause_edit_get(webinterface, request, session, rule_id, action_id):
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
            if action["action_type"] != "pause":
                webinterface.add_alert(f"Requested action type is invalid: {action['action_type']}", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/details")

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/automation/{rule_id}/details", rule.label)
            webinterface.add_breadcrumb(request, f"/automation/{rule_id}/edit_pause", "Edit action: Pause")
            return page_automation_action_form_pause(webinterface, request, session, rule, action, "edit",
                                              "Edit automation rule action: State")

        @webapp.route("/<string:rule_id>/edit_action_pause/<string:action_id>", methods=["POST"])
        @require_auth()
        def page_automation_action_pause_edit_post(webinterface, request, session, rule_id, action_id):
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
            if action["action_type"] != "pause":
                webinterface.add_alert(f"Requested action type is invalid: {action['action_type']}", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/details")

            data = {
                "action_type": "pause",
                "duration": webinterface.request_get_default(request, "duration", 5),
                "weight": int(webinterface.request_get_default(
                    request, "weight", (len(webinterface._Automation.get_action_items(rule_id)) + 1) * 10)),
            }
            try:
                data["duration"] = float(data["duration"])
            except Exception as e:
                webinterface.add_alert("Duration must be an integer or float.", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/details")

            try:
                data["weight"] = int(data["weight"])
            except Exception:
                webinterface.add_alert("Must enter a number for a weight.", "warning")
                return page_automation_action_form_pause(webinterface, request, session, rule, data, "add",
                                                         "Add a pause to automation rule")

            try:
                webinterface._Automation.edit_action_item(rule_id, action_id, **data)
            except YomboWarning as e:
                webinterface.add_alert(f"Cannot edit pause within automation rule. {e.message}", "warning")
                return page_automation_action_form_pause(webinterface, request, session, rule, data, "add",
                                              "Edit automation rule action: Pause")

            webinterface.add_alert(f"Edited a pause action for automation rule '{rule.label}'.")
            return webinterface.redirect(request, f"/automation/{rule_id}/details")

        def page_automation_action_form_pause(webinterface, request, session, rule, data, action_type, header_label):
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/automation/form_action_pause.html")

            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               rule=rule,
                               data=data,
                               action_type=action_type,
                               )

        @webapp.route("/<string:rule_id>/delete_action_pause/<string:action_id>", methods=["GET"])
        @require_auth()
        def page_automation_action_pause_delete_get(webinterface, request, session, rule_id, action_id):
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
            if action["action_type"] != "pause":
                webinterface.add_alert("Requested action type is invalid: {action['action_type']}", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/details")

            page = webinterface.get_template(
                request,
                webinterface.wi_dir + "/pages/automation/delete_action_pause.html"
            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/automation/{rule_id}/details", rule.label)
            webinterface.add_breadcrumb(request, f"/automation/{rule_id}/delete_pause", "Delete action: Pause")
            return page.render(alerts=webinterface.get_alerts(),
                               rule=rule,
                               action=action,
                               action_id=action_id,
                               )

        @webapp.route("/<string:rule_id>/delete_action_pause/<string:action_id>", methods=["POST"])
        @require_auth()
        def page_automation_action_pause_delete_post(webinterface, request, session, rule_id, action_id):
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
            if action["action_type"] != "pause":
                webinterface.add_alert(f"Requested action type is invalid: {action['action_type']}", "warning")
                return webinterface.redirect(request, f"/automation/{rule_id}/details")

            try:
                confirm = request.args.get("confirm")[0]
            except:
                webinterface.add_alert("Must enter 'delete' in the confirmation box to "
                                       "delete the pause from the automation rule.", "warning")
                return webinterface.redirect(request,
                                             f"/automation/{rule_id}/delete_pause/{action_id}")

            if confirm != "delete":
                webinterface.add_alert("Must enter 'delete' in the confirmation box to "
                                       "delete the pause from the automation rule.", "warning")
                return webinterface.redirect(request,
                                             f"/automation/{rule_id}/delete_pause/{action_id}")

            try:
                webinterface._Automation.delete_action_item(rule_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert(f"Cannot delete pause from automation rule. {e.message}", "warning")
                return webinterface.redirect(request, "/automation/index")

            webinterface.add_alert("Deleted pause action for automation rule.")
            return webinterface.redirect(request, f"/automation/{rule_id}/details")
