# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the device handling for /scenes sub directory.

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

logger = get_logger("library.webinterface.routes.scenes.device")


def route_scenes_device(webapp):
    with webapp.subroute("/scenes") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/scenes/index", "Scenes")

        @webapp.route('/<string:scene_id>/add_device', methods=['GET'])
        @require_auth()
        def page_scenes_action_device_add_get(webinterface, request, session, scene_id):
            session.has_access('scene', scene_id, 'edit', raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            data = {
                'action_id': None,
                'action_type': 'device',
                'device_machine_label': webinterface.request_get_default(request, 'device_machine_label', ""),
                'command_machine_label': webinterface.request_get_default(request, 'command_machine_label', ""),
                'inputs': webinterface.request_get_default(request, 'inputs', ""),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.get_action_items(scene_id)) + 1) * 10)),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/add_device" % scene_id, "Add action: Device")
            return page_scenes_form_device(webinterface, request, session, scene, data, 'add',
                                           "Add device to scene")

        @webapp.route('/<string:scene_id>/add_device', methods=['POST'])
        @require_auth()
        def page_scenes_action_device_add_post(webinterface, request, session, scene_id):
            session.has_access('scene', scene_id, 'edit', raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                incoming_data = json.loads(webinterface.request_get_default(request, 'json_output', "{}"))
            except Exception as e:
                webinterface.add_alert("Error decoding request data.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)
            keep_attributes = ['device_machine_label', 'command_machine_label', 'inputs', 'weight']
            data = {k: incoming_data[k] for k in keep_attributes if k in incoming_data}
            data['action_type'] = 'device'
            if 'device_machine_label' not in data:
                webinterface.add_alert("Device machine label information is missing.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)
            try:
                device = webinterface._Devices[data['device_machine_label']]
            except Exception as e:
                webinterface.add_alert("Device could not be found.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)

            if 'command_machine_label' not in data:
                webinterface.add_alert("Command machine label information is missing.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)
            try:
                command = webinterface._Commands[data['command_machine_label']]
            except Exception as e:
                webinterface.add_alert("Device could not be found.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)

            if 'inputs' not in data:
                data['inputs'] = {}

            if 'weight' not in data:
                data['weight'] = 40000
            else:
                try:
                    data['weight'] = int(data['weight'])
                except Exception as e:
                    webinterface.add_alert("Weight must be a whole number.", 'warning')
                    return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)
            if 'scene_id' in data:
                del data['scene_id']
            if 'action_id' in data:
                del data['action_id']

            # TODO: handle encrypted input values....

            try:
                webinterface._Scenes.add_action_item(scene_id, **data)
            except YomboWarning as e:
                webinterface.add_alert("Cannot add device to scene. %s" % e.message, 'warning')
                return page_scenes_form_device(webinterface, request, session, scene, data, 'add',
                                               "Add device to scene")

            webinterface.add_alert("Added device action to scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        @webapp.route('/<string:scene_id>/edit_device/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_scenes_action_device_edit_get(webinterface, request, session, scene_id, action_id):
            session.has_access('scene', scene_id, 'edit', raise_error=True)
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
            if action['action_type'] != 'device':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/edit_device" % scene.scene_id, "Edit action: Device")
            return page_scenes_form_device(webinterface, request, session, scene, action, 'edit',
                                           "Edit scene action: Device")

        @webapp.route('/<string:scene_id>/edit_device/<string:action_id>', methods=['POST'])
        @require_auth()
        def page_scenes_action_device_edit_post(webinterface, request, session, scene_id, action_id):
            session.has_access('scene', scene_id, 'edit', raise_error=True)
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
            if action['action_type'] != 'device':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)

            try:
                incoming_data = json.loads(webinterface.request_get_default(request, 'json_output', "{}"))
            except Exception as e:
                webinterface.add_alert("Error decoding request data.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)
            keep_attributes = ['device_machine_label', 'command_machine_label', 'inputs', 'weight']
            data = {k: incoming_data[k] for k in keep_attributes if k in incoming_data}
            data['action_type'] = 'device'

            if 'device_machine_label' not in data:
                webinterface.add_alert("Device machine label information is missing.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)
            try:
                device = webinterface._Devices[data['device_machine_label']]
            except Exception as e:
                webinterface.add_alert("Device could not be found.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)

            if 'command_machine_label' not in data:
                webinterface.add_alert("Command machine label information is missing.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)
            try:
                command = webinterface._Commands[data['command_machine_label']]
            except Exception as e:
                webinterface.add_alert("Device could not be found.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)

            if 'inputs' not in data:
                data['inputs'] = {}

            if 'weight' not in data:
                data['weight'] = 40000
            else:
                try:
                    data['weight'] = int(data['weight'])
                except Exception as e:
                    webinterface.add_alert("Weight must be a whole number.", 'warning')
                    return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)
            if 'scene_id' in data:
                del data['scene_id']
            if 'action_id' in data:
                del data['action_id']

            # TODO: handle encrypted input values....

            try:
                webinterface._Scenes.edit_action_item(scene_id, action_id, **data)
            except YomboWarning as e:
                webinterface.add_alert("Cannot edit device within scene. %s" % e.message, 'warning')
                return page_scenes_form_device(webinterface, request, session, scene, data, 'add',
                                               "Add device to scene")

            webinterface.add_alert("Updated device action for scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        def page_scenes_form_device(webinterface, request, session, scene, data, action_type, header_label):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/scenes/form_device.html')

            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               scene=scene,
                               data=data,
                               action_type=action_type,
                               )

        @webapp.route('/<string:scene_id>/delete_device/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_scenes_action_device_delete_get(webinterface, request, session, scene_id, action_id):
            session.has_access('scene', scene_id, 'edit', raise_error=True)
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
            if action['action_type'] != 'device':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)

            page = webinterface.get_template(
                request,
                webinterface.wi_dir + '/pages/scenes/delete_device.html'
            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/delete_device" % scene_id, "Delete action: Device")
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               action=action,
                               action_id=action_id,
                               )

        @webapp.route('/<string:scene_id>/delete_device/<string:action_id>', methods=['POST'])
        @require_auth()
        def page_scenes_action_device_delete_post(webinterface, request, session, scene_id, action_id):
            session.has_access('scene', scene_id, 'edit', raise_error=True)
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
            if action['action_type'] != 'device':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)

            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the device from the scene.', 'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/delete_device/%s' % (scene_id, action_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the device from the scene.', 'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/delete_device/%s' % (scene_id, action_id))

            try:
                webinterface._Scenes.delete_scene_item(scene_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Cannot delete device from scene. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            webinterface.add_alert("Deleted device action for scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)
