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
from yombo.lib.webinterface.auth import require_auth, run_first
from twisted.internet.defer import inlineCallbacks

def route_device_locations(webapp):
    """
    Extends routes of the webapp (web interface).

    :param webapp: the Klein web server instance
    :return:
    """
    with webapp.subroute("/device_locations") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/device_locations/index", "Device Locations")

        @webapp.route('/')
        @require_auth()
        def page_device_location(webinterface, request, session):
            return webinterface.redirect(request, '/device_locations/index')

        @webapp.route('/index')
        @require_auth()
        def page_device_location_index(webinterface, request, session):
            """
            Show an index of modules configured on the Gateway.
            :param webinterface: pointer to the web interface library
            :param request: a Twisted request
            :param session: User's session information.
            :return:
            """
            page = webinterface.get_template(request, webinterface._dir + 'pages/device_locations/index.html')
            root_breadcrumb(webinterface, request)
            # print("webinterface._DeviceLocations.device_locations: %s" % webinterface._DeviceLocations.device_locations)
            return page.render(alerts=webinterface.get_alerts(),
                               locations=webinterface._DeviceLocations.device_locations,
                               )

        @webapp.route('/<string:device_location_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_device_location_details_get(webinterface, request, session, device_location_id):
            DL_results = yield webinterface._YomboAPI.request('GET', '/v1/device_location/%s' % device_location_id)
            if DL_results['code'] > 299:
                print(DL_results)
                webinterface.add_alert(DL_results['content']['html_message'], 'warning')
                return webinterface.redirect(request, '/device_locations/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/device_locations/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/device_locations/%s/details" % DL_results['data']['id'],
                                        DL_results['data']['label'])
            return page.render(alerts=webinterface.get_alerts(),
                                    device_location=DL_results['data'],
                                    )

        @webapp.route('/add', methods=['GET'])
        @require_auth()
        def page_device_location_add_get(webinterface, request, session):
            print("page_device_location_add_get")
            data = {
                'location_type': webinterface.request_get_default(request, 'location_type', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/device_locations/add", "Add")
            return page_device_location_form(webinterface, request, session, 'add', data,
                                               "Add Device Location")

        @webapp.route('/add', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_device_location_add_post(webinterface, request, session):
            print("page_device_location_add_post")
            data = {
                'location_type': webinterface.request_get_default(request, 'location_type', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
            }

            DL_results = yield webinterface._DeviceLocations.add_device_location(data)

            if DL_results['status'] == 'failed':
                webinterface.add_alert(DL_results['apimsghtml'], 'warning')
                return page_device_location_form(webinterface, request, session, 'add', data, "Add Device Location")

            msg = {
                'header': 'Device Location Added',
                'label': 'Device Location added successfully',
                'description': '<p>The device location has been added.<p>Continue to <a href="/device_locations/index">Device Locations index</a> or <a href="/device_locations/%s/details">View new Device Location</a>.</p>' %
                               DL_results['device_location_id'],
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/device_locations/add", "Add")
            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/<string:device_location_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_device_location_edit_get(webinterface, request, session, device_location_id):
            DL_results = yield webinterface._YomboAPI.request('GET', '/v1/device_location/%s' % device_location_id)
            if DL_results['code'] > 299:
                webinterface.add_alert(DL_results['content']['html_message'], 'warning')
                return webinterface.redirect(request, '/device_location/index')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/device_locations/%s/details" % DL_results['data']['id'],
                                        DL_results['data']['label'])
            webinterface.add_breadcrumb(request, "/device_locations/%s/edit", "Edit")

            return page_device_location_form(webinterface, request, session, 'edit', DL_results['data'],
                                             "Edit Device Location: %s" % DL_results['data']['label'])

        @webapp.route('/<string:device_location_id>/edit', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_device_location_edit_post(webinterface, request, session, device_location_id):
            data = {
                'voice_cmd': webinterface.request_get_default(request, 'voice_cmd', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'id': device_location_id,
            }

            DL_results = yield webinterface._DeviceLocations.edit_device_location(device_location_id, data)

            if DL_results['status'] == 'failed':
                webinterface.add_alert(DL_results['apimsghtml'], 'warning')
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/device_locations/%s/details" % device_location_id,
                                            DL_results['data']['label'])
                webinterface.add_breadcrumb(request, "/device_locations/%s/edit" % device_location_id, "Edit")


                return webinterface.redirect(request, '/device_locations/index')

            msg = {
                'header': 'Device Location Updated',
                'label': 'Device Location updated successfully',
                'description': '<p>The device location has been updated.<p>Continue to <a href="/device_locations/index">Device Locations index</a> or <a href="/device_locations/%s/details">View updated Device Location</a>.</p>' %
                               DL_results['device_location_id'],
            }

            DL_api_results = yield webinterface._YomboAPI.request('GET', '/v1/device_location/%s' % device_location_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            if DL_api_results['code'] > 299:
                webinterface.add_breadcrumb(request, "/device_locations/%s/details" % device_location_id,
                                            DL_results['data']['label'])
                webinterface.add_breadcrumb(request, "/device_locations/%s/edit" % device_location_id, "Edit")

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        def page_device_location_form(webinterface, request, session, action_type, device_location, header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/device_locations/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               device_location=device_location,
                               action_type=action_type,
                               )

        @webapp.route('/<string:device_location_id>/delete', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_device_location_delete_get(webinterface, request, session, device_location_id):
            DL_results = yield webinterface._YomboAPI.request('GET', '/v1/device_location/%s' % device_location_id)
            if DL_results['code'] > 299:
                webinterface.add_alert(DL_results['content']['html_message'], 'warning')
                return webinterface.redirect(request, '/device_locations/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/device_locations/remove.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/device_locations/%s/details" % device_location_id,
                                        DL_results['data']['label'])
            webinterface.add_breadcrumb(request, "/device_locations/%s/delete" % device_location_id, "Delete")
            return page.render(alerts=webinterface.get_alerts(),
                                    device_location=DL_results['data'],
                                    )

        @webapp.route('/<string:device_location_id>/delete', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_device_location_delete_post(webinterface, request, session, device_location_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request, '/device_locations/%s/details' % device_location_id)

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the device location.', 'warning')
                return webinterface.redirect(request, '/device_locations/%s/details' % device_location_id)

            DL_results = yield webinterface._DeviceLocations.delete_device_location(device_location_id)

            if DL_results['status'] == 'failed':
                webinterface.add_alert(DL_results['apimsghtml'], 'warning')
                return webinterface.redirect(request, '/device_locations/%s/details' % device_location_id)

            msg = {
                'header': 'Device Location Deleted',
                'label': 'Device Location deleted successfully',
                'description': '<p>The device location has been deleted.<p><a href="/device_locations/index">Device Locations index</a>.</p>',
            }
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )
