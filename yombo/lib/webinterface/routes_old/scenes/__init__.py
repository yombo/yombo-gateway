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

        @webapp.route("/")
        @require_auth()
        def page_scenes(webinterface, request, session):
            session.has_access("scene", "*", "view", raise_error=True)
            return webinterface.redirect(request, "/scenes/index")

        @webapp.route("/index")
        @require_auth()
        def page_scenes_index(webinterface, request, session):
            session.has_access("scene", "*", "view", raise_error=True)
            item_keys, permissions = webinterface._Users.get_access(session, "scene", "view")
            root_breadcrumb(webinterface, request)
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/scenes/index.html")
            return page.render(
                alerts=webinterface.get_alerts(),
                user=session.user,
                permissions=permissions,
                item_keys=item_keys,
                )

        @webapp.route("/<string:scene_id>/details", methods=["GET"])
        @require_auth()
        def page_scenes_details_get(webinterface, request, session, scene_id):
            session.has_access("scene", scene_id, "view", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")

            page = webinterface.get_template(
                request,
                webinterface.wi_dir + "/pages/scenes/details.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/scenes/{scene.scene_id}/details", scene.label)
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               )

        @webapp.route("/<string:scene_id>/start", methods=["GET"])
        @require_auth()
        def page_scenes_trigger_get(webinterface, request, session, scene_id):
            session.has_access("scene", scene_id, "start", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")

            try:
                webinterface._Scenes.start(scene_id)
            except KeyError as e:
                webinterface.add_alert(f"Cannot start scene. {e.message}", "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            webinterface.add_alert(f"The scene '{scene.label}' has been started")
            return webinterface.redirect(request, f"/scenes/{scene.scene_id}/details")

        @webapp.route("/<string:scene_id>/stop", methods=["GET"])
        @require_auth()
        def page_scenes_stop_trigger_get(webinterface, request, session, scene_id):
            session.has_access("scene", scene_id, "stop", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")

            try:
                webinterface._Scenes.stop(scene_id)
            except KeyError as e:
                webinterface.add_alert(f"Cannot stop scene. {e.message}", "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            webinterface.add_alert(f"The scene '{scene.label}' has been stopped")
            return webinterface.redirect(request, f"/scenes/{scene.scene_id}/details")

        @webapp.route("/add", methods=["GET"])
        @require_auth()
        def page_scenes_add_get(webinterface, request, session):
            session.has_access("scene", "*", "add", raise_error=True)
            data = {
                "label": webinterface.request_get_default(request, "label", ""),
                "machine_label": webinterface.request_get_default(request, "machine_label", ""),
                "description": webinterface.request_get_default(request, "description", ""),
                "status": int(webinterface.request_get_default(request, "status", 1)),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/add", "Add")
            return page_scenes_form(webinterface, request, session, "add", data, "Add Scene")

        @webapp.route("/add", methods=["POST"])
        @require_auth()
        @inlineCallbacks
        def page_scenes_add_post(webinterface, request, session):
            session.has_access("scene", "*", "add", raise_error=True)
            data = {
                "label": webinterface.request_get_default(request, "label", ""),
                "machine_label": webinterface.request_get_default(request, "machine_label", ""),
                "description": webinterface.request_get_default(request, "description", ""),
                "status": int(webinterface.request_get_default(request, "status", 1)),
            }

            try:
                scene = yield webinterface._Scenes.add(data["label"], data["machine_label"],
                                                       data["description"], data["status"])
            except YomboWarning as e:
                webinterface.add_alert(f"Cannot add scene. {e.message}", "warning")
                return page_scenes_form(webinterface, request, session, "add", data, "Add Scene",)

            webinterface.add_alert(f"New scene '{scene.label}' added.")
            return webinterface.redirect(request, f"/scenes/{scene.scene_id}/details")

        @webapp.route("/<string:scene_id>/edit", methods=["GET"])
        @require_auth()
        def page_scenes_edit_get(webinterface, request, session, scene_id):
            session.has_access("scene", scene_id, "edit", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/scenes/{scene.scene_id}/details", scene.label)
            webinterface.add_breadcrumb(request, f"/scenes/{scene.scene_id}/edit", "Edit")
            data = {
                "label": scene.label,
                "machine_label": scene.machine_label,
                "description":  scene.description(),
                "status": scene.effective_status(),
                "scene_id": scene_id,
                "allow_intents": scene.data["config"]["allow_intents"],
            }
            return page_scenes_form(webinterface,
                                    request,
                                    session,
                                    "edit",
                                    data,
                                    f"Edit Scene: {scene.label}")

        @webapp.route("/<string:scene_id>/edit", methods=["POST"])
        @require_auth()
        def page_scenes_edit_post(webinterface, request, session, scene_id):
            session.has_access("scene", scene_id, "edit", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")

            data = {
                "label": webinterface.request_get_default(request, "label", ""),
                "machine_label": webinterface.request_get_default(request, "machine_label", ""),
                "description": webinterface.request_get_default(request, "description", ""),
                "status": int(webinterface.request_get_default(request, "status", 1)),
                "scene_id": scene_id,
                "allow_intents": int(webinterface.request_get_default(request, "allow_intents", 1)),
            }
            # print(f"scene save: {data}")

            try:
                scene = webinterface._Scenes.edit(scene_id,
                                                  data["label"], data["machine_label"],
                                                  data["description"], data["status"],
                                                  data["allow_intents"])
            except YomboWarning as e:
                webinterface.add_alert(f"Cannot edit scene. {e.message}", "warning")
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, f"/scenes/{scene.scene_id}/details", scene.label)
                webinterface.add_breadcrumb(request, f"/scenes/{scene.scene_id}/edit", "Edit")

                return page_scenes_form(webinterface, request, session, "edit", data,
                                        f"Edit Scene: {scene.label}")

            webinterface.add_alert(f"Scene '{scene.label}' edited.")
            return webinterface.redirect(request, f"/scenes/{scene.scene_id}/details")

        def page_scenes_form(webinterface, request, session, action_type, scene, header_label):
            page = webinterface.get_template(
                request,
                webinterface.wi_dir + "/pages/scenes/form.html")
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               scene=scene,
                               action_type=action_type,
                               )

        @webapp.route("/<string:scene_id>/delete", methods=["GET"])
        @require_auth()
        def page_scenes_details_post(webinterface, request, session, scene_id):
            session.has_access("scene", scene_id, "delete", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")

            page = webinterface.get_template(
                request,
                webinterface.wi_dir + "/pages/scenes/delete.html"
            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/scenes/{scene_id}/details", scene.label)
            webinterface.add_breadcrumb(request, f"/scenes/{scene_id}/delete", "Delete")
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               )

        @webapp.route("/<string:scene_id>/delete", methods=["POST"])
        @require_auth()
        @inlineCallbacks
        def page_scenes_delete_post(webinterface, request, session, scene_id):
            session.has_access("scene", scene_id, "delete", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")

            try:
                confirm = request.args.get("confirm")[0]
            except:
                webinterface.add_alert("Must enter 'delete' in the confirmation box to delete the scene.", "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            if confirm != "delete":
                webinterface.add_alert("Must enter 'delete' in the confirmation box to delete the scene.", "warning")
                return webinterface.redirect(request,
                                             f"/scenes/{scene_id}/details")

            try:
                yield scene.delete(session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(f"Cannot delete scene. {e.message}", "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            webinterface.add_alert("Scene deleted. Will be fully removed from system on next restart.")
            return webinterface.redirect(request, "/scenes/index")

        @webapp.route("/<string:scene_id>/disable", methods=["GET"])
        @require_auth()
        def page_scenes_disable_get(webinterface, request, session, scene_id):
            session.has_access("scene", scene_id, "disable", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/scenes/disable.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/scenes/{scene.scene_id}/details", scene.label)
            webinterface.add_breadcrumb(request, f"/scenes/{scene.scene_id}/disable", "Disable")
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               )

        @webapp.route("/<string:scene_id>/disable", methods=["POST"])
        @require_auth()
        def page_scenes_disable_post(webinterface, request, session, scene_id):
            session.has_access("scene", scene_id, "disable", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")

            try:
                confirm = request.args.get("confirm")[0]
            except:
                webinterface.add_alert("Must enter 'delete' in the confirmation box to disable the scene.",
                                       "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            if confirm != "disable":
                webinterface.add_alert("Must enter 'delete' in the confirmation box to disable the scene.",
                                       "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            try:
                scene.disable(session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(f"Cannot disable scene. {e.message}", "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            msg = {
                "header": "Scene Disabled",
                "label": "Scene disabled successfully",
                "description": "<p>The scene has been disabled."
                               "<p>Continue to:</p><ul>"
                               ' <li><strong><a href="/scenes/index">Scene index</a></strong></li>'
                               f' <li><a href="/scenes/{scene.scene_id}/details">View the disabled scene</a></li>'
                               "<ul>",
            }

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/display_notice.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/scenes/{scene.scene_id}/details", scene.label)
            webinterface.add_breadcrumb(request, f"/scenes/{scene.scene_id}/disable", "Disable")
            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )

        @webapp.route("/<string:scene_id>/enable", methods=["GET"])
        @require_auth()
        def page_scenes_enable_get(webinterface, request, session, scene_id):
            session.has_access("scene", scene_id, "enable", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/scenes/enable.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/scenes/{scene.scene_id}/details", scene.label)
            webinterface.add_breadcrumb(request, f"/scenes/{scene.scene_id}/enable", "Enable")
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               )

        @webapp.route("/<string:scene_id>/enable", methods=["POST"])
        @require_auth()
        def page_scenes_enable_post(webinterface, request, session, scene_id):
            session.has_access("scene", scene_id, "enable", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")
            try:
                confirm = request.args.get("confirm")[0]
            except:
                webinterface.add_alert("Must enter 'enable' in the confirmation box to enable the scene.", "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            if confirm != "enable":
                webinterface.add_alert("Must enter 'enable' in the confirmation box to enable the scene.", "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            try:
                scene.enable(session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(f"Cannot enable scene. {e.message}", "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            webinterface.add_alert(f"Scene '{scene.label}' enabled.")
            return webinterface.redirect(request, f"/scenes/{scene.scene_id}/details")

        @webapp.route("/<string:scene_id>/move_up/<string:action_id>", methods=["GET"])
        @require_auth()
        def page_scenes_action_move_up_get(webinterface, request, session, scene_id, action_id):
            session.has_access("scene", scene_id, "edit", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")
            try:
                action = webinterface._Scenes.get_action_items(scene_id, action_id)
            except KeyError as e:
                webinterface.add_alert("Requested action id could not be located.", "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            try:
                webinterface._Scenes.move_action_up(scene_id, action_id)
            except KeyError as e:
                webinterface.add_alert(f"Cannot move action up. {e.message}", "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            webinterface.add_alert("Action moved up.")
            return webinterface.redirect(request, f"/scenes/{scene_id}/details")

        @webapp.route("/<string:scene_id>/move_down/<string:action_id>", methods=["GET"])
        @require_auth()
        def page_scenes_action_move_down_get(webinterface, request, session, scene_id, action_id):
            session.has_access("scene", scene_id, "edit", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")
            try:
                action = webinterface._Scenes.get_action_items(scene_id, action_id)
            except KeyError as e:
                webinterface.add_alert("Requested action id could not be located.", "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            try:
                webinterface._Scenes.move_action_down(scene_id, action_id)
            except KeyError as e:
                webinterface.add_alert(f"Cannot move action down. {e.message}", "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            webinterface.add_alert("Action moved down.")
            return webinterface.redirect(request, f"/scenes/{scene_id}/details")

        @webapp.route("/<string:scene_id>/duplicate_scene", methods=["GET"])
        @require_auth()
        @inlineCallbacks
        def page_scenes_duplicate_scene_get(webinterface, request, session, scene_id):
            session.has_access("scene", scene_id, "view", raise_error=True)
            session.has_access("scene", "*", "add", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")

            try:
                yield webinterface._Scenes.duplicate_scene(scene_id)
            except KeyError as e:
                webinterface.add_alert(f"Cannot duplicate scene. {e.message}", "warning")
                return webinterface.redirect(request, "/scenes/index")

            webinterface.add_alert("Scene dupllicated.")
            return webinterface.redirect(request, "/scenes/index")
