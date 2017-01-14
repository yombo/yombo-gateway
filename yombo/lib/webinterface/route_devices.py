from __future__ import division
from collections import OrderedDict
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

from twisted.internet.defer import inlineCallbacks, returnValue

from yombo.lib.webinterface.auth import require_auth_pin, require_auth
from yombo.utils import random_string

def route_devices(webapp):
    with webapp.subroute("/devices") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_devices(webinterface, request, session):
            return webinterface.redirect(request, '/devices/index')

        @webapp.route('/index')
        @require_auth()
        def page_devices_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/index.html')
            return page.render(func=webinterface.functions,
                               _=_,  # translations
                               data=webinterface.data,
                               alerts=webinterface.get_alerts(),
                               devices=webinterface._Libraries['devices']._devicesByUUID,
                               )

        @webapp.route('/delayed_commands')
        @require_auth()
        def page_devices_delayed_commands(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/delayed_commands.html')
            print "delayed queue active: %s" % webinterface._Devices.delay_queue_active
            return page.render(alerts=webinterface.get_alerts(),
                               delayed_commands=webinterface._Devices.delay_queue_active,
                               )

        @webapp.route('/details/<string:device_id>')
        @require_auth()
        def page_devices_details(webinterface, request, session, device_id):
            try:
                device = webinterface._Devices[device_id]
            except Exception, e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                return webinterface.redirect(request, '/devices/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/details.html')
            print device.available_commands()
            print device.device_variables
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               devicetypes=webinterface._DeviceTypes,
                               commands=webinterface._Commands,
                               )
    
        @webapp.route('/edit/<string:device_id>', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devices_edit_get(webinterface, request, session, device_id):
            try:
                device = webinterface._Devices.get(device_id)
            except Exception, e:
                print "device find errr: %s" % e
                webinterface.add_alert('Device ID was not found.', 'warning')
                returnValue(webinterface.redirect(request, '/devices/index'))

            page = yield page_devices_edit_form(webinterface, request, session, device, None)
            returnValue(page)

        @inlineCallbacks
        def page_devices_edit_form(webinterface, request, session, device, var_data):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/edit.html')
            var_groups = yield webinterface._Libraries['localdb'].get_variable_groups('device_type', device.device_type_id)
            var_groups_final = []
            for group in var_groups:
                group = group.__dict__
                fields = yield webinterface._Libraries['localdb'].get_variable_fields_by_group(group['id'])
                fields_final = []
                for field in fields:
                    field = field.__dict__
                    if var_data is None:
                        var_data_field = yield webinterface._Libraries['localdb'].get_variable_data_by_relation(field['id'],
                                                                                                  device.device_id)
                    else:
                        if field['id'] in var_data:
                            var_data_field = var_data[field['id']]
                        else:
                            var_data_field = []

                    print "device var_data_field: %s" % var_data_field

                    var_data_final = []
                    for data in var_data_field:
                        var_data_final.append(data.__dict__)
                    field['data'] = var_data_final

                    fields_final.append(field)
                group['fields'] = fields_final
                var_groups_final.append(group)

            # print "final groups: %s" % var_groups_final
            returnValue(page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               dev_variables=var_groups_final,
                               commands=webinterface._Commands,
                               ))

        @webapp.route('/edit/<string:device_id>', methods=['POST'])
        @require_auth()
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
                returnValue(webinterface.redirect(request, '/devices/edit/%s' % device_id))

            pin_required = request.args.get('pin_required')[0]
            if pin_required == 'disabled':
                pin_required = 0
            elif pin_required == 'enabled':
                pin_required = 1
                if request.args.get('pin_code')[0] == "":
                    webinterface.add_alert('Device requires a pin code, but none was set.', 'warning')
                    returnValue(webinterface.redirect(request, '/devices/edit/%s' % device_id))
            else:
                webinterface.add_alert('Device pin required was set to an illegal value.', 'warning')
                returnValue(webinterface.redirect(request, '/devices/edit/%s' % device_id))

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
                'status': request.args.get('status')[0],
                'statistic_label': request.args.get('statistic_label')[0],
                'pin_required': pin_required,
                'pin_code': request.args.get('pin_code')[0],
                'pin_timeout': request.args.get('pin_timeout')[0],
                'energy_type': request.args.get('energy_type')[0],
                'energy_map': energy_map,
                'variable_data':  json_output['vars'],
            }

            results = yield device.edit_device(data)

            if results['status'] == 'failed':
                var_groups = yield webinterface._Libraries['localdb'].get_variable_groups('device_type',
                                                                                          device.device_type_id)
                var_groups_final = []
                for group in var_groups:
                    group = group.__dict__
                    fields = yield webinterface._Libraries['localdb'].get_variable_fields_by_group(group['id'])
                    fields_final = []
                    for field in fields:
                        field = field.__dict__
                        var_data = yield webinterface._Libraries['localdb'].get_variable_data_by_relation(field['id'],
                                                                                                          device.device_id)
                        var_data_final = []
                        for data in var_data:
                            var_data_final.append(data.__dict__)
                        field['data'] = var_data_final

                        fields_final.append(field)
                    group['fields'] = fields_final
                    var_groups_final.append(group)

                webinterface.add_alert(results['content']['html_message'], 'warning')
                page = webinterface.get_template(request, webinterface._dir + 'pages/devices/edit.html')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                               device=data,
                               dev_variables=var_groups_final,
                               commands=webinterface._Commands,
                               ))

            webinterface.add_alert('Device updated.')
            returnValue(webinterface.redirect(request, '/devices/index'))

        @webapp.route('/add')
        @require_auth()
        def page_devices_add_select_device_type_get(webinterface, request, session):
            # session['add_device'] = {
            #     'start': time(),
            #     'id': random_string(length=10),
            #     'stage': 0,
            # }
            # webinterface.temp_data[session['add_device']['id']] = {}

            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/add_select_device_type.html')

            return page.render(alerts=webinterface.get_alerts(),
                                    device_types = webinterface._DeviceTypes.device_types_by_id,
                                    )

        @webapp.route('/add_details', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devices_add_post(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/add_details.html')
            device_type_id = request.args.get('device_type_id')[0]
            try:
                device_type = webinterface._DeviceTypes[device_type_id]
            except Exception, e:
                webinterface.add_alert('Device Type ID was not found: %s' % device_type_id, 'warning')
                returnValue(webinterface.redirect(request, '/devices/add'))

            json_output = None
            try:
                json_output = json.loads(request.args.get('json_output')[0])
                start_percent = request.args.get('start_percent')
                status = request.args.get('status')[0]
                if status == 'disabled':
                    status = 0
                elif status == 'enabled':
                    status = 1
                elif status == 'deleted':
                    status = 2
                else:
                    webinterface.add_alert('Device status was set to an illegal value.', 'warning')
                    returnValue(webinterface.redirect(request, '/devices/edit/%s' % device_id))

                pin_required = request.args.get('pin_required')[0]
                if pin_required == 'disabled':
                    pin_required = 0
                elif pin_required == 'enabled':
                    pin_required = 1
                    if request.args.get('pin_code')[0] == "":
                        webinterface.add_alert('Device requires a pin code, but none was set.', 'warning')
                        returnValue(webinterface.redirect(request, '/devices/edit/%s' % device_id))
                else:
                    webinterface.add_alert('Device pin required was set to an illegal value.', 'warning')
                    returnValue(webinterface.redirect(request, '/devices/edit/%s' % device_id))

                energy_usage = request.args.get('energy_usage')
                energy_map = {}
                for idx, percent in enumerate(start_percent):
                    try:
                        energy_map[float(float(percent) / 100)] = energy_usage[idx]
                    except:
                        pass
                print "aaa"

                energy_map = OrderedDict(sorted(energy_map.items(), key=lambda (x, y): float(x)))
                print "aaa1"
                device = {
                    'device_id': json_output['device_id'],
                    'label': json_output['label'],
                    'description': json_output['description'],
                    'status': status,
                    'statistic_label': json_output['statistic_label'],
                    'device_type_id': json_output['device_type_id'],
                    'pin_required': pin_required,
                    'pin_code': json_output['pin_code'],
                    'pin_timeout': json_output['pin_timeout'],
                    'energy_type': json_output['energy_type'],
                    'energy_map': energy_map,
                    'variable_data': json_output['vars'],
                }
            except:
                device = {
                    'device_id': '',
                    'label': '',
                    'description': '',
                    'status': 1,
                    'statistic_label': '',
                    'device_type_id': device_type_id,
                    'pin_required': 0,
                    'pin_code': '',
                    'pin_timeout': 0,
                    'energy_type': 'calc',
                    'energy_map': {0:0, 1:0},
                }

            if json_output is not None:
                print "aaa2"
                results = yield webinterface._Devices.add_device(device)
                print "aaa4"

                if results['status'] == 'success':
                    webinterface.add_alert('Device added. A <a href="/tools/restart?location=/device/details/%s">restart is required</a>' % results['device_id'])
                    returnValue(webinterface.redirect(request, '/devices/index'))
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
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    device=device,
                                    dev_variables=var_groups_final,
                                    commands=webinterface._Commands,
                                    ))


        @webapp.route('/addsss', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devices_add_postasdfasdfasdf(webinterface, request, session, device_id):
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
                returnValue(webinterface.redirect(request, '/devices/edit/%s' % device_id))

            pin_required = request.args.get('pin_required')[0]
            if pin_required == 'disabled':
                pin_required = 0
            elif pin_required == 'enabled':
                pin_required = 1
                if request.args.get('pin_code')[0] == "":
                    webinterface.add_alert('Device requires a pin code, but none was set.', 'warning')
                    returnValue(webinterface.redirect(request, '/devices/edit/%s' % device_id))
            else:
                webinterface.add_alert('Device pin required was set to an illegal value.', 'warning')
                returnValue(webinterface.redirect(request, '/devices/edit/%s' % device_id))

            start_percent = request.args.get('start_percent')
            energy_usage = request.args.get('energy_usage')
            energy_map = {}
            for idx, percent in enumerate(start_percent):
                try:
                    energy_map[float(float(percent) / 100)] = energy_usage[idx]
                except:
                    pass

            energy_map = OrderedDict(sorted(energy_map.items(), key=lambda (x, y): float(x)))
            json_output = json.loads(request.args.get('json_output')[0])

            # print "energy usage: %s " % map
            data = {
                'label': request.args.get('label')[0],
                'description': request.args.get('description')[0],
                'status': request.args.get('status')[0],
                'statistic_label': request.args.get('statistic_label')[0],
                'pin_required': pin_required,
                'pin_code': request.args.get('pin_code')[0],
                'pin_timeout': request.args.get('pin_timeout')[0],
                'energy_type': request.args.get('energy_type')[0],
                'energy_map': energy_map,
                'variable_data': json_output['vars'],
            }

            results = yield device.edit_device(data)
            if results['code'] != 200:
                webinterface.add_alert(results['content']['html_message'], 'warning')
                page = webinterface.get_template(request, webinterface._dir + 'pages/devices/edit.html')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                                        device=data,
                                        commands=webinterface._Commands,
                                        ))

            webinterface.add_alert('Device updated.')
            returnValue(webinterface.redirect(request, '/devices/index'))