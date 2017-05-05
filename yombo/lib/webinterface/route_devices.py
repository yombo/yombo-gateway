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

from __future__ import division
from collections import OrderedDict
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

from twisted.internet.defer import inlineCallbacks, returnValue

from yombo.core.exceptions import YomboHookStopProcessing
from yombo.lib.webinterface.auth import require_auth, run_first
from yombo.utils import random_string, global_invoke_all
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.route_devices")

def route_devices(webapp):
    with webapp.subroute("/devices") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_devices(webinterface, request, session):
            return webinterface.redirect(request, '/devices/index')

        @webapp.route('/index')
        @require_auth()
        @run_first()
        def page_devices_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/index.html')
            return page.render(
                alerts=webinterface.get_alerts(),
                devices=webinterface._Libraries['devices'].devices,
                devicetypes=webinterface._DeviceTypes.device_types,
                request=request,
                )

        @webapp.route('/add')
        @require_auth()
        @run_first()
        def page_devices_add_select_device_type_get(webinterface, request, session):
            # session['add_device'] = {
            #     'start': time(),
            #     'id': random_string(length=10),
            #     'stage': 0,
            # }
            # webinterface.temp_data[session['add_device']['id']] = {}

            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/add_select_device_type.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/add", "Add Device - Select Device Type")
            device_types = webinterface._DeviceTypes.device_types
            # device_types_sorted = sorted(device_types, key=lambda x: device_types[x].label)
            device_types_sorted = sorted(device_types, key=lambda x: device_types[x].label)

            return page.render(
                alerts=webinterface.get_alerts(),
                device_types = device_types,
            )


        @webapp.route('/add/<string:device_type_id>', methods=['POST', 'GET'])
        @require_auth()
        @inlineCallbacks
        @run_first()
        def page_devices_add_post(webinterface, request, session, device_type_id):
            try:
                device_type = webinterface._DeviceTypes[device_type_id]
            except Exception, e:
                webinterface.add_alert('Device Type ID was not found: %s' % device_type_id, 'warning')
                returnValue(webinterface.redirect(request, '/devices/add'))

            ok_to_save = True

            if 'json_output' in request.args:
                json_output = request.args.get('json_output', [{}])[0]
                json_output = json.loads(json_output)
            else:
                json_output = {}
                ok_to_save = False

            try:
                status = json_output.get('status', 'enabled')
                if status == 'disabled':
                    status = 0
                elif status == 'enabled':
                    status = 1
                elif status == 'deleted':
                    status = 2
                else:
                    webinterface.add_alert('Device status was set to an illegal value.', 'warning')
                    returnValue(webinterface.redirect(request, '/devices'))


                pin_required = json_output.get('pin_required', 'disabled')
                if pin_required == 'disabled':
                    pin_required = 0
                elif pin_required == 'enabled':
                    pin_required = 1
                    if request.args.get('pin_code')[0] == "":
                        webinterface.add_alert('Device requires a pin code, but none was set.', 'warning')
                        returnValue(webinterface.redirect(request, '/devices'))
                else:
                    webinterface.add_alert('Device pin required was set to an illegal value.', 'warning')
                    returnValue(webinterface.redirect(request, '/devices'))

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

                energy_map = OrderedDict(sorted(energy_map.items(), key=lambda (x, y): float(x)))


            except Exception as e:
                logger.warn("Error while processing device add_details: {e}", e=e)

            device = {
                'device_id': json_output.get('device_id', ""),
                'label': json_output.get('label', ""),
                'description': json_output.get('description', ""),
                'status': status,
                'statistic_label': json_output.get('statistic_label', ""),
                'statistic_lifetime': json_output.get('statistic_lifetime', ""),
                'device_type_id': json_output.get('device_type_id', ""),
                'pin_required': pin_required,
                'pin_code': json_output.get('pin_code', ""),
                'pin_timeout': json_output.get('pin_timeout', ""),
                'energy_type': json_output.get('energy_type', ""),
                'energy_map': energy_map,
                'variable_data': json_output.get('vars', []),
            }


            if ok_to_save:
                try:
                    global_invoke_all('_device_before_add_',  **{'called_by': webinterface, 'device': device})
                except YomboHookStopProcessing as e:
                    webinterface.add_alert("Adding device was halted by '%s', reason: %s" % (e.name, e.message))
                    returnValue(webinterface.redirect(request, '/devices'))

                results = yield webinterface._Devices.add_device(device)

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
                                                     })

                    page = webinterface.get_template(request, webinterface._dir + 'pages/reboot_needed.html')
                    returnValue(page.render(alerts=webinterface.get_alerts(),
                                            msg=msg,
                                            ))
                else:
                    webinterface.add_alert("%s: %s" % (results['msg'], results['apimsghtml']))
                    device['device_id'] = results['device_id']

            var_groups = yield webinterface._Libraries['localdb'].get_variable_groups('device_type', device['device_type_id'])
            var_groups_final = []
            for group in var_groups:
                group = group.__dict__
                fields = yield webinterface._Libraries['localdb'].get_variable_fields_by_group(group['id'])
                fields_final = []
                for field in fields:
                    field = field.__dict__
                    fields_final.append(field)
                group['fields'] = fields_final
                var_groups_final.append(group)

            # print "final groups: %s" % var_groups_final
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/add_details.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/add", "Add Device - Details")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    device=device,
                                    dev_variables=var_groups_final,
                                    commands=webinterface._Commands,
                                    ))

        @webapp.route('/delayed_commands')
        @require_auth()
        @run_first()
        def page_devices_delayed_commands(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/delayed_commands.html')
            # print "delayed queue active: %s" % webinterface._Devices.delay_queue_active
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/delayed_commands", "Delayed Commands")
            return page.render(alerts=webinterface.get_alerts(),
                               delayed_commands=webinterface._Devices.delay_queue_active,
                               )

        @webapp.route('/<string:device_id>/details')
        @require_auth()
        @run_first()
        def page_devices_details(webinterface, request, session, device_id):
            try:
                device = webinterface._Devices[device_id]
            except Exception, e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                return webinterface.redirect(request, '/devices/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/details.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/%s/details" % device_id, device.label)
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               devicetypes=webinterface._DeviceTypes,
                               commands=webinterface._Commands,
                               )
    
        @webapp.route('/<string:device_id>/delete', methods=['GET'])
        @require_auth()
        @run_first()
        def page_device_delete_get(webinterface, request, session, device_id):
            try:
                device = webinterface._Devices[device_id]
            except Exception, e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                return webinterface.redirect(request, '/devices/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/delete.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/%s/details" % device_id, device.label)
            webinterface.add_breadcrumb(request, "/devices/%s/delete" % device_id, "Delete")
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               devicetypes=webinterface._DeviceTypes,
                               )

        @webapp.route('/<string:device_id>/delete', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_device_delete_post(webinterface, request, session, device_id):
            # print "in device delete post"
            try:
                device = webinterface._Devices[device_id]
            except Exception, e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                returnValue(webinterface.redirect(request, '/devices/index'))
            confirm = request.args.get('confirm')[0]
            if confirm != "delete":
                page = webinterface.get_template(request, webinterface._dir + 'pages/devices/delete.html')
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the device.', 'warning')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                                   device=device,
                                   devicetypes=webinterface._DeviceTypes,
                                   ))

            device_results = yield webinterface._Devices.delete_device(device.device_id)
            if device_results['status'] == 'failed':
                webinterface.add_alert(device_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devices/index'))

            webinterface.add_alert('Device deleted.', 'warning')
            returnValue(webinterface.redirect(request, '/devices/index'))

        @webapp.route('/<string:device_id>/disable', methods=['GET'])
        @require_auth()
        @run_first()
        def page_device_disable_get(webinterface, request, session, device_id):
            try:
                device = webinterface._Devices[device_id]
            except Exception, e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                return webinterface.redirect(request, '/devices/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/disable.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/%s/details" % device_id, device.label)
            webinterface.add_breadcrumb(request, "/devices/%s/disable" % device_id, "Disable")
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               devicetypes=webinterface._DeviceTypes,
                               )

        @webapp.route('/<string:device_id>/disable', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_device_disable_post(webinterface, request, session, device_id):
            try:
                device = webinterface._Devices[device_id]
            except Exception, e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                returnValue(webinterface.redirect(request, '/devices/index'))
            confirm = request.args.get('confirm')[0]
            if confirm != "disable":
                page = webinterface.get_template(request, webinterface._dir + 'pages/devices/disable.html')
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the device.', 'warning')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                                   device=device,
                                   devicetypes=webinterface._DeviceTypes,
                                   ))

            device_results = yield webinterface._Devices.disable_device(device.device_id)
            if device_results['status'] == 'failed':
                webinterface.add_alert(device_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devices/index'))

            webinterface.add_alert('Device disabled.', 'warning')
            returnValue(webinterface.redirect(request, '/devices/index'))


        @webapp.route('/<string:device_id>/enable', methods=['GET'])
        @require_auth()
        @run_first()
        def page_device_enable_get(webinterface, request, session, device_id):
            try:
                device = webinterface._Devices[device_id]
            except Exception, e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                return webinterface.redirect(request, '/devices/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/enable.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/%s/details" % device_id, device.label)
            webinterface.add_breadcrumb(request, "/devices/%s/enable" % device_id, "Enable")
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               devicetypes=webinterface._DeviceTypes,
                               )

        @webapp.route('/<string:device_id>/enable', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_device_enable_post(webinterface, request, session, device_id):
            try:
                device = webinterface._Devices[device_id]
            except Exception, e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                returnValue(webinterface.redirect(request, '/devices/index'))
            confirm = request.args.get('confirm')[0]
            if confirm != "enable":
                page = webinterface.get_template(request, webinterface._dir + 'pages/devices/enable.html')
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the device.', 'warning')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                                   device=device,
                                   devicetypes=webinterface._DeviceTypes,
                                   ))

            device_results = yield webinterface._Devices.enable_device(device.device_id)
            if device_results['status'] == 'failed':
                webinterface.add_alert(device_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devices/index'))

            webinterface.add_alert('Device enabled.', 'warning')
            returnValue(webinterface.redirect(request, '/devices/%s/details' % device_id))

        @webapp.route('/<string:device_id>/edit', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devices_edit_get(webinterface, request, session, device_id):
            try:
                device = webinterface._Devices.get(device_id)
            except Exception, e:
                webinterface.add_alert('Device ID was not found.', 'warning')
                returnValue(webinterface.redirect(request, '/devices/index'))

            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/%s/details" % device_id, device.label)
            webinterface.add_breadcrumb(request, "/devices/%s/edit" % device_id, "Edit")
            page = yield page_devices_edit_form(webinterface, request, session, device, None)
            returnValue(page)

        @webapp.route('/<string:device_id>/edit', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devices_edit_post(webinterface, request, session, device_id):
            try:
                device = webinterface._Devices.get(device_id)
            except Exception, e:
                webinterface.add_alert('Device ID was not found.', 'warning')
                returnValue(webinterface.redirect(request, '/devices/index'))
            status = request.args.get('status')[0]
            if status == 'disabled':
                status = 0
            elif status == 'enabled':
                status = 1
            elif status == 'deleted':
                status = 2
            else:
                webinterface.add_alert('Device status was set to an illegal value.', 'warning')
                returnValue(webinterface.redirect(request, '/devices/%s/edit' % device_id))

            pin_required = request.args.get('pin_required')[0]
            if pin_required == 'disabled':
                pin_required = 0
            elif pin_required == 'enabled':
                pin_required = 1
                if request.args.get('pin_code')[0] == "":
                    webinterface.add_alert('Device requires a pin code, but none was set.', 'warning')
                    returnValue(webinterface.redirect(request, '/devices/%s/edit' % device_id))
            else:
                webinterface.add_alert('Device pin required was set to an illegal value.', 'warning')
                returnValue(webinterface.redirect(request, '/devices/%s/edit' % device_id))

            start_percent = request.args.get('start_percent')
            energy_usage = request.args.get('energy_usage')
            energy_map = {}
            for idx, percent in enumerate(start_percent):
                try:
                    energy_map[float(float(percent)/100)] = energy_usage[idx]
                except:
                    pass

            energy_map = OrderedDict(sorted(energy_map.items(), key=lambda (x, y): float(x)))
            json_output = json.loads(request.args.get('json_output')[0])

            # print "energy usage: %s " % map
            data = {
                'label': request.args.get('label')[0],
                'description': request.args.get('description')[0],
                'status': status,
                'statistic_label': request.args.get('statistic_label')[0],
                'statistic_lifetime': request.args.get('statistic_lifetime')[0],
                'pin_required': pin_required,
                'pin_code': request.args.get('pin_code')[0],
                'pin_timeout': request.args.get('pin_timeout')[0],
                'energy_type': request.args.get('energy_type')[0],
                'energy_map': energy_map,
                'variable_data':  json_output['vars'],
            }

            results = yield webinterface._Devices.edit_device(device_id, data)

            if results['status'] == 'failed':

                data['device_type_id'] = device.device_type_id
                data['device_id'] = device.device_id
                webinterface.add_alert(results['apimsghtml'], 'warning')

                webinterface.home_breadcrumb(request)
                webinterface.add_breadcrumb(request, "/devices/index", "Devices")
                webinterface.add_breadcrumb(request, "/devices/%s/details" % device_id, device.label)
                webinterface.add_breadcrumb(request, "/devices/%s/edit" % device_id, "Edit")
                page = yield page_devices_edit_form(webinterface, request, session, data, json_output['vars'])
                returnValue(page)

            returnValue(webinterface.redirect(request, '/devices/%s/details' % device_id))



        @inlineCallbacks
        def page_devices_edit_form(webinterface, request, session, device, var_data):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/edit.html')
            var_groups_final_new = yield webinterface._Variables.get_variable_groups_fields_data(
                group_relation_type='device_type',
                group_relation_id=device['device_type_id'],
                data_relation_type='device',
                data_relation_id=device['device_id'],
            )
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    device=device,
                                    dev_variables=var_groups_final_new,
                                    commands=webinterface._Commands,
                                    ))
