# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/scenes" sub-route of the web interface.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.17.0

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
from yombo.utils.datatypes import coerce_value

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
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene doesn't exist: %s" % scene_id, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            page = webinterface.get_template(
                request,
                webinterface._dir + 'pages/scenes/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               )

        @webapp.route('/<string:scene_id>/trigger', methods=['GET'])
        @require_auth()
        def page_scenes_trigger_get(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene doesn't exist: %s" % scene_id, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            webinterface._Scenes.trigger(scene_id)
            webinterface.add_alert("The scene '%s' has been triggered" % scene.label)
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        @webapp.route('/<string:scene_id>/stop_trigger', methods=['GET'])
        @require_auth()
        def page_scenes_stop_trigger_get(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene doesn't exist: %s" % scene_id, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            webinterface._Scenes.stop_trigger(scene_id)
            webinterface.add_alert("The scene '%s' trigger has been stopped" % scene.label)
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
            print("111")
            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
            }

            print("111 2")
            try:
                print("111 3")
                scene = yield webinterface._Scenes.add(data['label'], data['machine_label'],
                                                       data['description'], data['status'])
                print("111 4")
            except YomboWarning as e:
                webinterface.add_alert(e, 'warning')
                return page_scenes_form(webinterface, request, session, 'add', data, "Add Scene",)

            webinterface.add_alert("New scene '%s' added." % scene.label)
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        @webapp.route('/<string:scene_id>/edit', methods=['GET'])
        @require_auth()
        def page_scenes_edit_get(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/edit" % scene.scene_id, "Edit")
            data = scene.asdict()
            data['scene_id'] = scene_id
            return page_scenes_form(webinterface,
                                    request,
                                    session,
                                    'edit',
                                    data,
                                    "Edit Scene: %s" % scene.label)

        @webapp.route('/<string:scene_id>/edit', methods=['POST'])
        @require_auth()
        def page_scenes_edit_post(webinterface, request, session, scene_id):
            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
            }

            try:
                scene = webinterface._Scenes.edit(scene_id,
                                                  data['label'], data['machine_label'],
                                                  data['description'], data['status'])
            except YomboWarning as e:
                webinterface.add_alert(e, 'warning')
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
                webinterface.add_breadcrumb(request, "/scenes/%s/edit", "Edit")

                return page_scenes_form(webinterface, request, session, 'edit', data,
                                                        "Edit Scene: %s" % scene.label)

                return webinterface.redirect(request, '/scenes/index')

            webinterface.add_alert("Scene '%s' edited." % scene.label)
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

            # msg = {
            #     'header': 'Scene Updated',
            #     'label': 'Scene updated successfully',
            #     'description': '<p>The scene has been updated.'
            #                    '<p>Continue to:</p><ul>'
            #                    ' <li><a href="/scenes/index">Scene index</a></li>'
            #                    ' <li><a href="/scenes/%s/details">View the edited scene</a></li>'
            #                    '<ul>' %
            #                    scene.scene_id,
            # }
            #
            # page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            # root_breadcrumb(webinterface, request)
            # webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            # webinterface.add_breadcrumb(request, "/scenes/%s/edit" % scene_id, "Edit")
            #
            # return page.render(alerts=webinterface.get_alerts(),
            #                    msg=msg,
            #                    )

        def page_scenes_form(webinterface, request, session, action_type, scene,
                                        header_label):
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
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene doesn't exist: %s" % scene_id, 'warning')
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
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene doesn't exist: %s" % scene_id, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the scene.', 'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/details' % scene_id)

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the scene.', 'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/details' % scene_id)

            action_results = yield scene.delete(session=session['yomboapi_session'])
            if action_results['status'] == 'failed':
                webinterface.add_alert(action_results['apimsghtml'], 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)
            msg = {
                'header': 'Scene Deleted',
                'label': 'Scene deleted successfully',
                'description': '<p>The scene has been delete.'
                               '<p>Continue to:</p><ul>'
                               ' <li><strong><a href="/scenes/index">Scene index</a></strong></li>'
                               '<ul>'
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/edit" % scene.scene_id, "Delete")

            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )

        @webapp.route('/<string:scene_id>/disable', methods=['GET'])
        @require_auth()
        def page_scenes_disable_get(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
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
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the scene.',
                                       'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/details' % scene_id)

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the scene.',
                                       'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            scene.disable(session=session['yomboapi_session'])

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
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
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
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')
            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the scene.', 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            if confirm != "enable":
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the scene.', 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            scene.enable(session=session['yomboapi_session'])

            webinterface.add_alert("Scene '%s' enabled." % scene.label)
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

