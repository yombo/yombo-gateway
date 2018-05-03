# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the state handling for /automation sub directory.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.19.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/routes/automation.py>`_
"""
# from collections import OrderedDict
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils.datatypes import coerce_value

logger = get_logger("library.webinterface.routes.automation.state")


def route_automation_state(webapp):
    with webapp.subroute("/automation") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/automation/index", "Automation")

        @webapp.route('/<string:rule_id>/set_trigger_state', methods=['GET'])
        @require_auth()
        def page_automation_trigger_set_state_get(webinterface, request, session, rule_id):
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            state_name = ""
            state_value = ""
            state_value_type = ""
            state_gateway_id = webinterface.gateway_id()

            trigger_data = rule.data['trigger']
            print("editing automation trigger for state: %s" % trigger_data)
            if trigger_data['trigger_type'] == "state":
                print("getting data from array")
                if 'name' in trigger_data:
                    state_name = trigger_data['name']
                if 'value' in trigger_data:
                    state_value = trigger_data['value']
                if 'value_type' in trigger_data:
                    state_value_type = trigger_data['value_type']
                if 'gateway_id' in trigger_data:
                    state_gateway_id = trigger_data['gateway_id']

            data = {
                'trigger_type': 'state',
                'name': webinterface.request_get_default(request, 'name', state_name),
                'value': webinterface.request_get_default(request, 'value', state_value),
                'value_type': webinterface.request_get_default(request, 'value_type', state_value_type),
                'gateway_id': webinterface.request_get_default(request, 'gateway_id', state_gateway_id),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/add_trigger_state" % rule_id, "Add action: State")
            return page_automation_trigger_set_state_form(webinterface, request, session, rule, data)

        @webapp.route('/<string:rule_id>/set_trigger_state', methods=['POST'])
        @require_auth()
        def page_automation_trigger_set_state_post(webinterface, request, session, rule_id):
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            data = {
                'trigger_type': 'state',
                'name': webinterface.request_get_default(request, 'name', ""),
                'value': webinterface.request_get_default(request, 'value', ""),
                'value_type': webinterface.request_get_default(request, 'value_type', ""),
                'gateway_id': webinterface.request_get_default(request, 'gateway_id', webinterface.gateway_id()),
            }

            if data['name'] == "":
                webinterface.add_alert('Must enter a state name.', 'warning')
                return page_automation_trigger_set_state_form(webinterface, request, session, rule, data)

            if data['value_type'] == "":
                webinterface.add_alert('Must enter a value type.', 'warning')
                return page_automation_trigger_set_state_form(webinterface, request, session, rule, data)

            try:
                webinterface._Automation.set_rule_trigger(rule_id, **data)
            except YomboWarning as e:
                webinterface.add_alert("Cannot add state to automation. %s" % e.message, 'warning')
                return page_automation_trigger_set_state_form(webinterface, request, session, rule, data)

            webinterface.add_alert("Set state trigger to automation rule.")
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)

        def page_automation_trigger_set_state_form(webinterface, request, session, rule, data):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/automation/form_trigger_state.html')

            return page.render(alerts=webinterface.get_alerts(),
                               rule=rule,
                               data=data,
                               )

        @webapp.route('/<string:rule_id>/add_action_state', methods=['GET'])
        @require_auth()
        def page_automation_action_add_state_get(webinterface, request, session, rule_id):
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            data = {
                'action_type': 'state',
                'name': webinterface.request_get_default(request, 'name', ""),
                'value': webinterface.request_get_default(request, 'value', ""),
                'value_type': webinterface.request_get_default(request, 'value_type', ""),
                'gateway_id': webinterface.request_get_default(request, 'gateway_id', webinterface.gateway_id()),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Automation.get_action_items(rule_id)) + 1) * 10)),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/add_action_state" % rule_id, "Add action: State")
            return page_automation_action_state_form(webinterface, request, session, rule, data, 'add', "Add state to rule")

        @webapp.route('/<string:rule_id>/add_action_state', methods=['POST'])
        @require_auth()
        def page_automation_action_add_state_post(webinterface, request, session, rule_id):
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            data = {
                'action_type': 'state',
                'name': webinterface.request_get_default(request, 'name', ""),
                'value': webinterface.request_get_default(request, 'value', ""),
                'value_type': webinterface.request_get_default(request, 'value_type', ""),
                'gateway_id': webinterface.request_get_default(request, 'gateway_id', webinterface.gateway_id()),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Automation.get_action_items(rule_id)) + 1) * 10)),
            }

            if data['name'] == "":
                webinterface.add_alert('Must enter a state name.', 'warning')
                return page_automation_action_state_form(webinterface, request, session, rule, data, 'add', "Add state to rule")

            if data['value'] == "":
                webinterface.add_alert('Must enter a state value to set.', 'warning')
                return page_automation_action_state_form(webinterface, request, session, rule, data, 'add', "Add state to rule")

            if data['value_type'] == "" or data['value_type'] not in ('integer', 'string', 'boolean', 'float'):
                webinterface.add_alert('Must enter a state value_type to ensure validity.', 'warning')
                return page_automation_action_state_form(webinterface, request, session, rule, data, 'add', "Add state to rule")

            value_type = data['value_type']
            if value_type == "string":
                data['value'] = coerce_value(data['value'], 'string')
            elif value_type == "integer":
                try:
                    data['value'] = coerce_value(data['value'], 'int')
                except Exception:
                    webinterface.add_alert("Cannot coerce state value into an integer", 'warning')
                    return page_automation_action_state_form(webinterface, request, session, rule, data, 'add', "Add state to rule")
            elif value_type == "float":
                try:
                    data['value'] = coerce_value(data['value'], 'float')
                except Exception:
                    webinterface.add_alert("Cannot coerce state value into an float", 'warning')
                    return page_automation_action_state_form(webinterface, request, session, rule, data, 'add', "Add state to rule")
            elif value_type == "boolean":
                try:
                    data['value'] = coerce_value(data['value'], 'bool')
                    if isinstance(data['value'], bool) is False:
                        raise Exception()
                except Exception:
                    webinterface.add_alert("Cannot coerce state value into an boolean", 'warning')
                    return page_automation_action_state_form(webinterface, request, session, rule, data, 'add', "Add state to rule")

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_automation_action_state_form(webinterface, request, session, rule, data, 'add', "Add state to rule")

            try:
                webinterface._Automation.add_action_item(rule_id, **data)
            except YomboWarning as e:
                webinterface.add_alert("Cannot add state to rule. %s" % e.message, 'warning')
                return page_automation_action_state_form(webinterface, request, session, rule, data, 'add', "Add state to rule")

            webinterface.add_alert("Added state action to rule.")
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)

        @webapp.route('/<string:rule_id>/edit_action_state/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_automation_action_edit_state_get(webinterface, request, session, rule_id, action_id):
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')
            try:
                action = webinterface._Automation.get_action_items(rule_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Requested action id could not be located.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)
            if action['action_type'] != 'state':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule.rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/edit_state" % rule.rule_id, "Edit action: State")
            return page_automation_action_state_form(webinterface, request, session, rule, action, 'edit',
                                          "Edit rule action: State")

        @webapp.route('/<string:rule_id>/edit_action_state/<string:action_id>', methods=['POST'])
        @require_auth()
        def page_automation_action_edit_state_post(webinterface, request, session, rule_id, action_id):
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')
            try:
                action = webinterface._Automation.get_action_items(rule_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Requested action id could not be located.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)
            data = {
                'action_type': 'state',
                'name': webinterface.request_get_default(request, 'name', ""),
                'value': webinterface.request_get_default(request, 'value', ""),
                'value_type': webinterface.request_get_default(request, 'value_type', ""),
                'gateway_id': webinterface.request_get_default(request, 'gateway_id', webinterface.gateway_id()),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Automation.get_action_items(rule_id)) + 1) * 10)),
            }

            if data['name'] == "":
                webinterface.add_alert('Must enter a state name.', 'warning')
                return page_automation_action_state_form(webinterface, request, session, rule, data, 'add', "Edit action action: State")

            if data['value'] == "":
                webinterface.add_alert('Must enter a state value to set.', 'warning')
                return page_automation_action_state_form(webinterface, request, session, rule, data, 'add', "Edit action action: State")

            if data['value_type'] == "" or data['value_type'] not in ('integer', 'string', 'boolean', 'float'):
                webinterface.add_alert('Must enter a state value_type to ensure validity.', 'warning')
                return page_automation_action_state_form(webinterface, request, session, rule, data, 'add', "Edit action action: State")

            value_type = data['value_type']
            if value_type == "string":
                data['value'] = coerce_value(data['value'], 'string')
            elif value_type == "integer":
                try:
                    data['value'] = coerce_value(data['value'], 'int')
                except Exception:
                    webinterface.add_alert("Cannot coerce state value into an integer", 'warning')
                    return page_automation_action_state_form(webinterface, request, session, rule, data, 'add',
                                                      "Edit rule action: State")
            elif value_type == "float":
                try:
                    data['value'] = coerce_value(data['value'], 'float')
                except Exception:
                    webinterface.add_alert("Cannot coerce state value into an float", 'warning')
                    return page_automation_action_state_form(webinterface, request, session, rule, data, 'add',
                                                      "Edit rule action: State")
            elif value_type == "boolean":
                try:
                    data['value'] = coerce_value(data['value'], 'bool')
                    if isinstance(data['value'], bool) is False:
                        raise Exception()
                except Exception:
                    webinterface.add_alert("Cannot coerce state value into an boolean", 'warning')
                    return page_automation_action_state_form(webinterface, request, session, rule, data, 'add',
                                                      "Edit rule action: State")
            else:
                webinterface.add_alert("Unknown value type.", 'warning')
                return page_automation_action_state_form(webinterface, request, session, rule, data, 'add',
                                                  "Edit rule action: State")

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_automation_action_state_form(webinterface, request, session, rule, data, 'add', "Edit action action: State")

            try:
                webinterface._Automation.edit_action_item(rule_id, action_id, **data)
            except YomboWarning as e:
                webinterface.add_alert("Cannot edit state within rule. %s" % e.message, 'warning')
                return page_automation_action_state_form(webinterface, request, session, rule, data, 'add', "Edit action action: State")

            webinterface.add_alert("Edited state action for rule.")
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)

        def page_automation_action_state_form(webinterface, request, session, rule, data, action_type, header_label):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/automation/form_action_state.html')

            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               rule=rule,
                               data=data,
                               action_type=action_type,
                               )

        @webapp.route('/<string:rule_id>/delete_action_state/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_automation_action_edit_delete_get(webinterface, request, session, rule_id, action_id):
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')
            try:
                action = webinterface._Automation.get_action_items(rule_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Requested action id could not be located.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)
            if action['action_type'] != 'state':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)

            page = webinterface.get_template(
                request,
                webinterface.wi_dir + '/pages/automation/delete_action_state.html'
            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/delete_state" % rule_id, "Delete action: State")
            return page.render(alerts=webinterface.get_alerts(),
                               rule=rule,
                               action=action,
                               action_id=action_id,
                               )

        @webapp.route('/<string:rule_id>/delete_action_state/<string:action_id>', methods=['POST'])
        @require_auth()
        def page_automation_action_edit_delete_post(webinterface, request, session, rule_id, action_id):
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')
            try:
                action = webinterface._Automation.get_action_items(rule_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Requested action id could not be located.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)
            if action['action_type'] != 'state':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)

            try:
                confirm = request.args.get('confirm')[0]
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the state from the automation.', 'warning')
            except:
                return webinterface.redirect(request,
                                             '/automation/%s/delete_state/%s' % (rule_id, action_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the state from the automation.', 'warning')
                return webinterface.redirect(request,
                                             '/automation/%s/delete_state/%s' % (rule_id, action_id))

            try:
                webinterface._Automation.delete_action_item(rule_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Cannot delete state from automation. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            webinterface.add_alert("Deleted state action for automation rule.")
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)
