# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the template handling for /automation sub directory.

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

logger = get_logger("library.webinterface.routes.automation.template")


def route_automation_template(webapp):
    with webapp.subroute("/automation") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/automation/index", "Automation Rules")

        @webapp.route('/<string:rule_id>/set_condition_template', methods=['GET'])
        @require_auth()
        def page_automation_condition_template_get(webinterface, request, session, rule_id):
            session.has_access('automation:%s' % rule_id, 'edit', raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            if 'template' in rule.data['condition']:
                template = rule.data['condition']['template']
            else:
                template = ""
            if 'description' in rule.data['condition']:
                description = rule.data['condition']['description']
            else:
                description = ""
            data = {
                'description': webinterface.request_get_default(request, 'description', description),
                'template': webinterface.request_get_default(request, 'template', template),
            }

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/add_condition_template" % rule_id, "Add action: Template")
            return page_automation_condition_form_template(webinterface, request, session, rule, data)

        @webapp.route('/<string:rule_id>/set_condition_template', methods=['POST'])
        @require_auth()
        def page_automation_condition_template_post(webinterface, request, session, rule_id):
            session.has_access('automation:%s' % rule_id, 'edit', raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            data = {
                'description': webinterface.request_get_default(request, 'description', ""),
                'template': webinterface.request_get_default(request, 'template', ""),
            }

            if data['description'] is "":
                webinterface.add_alert('Must enter a description.', 'warning')
                return page_automation_condition_form_template(webinterface, request, session, rule, data)
            if data['template'] is "":
                webinterface.add_alert('Must enter a template.', 'warning')
                return page_automation_condition_form_template(webinterface, request, session, rule, data)

            try:
                webinterface._Automation.set_rule_condition(rule_id, **data)
            except YomboWarning as e:
                webinterface.add_alert("Cannot set rule condition template: %s" % e.message, 'warning')
                return page_automation_action_form_template(webinterface, request, session, rule, data, 'add', "Add a template to automation rule")

            webinterface.add_alert("Added template action to automation rule.")
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)

        @webapp.route('/<string:rule_id>/edit_action_template/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_automation_action_template_edit_get(webinterface, request, session, rule_id, action_id):
            session.has_access('automation:%s' % rule_id, 'edit', raise_error=True)
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
            if action['action_type'] != 'template':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule.rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/edit_template" % rule.rule_id, "Edit action: Template")
            return page_automation_action_form_template(webinterface, request, session, rule, action, 'edit',
                                              "Edit automation rule action: Template")

        @webapp.route('/<string:rule_id>/edit_action_template/<string:action_id>', methods=['POST'])
        @require_auth()
        def page_automation_action_template_edit_post(webinterface, request, session, rule_id, action_id):
            session.has_access('automation:%s' % rule_id, 'edit', raise_error=True)
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
            if action['action_type'] != 'template':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)

            data = {
                'action_type': 'template',
                'description': webinterface.request_get_default(request, 'description', ""),
                'template': webinterface.request_get_default(request, 'template', 5),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Automation.get_action_items(rule_id)) + 1) * 10)),
            }

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_automation_action_form_template(webinterface, request, session, rule, data, 'add', "Add a template to automation rule")

            try:
                webinterface._Automation.edit_action_item(rule_id, action_id, **data)
            except YomboWarning as e:
                webinterface.add_alert("Cannot edit template within automation rule. %s" % e.message, 'warning')
                return page_automation_action_form_template(webinterface, request, session, rule, data, 'add', "Edit automation rule action: Template")

            webinterface.add_alert("Edited a template action for automation rule '%s'." % rule.label)
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)

        def page_automation_condition_form_template(webinterface, request, session, rule, data):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/automation/form_condition_template.html')

            return page.render(alerts=webinterface.get_alerts(),
                               rule=rule,
                               data=data,
                               )

        @webapp.route('/<string:rule_id>/add_action_template', methods=['GET'])
        @require_auth()
        def page_automation_action_template_add_get(webinterface, request, session, rule_id):
            session.has_access('automation:%s' % rule_id, 'edit', raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            data = {
                'action_type': 'template',
                'description': webinterface.request_get_default(request, 'description', ""),
                'template': webinterface.request_get_default(request, 'template', ""),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Automation.get_action_items(rule_id)) + 1) * 10)),
            }

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_automation_action_form_template(webinterface, request, session, rule, data, 'add', "Add a template to automation rule")

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/add_action_template" % rule_id, "Add action: Template")
            return page_automation_action_form_template(webinterface, request, session, rule, data, 'add', "Add a template to automation rule")

        @webapp.route('/<string:rule_id>/add_action_template', methods=['POST'])
        @require_auth()
        def page_automation_action_template_add_post(webinterface, request, session, rule_id):
            session.has_access('automation:%s' % rule_id, 'edit', raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            data = {
                'action_type': 'template',
                'description': webinterface.request_get_default(request, 'description', ""),
                'template': webinterface.request_get_default(request, 'template', ""),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Automation.get_action_items(rule_id)) + 1) * 10)),
            }

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_automation_action_form_template(webinterface, request, session, rule, data, 'add', "Add a template to automation rule")

            try:
                webinterface._Automation.add_action_item(rule_id, **data)
            except YomboWarning as e:
                webinterface.add_alert("Cannot add template to automation rule. %s" % e.message, 'warning')
                return page_automation_action_form_template(webinterface, request, session, rule, data, 'add', "Add a template to automation rule")

            webinterface.add_alert("Added template action to automation rule.")
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)

        @webapp.route('/<string:rule_id>/edit_action_template/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_automation_action_template_edit_get(webinterface, request, session, rule_id, action_id):
            session.has_access('automation:%s' % rule_id, 'edit', raise_error=True)
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
            if action['action_type'] != 'template':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule.rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/edit_template" % rule.rule_id, "Edit action: Template")
            return page_automation_action_form_template(webinterface, request, session, rule, action, 'edit',
                                              "Edit automation rule action: Template")

        @webapp.route('/<string:rule_id>/edit_action_template/<string:action_id>', methods=['POST'])
        @require_auth()
        def page_automation_action_template_edit_post(webinterface, request, session, rule_id, action_id):
            session.has_access('automation:%s' % rule_id, 'edit', raise_error=True)
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
            if action['action_type'] != 'template':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)

            data = {
                'action_type': 'template',
                'description': webinterface.request_get_default(request, 'description', ""),
                'template': webinterface.request_get_default(request, 'template', 5),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Automation.get_action_items(rule_id)) + 1) * 10)),
            }

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_automation_action_form_template(webinterface, request, session, rule, data, 'add', "Add a template to automation rule")

            try:
                webinterface._Automation.edit_action_item(rule_id, action_id, **data)
            except YomboWarning as e:
                webinterface.add_alert("Cannot edit template within automation rule. %s" % e.message, 'warning')
                return page_automation_action_form_template(webinterface, request, session, rule, data, 'add', "Edit automation rule action: Template")

            webinterface.add_alert("Edited a template action for automation rule '%s'." % rule.label)
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)

        def page_automation_action_form_template(webinterface, request, session, rule, data, action_type, header_label):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/automation/form_action_template.html')

            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               rule=rule,
                               data=data,
                               action_type=action_type,
                               )

        @webapp.route('/<string:rule_id>/delete_action_template/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_automation_action_template_delete_get(webinterface, request, session, rule_id, action_id):
            session.has_access('automation:%s' % rule_id, 'edit', raise_error=True)
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
            if action['action_type'] != 'template':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)

            page = webinterface.get_template(
                request,
                webinterface.wi_dir + '/pages/automation/delete_action_template.html'
            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/delete_action_template" % rule_id, "Delete action: Template")
            return page.render(alerts=webinterface.get_alerts(),
                               rule=rule,
                               action=action,
                               action_id=action_id,
                               )

        @webapp.route('/<string:rule_id>/delete_action_template/<string:action_id>', methods=['POST'])
        @require_auth()
        def page_automation_action_template_delete_post(webinterface, request, session, rule_id, action_id):
            session.has_access('automation:%s' % rule_id, 'edit', raise_error=True)
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
            if action['action_type'] != 'template':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)

            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the template from the automation rule.', 'warning')
                return webinterface.redirect(request,
                                             '/automation/%s/delete_action_template/%s' % (rule_id, action_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the template from the automation rule.', 'warning')
                return webinterface.redirect(request,
                                             '/automation/%s/delete_action_template/%s' % (rule_id, action_id))

            try:
                webinterface._Automation.delete_action_item(rule_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Cannot delete template from automation rule. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            webinterface.add_alert("Deleted template action for automation rule.")
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)