#########################################
## States
#########################################

        @webapp.route('/<string:scene_id>/add_state', methods=['GET'])
        @require_auth()
        def page_scenes_item_state_add_get(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            data = {
                'item_type': 'state',
                'name': webinterface.request_get_default(request, 'name', ""),
                'value': webinterface.request_get_default(request, 'value', ""),
                'value_type': webinterface.request_get_default(request, 'value_type', ""),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.get_scene_item(scene_id)) + 1) * 10)),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/add_state" % scene_id, "Add Item: State")
            return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Add state to scene")

        @webapp.route('/<string:scene_id>/add_state', methods=['POST'])
        @require_auth()
        def page_scenes_item_state_add_post(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            data = {
                'item_type': 'state',
                'name': webinterface.request_get_default(request, 'name', ""),
                'value': webinterface.request_get_default(request, 'value', ""),
                'value_type': webinterface.request_get_default(request, 'value_type', ""),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.scenes) +1) * 10)),
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
                results = webinterface._Scenes.add_scene_item(scene_id, **data)
            except YomboWarning as e:
                webinterface.add_alert(e, 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Add state to scene")

            webinterface.add_alert("Added state item to scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        @webapp.route('/<string:scene_id>/edit_state/<string:item_id>', methods=['GET'])
        @require_auth()
        def page_scenes_item_state_edit_get(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/edit_state" % scene.scene_id, "Edit item: State")
            data = webinterface._Scenes.get_scene_item(scene_id, item_id)
            return page_scenes_form_state(webinterface, request, session, scene, data, 'edit',
                                              "Edit scene item: State")

        @webapp.route('/<string:scene_id>/edit_state/<string:item_id>', methods=['POST'])
        @require_auth()
        def page_scenes_item_state_edit_post(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')
            data = {
                'item_type': 'state',
                'name': webinterface.request_get_default(request, 'name', ""),
                'value': webinterface.request_get_default(request, 'value', ""),
                'value_type': webinterface.request_get_default(request, 'value_type', ""),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.scenes) + 1) * 10)),
            }

            if data['name'] == "":
                webinterface.add_alert('Must enter a state name.', 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Edit scene item: State")

            if data['value'] == "":
                webinterface.add_alert('Must enter a state value to set.', 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Edit scene item: State")

            if data['value_type'] == "" or data['value_type'] not in ('integer', 'string', 'boolean', 'float'):
                webinterface.add_alert('Must enter a state value_type to ensure validity.', 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Edit scene item: State")

            value_type = data['value_type']
            if value_type == "string":
                data['value'] = coerce_value(data['value'], 'string')
            elif value_type == "integer":
                try:
                    data['value'] = coerce_value(data['value'], 'int')
                except Exception:
                    webinterface.add_alert("Cannot coerce state value into an integer", 'warning')
                    return page_scenes_form_state(webinterface, request, session, scene, data, 'add',
                                                      "Edit scene item: State")
            elif value_type == "float":
                try:
                    data['value'] = coerce_value(data['value'], 'float')
                except Exception:
                    webinterface.add_alert("Cannot coerce state value into an float", 'warning')
                    return page_scenes_form_state(webinterface, request, session, scene, data, 'add',
                                                      "Edit scene item: State")
            elif value_type == "boolean":
                try:
                    data['value'] = coerce_value(data['value'], 'bool')
                    if isinstance(data['value'], bool) is False:
                        raise Exception()
                except Exception:
                    webinterface.add_alert("Cannot coerce state value into an boolean", 'warning')
                    return page_scenes_form_state(webinterface, request, session, scene, data, 'add',
                                                      "Edit scene item: State")
            else:
                webinterface.add_alert("Unknown value type.", 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add',
                                                  "Edit scene item: State")

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Edit scene item: State")

            try:
                webinterface._Scenes.edit_scene_item(scene_id, item_id, **data)
            except YomboWarning as e:
                webinterface.add_alert(e, 'warning')
                return page_scenes_form_state(webinterface, request, session, scene, data, 'add', "Edit scene item: State")

            webinterface.add_alert("Edited state item for scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        def page_scenes_form_state(webinterface, request, session, scene, data, action_type, header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/scenes/form_state.html')

            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               scene=scene,
                               data=data,
                               action_type=action_type,
                               )

        @webapp.route('/<string:scene_id>/delete_state/<string:item_id>', methods=['GET'])
        @require_auth()
        def page_scenes_item_state_delete_get(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene doesn't exist: %s" % scene_id, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                item = webinterface._Scenes.get_scene_item(scene_id, item_id)
            except KeyError as e:
                webinterface.add_alert("Requested item for scene doesn't exist.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            page = webinterface.get_template(
                request,
                webinterface._dir + 'pages/scenes/delete_state.html'
            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/delete_state" % scene_id, "Delete item: State")
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               item=item,
                               item_id=item_id,
                               )

        @webapp.route('/<string:scene_id>/delete_state/<string:item_id>', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_scenes_item_state_delete_post(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene doesn't exist: %s" % scene_id, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                item = webinterface._Scenes.get_scene_item(scene_id, item_id)
            except KeyError as e:
                webinterface.add_alert("Requested item for scene doesn't exist.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                confirm = request.args.get('confirm')[0]
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the state from the scene.', 'warning')
            except:
                return webinterface.redirect(request,
                                             '/scenes/%s/delete_state/%s' % (scene_id, item_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the state from the scene.', 'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/delete_state/%s' % (scene_id, item_id))

            try:
                yield webinterface._Scenes.delete_scene_item(scene_id, item_id)
            except Exception as e:
                webinterface.add_alert(e, 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            webinterface.add_alert("Deleted state item for scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

#########################################
## pause
#########################################

        @webapp.route('/<string:scene_id>/add_pause', methods=['GET'])
        @require_auth()
        def page_scenes_item_pause_add_get(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            data = {
                'item_type': 'pause',
                'duration': webinterface.request_get_default(request, 'duration', 5),
                'weight': webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.get_scene_item(scene_id)) + 1) * 10),
            }
            try:
                data['duration'] = float(data['duration'])
            except Exception as e:
                webinterface.add_alert("Duration must be an integer or float.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_scenes_form_pause(webinterface, request, session, scene, data, 'add', "Add a pause to scene")

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/add_pause" % scene_id, "Add Item: Pause")
            return page_scenes_form_pause(webinterface, request, session, scene, data, 'add', "Add a pause to scene")

        @webapp.route('/<string:scene_id>/add_pause', methods=['POST'])
        @require_auth()
        def page_scenes_item_pause_add_post(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            data = {
                'item_type': 'pause',
                'duration': webinterface.request_get_default(request, 'duration', 5),
                'weight': webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.get_scene_item(scene_id)) + 1) * 10),
            }
            try:
                data['duration'] = float(data['duration'])
            except Exception as e:
                webinterface.add_alert("Duration must be an integer or float.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_scenes_form_pause(webinterface, request, session, scene, data, 'add', "Add a pause to scene")

            try:
                results = webinterface._Scenes.add_scene_item(scene_id, **data)
            except YomboWarning as e:
                webinterface.add_alert(e, 'warning')
                return page_scenes_form_pause(webinterface, request, session, scene, data, 'add', "Add a pause to scene")

            webinterface.add_alert("Added pause item to scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        @webapp.route('/<string:scene_id>/edit_pause/<string:item_id>', methods=['GET'])
        @require_auth()
        def page_scenes_item_pause_edit_get(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/edit_pause" % scene.scene_id, "Edit item: State")
            data = webinterface._Scenes.get_scene_item(scene_id, item_id)
            return page_scenes_form_pause(webinterface, request, session, scene, data, 'edit',
                                              "Edit scene item: State")

        @webapp.route('/<string:scene_id>/edit_pause/<string:item_id>', methods=['POST'])
        @require_auth()
        def page_scenes_item_pause_edit_post(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            data = {
                'item_type': 'pause',
                'duration': webinterface.request_get_default(request, 'duration', 5),
                'weight': webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.get_scene_item(scene_id)) + 1) * 10),
            }
            try:
                data['duration'] = float(data['duration'])
            except Exception as e:
                webinterface.add_alert("Duration must be an integer or float.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_scenes_form_pause(webinterface, request, session, scene, data, 'add', "Add a pause to scene")

            try:
                webinterface._Scenes.edit_scene_item(scene_id, item_id, **data)
            except YomboWarning as e:
                webinterface.add_alert(e, 'warning')
                return page_scenes_form_pause(webinterface, request, session, scene, data, 'add', "Edit scene item: State")

            webinterface.add_alert("Edited a pause item for scene '%s'." % scene.label)
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        def page_scenes_form_pause(webinterface, request, session, scene, data, action_type, header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/scenes/form_pause.html')

            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               scene=scene,
                               data=data,
                               action_type=action_type,
                               )

        @webapp.route('/<string:scene_id>/delete_pause/<string:item_id>', methods=['GET'])
        @require_auth()
        def page_scenes_item_pause_delete_get(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene doesn't exist: %s" % scene_id, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                item = webinterface._Scenes.get_scene_item(scene_id, item_id)
            except KeyError as e:
                webinterface.add_alert("Requested item for scene doesn't exist.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            page = webinterface.get_template(
                request,
                webinterface._dir + 'pages/scenes/delete_pause.html'
            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/delete_pause" % scene_id, "Delete item: Pause")
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               item=item,
                               item_id=item_id,
                               )

        @webapp.route('/<string:scene_id>/delete_pause/<string:item_id>', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_scenes_item_pause_delete_post(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene doesn't exist: %s" % scene_id, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                item = webinterface._Scenes.get_scene_item(scene_id, item_id)
            except KeyError as e:
                webinterface.add_alert("Requested item for scene doesn't exist.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the pause from the scene.', 'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/delete_pause/%s' % (scene_id, item_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the pause from the scene.', 'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/delete_pause/%s' % (scene_id, item_id))

            try:
                yield webinterface._Scenes.delete_scene_item(scene_id, item_id)
            except Exception as e:
                webinterface.add_alert(e, 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            webinterface.add_alert("Deleted pause item for scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

#########################################
## Devices
#########################################

        @webapp.route('/<string:scene_id>/add_device', methods=['GET'])
        @require_auth()
        def page_scenes_item_device_add_get(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            data = {
                'item_id': None,
                'item_type': 'device',
                'device_id': webinterface.request_get_default(request, 'device_id', ""),
                'command_id': webinterface.request_get_default(request, 'command_id', ""),
                'inputs': webinterface.request_get_default(request, 'inputs', ""),
                'weight': int(webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.get_scene_item(scene_id)) + 1) * 10)),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/add_device" % scene_id, "Add Item: Device")
            return page_scenes_form_device(webinterface, request, session, scene, data, 'add', "Add device to scene")

        @webapp.route('/<string:scene_id>/add_device', methods=['POST'])
        @require_auth()
        def page_scenes_item_device_add_post(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                incoming_data = json.loads(webinterface.request_get_default(request, 'json_output', "{}"))
            except Exception as e:
                webinterface.add_alert("Error decoding request data.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)
            keep_attributes = ['device_id', 'command_id', 'inputs', 'weight']
            data = {k: incoming_data[k] for k in keep_attributes if k in incoming_data}
            data['item_type'] = 'device'
            if 'device_id' not in data:
                webinterface.add_alert("Device ID information is missing.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)
            try:
                device = webinterface._Devices[data['device_id']]
            except Exception as e:
                webinterface.add_alert("Device could not be found.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)

            if 'command_id' not in data:
                webinterface.add_alert("Command ID information is missing.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)
            try:
                command = webinterface._Commands[data['command_id']]
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
            if 'item_id' in data:
                del data['item_id']

            # TODO: handle encrypted input values....

            try:
                results = webinterface._Scenes.add_scene_item(scene_id, **data)
            except YomboWarning as e:
                webinterface.add_alert(e, 'warning')
                return page_scenes_form_device(webinterface, request, session, scene, data, 'add', "Add device to scene")

            webinterface.add_alert("Added device item to scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        @webapp.route('/<string:scene_id>/edit_device/<string:item_id>', methods=['GET'])
        @require_auth()
        def page_scenes_item_device_edit_get(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/edit_device" % scene.scene_id, "Edit item: Device")
            data = webinterface._Scenes.get_scene_item(scene_id, item_id)
            return page_scenes_form_device(webinterface, request, session, scene, data, 'edit',
                                              "Edit scene item: Device")

        @webapp.route('/<string:scene_id>/edit_device/<string:item_id>', methods=['POST'])
        @require_auth()
        def page_scenes_item_device_edit_post(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                incoming_data = json.loads(webinterface.request_get_default(request, 'json_output', "{}"))
            except Exception as e:
                webinterface.add_alert("Error decoding request data.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)
            keep_attributes = ['device_id', 'command_id', 'inputs', 'weight']
            data = {k: incoming_data[k] for k in keep_attributes if k in incoming_data}
            data['item_type'] = 'device'


            if 'device_id' not in data:
                webinterface.add_alert("Device ID information is missing.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)
            try:
                device = webinterface._Devices[data['device_id']]
            except Exception as e:
                webinterface.add_alert("Device could not be found.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)

            if 'command_id' not in data:
                webinterface.add_alert("Command ID information is missing.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/add_device' % scene_id)
            try:
                command = webinterface._Commands[data['command_id']]
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
            if 'item_id' in data:
                del data['item_id']

            # TODO: handle encrypted input values....

            try:
                webinterface._Scenes.edit_scene_item(scene_id, item_id, **data)
            except YomboWarning as e:
                webinterface.add_alert(e, 'warning')
                return page_scenes_form_device(webinterface, request, session, scene, data, 'add', "Add device to scene")

            webinterface.add_alert("Added device item to scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)


        def page_scenes_form_device(webinterface, request, session, scene, data, action_type, header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/scenes/form_device.html')

            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               scene=scene,
                               data=data,
                               action_type=action_type,
                               )

        @webapp.route('/<string:scene_id>/delete_device/<string:item_id>', methods=['GET'])
        @require_auth()
        def page_scenes_item_device_delete_get(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene doesn't exist: %s" % scene_id, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                item = webinterface._Scenes.get_scene_item(scene_id, item_id)
            except KeyError as e:
                webinterface.add_alert("Requested item for scene doesn't exist.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            page = webinterface.get_template(
                request,
                webinterface._dir + 'pages/scenes/delete_device.html'
            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/delete_device" % scene_id, "Delete item: Device")
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               item=item,
                               item_id=item_id,
                               )

        @webapp.route('/<string:scene_id>/delete_device/<string:item_id>', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_scenes_item_device_delete_post(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene doesn't exist: %s" % scene_id, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                item = webinterface._Scenes.get_scene_item(scene_id, item_id)
            except KeyError as e:
                webinterface.add_alert("Requested item for scene doesn't exist.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the device from the scene.', 'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/delete_device/%s' % (scene_id, item_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the device from the scene.', 'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/delete_device/%s' % (scene_id, item_id))

            try:
                yield webinterface._Scenes.delete_scene_item(scene_id, item_id)
            except Exception as e:
                webinterface.add_alert(e, 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            webinterface.add_alert("Deleted device item for scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)
