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

def route_roles(webapp):
    with webapp.subroute("/roles") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/roles/index", "Roles")

        @webapp.route('/')
        @require_auth()
        def page_roles(webinterface, request, session):
            session.has_access('role', '*', 'view', raise_error=True)
            return webinterface.redirect(request, '/roles/index')

        @webapp.route('/index')
        @require_auth()
        def page_roles_index(webinterface, request, session):
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
            session.has_access('role', '*', 'add', raise_error=True)
            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
            }

            try:
                print("adding role data: %s" % data)
                role = yield webinterface._Users.add_role(data, source="user")
            except YomboWarning as e:
                webinterface.add_alert("Cannot add role. %s" % e.message, 'warning')
                return page_roles_form(webinterface, request, session, 'add', data, "Add Role",)

            webinterface.add_alert("New role '%s' added." % data['label'])
            return webinterface.redirect(request, "/roles/%s/details" % role.role_id)

        @webapp.route('/<string:role_id>/edit', methods=['GET'])
        @require_auth()
        def page_roles_edit_get(webinterface, request, session, role_id):
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
            page = webinterface.get_template(
                request,
                webinterface.wi_dir + '/pages/roles/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               role=role,
                               action_type=action_type,
                               )