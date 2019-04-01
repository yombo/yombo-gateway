# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the scenes handling for /scenes sub directory.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.18.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/routes/scenes.py>`_
"""
# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.routes.scenes.scene")


def route_scenes_scene(webapp):
    with webapp.subroute("/scenes") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/scenes/index", "Scenes")

        @webapp.route("/<string:scene_id>/add_scene", methods=["GET"])
        @require_auth()
        def page_scenes_action_scene_add_get(webinterface, request, session, scene_id):
            session.has_access("scene", scene_id, "edit", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")

            data = {
                "action_type": "scene",
                "scene_machine_label": webinterface.request_get_default(request, "scene_machine_label", ""),
                "scene_action": webinterface.request_get_default(request, "scene_action", ""),
                "weight": webinterface.request_get_default(
                    request, "weight", (len(webinterface._Scenes.get_action_items(scene_id)) + 1) * 10),
            }

            try:
                data["weight"] = int(data["weight"])
            except Exception:
                webinterface.add_alert("Must enter a number for a weight.", "warning")
                return page_scenes_form_scene(webinterface, request, session, scene, data, "add",
                                              "Add a scene to scene")

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/scenes/{scene_id}/details", scene.label)
            webinterface.add_breadcrumb(request, f"/scenes/{scene_id}/add_scene", "Add Action: Pause")
            return page_scenes_form_scene(webinterface, request, session, scene, data, "add",
                                          "Add a scene to scene")

        @webapp.route("/<string:scene_id>/add_scene", methods=["POST"])
        @require_auth()
        def page_scenes_action_scene_add_post(webinterface, request, session, scene_id):
            session.has_access("scene", scene_id, "edit", raise_error=True)
            try:
                scene = webinterface._Scenes.get(scene_id)
            except KeyError as e:
                webinterface.add_alert(e.message, "warning")
                return webinterface.redirect(request, "/scenes/index")

            data = {
                "action_type": "scene",
                "scene_machine_label": webinterface.request_get_default(request, "scene_machine_label", ""),
                "scene_action": webinterface.request_get_default(request, "scene_action", ""),
                "weight": webinterface.request_get_default(
                    request, "weight", (len(webinterface._Scenes.get_action_items(scene_id)) + 1) * 10),
            }

            try:
                data["weight"] = int(data["weight"])
            except Exception:
                webinterface.add_alert("Must enter a number for a weight.", "warning")
                return page_scenes_form_scene(webinterface, request, session, scene, data, "add",
                                              "Add a scene to scene")

            try:
                webinterface._Scenes.add_action_item(scene_id, **data)
            except KeyError as e:
                webinterface.add_alert(f"Cannot add scene control to scene. {e.message}", "warning")
                return page_scenes_form_scene(webinterface, request, session, scene, data, "add",
                                              "Add a scene to scene")

            webinterface.add_alert("Added scene action to scene.")
            return webinterface.redirect(request, f"/scenes/{scene.scene_id}/details")

        @webapp.route("/<string:scene_id>/edit_scene/<string:action_id>", methods=["GET"])
        @require_auth()
        def page_scenes_action_scene_edit_get(webinterface, request, session, scene_id, action_id):
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
            if action["action_type"] != "scene":
                webinterface.add_alert("Requested action type is invalid.", "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/scenes/{scene.scene_id}/details", scene.label)
            webinterface.add_breadcrumb(request, f"/scenes/{scene.scene_id}/edit_scene", "Edit action: Scene Control")
            return page_scenes_form_scene(webinterface, request, session, scene, action, "edit",
                                          "Edit scene action: Scene control")

        @webapp.route("/<string:scene_id>/edit_scene/<string:action_id>", methods=["POST"])
        @require_auth()
        def page_scenes_action_scene_edit_post(webinterface, request, session, scene_id, action_id):
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
            if action["action_type"] != "scene":
                webinterface.add_alert("Requested action type is invalid.", "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")

            data = {
                "action_type": "scene",
                "scene_machine_label": webinterface.request_get_default(request, "scene_machine_label", ""),
                "scene_action": webinterface.request_get_default(request, "scene_action", ""),
                "weight": webinterface.request_get_default(
                    request, "weight", (len(webinterface._Scenes.get_action_items(scene_id)) + 1) * 10),
            }

            try:
                data["weight"] = int(data["weight"])
            except Exception:
                webinterface.add_alert("Must enter a number for a weight.", "warning")
                return page_scenes_form_scene(webinterface, request, session, scene, data, "add",
                                              "Edit scene control")

            try:
                webinterface._Scenes.edit_action_item(scene_id, action_id, **data)
            except KeyError as e:
                webinterface.add_alert(f"Cannot edit scene control within scene. {e.message}", "warning")
                return page_scenes_form_scene(webinterface, request, session, scene, data, "add",
                                              "Edit scene action: Scene control")

            webinterface.add_alert(f"Edited a scene action for scene '{scene.label}'.")
            return webinterface.redirect(request, f"/scenes/{scene.scene_id}/details")

        def page_scenes_form_scene(webinterface, request, session, scene, data, action_type, header_label):
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/scenes/form_scene.html")

            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               scene=scene,
                               data=data,
                               action_type=action_type,
                               )

        @webapp.route("/<string:scene_id>/delete_scene/<string:action_id>", methods=["GET"])
        @require_auth()
        def page_scenes_action_scene_delete_get(webinterface, request, session, scene_id, action_id):
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
            if action["action_type"] != "scene":
                webinterface.add_alert("Requested action type is invalid.", "warning")
                return webinterface.redirect(request, f"/scenes/{scene_id}/details")


            page = webinterface.get_template(request,
                                             webinterface.wi_dir + "/pages/scenes/delete_scene.html"
                                            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/scenes/{scene_id}/details", scene.label)
            webinterface.add_breadcrumb(request, f"/scenes/{scene_id}/delete_scene", "Delete action: Scene Control")
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               action=action,
                               action_id=action_id,
                               )

        @webapp.route("/<string:scene_id>/delete_scene/<string:action_id>", methods=["POST"])
        @require_auth()
        def page_scenes_action_scene_delete_post(webinterface, request, session, scene_id, action_id):
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
                confirm = request.args.get("confirm")[0]
            except:
                webinterface.add_alert("Must enter 'delete' in the confirmation box to "
                                       "delete the scene control from the scene.", "warning")
                return webinterface.redirect(request,
                                             f"/scenes/{scene_id}/delete_scene/{action_id}")

            if confirm != "delete":
                webinterface.add_alert("Must enter 'delete' in the confirmation box to "
                                       "delete the scene control from the scene.", "warning")
                return webinterface.redirect(request,
                                             f"/scenes/{scene_id}/delete_scene/{action_id}")

            try:
                webinterface._Scenes.delete_scene_item(scene_id, action_id)
            except KeyError as e:
                webinterface.add_alert(f"Cannot delete scene control from scene. {e.message}", "warning")
                return webinterface.redirect(request, "/scenes/index")

            webinterface.add_alert("Deleted scene action for scene.")
            return webinterface.redirect(request, f"/scenes/{scene.scene_id}/details")
