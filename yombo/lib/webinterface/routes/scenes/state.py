# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the state handling for /scenes sub directory.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.18.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/routes/scenes.py>`_
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

logger = get_logger("library.webinterface.routes.scenes.state")


def route_scenes_state(webapp):
    with webapp.subroute("/scenes") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/scenes/index", "Scenes")

        @webapp.route('/<string:scene_id>/add_state', methods=['GET'])
        @require_auth()
        def page_scenes_action_state_add_get(webinterface, request, session, scene_id):
            session.has_access('scene:%s' % scene_id, 'edit', raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            data = {
                'action_type': 'state',
                'name': webinterface.request_get_default(request, 'name', ""),
                'value': webinterface.request_get_default(request, 'value', ""),
                'value_type': webinterface.request_get_default(request, 'value_type', ""),
                'gateway_id': webinterface.request_get_default(request, 'gateway_id', webinterface.gateway_id()),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.get_action_items(scene_id)) + 1) * 10)),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/add_state" % scene_id, "Add action: State")
            return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Add state to scene")

        @webapp.route('/<string:scene_id>/add_state', methods=['POST'])
        @require_auth()
        def page_scenes_action_state_add_post(webinterface, request, session, scene_id):
            session.has_access('scene:%s' % scene_id, 'edit', raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            data = {
                'action_type': 'state',
                'name': webinterface.request_get_default(request, 'name', ""),
                'value': webinterface.request_get_default(request, 'value', ""),
                'value_type': webinterface.request_get_default(request, 'value_type', ""),
                'gateway_id': webinterface.request_get_default(request, 'gateway_id', webinterface.gateway_id()),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.get_action_items(scene_id)) + 1) * 10)),
            }

            if data['name'] == "":
                webinterface.add_alert('Must enter a state name.', 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Add state to scene")

            if data['value'] == "":
                webinterface.add_alert('Must enter a state value to set.', 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Add state to scene")

            if data['value_type'] == "" or data['value_type'] not in ('integer', 'string', 'boolean', 'float'):
                webinterface.add_alert('Must enter a state value_type to ensure validity.', 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Add state to scene")

            value_type = data['value_type']
            if value_type == "string":
                data['value'] = coerce_value(data['value'], 'string')
            elif value_type == "integer":
                try:
                    data['value'] = coerce_value(data['value'], 'int')
                except Exception:
                    webinterface.add_alert("Cannot coerce state value into an integer", 'warning')
                    return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Add state to scene")
            elif value_type == "float":
                try:
                    data['value'] = coerce_value(data['value'], 'float')
                except Exception:
                    webinterface.add_alert("Cannot coerce state value into an float", 'warning')
                    return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Add state to scene")
            elif value_type == "boolean":
                try:
                    data['value'] = coerce_value(data['value'], 'bool')
                    if isinstance(data['value'], bool) is False:
                        raise Exception()
                except Exception:
                    webinterface.add_alert("Cannot coerce state value into an boolean", 'warning')
                    return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Add state to scene")

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Add state to scene")

            try:
                webinterface._Scenes.add_action_item(scene_id, **data)
            except YomboWarning as e:
                webinterface.add_alert("Cannot add state to scene. %s" % e.message, 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Add state to scene")

            webinterface.add_alert("Added state action to scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        @webapp.route('/<string:scene_id>/edit_state/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_scenes_action_state_edit_get(webinterface, request, session, scene_id, action_id):
            session.has_access('scene:%s' % scene_id, 'edit', raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')
            try:
                action = webinterface._Scenes.get_action_items(scene_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Requested action id could not be located.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)
            if action['action_type'] != 'state':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/edit_state" % scene.scene_id, "Edit action: State")
            return page_scenes_form_state(webinterface, request, session, scene, action, 'edit',
                                          "Edit scene action: State")

        @webapp.route('/<string:scene_id>/edit_state/<string:action_id>', methods=['POST'])
        @require_auth()
        def page_scenes_action_state_edit_post(webinterface, request, session, scene_id, action_id):
            session.has_access('scene:%s' % scene_id, 'edit', raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')
            try:
                action = webinterface._Scenes.get_action_items(scene_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Requested action id could not be located.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)
            if action['action_type'] != 'state':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)

            data = {
                'action_type': 'state',
                'name': webinterface.request_get_default(request, 'name', ""),
                'value': webinterface.request_get_default(request, 'value', ""),
                'value_type': webinterface.request_get_default(request, 'value_type', ""),
                'gateway_id': webinterface.request_get_default(request, 'gateway_id', webinterface.gateway_id()),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.get_action_items(scene_id)) + 1) * 10)),
            }

            if data['name'] == "":
                webinterface.add_alert('Must enter a state name.', 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Edit scene action: State")

            if data['value'] == "":
                webinterface.add_alert('Must enter a state value to set.', 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Edit scene action: State")

            if data['value_type'] == "" or data['value_type'] not in ('integer', 'string', 'boolean', 'float'):
                webinterface.add_alert('Must enter a state value_type to ensure validity.', 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Edit scene action: State")

            value_type = data['value_type']
            if value_type == "string":
                data['value'] = coerce_value(data['value'], 'string')
            elif value_type == "integer":
                try:
                    data['value'] = coerce_value(data['value'], 'int')
                except Exception:
                    webinterface.add_alert("Cannot coerce state value into an integer", 'warning')
                    return page_scenes_form_state(webinterface, request, session, scene, data, 'add',
                                                      "Edit scene action: State")
            elif value_type == "float":
                try:
                    data['value'] = coerce_value(data['value'], 'float')
                except Exception:
                    webinterface.add_alert("Cannot coerce state value into an float", 'warning')
                    return page_scenes_form_state(webinterface, request, session, scene, data, 'add',
                                                      "Edit scene action: State")
            elif value_type == "boolean":
                try:
                    data['value'] = coerce_value(data['value'], 'bool')
                    if isinstance(data['value'], bool) is False:
                        raise Exception()
                except Exception:
                    webinterface.add_alert("Cannot coerce state value into an boolean", 'warning')
                    return page_scenes_form_state(webinterface, request, session, scene, data, 'add',
                                                      "Edit scene action: State")
            else:
                webinterface.add_alert("Unknown value type.", 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add',
                                                  "Edit scene action: State")

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Edit scene action: State")

            try:
                webinterface._Scenes.edit_action_item(scene_id, action_id, **data)
            except YomboWarning as e:
                webinterface.add_alert("Cannot edit state within scene. %s" % e.message, 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Edit scene action: State")

            webinterface.add_alert("Edited state action for scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        def page_scenes_form_state(webinterface, request, session, scene, data, action_type, header_label):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/scenes/form_state.html')

            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               scene=scene,
                               data=data,
                               action_type=action_type,
                               )

        @webapp.route('/<string:scene_id>/delete_state/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_scenes_action_state_delete_get(webinterface, request, session, scene_id, action_id):
            session.has_access('scene:%s' % scene_id, 'edit', raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')
            try:
                action = webinterface._Scenes.get_action_items(scene_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Requested action id could not be located.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)
            if action['action_type'] != 'state':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)

            page = webinterface.get_template(
                request,
                webinterface.wi_dir + '/pages/scenes/delete_state.html'
            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/delete_state" % scene_id, "Delete action: State")
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               action=action,
                               action_id=action_id,
                               )

        @webapp.route('/<string:scene_id>/delete_state/<string:action_id>', methods=['POST'])
        @require_auth()
        def page_scenes_action_state_delete_post(webinterface, request, session, scene_id, action_id):
            session.has_access('scene:%s' % scene_id, 'edit', raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')
            try:
                action = webinterface._Scenes.get_action_items(scene_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Requested action id could not be located.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)
            if action['action_type'] != 'state':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)

            try:
                confirm = request.args.get('confirm')[0]
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the state from the scene.', 'warning')
            except:
                return webinterface.redirect(request,
                                             '/scenes/%s/delete_state/%s' % (scene_id, action_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the state from the scene.', 'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/delete_state/%s' % (scene_id, action_id))

            try:
                webinterface._Scenes.delete_scene_item(scene_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Cannot delete state from scene. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            webinterface.add_alert("Deleted state action for scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)
