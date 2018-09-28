# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/users" sub-route of the web interface.

Responsible for adding, removing, and updating users and their roles.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.20.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/route_devices.py>`_
"""

from collections import OrderedDict
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.route_devices")

def route_users(webapp):
    with webapp.subroute("/users") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/users/index", "Users")

        @webapp.route('/')
        @require_auth()
        def page_users(webinterface, request, session):
            session.has_access('user', '*', 'view', raise_error=True)
            return webinterface.redirect(request, '/users/index')

        @webapp.route('/index')
        @require_auth()
        def page_users_index(webinterface, request, session):
            session.has_access('user', '*', 'view', raise_error=True)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/users/index.html')
            root_breadcrumb(webinterface, request)
            return page.render(
                alerts=webinterface.get_alerts(),
            )

        @webapp.route('/<string:user_requested>/details', methods=['GET'])
        @require_auth()
        def page_users_details_get(webinterface, request, session, user_requested):
            session.has_access('user', user_requested, 'view', raise_error=True)
            try:
                user = webinterface._Users.get(user_requested)
            except KeyError:
                webinterface.add_alert('Requested user not found.', 'warning')
                return webinterface.redirect(request, '/users')

            return return_user_details(webinterface, request, session, user)


        @webapp.route('/<string:user_requested>/details', methods=['POST'])
        @require_auth(access_path="module_amazonalexa:manage", access_action="view")
        def page_users_details_post(webinterface, request, session, user_requested):
            session.has_access('user', user_requested, 'view', raise_error=True)
            session.has_access('user', user_requested, 'edit', raise_error=True)
            try:
                role_label = request.args.get('role_label')[0]
            except KeyError:
                webinterface.add_alert('Invalid request.', 'warning')
                return webinterface.redirect(request, '/users/%s/details' % user_requested)

            try:
                user = webinterface._Users.get(user_requested)
            except KeyError:
                webinterface.add_alert('Requested user not found.', 'warning')
                return webinterface.redirect(request, '/users/index')

            try:
                user.attach_role(role_label)
            except YomboWarning as e:
                webinterface.add_alert('Error adding role: %s' % e)
                return return_user_details(webinterface, request, session, user)
            webinterface.add_alert('Role added to user.')

            return return_user_details(webinterface, request, session, user)

        def return_user_details(webinterface, request, session, user):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/users/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/users/someuser/details", user.name)
            return page.render(
                alerts=webinterface.get_alerts(),
                user=user,
                session=session,
            )

        @webapp.route('/<string:user_requested>/unattach_role/<string:role_id>', methods=['GET'])
        @require_auth()
        def page_users_unattach_role_get(webinterface, request, session, user_requested, role_id):
            session.has_access('user', user_requested, 'view', raise_error=True)
            session.has_access('user', user_requested, 'edit', raise_error=True)
            try:
                user = webinterface._Users.get(user_requested)
            except KeyError:
                webinterface.add_alert('Requested user not found.', 'warning')
                return webinterface.redirect(request, '/users')
            try:
                user.unattach_role(role_id)
            except KeyError:
                webinterface.add_alert('Cannot find role')
                return return_user_details(webinterface, request, session, user)
            except YomboWarning as e:
                webinterface.add_alert('Error removing role: %s' % e)
                return return_user_details(webinterface, request, session, user)

            webinterface.add_alert('Role removed from user.')
            return webinterface.redirect(request, '/users/%s/details' % user.user_id)

        @webapp.route('/<string:user_requested>/add_item_permission', methods=['POST'])
        @require_auth()
        def page_users_add_item_permission_post(webinterface, request, session, user_requested):
            session.has_access('user', '*', 'edit', raise_error=True)
            try:
                user = webinterface._Users.get(user_requested)
            except KeyError:
                webinterface.add_alert('Requested user not found.', 'warning')
                return webinterface.redirect(request, '/users')

            try:
                platform = request.args.get('platform')[0]
            except KeyError:
                webinterface.add_alert('Invalid request, platform is missing.', 'warning')
                return webinterface.redirect(request, '/users/index' % user_requested)

            try:
                item = request.args.get('item')[0]
            except KeyError:
                webinterface.add_alert('Invalid request, item is missing.', 'warning')
                return webinterface.redirect(request, '/users/index' % user_requested)

            newactions = {}
            for action, values in request.args.items():
                if action.startswith('allow_') or action.startswith('deny_'):
                    details = action.split('_', 2)
                    if details[0] not in newactions:
                        newactions[details[0]] = []
                    newactions[details[0]].append(details[1])

            try:
                for access, actions in newactions.items():
                    user.add_item_permission(platform, item, access, actions)
            except YomboWarning as e:
                webinterface.add_alert('Error adding device actions: %s' % e)

            return webinterface.redirect(request, '/users/%s/details' % user.user_id)

        @webapp.route('/<string:user_requested>/remove_item_permission/<string:platform>/<string:item_id>', methods=['GET'])
        @require_auth()
        def page_users_remove_item_permission_get(webinterface, request, session, user_requested, platform, item_id):
            session.has_access('user', '*', 'edit', raise_error=True)
            try:
                user = webinterface._Users.get(user_requested)
            except KeyError:
                webinterface.add_alert('Requested user not found.', 'warning')
                return webinterface.redirect(request, '/users')

            try:
                user.remove_item_permission(platform, item_id)
            except YomboWarning as e:
                webinterface.add_alert('Error removing device actions: %s' % e)

            return webinterface.redirect(request, '/users/%s/details' % user.user_id)

        @webapp.route('/<string:user_requested>/remove_item_permission/<string:platform>/<string:item_id>/<string:access>/<string:action>', methods=['GET'])
        @require_auth()
        def page_users_remove_item_permission_action_get(webinterface, request, session, user_requested, platform,
                                                         item_id, access, action):
            session.has_access('user', '*', 'edit', raise_error=True)
            try:
                user = webinterface._Users.get(user_requested)
            except KeyError:
                webinterface.add_alert('Requested user not found.', 'warning')
                return webinterface.redirect(request, '/users')

            try:
                user.remove_item_permission(platform, item_id, access, action)
            except YomboWarning as e:
                webinterface.add_alert('Error removing device actions: %s' % e)

            return webinterface.redirect(request, '/users/%s/details' % user.user_id)

        @webapp.route('/add', methods=['GET'])
        @require_auth()
        def page_users_add_get(webinterface, request, session):
            session.has_access('user', '*', 'add', raise_error=True)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/users/add.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/users/add", "Add User")
            return page.render(
                alerts=webinterface.get_alerts(),
            )

        @webapp.route('/add', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_users_add_post(webinterface, request, session):
            session.has_access('user', '*', 'add', raise_error=True)
            try:
                user_requested = request.args.get('user_requested')[0]
            except KeyError:
                webinterface.add_alert('Invalid request.', 'warning')
                return webinterface.redirect(request, '/users/index' % user_requested)

            try:
                webinterface._Users.get(user_requested)
            except KeyError:
                pass
            else:
                webinterface.add_alert('User already belongs to gateway.', 'warning')
                return webinterface.redirect(request, '/users/index')

            try:
                search_results = yield webinterface._Users.api_search_user(user_requested)
            except YomboWarning as e:
                webinterface.add_alert("User not found: %s" % user_requested)
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/users/add.html')
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/users/add", "Add User")
                return page.render(
                    alerts=webinterface.get_alerts(),
                    last_search=user_requested,
                )

            try:
                add_results = yield webinterface._Users.add_user(search_results['id'],
                                                                 session['yomboapi_session'])
            except YomboWarning as e:
                print("page_users_add_post error details: %s" % e.details)
                webinterface.add_alert(e.html_message)
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/users/add.html')
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/users/add", "Add User")
                return page.render(
                    alerts=webinterface.get_alerts(),
                    last_search=user_requested,
                )
            webinterface.add_alert("User added")
            return webinterface.redirect(request, '/users/%s/details' % user_requested)

        @webapp.route('/<string:user_id>/remove', methods=['GET'])
        @require_auth()
        def page_users_remove_get(webinterface, request, session, user_id):
            session.has_access('user', user_id, 'delete', raise_error=True)
            try:
                user = webinterface._Users.get(user_id)
            except KeyError:
                webinterface.add_alert('Requested user not found.', 'warning')
                return webinterface.redirect(request, '/users')

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/users/remove.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/users/%s/details" % user.user_id, user.email)
            webinterface.add_breadcrumb(request, "/users/%s/remove" % user.user_id, "Remove")
            return page.render(alerts=webinterface.get_alerts(),
                               user=user,
                               )

        @webapp.route('/<string:user_id>/remove', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_users_remove_post(webinterface, request, session, user_id):
            session.has_access('user', user_id, 'delete', raise_error=True)
            try:
                user = webinterface._Users.get(user_id)
            except KeyError:
                webinterface.add_alert('Requested user not found.', 'warning')
                return webinterface.redirect(request, '/users')

            confirm = request.args.get('confirm')[0]
            if confirm != "remove":
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/users/remove.html')
                webinterface.add_alert('Must enter "disable" in the confirmation box to remove the module.', 'warning')
                return page.render(alerts=webinterface.get_alerts(),
                                   user=user,
                                   )

            try:
                results = yield webinterface._Users.remove_user(user.user_id, session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message)
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/users/remove.html')
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/users/%s/details" % user.user_id, user.email)
                webinterface.add_breadcrumb(request, "/users/%s/remove" % user.user_id, "Remove")
                return page.render(alerts=webinterface.get_alerts(),
                                   user=user,
                                   )

            webinterface.add_alert("User removed")
            return webinterface.redirect(request, '/users/index')
