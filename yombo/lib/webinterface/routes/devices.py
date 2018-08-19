# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/devices" sub-route of the web interface.

Responsible for adding, removing, and updating devices that are used by the gateway.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2017 by Yombo.
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
from yombo.core.exceptions import YomboWarning, YomboNoAccess
from yombo.lib.webinterface.auth import require_auth
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.route_devices")

def add_devices_breadcrumb(webinterface, request, device_id, session):
    local_devices = []
    cluster_devices = []

    permissions, item_permissions = webinterface._Users.get_access(session.item_permissions, session.roles, 'device')

    for select_device_id, select_device in webinterface._Devices.sorted().items():
        if select_device.enabled_status != 1 or select_device.machine_label not in item_permissions['device'] or \
                'allow_view' not in item_permissions['device'][select_device.machine_label]:
            continue

        if select_device.gateway_id == webinterface.gateway_id():
            label = select_device.area_label
        else:
            label = select_device.full_label

        if select_device.device_id == device_id:
            data = (label, "$/devices/%s/details" % select_device_id)
        else:
            data = (label, "/devices/%s/details" % select_device_id)

        if select_device.gateway_id == webinterface.gateway_id():
            local_devices.append(data)
        else:
            cluster_devices.append(data)

    data = OrderedDict()
    if len(local_devices) > 0:
        data['Local Gateway'] = OrderedDict()
        for item in local_devices:
            data['Local Gateway'][item[0]] = item[1]
    if len(cluster_devices) > 0:
        data['Local Cluster'] = OrderedDict()
        for item in cluster_devices:
            data['Local Cluster'][item[0]] = item[1]

    webinterface.add_breadcrumb(request, style='select_groups', data=data)


