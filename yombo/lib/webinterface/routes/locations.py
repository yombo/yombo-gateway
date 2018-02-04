# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/modules" sub-route of the web interface.

Responsible for adding, removing, and updating modules that are used by the gateway.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/route_modules.py>`_
"""

try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import require_auth
from yombo.core.exceptions import YomboWarning

def route_locations(webapp):
    """
    Extends routes of the webapp (web interface).

    :param webapp: the Klein web server instance
    :return:
    """
    with webapp.subroute("/locations") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/locations/index", "Locations")

        @webapp.route('/')
        @require_auth()
        def page_lib_location(webinterface, request, session):
            return webinterface.redirect(request, '/locations/index')

        @webapp.route('/index')
        @require_auth()
        def page_lib_location_index(webinterface, request, session):
            """
            Show an index of modules configured on the Gateway.
            :param webinterface: pointer to the web interface library
            :param request: a Twisted request
            :param session: User's session information.
            :return:
            """
            page = webinterface.get_template(request, webinterface._dir + 'pages/locations/index.html')
            root_breadcrumb(webinterface, request)
            # print("webinterface._Locations.locations: %s" % webinterface._Locations.locations)
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/<string:location_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_lib_location_details_get(webinterface, request, session, location_id):
            try:
                DL_results = yield webinterface._YomboAPI.request('GET', '/v1/location/%s' % location_id)
            except YomboWarning as e:
                print(e)
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/locations/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/locations/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/locations/%s/details" % DL_results['data']['id'],
                                        DL_results['data']['label'])
            return page.render(alerts=webinterface.get_alerts(),
                               location=DL_results['data'],
                               )

        @webapp.route('/add', methods=['GET'])
        @require_auth()
        def page_lib_location_add_get(webinterface, request, session):
            print("page_location_add_get")
            data = {
                'location_type': webinterface.request_get_default(request, 'location_type', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/locations/add", "Add")
            return page_lib_location_form(webinterface, request, session, 'add', data,
                                               "Add Location")

        @webapp.route('/add', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_lib_location_add_post(webinterface, request, session):
            print("page_location_add_post")
            data = {
                'location_type': webinterface.request_get_default(request, 'location_type', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
            }

            results = yield webinterface._Locations.add_location(data)
            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                return page_lib_location_form(webinterface, request, session, 'add', data, "Add Location")

            msg = {
                'header': 'Location Added',
                'label': 'Location added successfully',
                'description': '<p>The location has been added.<p>Continue to <a href="/locations/index">Locations index</a> or <a href="/locations/%s/details">View new Location</a>.</p>' %
                               results['location_id'],
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/locations/add", "Add")
            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )

        @webapp.route('/<string:location_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_lib_location_edit_get(webinterface, request, session, location_id):
            try:
                DL_results = yield webinterface._YomboAPI.request('GET', '/v1/location/%s' % location_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/locations/index')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/locations/%s/details" % DL_results['data']['id'],
                                        DL_results['data']['label'])
            webinterface.add_breadcrumb(request, "/locations/%s/edit", "Edit")

            return page_lib_location_form(webinterface,
                                          request, session, 'edit', DL_results['data'],
                                          "Edit Location: %s" % DL_results['data']['label'])

        @webapp.route('/<string:location_id>/edit', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_lib_location_edit_post(webinterface, request, session, location_id):
            data = {
                'voice_cmd': webinterface.request_get_default(request, 'voice_cmd', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'id': location_id,
            }

            DL_results = yield webinterface._Locations.edit_location(location_id, data)

            if DL_results['status'] == 'failed':
                webinterface.add_alert(DL_results['apimsghtml'], 'warning')
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/locations/%s/details" % location_id,
                                            DL_results['data']['label'])
                webinterface.add_breadcrumb(request, "/locations/%s/edit" % location_id, "Edit")


                return webinterface.redirect(request, '/locations/index')

            msg = {
                'header': 'Location Updated',
                'label': 'Location updated successfully',
                'description': '<p>The location has been updated.<p>Continue to <a href="/locations/index">Locations index</a> or <a href="/locations/%s/details">View updated Location</a>.</p>' %
                               DL_results['location_id'],
            }

            # DL_api_results = yield webinterface._YomboAPI.request('GET', '/v1/location/%s' % location_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/locations/%s/details" % location_id,
                                        data['label'])
            webinterface.add_breadcrumb(request, "/locations/%s/edit", "Edit")

            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )

        def page_lib_location_form(webinterface, request, session, action_type, location, header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/locations/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               location=location,
                               action_type=action_type,
                               )

        @webapp.route('/<string:location_id>/delete', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_lib_location_delete_get(webinterface, request, session, location_id):
            try:
                DL_results = yield webinterface._YomboAPI.request('GET', '/v1/location/%s' % location_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/locations/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/locations/remove.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/locations/%s/details" % location_id,
                                        DL_results['data']['label'])
            webinterface.add_breadcrumb(request, "/locations/%s/delete" % location_id, "Delete")
            return page.render(alerts=webinterface.get_alerts(),
                               location=DL_results['data'],
                               )

        @webapp.route('/<string:location_id>/delete', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_lib_location_delete_post(webinterface, request, session, location_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request, '/locations/%s/details' % location_id)

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the location.', 'warning')
                return webinterface.redirect(request, '/locations/%s/details' % location_id)

            DL_results = yield webinterface._Locations.delete_location(location_id)

            if DL_results['status'] == 'failed':
                webinterface.add_alert(DL_results['apimsghtml'], 'warning')
                return webinterface.redirect(request, '/locations/%s/details' % location_id)

            msg = {
                'header': 'Location Deleted',
                'label': 'Location deleted successfully',
                'description': '<p>The location has been deleted.<p><a href="/locations/index">Locations index</a>.</p>',
            }
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )
