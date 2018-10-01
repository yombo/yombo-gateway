# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/roles" sub-route of the web interface.

Responsible for adding, removing, and updating roles.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.20.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/route_devices.py>`_
"""
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.route_devices")

def route_roles(webapp):
    with webapp.subroute("/roles") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/roles/index", "Roles")

        @webapp.route('/')
        @require_auth()
        def page_roles(webinterface, request, session):
            """ Redirects to /roles/index """
            session.has_access('role', '*', 'view', raise_error=True)
            return webinterface.redirect(request, '/roles/index')

        @webapp.route('/index')
        @require_auth()
        def page_roles_index(webinterface, request, session):
            """ Handles roles index page. """
            session.has_access('role', '*', 'view', raise_error=True)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/roles/index.html')
            root_breadcrumb(webinterface, request)
            return page.render(
                alerts=webinterface.get_alerts(),
                request=request,
            )

        @webapp.route('/<string:role_id>/details', methods=['GET'])
        @require_auth()
        def page_roles_details_get(webinterface, request, session, role_id):
            """ Displays details for a role. """
            session.has_access('role', role_id, 'view', raise_error=True)
            try:
                role = webinterface._Users.get_role(role_id)
            except KeyError:
                role = None
            if role is None:
                webinterface.add_alert('Invalid role.', 'warning')
                return webinterface.redirect(request, '/roles/index')

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/roles/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/roles/%s/details" % role_id, role.label)
            return page.render(
                alerts=webinterface.get_alerts(),
                request=request,
                role=role,
            )

        @webapp.route('/add', methods=['GET'])
        @require_auth()
        def page_roles_add_get(webinterface, request, session):
            """ Display form to add a new role. """
            session.has_access('role', '*', 'add', raise_error=True)
            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/roles/add", "Add")
            return page_roles_form(webinterface, request, session, 'add', data, "Add Role")

        @webapp.route('/add', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_roles_add_post(webinterface, request, session):
            """ Receive new role via HTTP POST and then tosses it to Users library to add. """
            session.has_access('role', '*', 'add', raise_error=True)
            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
            }

            try:
                role = yield webinterface._Users.add_role(data, source="user")
            except YomboWarning as e:
                webinterface.add_alert("Cannot add role. %s" % e.message, 'warning')
                return page_roles_form(webinterface, request, session, 'add', data, "Add Role",)

            webinterface.add_alert("New role '%s' added." % data['label'])
            return webinterface.redirect(request, "/roles/%s/details" % role.role_id)

        @webapp.route('/<string:role_id>/edit', methods=['GET'])
        @require_auth()
        def page_roles_edit_get(webinterface, request, session, role_id):
            """ Display form to edit a role. """
            session.has_access('role', role_id, 'edit', raise_error=True)
            try:
                role = webinterface._Users.get_role(role_id)
            except KeyError:
                role = None
            if role is None:
                webinterface.add_alert('Invalid role.', 'warning')
                return webinterface.redirect(request, '/roles/index')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/roles/%s/details" % role.role_id, role.label)
            webinterface.add_breadcrumb(request, "/roles/%s/edit" % role.role_id, "Edit")
            data = {
                'label': role.label,
                'machine_label': role.machine_label,
                'description':  role.description(),
                'role_id': role_id
            }
            return page_roles_form(webinterface,
                                   request,
                                   session,
                                   'edit',
                                   data,
                                   "Edit Role: %s" % role.label)

        @webapp.route('/<string:role_id>/edit', methods=['POST'])
        @require_auth()
        def page_roles_edit_post(webinterface, request, session, role_id):
            """ Receives HTTP POST with updated role information. """
            session.has_access('role', role_id, 'edit', raise_error=True)
            try:
                role = webinterface._Users.get_role(role_id)
            except KeyError:
                role = None
            if role is None:
                webinterface.add_alert('Invalid role.', 'warning')
                return webinterface.redirect(request, '/roles/index')

            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'role_id': role_id,
            }

            try:
                role = webinterface._roles.edit(role_id,
                                                data['label'], data['machine_label'],
                                                data['description'], data['status'])
            except YomboWarning as e:
                webinterface.add_alert("Cannot edit role. %s" % e.message, 'warning')
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/roles/%s/details" % role.role_id, role.label)
                webinterface.add_breadcrumb(request, "/roles/%s/edit", "Edit")

                return page_roles_form(webinterface, request, session, 'edit', data,
                                       "Edit Role: %s" % role.label)

            webinterface.add_alert("Role '%s' edited." % role.label)
            return webinterface.redirect(request, "/roles/%s/details" % role.role_id)

        def page_roles_form(webinterface, request, session, action_type, role, header_label):
            """ Displays the form for adding and editing. """
            page = webinterface.get_template(
                request,
                webinterface.wi_dir + '/pages/roles/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               role=role,
                               action_type=action_type,
                               )

        @webapp.route('/<string:role_id>/add_item_permission', methods=['POST'])
        @require_auth()
        def page_roles_add_item_permission_post(webinterface, request, session, role_id):
            """
            Adds a new item to a role. Collects the HTTP POST data, and finds the role instance, and then
            passes the data to that instance for handling.
            """
            session.has_access('role', role_id, 'edit', raise_error=True)
            try:
                role = webinterface._Users.get_role(role_id)
            except KeyError:
                role = None
            if role is None:
                webinterface.add_alert('Invalid role.', 'warning')
                return webinterface.redirect(request, '/roles/index')

            try:
                platform = request.args.get('platform')[0]
            except KeyError:
                webinterface.add_alert('Invalid request, platform is missing.', 'warning')
                return webinterface.redirect(request, "/roles/%s/details" % role.role_id)

            try:
                item = request.args.get('item')[0]
            except KeyError:
                webinterface.add_alert('Invalid request, item is missing.', 'warning')
                return webinterface.redirect(request, "/roles/%s/details" % role.role_id)

            newactions = {}
            for action, values in request.args.items():
                if action.startswith('allow_') or action.startswith('deny_'):
                    details = action.split('_', 2)
                    if details[0] not in newactions:
                        newactions[details[0]] = []
                    newactions[details[0]].append(details[1])

            try:
                for access, actions in newactions.items():
                    role.add_item_permission(platform, item, access, actions)
            except YomboWarning as e:
                webinterface.add_alert('Error adding device actions: %s' % e)

            try:
                add_type = request.args.get('add_type', [None])[0]
            except KeyError:
                add_type = None

            if add_type == None:
                try:
                    for access, actions in newactions.items():
                        role.add_item_permission(platform, item, access, actions)
                except YomboWarning as e:
                    webinterface.add_alert('Error adding device actions: %s' % e)

            elif add_type == "manual":
                try:
                    action = request.args.get('action')[0]
                except KeyError:
                    webinterface.add_alert('Invalid request, action is missing.', 'warning')
                    return webinterface.redirect(request, "/roles/%s/details" % role.role_id)
                try:
                    access = request.args.get('access')[0]
                except KeyError:
                    webinterface.add_alert('Invalid request, access is missing.', 'warning')
                    return webinterface.redirect(request, "/roles/%s/details" % role.role_id)

                except YomboWarning as e:
                    webinterface.add_alert('Error adding device actions: %s' % e)
                role.add_item_permission(platform, item, access, actions)

            return webinterface.redirect(request, '/roles/%s/details' % role_id)

        @webapp.route('/<string:role_id>/remove_item_permission/<string:platform>/<string:item_id>', methods=['GET'])
        @require_auth()
        def page_roles_remove_item_permission_get(webinterface, request, session, role_id, platform, item_id):
            """
            Receives request from HTTP GET. Finds the role instance, and then has it remove the permission_id.

            :param webinterface:
            :param request:
            :param session:
            :param role_id:
            :param platform:
            :return:
            """
            session.has_access('role', role_id, 'edit', raise_error=True)
            try:
                role = webinterface._Users.get_role(role_id)
            except KeyError:
                role = None
            if role is None:
                webinterface.add_alert('Invalid role.', 'warning')
                return webinterface.redirect(request, '/roles/index')

            try:
                role.remove_item_permission(platform, item_id)
            except YomboWarning as e:
                webinterface.add_alert('Error removing roles permissions: %s' % e)

            return webinterface.redirect(request, '/roles/%s/details' % role_id)

        @webapp.route('/<string:role_id>/remove_item_permission/<string:platform>/<string:item_id>/<string:access>/<string:action>', methods=['GET'])
        @require_auth()
        def page_roles_remove_item_permission_action_get(webinterface, request, session, role_id, platform,
                                                         item_id, access, action):
            session.has_access('role', role_id, 'edit', raise_error=True)
            try:
                role = webinterface._Users.get_role(role_id)
            except KeyError:
                role = None
            if role is None:
                webinterface.add_alert('Invalid role.', 'warning')
                return webinterface.redirect(request, '/roles/index')

            print("page_roles_remove_item_permission_action_get: action: %s" % action)
            try:
                role.remove_item_permission(platform, item_id, access, action)
            except YomboWarning as e:
                webinterface.add_alert('Error removing device actions: %s' % e)
            return webinterface.redirect(request, '/roles/%s/details' % role_id)
