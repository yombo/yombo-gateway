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
            session.has_access('user:*', 'view', raise_error=True)
            return webinterface.redirect(request, '/users/index')

        @webapp.route('/index')
        @require_auth()
        def page_users_index(webinterface, request, session):
            session.has_access('user:*', 'view', raise_error=True)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/users/index.html')
            root_breadcrumb(webinterface, request)
            return page.render(
                alerts=webinterface.get_alerts(),
            )

        @webapp.route('/<string:user_requested>/details', methods=['GET'])
        @require_auth()
        def page_users_details_get(webinterface, request, session, user_requested):
            session.has_access('user:%s' % user_requested, 'view', raise_error=True)
            try:
                user = webinterface._Users.get(user_requested)
            except KeyError:
                webinterface.add_alert('Requested user not found.', 'warning')
                return webinterface.redirect(request, '/users')
            if session.has_access('users:%s' % user.email, 'view') is False:
                print("Current user not supposed to have access...")

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/users/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/users/someuser/details", user.name)
            return page.render(
                alerts=webinterface.get_alerts(),
                user=user,
            )

        @webapp.route('/<string:user_requested>/details', methods=['POST'])
        @require_auth(access_path="module_amazonalexa:manage", access_action="view")
        def page_users_details_post(webinterface, request, session, user_requested):
            session.has_access('user:%s' % user_requested, 'view', raise_error=True)
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

            user.add_role(role_label)

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/users/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/users/someuser/details", user.name)
            return page.render(
                alerts=webinterface.get_alerts(),
                user=user,
            )

        @webapp.route('/add', methods=['GET'])
        @require_auth()
        def page_users_add_get(webinterface, request, session):
            session.has_access('user:*', 'add', raise_error=True)
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
            session.has_access('user:*', 'add', raise_error=True)
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
                search_results = yield webinterface._YomboAPI.request('GET',
                                                                      '/v1/user/%s' % user_requested,
                                                                      None,
                                                                      session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert("User not found: %s" % user_requested)
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/users/add.html')
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/users/add", "Add User")
                return page.render(
                    alerts=webinterface.get_alerts(),
                    last_search=user_requested,
                )

            data = {
                'user_id': search_results['data']['id'],
            }
            try:
                add_results = yield webinterface._YomboAPI.request('POST',
                                                                   '/v1/gateway/%s/user' % webinterface.gateway_id(),
                                                                   data,
                                                                   session['yomboapi_session'])
            except YomboWarning as e:
                print("add_results e: %s" % e)
                webinterface.add_alert("Could not add user to gateway: %s" % e.html_message)
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/users/add.html')
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/users/add", "Add User")
                return page.render(
                    alerts=webinterface.get_alerts(),
                    last_search=user_requested,
                )

            add_results['data']['id'] = add_results['data']['user_id']
            webinterface._Users.add_user(add_results['data'])
            webinterface.add_alert("User added")

            return webinterface.redirect(request, '/users/%s/details' % user_requested)
