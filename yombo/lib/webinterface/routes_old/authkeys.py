# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/authkey" sub-route of the web interface.

Responsible for adding, removing, and updating auth keys that are used to
access the gateway API.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.15.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/routes/authkey.py>`_
"""

import voluptuous as vol

from twisted.internet.defer import inlineCallbacks

from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.lib.webinterface.auth import require_auth
import yombo.utils.validators as val

logger = get_logger("library.webinterface.routes.authkey")

AUTHKEY_SUBMIT_FIELDS = vol.Schema({
    vol.Required("label"): val.string,
    vol.Required("description"): val.string,
    vol.Required("enabled"): val.boolean,
})

def route_authkeys(webapp):
    """
    Extends routes of the webapp (web interface).

    :param webapp: the Klein web server instance
    :return:
    """
    with webapp.subroute("/authkeys") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/authkeys/index", "Auth Keys")

        def return_authkey_details(webinterface, request, session, auth_key):
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/authkeys/details.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/authkeys/{auth_key.auth_id}/details",
                                        auth_key.label)
            return page.render(alerts=webinterface.get_alerts(),
                               authkey=auth_key,
                               )

        @webapp.route("/")
        @require_auth()
        def page_lib_authkey(webinterface, request, session):
            return webinterface.redirect(request, "/authkeys/index")

        @webapp.route("/index")
        @require_auth()
        def page_lib_authkey_index(webinterface, request, session):
            """
            Show an index of Auth Keys configured across all gateways within a cluster.

            :param webinterface: pointer to the web interface library
            :param request: a Twisted request
            :param session: User"s session information.
            :return:
            """
            session.has_access("authkey", "*", "view")

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/authkeys/index.html")
            root_breadcrumb(webinterface, request)
            return page.render(alerts=webinterface.get_alerts(),
                               authkeys=webinterface._AuthKeys.authkeys,
                               )

        @webapp.route("/<string:authkey_id>/details", methods=["GET"])
        @require_auth()
        def page_lib_authkey_details_get(webinterface, request, session, authkey_id):
            authkey_id = webinterface._Validate.id_string(authkey_id)
            if session.has_access("authkey", authkey_id, "view", raise_error=False) is False:
                webinterface.add_alert("You don't have access to edit this.", "warning")
                return webinterface.redirect(request, "/authkeys/index")

            try:
                auth_key = webinterface._AuthKeys.get(authkey_id)
            except KeyError:
                webinterface.add_alert("Invalid Auth Key id.", "warning")
                return webinterface.redirect(request, "/authkeys/index")

            return return_authkey_details(webinterface, request, session, auth_key)

        @webapp.route("/<string:authkey_id>/details", methods=["POST"])
        @require_auth(access_path="module_amazonalexa:manage", access_action="view")
        def page_lib_authkey_details_post(webinterface, request, session, authkey_id):
            if session.has_access("authkey", authkey_id, "view", raise_error=False) is False:
                webinterface.add_alert("You don't have access to edit this.", "warning")
                return webinterface.redirect(request, "/authkeys/index")

            try:
                auth_key = webinterface._AuthKeys.get(authkey_id)
            except KeyError:
                webinterface.add_alert("Invalid Auth Key id.", "warning")
                return webinterface.redirect(request, "/authkeys/index")

            try:
                role_label = request.args.get("role_label")[0]
            except KeyError:
                webinterface.add_alert("Invalid role to add.", "warning")
                return webinterface.redirect(request, f"/authkeys/{authkey_id}/details")

            try:
                auth_key.attach_role(role_label)
            except YomboWarning as e:
                webinterface.add_alert(f"Error adding role: {e}")
                return return_authkey_details(webinterface, request, session, auth_key)

            webinterface.add_alert("Role added to authkey.")
            return return_authkey_details(webinterface, request, session, auth_key)

        @webapp.route("/add", methods=["GET"])
        @require_auth()
        def page_lib_authkey_add_get(webinterface, request, session):
            if session.has_access("authkey", "*", "add", raise_error=False) is False:
                webinterface.add_alert("You don't have access to add this item.", "warning")
                return webinterface.redirect(request, "/authkeys/index")

            data = {
                "label": webinterface.request_get_default(request, "label", ""),
                "description": webinterface.request_get_default(request, "description", ""),
                "enabled": webinterface.request_get_default(request, "enabled", True),
            }
            try:
                AUTHKEY_SUBMIT_FIELDS(data)
            except vol.MultipleInvalid as e:
                logger.info("Error adding authkey key: {error}", e=e)


            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/authkeys/add", "Add")
            return page_lib_authkey_form(webinterface, request, session, "add", data,
                                               "Add Auth Key")

        @webapp.route("/add", methods=["POST"])
        @require_auth()
        def page_lib_authkey_add_post(webinterface, request, session):
            if session.has_access("authkey", "*", "add", raise_error=False) is False:
                webinterface.add_alert("You don't have access to add this item.", "warning")
                return webinterface.redirect(request, "/authkeys/index")

            data = {
                "label": webinterface.request_get_default(request, "label", ""),
                "description": webinterface.request_get_default(request, "description", ""),
                "enabled": webinterface.request_get_default(request, "enabled", True),
            }

            try:
                auth_key = webinterface._AuthKeys.add_authkey({
                    "label": data["label"],
                    "description": data["description"],
                    "created_by": session.auth_id,
                    "created_by_type": session.auth_type_id,
                    }
                )
            except YomboWarning as e:
                webinterface.add_alert(f"Unable to add Auth Key: {e}", "warning")
                return page_lib_authkey_form(webinterface, request, session, "add", data, "Add Location")

            if auth_key is None:
                webinterface.add_alert("Unable to add Auth Key, unknown reason. Sorry I'm not more helpful.",
                                       "warning")
                return page_lib_authkey_form(webinterface, request, session, "add", data, "Add Location")

            msg = {
                "header": "Auth Key added",
                "label": "New API auth added successfully",
                "description": "<p>New Auth Key has been created. Be sure to keep this key secure as it grants access to everything. </p>"
                               f"<p><strong>{auth_key.auth_id}</strong></p>"
                               '<p>Continue to <strong><a href="/authkeys/index">Auth Key index</a></strong> or '
                               f'<a href="/authkeys/{auth_key.auth_id}/details">View new Auth Key</a>.</p>'
            }

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/display_notice.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/authkeys/add", "Add")
            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )

        @webapp.route("/<string:authkey_id>/edit", methods=["GET"])
        @require_auth()
        def page_lib_authkey_edit_get(webinterface, request, session, authkey_id):
            authkey_id = webinterface._Validate.id_string(authkey_id)
            if session.has_access("authkey", authkey_id, "edit", raise_error=False) is False:
                webinterface.add_alert("You don't have access to edit this.", "warning")
                return webinterface.redirect(request, "/authkeys/index")

            try:
                auth_key = webinterface._AuthKeys.get(authkey_id)
            except KeyError:
                webinterface.add_alert("Invalid Auth Key id.", "warning")
                return webinterface.redirect(request, "/authkeys/index")

            if auth_key.created_by_type != "user":
                webinterface.add_alert(f"This auth key cannot be edited, created by: {auth_key.created_by}",
                                       "warning")
                return webinterface.redirect(request, f"/authkeys/{authkey_id}/details")

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/authkeys/{auth_key.auth_id}/details",
                                        auth_key.label)
            webinterface.add_breadcrumb(request, f"/authkeys/{auth_key.auth_id}/edit", "Edit")

            return page_lib_authkey_form(webinterface, request, session, "edit", auth_key.__dict__,
                                         f"Edit API Auth: {auth_key.label}")

        @webapp.route("/<string:authkey_id>/edit", methods=["POST"])
        @require_auth()
        def page_lib_authkey_edit_post(webinterface, request, session, authkey_id):
            authkey_id = webinterface._Validate.id_string(authkey_id)
            if session.has_access("authkey", authkey_id, "edit", raise_error=False) is False:
                webinterface.add_alert("You don't have access to edit this.", "warning")
                return webinterface.redirect(request, "/authkeys/index")

            try:
                auth_key = webinterface._AuthKeys.get(authkey_id)
            except KeyError:
                webinterface.add_alert("Invalid Auth Key id.", "warning")
                return webinterface.redirect(request, "/authkeys/index")

            if auth_key.created_by_type != "user":
                webinterface.add_alert(f"This auth key cannot be edited, created by: {auth_key.created_by}",
                                       "warning")
                return webinterface.redirect(request, f"/authkeys/{authkey_id}/details")

            attributes = ["label", "description", "enabled"]
            data = {}
            for attr in attributes:
                temp = webinterface.request_get_default(request, attr, "")
                if temp != "":
                    data[attr] = temp

            auth_key.update_attributes(data)

            msg = {
                "header": "API Auth Updated",
                "label": "API Auth updated successfully",
                "description": f"<p>Auth Key updated: <strong>{authkey_id}</strong></p>"
                               '<p>Continue to <strong>'
                               '<a href="/authkeys/index">API Auth the index</a></strong> or '
                               f'<a href="/authkeys/{authkey_id}/details">View edited Auth Key</a>.</p>'
            }
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/display_notice.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/authkeys/add", "Add")
            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        def page_lib_authkey_form(webinterface, request, session, action_type, authkey, header_label):
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/authkeys/form.html")
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               authkey=authkey,
                               action_type=action_type,
                               )

        @webapp.route("/<string:authkey_id>/remove", methods=["GET"])
        @require_auth()
        def page_lib_authkey_delete_get(webinterface, request, session, authkey_id):
            authkey_id = webinterface._Validate.id_string(authkey_id)
            if session.has_access("authkey", "*", "delete", raise_error=False) is False:
                webinterface.add_alert("You don't have access to delete this.", "warning")
                return webinterface.redirect(request, f"/authkeys/{authkey_id}/details")

            try:
                auth_key = webinterface._AuthKeys.get(authkey_id)
            except KeyError:
                webinterface.add_alert("Invalid Auth Key id.", "warning")
                return webinterface.redirect(request, "/authkeys/index")

            if auth_key.created_by_type != "user":
                webinterface.add_alert(f"This auth key cannot be edited, created by: {auth_key.created_by}",
                                       "warning")
                return webinterface.redirect(request, f"/authkeys/{authkey_id}/details")

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/authkeys/remove.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/authkeys/{authkey_id}/details",
                                        auth_key.label)
            webinterface.add_breadcrumb(request, f"/authkeys/{authkey_id}/remove",
                                        "Delete")
            return page.render(alerts=webinterface.get_alerts(),
                               authkey=auth_key,
                               )

        @webapp.route("/<string:authkey_id>/remove", methods=["POST"])
        @require_auth()
        def page_lib_authkey_delete_post(webinterface, request, session, authkey_id):
            authkey_id = webinterface._Validate.id_string(authkey_id)
            if session.has_access("authkey", "*", "delete", raise_error=False) is False:
                webinterface.add_alert("You don't have access to delete this.", "warning")
                return webinterface.redirect(request, f"/authkeys/{authkey_id}/details")

            try:
                auth_key = webinterface._AuthKeys.get(authkey_id)
            except KeyError:
                webinterface.add_alert("Invalid Auth Key id.", "warning")
                return webinterface.redirect(request, "/authkeys/index")

            if auth_key.created_by_type != "user":
                webinterface.add_alert(f"This auth key cannot be edited, created by: {auth_key.created_by}",
                                       "warning")
                return webinterface.redirect(request, f"/authkeys/{authkey_id}/details")

            try:
                confirm = request.args.get("confirm")[0]
            except:
                return webinterface.redirect(request, f"/authkeys/{authkey_id}/remove")

            if confirm != "delete":
                webinterface.add_alert("Must enter 'delete' in the confirmation box to delete the Auth Key.", "warning")
                return webinterface.redirect(request, f"/authkeys/{authkey_id}/remove")
            auth_key.expire()

            msg = {
                "header": "API Auth Deleted",
                "label": "API Auth deleted successfully",
                "description": '<p>The Auth Key has been deleted.<p><a href="/authkeys/index">API Auth index</a>.</p>',
            }
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/display_notice.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/authkey", "Deleted Auth Key")

            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )

        @webapp.route("/<string:authkey_id>/rotate", methods=["GET"])
        @require_auth()
        def page_lib_authkey_rotate_get(webinterface, request, session, authkey_id):
            authkey_id = webinterface._Validate.id_string(authkey_id)
            if session.has_access("authkey", authkey_id, "edit", raise_error=False) is False:
                webinterface.add_alert("You don't have access to edit this.", "warning")
                return webinterface.redirect(request, f"/authkeys/{authkey_id}/details")

            try:
                auth_key = webinterface._AuthKeys.get(authkey_id)
            except KeyError:
                webinterface.add_alert("Invalid Auth Key id.", "warning")
                return webinterface.redirect(request, "/authkeys/index")

            if auth_key.created_by_type != "user":
                webinterface.add_alert(f"This auth key cannot be edited, created by: {auth_key.created_by}",
                                       "warning")
                return webinterface.redirect(request, f"/authkeys/{authkey_id}/details")

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/authkeys/rotate.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/authkeys/{authkey_id}/details",
                                        auth_key.label)
            webinterface.add_breadcrumb(request, f"/authkeys/{authkey_id}/remove",
                                        "Rotate")
            return page.render(alerts=webinterface.get_alerts(),
                               authkey=auth_key,
                               )

        @webapp.route("/<string:authkey_id>/rotate", methods=["POST"])
        @require_auth()
        def page_lib_authkey_rotate_post(webinterface, request, session, authkey_id):
            authkey_id = webinterface._Validate.id_string(authkey_id)
            if session.has_access("authkey", authkey_id, "edit", raise_error=False) is False:
                webinterface.add_alert("You don't have access to edit this.", "warning")
                return webinterface.redirect(request, f"/authkeys/{authkey_id}/details")

            try:
                auth_key = webinterface._AuthKeys.get(authkey_id)
            except KeyError:
                webinterface.add_alert("Invalid Auth Key id.", "warning")
                return webinterface.redirect(request, "/authkeys/index")

            if auth_key.created_by_type != "user":
                webinterface.add_alert(f"This auth key cannot be edited, created by: {auth_key.created_by}",
                                       "warning")
                return webinterface.redirect(request, f"/authkeys/{authkey_id}/details")

            try:
                confirm = request.args.get("confirm")[0]
            except:
                return webinterface.redirect(request, f"/authkeys/{authkey_id}/rotate")

            if confirm != "rotate":
                webinterface.add_alert("Must enter 'rotate' in the confirmation box to rotate the Auth Key.", "warning")
                return webinterface.redirect(request, f"/authkeys/{authkey_id}/rotate")
            auth_key.rotate()

            msg = {
                "header": "API Auth Rotated",
                "label": "API Auth rotated successfully",
                "description": f"<p>The Auth Key has been rotated.</p><p>The new key: {auth_key.auth_id}</p>"
                               f"<p><a href=\"/authkeys/index\">API Auth index</a>.</p>",
            }
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/display_notice.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/authkeys/{authkey_id}/details",
                                        auth_key.label)
            webinterface.add_breadcrumb(request, f"/authkeys/{authkey_id}/remove",
                                        "Rotate")

            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )
