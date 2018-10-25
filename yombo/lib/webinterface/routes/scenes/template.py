# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the template handling for /scenes sub directory.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.18.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/routes/scenes.py>`_
"""
# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.routes.scenes.template")


def route_scenes_template(webapp):
    with webapp.subroute("/scenes") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/scenes/index", "Scenes")

        @webapp.route('/<string:scene_id>/add_template', methods=['GET'])
        @require_auth()
        def page_scenes_action_template_add_get(webinterface, request, session, scene_id):
            session.has_access('scene', scene_id, 'edit', raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            data = {
                'action_type': 'template',
                'description': webinterface.request_get_default(request, 'description', ""),
                'template': webinterface.request_get_default(request, 'template', ""),
                'weight': webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.get_action_items(scene_id)) + 1) * 10),
            }

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_scenes_form_template(webinterface, request, session, scene, data, 'add', "Add a template to scene")

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/add_template" % scene_id, "Add action: Template")
            return page_scenes_form_template(webinterface, request, session, scene, data, 'add', "Add a template to scene")

        @webapp.route('/<string:scene_id>/add_template', methods=['POST'])
        @require_auth()
        def page_scenes_action_template_add_post(webinterface, request, session, scene_id):
            session.has_access('scene', scene_id, 'edit', raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            data = {
                'action_type': 'template',
                'description': webinterface.request_get_default(request, 'description', ""),
                'template': webinterface.request_get_default(request, 'template', ""),
                'weight': webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.get_action_items(scene_id)) + 1) * 10),
            }

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_scenes_form_template(webinterface, request, session, scene, data, 'add', "Add a template to scene")

            try:
                webinterface._Scenes.add_action_item(scene_id, **data)
            except KeyError as e:
                webinterface.add_alert("Cannot add template to scene. %s" % e.message, 'warning')
                return page_scenes_form_template(webinterface, request, session, scene, data, 'add', "Add a template to scene")

            webinterface.add_alert("Added template action to scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        @webapp.route('/<string:scene_id>/edit_template/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_scenes_action_template_edit_get(webinterface, request, session, scene_id, action_id):
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')
            try:
                action = webinterface._Scenes.get_action_items(scene_id, action_id)
            except KeyError as e:
                webinterface.add_alert("Requested action id could not be located.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)
            if action['action_type'] != 'template':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/edit_template" % scene.scene_id, "Edit action: Template")
            return page_scenes_form_template(webinterface, request, session, scene, action, 'edit',
                                              "Edit scene action: Template")

        @webapp.route('/<string:scene_id>/edit_template/<string:action_id>', methods=['POST'])
        @require_auth()
        def page_scenes_action_template_edit_post(webinterface, request, session, scene_id, action_id):
            session.has_access('scene', scene_id, 'edit', raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')
            try:
                action = webinterface._Scenes.get_action_items(scene_id, action_id)
            except KeyError as e:
                webinterface.add_alert("Requested action id could not be located.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)
            if action['action_type'] != 'template':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)

            data = {
                'action_type': 'template',
                'description': webinterface.request_get_default(request, 'description', ""),
                'template': webinterface.request_get_default(request, 'template', 5),
                'weight': webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.get_action_items(scene_id)) + 1) * 10),
            }

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_scenes_form_template(webinterface, request, session, scene, data, 'add', "Add a template to scene")

            try:
                webinterface._Scenes.edit_action_item(scene_id, action_id, **data)
            except KeyError as e:
                webinterface.add_alert("Cannot edit template within scene. %s" % e.message, 'warning')
                return page_scenes_form_template(webinterface, request, session, scene, data, 'add', "Edit scene action: Template")

            webinterface.add_alert("Edited a template action for scene '%s'." % scene.label)
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        def page_scenes_form_template(webinterface, request, session, scene, data, action_type, header_label):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/scenes/form_template.html')

            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               scene=scene,
                               data=data,
                               action_type=action_type,
                               )

        @webapp.route('/<string:scene_id>/delete_template/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_scenes_action_template_delete_get(webinterface, request, session, scene_id, action_id):
            session.has_access('scene', scene_id, 'edit', raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')
            try:
                action = webinterface._Scenes.get_action_items(scene_id, action_id)
            except KeyError as e:
                webinterface.add_alert("Requested action id could not be located.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)
            if action['action_type'] != 'template':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)

            page = webinterface.get_template(
                request,
                webinterface.wi_dir + '/pages/scenes/delete_template.html'
            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/delete_template" % scene_id, "Delete action: Template")
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               action=action,
                               action_id=action_id,
                               )

        @webapp.route('/<string:scene_id>/delete_template/<string:action_id>', methods=['POST'])
        @require_auth()
        def page_scenes_action_template_delete_post(webinterface, request, session, scene_id, action_id):
            session.has_access('scene', scene_id, 'edit', raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')
            try:
                action = webinterface._Scenes.get_action_items(scene_id, action_id)
            except KeyError as e:
                webinterface.add_alert("Requested action id could not be located.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)
            if action['action_type'] != 'template':
                webinterface.add_alert("Requested action type is invalid.", 'warning')
                return webinterface.redirect(request, "/scenes/%s/details" % scene_id)
            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the template from the scene.', 'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/delete_template/%s' % (scene_id, action_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the template from the scene.', 'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/delete_template/%s' % (scene_id, action_id))

            try:
                webinterface._Scenes.delete_scene_item(scene_id, action_id)
            except KeyError as e:
                webinterface.add_alert("Cannot delete template from scene. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            webinterface.add_alert("Deleted template action for scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)
