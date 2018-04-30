# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/scenes" sub-route of the web interface.

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

from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.routes.scenes")


def route_scenes(webapp):
    with webapp.subroute("/scenes") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/scenes/index", "Scenes")

        @webapp.route('/')
        @require_auth()
        def page_scenes(webinterface, request, session):
            return webinterface.redirect(request, '/scenes/index')

        @webapp.route('/index')
        @require_auth()
        def page_scenes_index(webinterface, request, session):
            root_breadcrumb(webinterface, request)
            page = webinterface.get_template(request, webinterface._dir + 'pages/scenes/index.html')
            return page.render(
                alerts=webinterface.get_alerts(),
                )

        @webapp.route('/<string:scene_id>/details', methods=['GET'])
        @require_auth()
        def page_scenes_details_get(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            page = webinterface.get_template(
                request,
                webinterface._dir + 'pages/scenes/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               )

        @webapp.route('/<string:scene_id>/start', methods=['GET'])
        @require_auth()
        def page_scenes_trigger_get(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                webinterface._Scenes.start(scene_id)
            except YomboWarning as e:
                webinterface.add_alert("Cannot start scene. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            webinterface.add_alert("The scene '%s' has been started" % scene.label)
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        @webapp.route('/<string:scene_id>/stop', methods=['GET'])
        @require_auth()
        def page_scenes_stop_trigger_get(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                webinterface._Scenes.stop(scene_id)
            except YomboWarning as e:
                webinterface.add_alert("Cannot stop scene. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            webinterface.add_alert("The scene '%s' has been stopped" % scene.label)
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        @webapp.route('/add', methods=['GET'])
        @require_auth()
        def page_scenes_add_get(webinterface, request, session):
            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/add", "Add")
            return page_scenes_form(webinterface, request, session, 'add', data, "Add Scene")

        @webapp.route('/add', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_scenes_add_post(webinterface, request, session):
            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
            }

            try:
                scene = yield webinterface._Scenes.add(data['label'], data['machine_label'],
                                                       data['description'], data['status'])
            except YomboWarning as e:
                webinterface.add_alert("Cannot add scene. %s" % e.message, 'warning')
                return page_scenes_form(webinterface, request, session, 'add', data, "Add Scene",)

            webinterface.add_alert("New scene '%s' added." % scene.label)
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        @webapp.route('/<string:scene_id>/edit', methods=['GET'])
        @require_auth()
        def page_scenes_edit_get(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/edit" % scene.scene_id, "Edit")
            data = {
                'label': scene.label,
                'machine_label': scene.machine_label,
                'description':  scene.description(),
                'status': scene.effective_status(),
                'scene_id': scene_id
            }
            return page_scenes_form(webinterface,
                                    request,
                                    session,
                                    'edit',
                                    data,
                                    "Edit Scene: %s" % scene.label)

        @webapp.route('/<string:scene_id>/edit', methods=['POST'])
        @require_auth()
        def page_scenes_edit_post(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
                'scene_id': scene_id,
            }

            try:
                scene = webinterface._Scenes.edit(scene_id,
                                                  data['label'], data['machine_label'],
                                                  data['description'], data['status'])
            except YomboWarning as e:
                webinterface.add_alert("Cannot edit scene. %s" % e.message, 'warning')
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
                webinterface.add_breadcrumb(request, "/scenes/%s/edit", "Edit")

                return page_scenes_form(webinterface, request, session, 'edit', data,
                                                        "Edit Scene: %s" % scene.label)

            webinterface.add_alert("Scene '%s' edited." % scene.label)
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        def page_scenes_form(webinterface, request, session, action_type, scene, header_label):
            page = webinterface.get_template(
                request,
                webinterface._dir + 'pages/scenes/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               scene=scene,
                               action_type=action_type,
                               )

        @webapp.route('/<string:scene_id>/delete', methods=['GET'])
        @require_auth()
        def page_scenes_details_post(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            page = webinterface.get_template(
                request,
                webinterface._dir + 'pages/scenes/delete.html'
            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/delete" % scene_id, "Delete")
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               )

        @webapp.route('/<string:scene_id>/delete', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_scenes_delete_post(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the scene.', 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the scene.', 'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/details' % scene_id)

            try:
                yield scene.delete(session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert("Cannot delete scene. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            webinterface.add_alert('Scene deleted. Will be fully removed from system on next restart.')
            return webinterface.redirect(request, '/scenes/index')

        @webapp.route('/<string:scene_id>/disable', methods=['GET'])
        @require_auth()
        def page_scenes_disable_get(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/scenes/disable.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/disable" % scene.scene_id, "Disable")
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               )

        @webapp.route('/<string:scene_id>/disable', methods=['POST'])
        @require_auth()
        def page_scenes_disable_post(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the scene.',
                                       'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the scene.',
                                       'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            try:
                scene.disable(session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert("Cannot disable scene. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            msg = {
                'header': 'Scene Disabled',
                'label': 'Scene disabled successfully',
                'description': '<p>The scene has been disabled.'
                               '<p>Continue to:</p><ul>'
                               ' <li><strong><a href="/scenes/index">Scene index</a></strong></li>'
                               ' <li><a href="/scenes/%s/details">View the disabled scene</a></li>'
                               '<ul>' %
                               scene.scene_id,
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/disable" % scene.scene_id, "Disable")
            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )

        @webapp.route('/<string:scene_id>/enable', methods=['GET'])
        @require_auth()
        def page_scenes_enable_get(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/scenes/enable.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/enable" % scene.scene_id, "Enable")
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               )

        @webapp.route('/<string:scene_id>/enable', methods=['POST'])
        @require_auth()
        def page_scenes_enable_post(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')
            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the scene.', 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            if confirm != "enable":
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the scene.', 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            try:
                scene.enable(session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert("Cannot enable scene. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            webinterface.add_alert("Scene '%s' enabled." % scene.label)
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        @webapp.route('/<string:scene_id>/move_up/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_scenes_action_move_up_get(webinterface, request, session, scene_id, action_id):
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

            try:
                webinterface._Scenes.move_action_up(scene_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Cannot move action up. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            webinterface.add_alert("Action moved up.")
            return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

        @webapp.route('/<string:scene_id>/move_down/<string:action_id>', methods=['GET'])
        @require_auth()
        def page_scenes_action_move_down_get(webinterface, request, session, scene_id, action_id):
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

            try:
                webinterface._Scenes.move_action_down(scene_id, action_id)
            except YomboWarning as e:
                webinterface.add_alert("Cannot move action down. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            webinterface.add_alert("Action moved down.")
            return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

        @webapp.route('/<string:scene_id>/duplicate_scene', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_scenes_duplicate_scene_get(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes.get(scene_id)
            except YomboWarning as e:
                webinterface.add_alert(e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                yield webinterface._Scenes.duplicate_scene(scene_id)
            except YomboWarning as e:
                webinterface.add_alert("Cannot duplicate scene. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            webinterface.add_alert("Scene dupllicated.")
            return webinterface.redirect(request, '/scenes/index')
