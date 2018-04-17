# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the automation rule handling for /automation sub directory.

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

logger = get_logger("library.webinterface.routes.automation.scene")


def route_automation_scene(webapp):
    with webapp.subroute("/automation") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/automation/index", "Automation Rule")

        @webapp.route('/<string:rule_id>/add_action_scene', methods=['GET'])
        @require_auth()
        def page_automation_action_scene_add_get(webinterface, request, session, rule_id):
            try:
                rule = webinterface._Automation[rule_id]
            except KeyError as e:
                webinterface.add_alert("Requested automation rule doesn't exist.", 'warning')
                return webinterface.redirect(request, '/automation/index')

            data = {
                'action_type': 'scene',
                'scene_machine_label': webinterface.request_get_default(request, 'scene_machine_label', ""),
                'action': webinterface.request_get_default(request, 'action', ""),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Automation.get_action_items(rule_id)) + 1) * 10)),
            }

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_automation_form_scene(webinterface, request, session, rule, data, 'add',
                                              "Add a scene to automation rule")

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/add_action_scene" % rule_id, "Add Item: Pause")
            return page_automation_form_scene(webinterface, request, session, rule, data, 'add',
                                          "Add a scene control to automation rule")

        @webapp.route('/<string:rule_id>/add_action_scene', methods=['POST'])
        @require_auth()
        def page_automation_action_scene_add_post(webinterface, request, session, rule_id):
            try:
                rule = webinterface._Automation[rule_id]
            except KeyError as e:
                webinterface.add_alert("Requested automation rule doesn't exist.", 'warning')
                return webinterface.redirect(request, '/automation/index')

            data = {
                'action_type': 'scene',
                'scene_machine_label': webinterface.request_get_default(request, 'scene_machine_label', ""),
                'action': webinterface.request_get_default(request, 'action', ""),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Automation.get_action_items(rule_id)) + 1) * 10)),
            }

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_automation_form_scene(webinterface, request, session, rule, data, 'add',
                                              "Add a scene control to automation rule")

            try:
                webinterface._Automation.add_action_item(rule_id, **data)
            except YomboWarning as e:
                webinterface.add_alert("Cannot add scene control to automation rule. %s" % e.message, 'warning')
                return page_automation_form_scene(webinterface, request, session, rule, data, 'add',
                                              "Add a scene control to automation rule")

            webinterface.add_alert("Added scene control to automation rule.")
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)

        @webapp.route('/<string:rule_id>/edit_action_scene/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_automation_action_scene_edit_get(webinterface, request, session, rule_id, action_id):
            try:
                rule = webinterface._Automation[rule_id]
            except KeyError as e:
                webinterface.add_alert("Requested automation rule doesn't exist.", 'warning')
                return webinterface.redirect(request, '/automation/index')
            try:
                item = webinterface._Automation.get_action_items(rule_id, action_id)
            except KeyError as e:
                webinterface.add_alert("Requested item for rule doesn't exist.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)
            if item['action_type'] != 'scene':
                webinterface.add_alert("Requested action type is invalid: %s" % item['action_type'], 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule.rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/edit_action_scene" % rule.rule_id, "Edit action: Scene Control")
            return page_automation_form_scene(webinterface, request, session, rule, item, 'edit',
                                          "Edit automtion rule action: Scene control")

        @webapp.route('/<string:rule_id>/edit_action_scene/<string:action_id>', methods=['POST'])
        @require_auth()
        def page_automation_action_scene_edit_post(webinterface, request, session, rule_id, action_id):
            try:
                rule = webinterface._Automation[rule_id]
            except KeyError as e:
                webinterface.add_alert("Requested automation rule doesn't exist.", 'warning')
                return webinterface.redirect(request, '/automation/index')
            try:
                item = webinterface._Automation.get_action_items(rule_id, action_id)
            except KeyError as e:
                webinterface.add_alert("Requested item for rule doesn't exist.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)
            if item['action_type'] != 'scene':
                webinterface.add_alert("Requested action type is invalid: %s" % item['action_type'], 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)


            data = {
                'action_type': 'scene',
                'scene_machine_label': webinterface.request_get_default(request, 'scene_machine_label', ""),
                'action': webinterface.request_get_default(request, 'action', ""),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Automation.get_action_items(rule_id)) + 1) * 10)),
            }

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_automation_form_scene(webinterface, request, session, rule, data, 'add',
                                              "Edit automation action: Scene control")

            try:
                webinterface._Automation.edit_action_item(rule_id, action_id, **data)
            except YomboWarning as e:
                webinterface.add_alert("Cannot edit scene control within automation rule. %s" % e.message, 'warning')
                return page_automation_form_scene(webinterface, request, session, rule, data, 'add',
                                              "Edit automation action: Scene control")

            webinterface.add_alert("Edited automation rule for scene '%s'." % rule.label)
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)

        def page_automation_form_scene(webinterface, request, session, rule, data, action_type, header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/automation/form_action_scene.html')

            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               rule=rule,
                               data=data,
                               action_type=action_type,
                               )

        @webapp.route('/<string:rule_id>/delete_action_scene/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_automation_action_scene_delete_get(webinterface, request, session, rule_id, action_id):
            try:
                rule = webinterface._Automation[rule_id]
            except KeyError as e:
                webinterface.add_alert("Requested automation rule doesn't exist.", 'warning')
                return webinterface.redirect(request, '/automation/index')
            try:
                item = webinterface._Automation.get_action_items(rule_id, action_id)
            except KeyError as e:
                webinterface.add_alert("Requested item for rule doesn't exist.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)
            if item['action_type'] != 'scene':
                webinterface.add_alert("Requested action type is invalid: %s" % item['action_type'], 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/automation/delete_action_scene.html'
                                            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/automation/%s/details" % rule_id, rule.label)
            webinterface.add_breadcrumb(request, "/automation/%s/delete_action_scene" % rule_id, "Delete action: Scene Control")
            return page.render(alerts=webinterface.get_alerts(),
                               rule=rule,
                               item=item,
                               action_id=action_id,
                               )

        @webapp.route('/<string:rule_id>/delete_action_scene/<string:action_id>', methods=['POST'])
        @require_auth()
        def page_automation_action_scene_delete_post(webinterface, request, session, rule_id, action_id):
            try:
                rule = webinterface._Automation[rule_id]
            except KeyError as e:
                webinterface.add_alert("Requested automation rule doesn't exist.", 'warning')
                return webinterface.redirect(request, '/automation/index')
            try:
                item = webinterface._Automation.get_action_items(rule_id, action_id)
            except KeyError as e:
                webinterface.add_alert("Requested item for rule doesn't exist.", 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)
            if item['action_type'] != 'scene':
                webinterface.add_alert("Requested action type is invalid: %s" % item['action_type'], 'warning')
                return webinterface.redirect(request, "/automation/%s/details" % rule_id)

            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the scene control from the automation rule.', 'warning')
                return webinterface.redirect(request,
                                             '/automation/%s/delete_action_scene/%s' % (rule_id, action_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the scene control from the automation rule.', 'warning')
                return webinterface.redirect(request,
                                             '/automation/%s/delete_action_scene/%s' % (rule_id, action_id))

            try:
                webinterface._Automation.delete_action_item(rule_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Cannot delete scene control from automation rule. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/automation/index')

            webinterface.add_alert("Deleted scene item for automation rule.")
            return webinterface.redirect(request, "/automation/%s/details" % rule.rule_id)
