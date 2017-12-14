# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/apiauth" sub-route of the web interface.

Responsible for adding, removing, and updating api auth keys that are used to
access the gateway API.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.15.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/routes/apiauth.py>`_
"""

try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import require_auth
from yombo.core.exceptions import YomboWarning

def route_apiauth(webapp):
    """
    Extends routes of the webapp (web interface).

    :param webapp: the Klein web server instance
    :return:
    """
    with webapp.subroute("/apiauth") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/apiauth/index", "API Auth")

        @webapp.route('/')
        @require_auth()
        def page_lib_apiauth(webinterface, request, session):
            return webinterface.redirect(request, '/apiauth/index')

        @webapp.route('/index')
        @require_auth()
        @inlineCallbacks
        def page_lib_apiauth_index(webinterface, request, session):
            """
            Show an index of api auth keys configured across all gateways within a cluster.

            :param webinterface: pointer to the web interface library
            :param request: a Twisted request
            :param session: User's session information.
            :return:
            """
            page = webinterface.get_template(request, webinterface._dir + 'pages/apiauth/index.html')
            root_breadcrumb(webinterface, request)
            # print("webinterface._Locations.locations: %s" % webinterface._Locations.locations)
            try:
                api_auths = yield webinterface.apiauths.get_all()
            except YomboWarning as e:
                api_auths = []
            return page.render(alerts=webinterface.get_alerts(),
                               apiauths=api_auths,
                               )

        @webapp.route('/<string:apiauth_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_lib_apiauth_details_get(webinterface, request, session, apiauth_id):
            api_auth = yield webinterface.apiauths.get(api_auth_id=apiauth_id)
            if api_auth is None:
                webinterface.add_alert('Invalid API Auth Key id: %s' % apiauth_id, 'warning')
                return webinterface.redirect(request, '/apiauth/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/apiauth/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/apiauth/%s/details" % apiauth_id,
                                        api_auth.label)
            return page.render(alerts=webinterface.get_alerts(),
                               apiauths=webinterface.apiauths,
                               apiauth=api_auth,
                               )

        @webapp.route('/add', methods=['GET'])
        @require_auth()
        def page_lib_apiauth_add_get(webinterface, request, session):
            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'permissions': webinterface.request_get_default(request, 'permissions', {}),
                'is_valid': webinterface.request_get_default(request, 'is_valid', True),
                'gateway_id': webinterface.request_get_default(request, 'gateway_id', webinterface.gateway_id()),
            }

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/apiauth/add", "Add")
            return page_lib_apiauth_form(webinterface, request, session, 'add', data,
                                               "Add API Auth")

        @webapp.route('/add', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_lib_apiauth_add_post(webinterface, request, session):
            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'permissions': webinterface.request_get_default(request, 'permissions', {}),
                'is_valid': webinterface.request_get_default(request, 'is_valid', True),
                'gateway_id': webinterface.request_get_default(request, 'gateway_id', webinterface.gateway_id()),
            }

            api_auth = yield webinterface.apiauths.create(
                request,
                data=data,
            )

            if api_auth is None:
                webinterface.add_alert("Unable to add API Auth key, unknown reason. Sorry I'm not more helpful.",
                                       'warning')
                return page_lib_apiauth_form(webinterface, request, session, 'add', data, "Add Location")

            msg = {
                'header': 'API Auth key added',
                'label': 'New API auth added successfully',
                'description': '<p>New API Auth key: <strong>%s</strong></p>'
                               '<p>Continue to <strong><a href="/apiauth/index">API Auth key index</a></strong> or <a href="/apiauth/%s/details">View new API Auth Key</a>.</p>' %
                               (api_auth.api_auth_id, api_auth.api_auth_id),
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/apiauth/add", "Add")
            return page.render(alerts=webinterface.get_alerts(),
                                msg=msg,
                                )

        @webapp.route('/<string:apiauth_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_lib_apiauth_edit_get(webinterface, request, session, apiauth_id):
            api_auth = yield webinterface.apiauths.get(api_auth_id=apiauth_id)
            if api_auth is None:
                webinterface.add_alert('Invalid API Auth Key id: %s' % apiauth_id, 'warning')
                return webinterface.redirect(request, '/apiauth/index')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/apiauth/%s/details" % api_auth.api_auth_id,
                                        api_auth.label)
            webinterface.add_breadcrumb(request, "/apiauth/%s/edit", "Edit")

            return page_lib_apiauth_form(webinterface, request, session, 'edit', api_auth.__dict__,
                                             "Edit API Auth: %s" % api_auth.label)

        @webapp.route('/<string:apiauth_id>/edit', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_lib_apiauth_edit_post(webinterface, request, session, apiauth_id):
            api_auth = yield webinterface.apiauths.get(api_auth_id=apiauth_id)
            if api_auth is None:
                webinterface.add_alert('Invalid API Auth Key id: %s' % apiauth_id, 'warning')
                return webinterface.redirect(request, '/apiauth/index')

            attributes = ['label', 'description', 'is_valid']
            data = {}
            for attr in attributes:
                temp = webinterface.request_get_default(request, attr, "")
                if temp != "":
                    data[attr] = temp

            print("updatinga ttributes: %s" % data)
            api_auth.update_attributes(data)

            msg = {
                'header': 'API Auth Updated',
                'label': 'API Auth updated successfully',
                'description': '<p>API Auth key updated: <strong>%s</strong></p>'
                               '<p>Continue to <strong><a href="/apiauth/index">API Auth the index</a></strong> or <a href="/apiauth/%s/details">View edited API Auth Key</a>.</p>' %
                               (apiauth_id, apiauth_id)
            }
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/apiauth/add", "Add")
            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        def page_lib_apiauth_form(webinterface, request, session, action_type, apiauth, header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/apiauth/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               apiauth=apiauth,
                               action_type=action_type,
                               )

        @webapp.route('/<string:apiauth_id>/delete', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_lib_apiauth_delete_get(webinterface, request, session, apiauth_id):
            api_auth = yield webinterface.apiauths.get(api_auth_id=apiauth_id)
            if api_auth is None:
                webinterface.add_alert('Invalid API Auth Key id: %s' % apiauth_id, 'warning')
                return webinterface.redirect(request, '/apiauth/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/apiauth/remove.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/apiauth/%s/details" % apiauth_id,
                                        api_auth.label)
            webinterface.add_breadcrumb(request, "/apiauth/%s/delete" % apiauth_id,
                                        'Delete')
            return page.render(alerts=webinterface.get_alerts(),
                               apiauth=api_auth,
                               )

        @webapp.route('/<string:apiauth_id>/delete', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_lib_apiauth_delete_post(webinterface, request, session, apiauth_id):
            api_auth = yield webinterface.apiauths.get(api_auth_id=apiauth_id)
            if api_auth is None:
                webinterface.add_alert('Invalid API Auth Key id: %s' % apiauth_id, 'warning')
                return webinterface.redirect(request, '/apiauth/index')

            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request, '/apiauth/%s/delete' % apiauth_id)

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the API Auth key.', 'warning')
                return webinterface.redirect(request, '/apiauth/%s/delete' % apiauth_id)
            api_auth.expire_session()

            msg = {
                'header': 'API Auth Deleted',
                'label': 'API Auth deleted successfully',
                'description': '<p>The API Auth key has been deleted.<p><a href="/apiauth/index">API Auth index</a>.</p>',
            }
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )
