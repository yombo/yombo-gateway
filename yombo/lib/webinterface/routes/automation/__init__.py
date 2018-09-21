# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/automation" sub-route of the web interface.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.19.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/routes/automation/__init__.py>`_
"""
# from collections import OrderedDict
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.lib.webinterface.auth import require_auth
from yombo.utils import is_true_false

logger = get_logger("library.webinterface.routes.automation")


def route_automation(webapp):
    with webapp.subroute("/automation") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/automation/index", "Automation")

        @webapp.route('/')
        @require_auth()
        def page_automation(webinterface, request, session):
            session.has_access('automation', '*', 'view', raise_error=True)
            return webinterface.redirect(request, '/automation/index')

        @webapp.route('/index')
        @require_auth()
        def page_automation_index(webinterface, request, session):
            session.has_access('automation', '*', 'view', raise_error=True)
            root_breadcrumb(webinterface, request)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/automation/index.html')
            return page.render(
                alerts=webinterface.get_alerts(),
                )

        @webapp.route('/<string:rule_id>/details', methods=['GET'])
        @require_auth()
        def page_automation_details_get(webinterface, request, session, rule_id):
            rule_id = webinterface._Validate.id_string(rule_id)
            session.has_access('automation', rule_id, 'view', raise_error=True)
            try:
                rule = webinterface._Automation[rule_id]
            except KeyError as e:
                webinterface.add_alert("Requested rule doesn't exist: %s" % rule_id, 'warning')
                return webinterface.redirect(request, '/automation/index')

            page = webinterface.get_template(
                request,
                webinterface.wi_dir + '/pages/automation/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule.rule_id, rule.label)
            return page.render(alerts=webinterface.get_alerts(),
                               rule=rule,
                               )

        @webapp.route('/<string:rule_id>/stop', methods=['GET'])
        @require_auth()
        def page_automation_stop_rule_get(webinterface, request, session, rule_id):
            rule_id = webinterface._Validate.id_string(rule_id)
            session.has_access('automation', rule_id, 'stop', raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            try:
                webinterface._Automation.stop(rule_id)
            except YomboWarning as e:
                webinterface.add_alert("Cannot stop automation rule. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/automation/%s/details' % rule_id)

            webinterface.add_alert("The automation rule '%s' has been stopped" % rule.label)
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)

        @webapp.route('/add', methods=['GET'])
        @require_auth()
        def page_automation_add_get(webinterface, request, session):
            session.has_access('automation', '*', 'add', raise_error=True)
            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'run_on_start': webinterface.request_get_default(request, 'run_on_start', True),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
            }
            try:
                data['run_on_start'] = is_true_false(data['run_on_start'])
            except:
                webinterface.add_alert("Cannot add automation rule. run_on_start must be either true or false.",
                                       'warning')
                return page_automation_form(webinterface, request, session, 'add', data, "Add Automation Rule",)

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/add", "Add")
            return page_automation_form(webinterface, request, session, 'add', data, "Add Automation Rule")

        @webapp.route('/add', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_automation_add_post(webinterface, request, session):
            session.has_access('automation', '*', 'add', raise_error=True)
            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'run_on_start': webinterface.request_get_default(request, 'run_on_start', "true"),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
            }

            try:
                data['run_on_start'] = is_true_false(data['run_on_start'])
            except:
                webinterface.add_alert("Cannot add automation rule. run_on_start must be either true or false.",
                                       'warning')
                return page_automation_form(webinterface, request, session, 'add', data, "Add Automation rule",)
            try:
                rule = yield webinterface._Automation.add(data['label'], data['machine_label'],
                                                          data['description'], data['status'],
                                                          data['run_on_start'])
            except YomboWarning as e:
                webinterface.add_alert("Cannot add automation rule. %s" % e.message, 'warning')
                return page_automation_form(webinterface, request, session, 'add', data, "Add Automation rule",)

            webinterface.add_alert("New automation rule '%s' added." % rule.label)
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)

        @webapp.route('/<string:rule_id>/edit', methods=['GET'])
        @require_auth()
        def page_automation_edit_rule_get(webinterface, request, session, rule_id):
            session.has_access('automation', rule_id, 'edit', raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule.rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/edit" % rule.rule_id, "Edit")
            data = {
                'label': rule.label,
                'machine_label': rule.machine_label,
                'description':  rule.description(),
                'status': rule.effective_status(),
                'run_on_start': rule.data['config']['run_on_start'],
                'rule_id': rule_id
            }
            return page_automation_form(webinterface,
                                        request,
                                        session,
                                        'edit',
                                        data,
                                        "Edit Automation rule: %s" % rule.label)

        @webapp.route('/<string:rule_id>/edit', methods=['POST'])
        @require_auth()
        def page_automation_edit_rule_post(webinterface, request, session, rule_id):
            session.has_access('automation', rule_id, 'edit', raise_error=True)
            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'run_on_start': webinterface.request_get_default(request, 'run_on_start', True),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
                'rule_id': rule_id,
            }
            try:
                data['run_on_start'] = is_true_false(data['run_on_start'])
            except:
                webinterface.add_alert("Cannot add automation rule. run_on_start must be either true or false.",
                                       'warning')
                return page_automation_form(webinterface, request, session, 'add', data, "Add Automation rule",)

            try:
                rule = webinterface._Automation.edit(rule_id,
                                                     data['label'], data['machine_label'],
                                                     data['description'], data['status'],
                                                     data['run_on_start'])
            except YomboWarning as e:
                webinterface.add_alert("Cannot edit automation rule. %s" % e.message, 'warning')
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/automation/%s/details" % rule.rule_id, rule.label)
                webinterface.add_breadcrumb(request, "/automation/%s/edit", "Edit")

                return page_automation_form(webinterface, request, session, 'edit', data,
                                                        "Edit Automation rule: %s" % rule.label)

            webinterface.add_alert("Automation rule '%s' edited." % rule.label)
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)

        def page_automation_form(webinterface, request, session, action_type, rule, header_label):
            page = webinterface.get_template(
                request,
                webinterface.wi_dir + '/pages/automation/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               rule=rule,
                               action_type=action_type,
                               )

        @webapp.route('/<string:rule_id>/delete', methods=['GET'])
        @require_auth()
        def page_automation_delete_rule_get(webinterface, request, session, rule_id):
            session.has_access('automation', rule_id, 'delete', raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            page = webinterface.get_template(
                request,
                webinterface.wi_dir + '/pages/automation/delete.html'
            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/delete" % rule_id, "Delete")
            return page.render(alerts=webinterface.get_alerts(),
                               rule=rule,
                               )

        @webapp.route('/<string:rule_id>/delete', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_automation_delete_rule_post(webinterface, request, session, rule_id):
            session.has_access('automation', rule_id, 'delete', raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the automation rule.', 'warning')
                return webinterface.redirect(request, '/automation/%s/details' % rule_id)

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the automation rule.', 'warning')
                return webinterface.redirect(request,
                                             '/automation/%s/details' % rule_id)

            try:
                yield rule.delete(session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert("Cannot delete automation rule. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/automation/%s/details' % rule_id)

            webinterface.add_alert('Automation rule deleted. Will be fully removed from system on next restart.')
            return webinterface.redirect(request, '/automation/index')

        @webapp.route('/<string:rule_id>/disable', methods=['GET'])
        @require_auth()
        def page_automation_disable_rule_get(webinterface, request, session, rule_id):
            session.has_access('automation', rule_id, 'disable', raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/automation/disable.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule.rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/disable" % rule.rule_id, "Disable")
            return page.render(alerts=webinterface.get_alerts(),
                               rule=rule,
                               )

        @webapp.route('/<string:rule_id>/disable', methods=['POST'])
        @require_auth()
        def page_automation_disable_rule_post(webinterface, request, session, rule_id):
            session.has_access('automation', rule_id, 'disable', raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the automation rule.',
                                       'warning')
                return webinterface.redirect(request, '/automation/%s/details' % rule_id)

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the automation rule.',
                                       'warning')
                return webinterface.redirect(request, '/automation/%s/details' % rule_id)

            try:
                rule.disable(session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert("Cannot disable automation rule. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/automation/%s/details' % rule_id)

            msg = {
                'header': 'Automation rule Disabled',
                'label': 'Automation rule disabled successfully',
                'description': '<p>The automation rule has been disabled.'
                               '<p>Continue to:</p><ul>'
                               ' <li><strong><a href="/automation/index">Automation rule index</a></strong></li>'
                               ' <li><a href="/automation/%s/details">View the disabled automation rule</a></li>'
                               '<ul>' %
                               rule.rule_id,
            }

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule.rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/disable" % rule.rule_id, "Disable")
            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )

        @webapp.route('/<string:rule_id>/enable', methods=['GET'])
        @require_auth()
        def page_automation_enable_rule_get(webinterface, request, session, rule_id):
            session.has_access('automation', rule_id, 'enable', raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/automation/enable.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule.rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/enable" % rule.rule_id, "Enable")
            return page.render(alerts=webinterface.get_alerts(),
                               rule=rule,
                               )

        @webapp.route('/<string:rule_id>/enable', methods=['POST'])
        @require_auth()
        def page_automation_enable_rule_post(webinterface, request, session, rule_id):
            session.has_access('automation', rule_id, 'enable', raise_error=True)
            try:
                rule = webinterface._Automation.get(rule_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')
            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the automation rule.', 'warning')
                return webinterface.redirect(request, '/automation/%s/details' % rule_id)

            if confirm != "enable":
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the automation rule.', 'warning')
                return webinterface.redirect(request, '/automation/%s/details' % rule_id)

            try:
                rule.enable(session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert("Cannot enable automation rule. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/automation/%s/details' % rule_id)

            webinterface.add_alert("Automation rule '%s' enabled." % rule.label)
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)

        @webapp.route('/<string:rule_id>/move_up/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_automation_action_move_up_get(webinterface, request, session, rule_id, action_id):
            session.has_access('automation', rule_id, 'edit', raise_error=True)
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

            try:
                webinterface._Automation.move_action_up(rule_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Cannot move action up. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/automation/%s/details' % rule_id)

            webinterface.add_alert("Action moved up.")
            return webinterface.redirect(request, '/automation/%s/details' % rule_id)

        @webapp.route('/<string:rule_id>/move_down/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_automation_action_move_down_get(webinterface, request, session, rule_id, action_id):
            session.has_access('automation', rule_id, 'edit', raise_error=True)
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

            try:
                webinterface._Automation.move_action_down(rule_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Cannot move action down. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/automation/%s/details' % rule_id)

            webinterface.add_alert("Action moved up.")
            return webinterface.redirect(request, '/automation/%s/details' % rule_id)

        @webapp.route('/<string:rule_id>/duplicate_automation', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_automation_duplicate_rule_get(webinterface, request, session, rule_id):
            session.has_access('automation', rule_id, 'add', raise_error=True)
            session.has_access('automation', rule_id, 'view', raise_error=True)
            try:
                rule = webinterface._Automation[rule_id]
            except KeyError as e:
                webinterface.add_alert("Requested automation rule doesn't exist.", 'warning')
                return webinterface.redirect(request, '/automation/index')

            try:
                yield webinterface._Automation.duplicate_automation_rule(rule_id)
            except YomboWarning as e:
                webinterface.add_alert("Cannot duplicate automation rule. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            webinterface.add_alert("Automation rule dupllicated.")
            return webinterface.redirect(request, '/automation/index')