def route_devices(webapp):
    with webapp.subroute("/devices") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_devices(webinterface, request, session):
            session.has_access('device', '*', 'view')
            return webinterface.redirect(request, '/devices/index')

        @webapp.route('/index')
        @require_auth()
        def page_devices_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/devices/index.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            permissions, item_permissions = webinterface._Users.get_access(session.item_permissions,
                                                                           session.roles,
                                                                           'device')
            return page.render(
                alerts=webinterface.get_alerts(),
                request=request,
                user=session.user,
                permissions=permissions,
                item_permissions=item_permissions,
            )

        @webapp.route('/add')
        @require_auth()
        @inlineCallbacks
        def page_devices_add_select_device_type_get(webinterface, request, session):
            session.has_access('device', '*', 'add')

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/devices/add_select_device_type.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/add", "Add Device - Select Device Type")
            device_types = yield webinterface._DeviceTypes.addable_device_types()

            return page.render(
                alerts=webinterface.get_alerts(),
                device_types=device_types,
            )

        @webapp.route('/add/<string:device_type_id>', methods=['POST', 'GET'])
        @require_auth()
        @inlineCallbacks
        def page_devices_add_post(webinterface, request, session, device_type_id):
            session.has_access('device', '*', 'add')

            try:
                device_type = webinterface._DeviceTypes[device_type_id]
                device_type_id = device_type.device_type_id
            except Exception as e:
                webinterface.add_alert('Device Type ID was not found: %s' % device_type_id, 'warning')
                return webinterface.redirect(request, '/devices/add')

            ok_to_save = True

            if 'json_output' in request.args:
                json_output = request.args.get('json_output', [{}])[0]
                json_output = json.loads(json_output)
                if 'first_time' in json_output:
                    ok_to_save = False
            else:
                json_output = {}
                ok_to_save = False

            try:
                pin_required = int(json_output.get('pin_required', 0))
                if pin_required == 1:
                    if request.args.get('pin_code')[0] == "":
                        webinterface.add_alert('Device requires a pin code, but none was set.', 'warning')
                        return webinterface.redirect(request, '/devices')
            except Exception as e:
                logger.warn("Processing 'pin_required': {e}", e=e)
                pin_required = 0

            try:
                start_percent = json_output.get('start_percent', None)
                energy_usage = json_output.get('energy_usage', None)
                energy_map = {}
                if start_percent is not None and energy_usage is not None:
                    for idx, percent in enumerate(start_percent):
                        try:
                            energy_map[float(float(percent) / 100)] = energy_usage[idx]
                        except:
                            pass
                else:
                    ok_to_save = False

                energy_map = OrderedDict(sorted(list(energy_map.items()), key=lambda x_y: float(x_y[0])))
            except Exception as e:
                logger.warn("Error while processing device add_details: {e}", e=e)

            variable_data = yield webinterface._Variables.extract_variables_from_web_data(json_output.get('vars', {}))
            device = {
                # 'garage_id': json_output.get('garage_id', ""),
                'location_id': json_output.get('location_id', ""),
                'area_id': json_output.get('area_id', ""),
                'machine_label': json_output.get('machine_label', ""),
                'label': json_output.get('label', ""),
                'description': json_output.get('description', ""),
                'status': int(json_output.get('status', 1)),
                'statistic_label': json_output.get('statistic_label', ""),
                'statistic_type': json_output.get('statistic_type', "datapoint"),
                'statistic_bucket_size': json_output.get('statistic_bucket_size', ""),
                'statistic_lifetime': json_output.get('statistic_lifetime', 365),
                'device_type_id': device_type_id,
                'pin_required': pin_required,
                'pin_code': json_output.get('pin_code', ""),
                'pin_timeout': json_output.get('pin_timeout', ""),
                'energy_type': json_output.get('energy_type', ""),
                'energy_map': energy_map,
                'variable_data': variable_data,
                'voice_cmd': None,
                # 'voice_cmd_order': None,
                # 'voice_cmd_src': None,
            }

            if ok_to_save:
                try:
                    results = yield webinterface._Devices.add_device(device, source="webinterface", session=session['yomboapi_session'])
                except YomboWarning as e:
                    webinterface.add_alert("Cannot add device, reason: %s" % e.message)
                    return webinterface.redirect(request, '/devices')

                if results['status'] == 'success':
                    msg = {
                        'header':'Device Added',
                        'label':'Device added successfully',
                        'description': '',
                    }

                    webinterface._Notifications.add({'title': 'Restart Required',
                                                     'message': 'Device added. A system <strong><a  class="confirm-restart" href="#" title="Restart Yombo Gateway">restart is required</a></strong> to take affect.',
                                                     'source': 'Web Interface',
                                                     'persist': False,
                                                     'priority': 'high',
                                                     'always_show': True,
                                                     'always_show_allow_clear': False,
                                                     'id': 'reboot_required',
                                                     'local': True,
                                                     })

                    page = webinterface.get_template(request, webinterface.wi_dir + '/pages/misc/reboot_needed.html')
                    return page.render(alerts=webinterface.get_alerts(),
                                       msg=msg,
                                       )
                else:
                    webinterface.add_alert("%s: %s" % (results['msg'], results['apimsghtml']))
                    device['device_id'] = results['device_id']

            device_variables = yield webinterface._Variables.get_variable_groups_fields(
                group_relation_type='device_type',
                group_relation_id=device_type_id,
            )

            if device['variable_data'] is not None:
                device_variables = yield webinterface._Variables.merge_variable_groups_fields_data_data(
                    device_variables,
                    json_output.get('vars', {})
                )


            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/devices/add_details.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/add", "Add Device - Details")
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               device_variables=device_variables,
                               device_type=device_type,
                               locations=webinterface._Locations.locations_sorted,
                               states=webinterface._States.get("#")
                               )

        @webapp.route('/<string:device_id>/details')
        @require_auth()
        @inlineCallbacks
        def page_devices_details(webinterface, request, session, device_id):
            session.has_access('device', device_id, 'view')

            try:
                device = webinterface._Devices[device_id]
                device_id = device.device_id
            except Exception as e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                return webinterface.redirect(request, '/devices/index')
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/devices/details.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            add_devices_breadcrumb(webinterface, request, device_id, session)
            device_variables = yield device.device_variables()
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               device_variables=device_variables,
                               states=webinterface._States.get("#")
                               )

        @webapp.route('/<string:device_id>/delete', methods=['GET'])
        @require_auth()
        def page_device_delete_get(webinterface, request, session, device_id):
            session.has_access('device', device_id, 'delete')

            try:
                device = webinterface._Devices[device_id]
                device_id = device.device_id
            except Exception as e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                return webinterface.redirect(request, '/devices/index')
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/devices/delete.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/%s/details" % device_id, device.label)
            webinterface.add_breadcrumb(request, "/devices/%s/delete" % device_id, "Delete")
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               states=webinterface._States.get("#")
                               )

        @webapp.route('/<string:device_id>/delete', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_device_delete_post(webinterface, request, session, device_id):
            session.has_access('device', device_id, 'delete')

            try:
                device = webinterface._Devices[device_id]
                device_id = device.device_id
            except Exception as e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                return webinterface.redirect(request, '/devices/index')
            try:
                confirm = request.args.get('confirm')[0]
            except Exception:
                confirm = None
            if confirm != "delete":
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/devices/delete.html')
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the device.', 'warning')
                return page.render(alerts=webinterface.get_alerts(),
                                   device=device,
                                   states=webinterface._States.get("#")
                                   )

            device_results = yield webinterface._Devices.delete_device(device.device_id,
                                                                       session=session['yomboapi_session'])
            if device_results['status'] == 'failed':
                webinterface.add_alert(device_results['apimsghtml'], 'warning')
                return webinterface.redirect(request, '/devices/index')

            webinterface.add_alert('Device deleted.', 'warning')
            return webinterface.redirect(request, '/devices/index')

        @webapp.route('/<string:device_id>/disable', methods=['GET'])
        @require_auth()
        def page_device_disable_get(webinterface, request, session, device_id):
            session.has_access('device', device_id, 'disable')

            try:
                device = webinterface._Devices[device_id]
                device_id = device.device_id
            except Exception as e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                return webinterface.redirect(request, '/devices/index')
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/devices/disable.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/%s/details" % device_id, device.label)
            webinterface.add_breadcrumb(request, "/devices/%s/disable" % device_id, "Disable")
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               )

        @webapp.route('/<string:device_id>/disable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_device_disable_post(webinterface, request, session, device_id):
            session.has_access('device', device_id, 'disable')

            try:
                device = webinterface._Devices[device_id]
                device_id = device.device_id
            except Exception as e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                return webinterface.redirect(request, '/devices/index')
            confirm = request.args.get('confirm')[0]
            if confirm != "disable":
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/devices/disable.html')
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the device.', 'warning')
                return page.render(alerts=webinterface.get_alerts(),
                                   device=device,
                                   )

            device_results = yield webinterface._Devices.disable_device(device.device_id,
                                                                        session=session['yomboapi_session'])
            if device_results['status'] == 'failed':
                webinterface.add_alert(device_results['apimsghtml'], 'warning')
                return webinterface.redirect(request, '/devices/index')

            webinterface.add_alert('Device disabled.', 'warning')
            return webinterface.redirect(request, '/devices/index')


        @webapp.route('/<string:device_id>/enable', methods=['GET'])
        @require_auth()
        def page_device_enable_get(webinterface, request, session, device_id):
            session.has_access('device', device_id, 'enable')

            try:
                device = webinterface._Devices[device_id]
                device_id = device.device_id
            except Exception as e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                return webinterface.redirect(request, '/devices/index')
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/devices/enable.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/%s/details" % device_id, device.label)
            webinterface.add_breadcrumb(request, "/devices/%s/enable" % device_id, "Enable")
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               )

        @webapp.route('/<string:device_id>/enable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_device_enable_post(webinterface, request, session, device_id):
            session.has_access('device', device_id, 'enable')

            try:
                device = webinterface._Devices[device_id]
                device_id = device.device_id
            except Exception as e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                return webinterface.redirect(request, '/devices/index')
            confirm = request.args.get('confirm')[0]
            if confirm != "enable":
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/devices/enable.html')
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the device.', 'warning')
                return page.render(alerts=webinterface.get_alerts(),
                                   device=device,
                                   )

            device_results = yield webinterface._Devices.enable_device(device.device_id,
                                                                       session=session['yomboapi_session'])
            if device_results['status'] == 'failed':
                webinterface.add_alert(device_results['apimsghtml'], 'warning')
                return webinterface.redirect(request, '/devices/index')

            webinterface.add_alert('Device enabled.', 'warning')
            return webinterface.redirect(request, '/devices/%s/details' % device_id)

        @webapp.route('/<string:device_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devices_edit_get(webinterface, request, session, device_id):
            session.has_access('device', device_id, 'edit')

            try:
                device_api_results = yield webinterface._YomboAPI.request('GET', '/v1/device/%s' % device_id,
                                                                          session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devices/index')
            device = device_api_results['data']
            device['device_id'] = device['id']
            del device['id']
            new_map = {}
            for key, value in device['energy_map'].items():
                new_map[float(key)] = float(value)
            device['energy_map'] = new_map

            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/%s/details" % device_id,
                                        webinterface._Locations.area_label(device['area_id'], device['label']))
            webinterface.add_breadcrumb(request, "/devices/%s/edit" % device_id, "Edit")
            variable_data = yield webinterface._Variables.get_variable_data('device', device['device_id'])
            page = yield page_devices_edit_form(
                webinterface,
                request,
                session,
                device,
                variable_data,
            )
            return page

        @webapp.route('/<string:device_id>/edit', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devices_edit_post(webinterface, request, session, device_id):
            session.has_access('device', device_id, 'edit')

            device = webinterface._Devices.devices[device_id]
            device_id = device.device_id

            status = request.args.get('status')[0]
            if status == 'disabled':
                status = 0
            elif status == 'enabled':
                status = 1
            elif status == 'deleted':
                status = 2
            else:
                webinterface.add_alert('Device status was set to an illegal value.', 'warning')
                return webinterface.redirect(request, '/devices/%s/edit' % device_id)

            pin_required = request.args.get('pin_required')[0]
            if pin_required == 'disabled':
                pin_required = 0
            elif pin_required == 'enabled':
                pin_required = 1
                if request.args.get('pin_code')[0] == "":
                    webinterface.add_alert('Device requires a pin code, but none was set.', 'warning')
                    return webinterface.redirect(request, '/devices/%s/edit' % device_id)
            else:
                webinterface.add_alert('Device pin required was set to an illegal value.', 'warning')
                return webinterface.redirect(request, '/devices/%s/edit' % device_id)

            start_percent = request.args.get('start_percent')
            energy_usage = request.args.get('energy_usage')
            energy_map = {}
            for idx, percent in enumerate(start_percent):
                try:
                    energy_map[float(float(percent)/100)] = energy_usage[idx]
                except:
                    pass

            energy_map = OrderedDict(sorted(list(energy_map.items()), key=lambda x_y1: float(x_y1[0])))
            json_output = json.loads(request.args.get('json_output')[0])

            # print("energy_map: %s " % energy_map)
            variable_data = yield webinterface._Variables.extract_variables_from_web_data(json_output['vars'])
            data = {
                # 'garage_id': request.args.get('garage_id', ""),
                'location_id': request.args.get('location_id')[0],
                'area_id': request.args.get('area_id')[0],
                'machine_label': request.args.get('machine_label')[0],
                'device_type_id': request.args.get('device_type_id')[0],
                'label': request.args.get('label')[0],
                'description': request.args.get('description')[0],
                'status': status,
                'statistic_label': request.args.get('statistic_label')[0],
                'statistic_type': request.args.get('statistic_type')[0],
                'statistic_bucket_size': request.args.get('statistic_bucket_size')[0],
                'statistic_lifetime': request.args.get('statistic_lifetime')[0],
                'pin_required': pin_required,
                'pin_code': request.args.get('pin_code')[0],
                'pin_timeout': request.args.get('pin_timeout')[0],
                'energy_type': request.args.get('energy_type')[0],
                'energy_map': energy_map,
                'variable_data':  variable_data,
                'voice_cmd': None,
                # 'voice_cmd_order': None,
                # 'voice_cmd_src': None,
            }

            try:
                results = yield webinterface._Devices.edit_device(device_id, data, session=session['yomboapi_session'])
            except YomboWarning as e:
                results = {
                    'status': 'failed',
                    'apimsghtml': e,
                }

            if results['status'] == 'failed':

                data['device_type_id'] = device.device_type_id
                data['device_id'] = device_id
                webinterface.add_alert(results['apimsghtml'], 'warning')

                webinterface.home_breadcrumb(request)
                webinterface.add_breadcrumb(request, "/devices/index", "Devices")
                webinterface.add_breadcrumb(request, "/devices/%s/details" % device_id,
                                            webinterface._Locations.area_label(device['area_id'], device['label']))
                webinterface.add_breadcrumb(request, "/devices/%s/edit" % device_id, "Edit")
                page = yield page_devices_edit_form(
                    webinterface,
                    request,
                    session,
                    data,
                    json_output['vars']
                )
                return page

            webinterface.add_alert('Device saved.', 'warning')
            return webinterface.redirect(request, '/devices/%s/details' % device_id)

        @inlineCallbacks
        def page_devices_edit_form(webinterface, request, session, device, variable_data=None):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/devices/edit.html')
            # device_variables = device.device_variables
            # print("device: %s" % device)
            device_variables = yield webinterface._Variables.get_variable_groups_fields(
                group_relation_type='device_type',
                group_relation_id=device['device_type_id']
            )

            if variable_data is not None:
                device_variables = yield webinterface._Variables.merge_variable_groups_fields_data_data(
                                         device_variables,
                                         variable_data,
                                         )

            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               device_variables=device_variables,
                               states=webinterface._States.get("#"),
                               )

        @webapp.route('/device_commands')
        @require_auth()
        def page_devices_device_commands(webinterface, request, session):
            session.has_access('device_command', '*', 'view')

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/devices/device_commands.html')
            # print "delayed queue active: %s" % webinterface._Devices.delay_queue_active
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/delayed_commands", "Device Commands")
            return page.render(alerts=webinterface.get_alerts(),
                               device_commands=webinterface._Devices.device_commands,
                               )

        @webapp.route('/device_commands/<string:device_command_id>/details')
        @require_auth()
        def page_devices_device_commands_details(webinterface, request, session, device_command_id):
            session.has_access('device_command', device_command_id, 'view')

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/devices/device_command_details.html')
            # print "delayed queue active: %s" % webinterface._Devices.delay_queue_active
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/device_commands", "Device Commands")
            webinterface.add_breadcrumb(request, "/devices/device_commands", "Request")
            try:
                device_command = webinterface._Devices.device_commands[device_command_id]
            except Exception as e:
                webinterface.add_alert("Cannot find requested id. <br>Error details: %s" % e)
                return webinterface.redirect(request, '/devices/device_commands')
            return page.render(alerts=webinterface.get_alerts(),
                               device_command=device_command,
                               )
