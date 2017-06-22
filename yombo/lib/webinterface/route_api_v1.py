# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
import six
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, returnValue

from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth

from yombo.utils import epoch_to_string, bytes_to_unicode

def return_good(request, message=None, payload=None, status=None):
    request.setHeader('Content-Type', 'application/json')
    if status is None:
        status = 200
    request.setResponseCode(status)
    if payload is None:
        payload = {}
    if message is None:
        message = "OK"
    return json.dumps({
        'status': status,
        'message': message,
        'payload': payload,
    })

def return_not_found(request, message=None, status=None):
    request.setHeader('Content-Type', 'application/json')
    if status is None:
        status = 404
    request.setResponseCode(status)
    if message is None:
        message = "Not found"
    return json.dumps({
        'status': status,
        'message': message,
    })

def return_error(request, message=None, status=None):
    request.setHeader('Content-Type', 'application/json')
    if status is 500:
        status = 401
    request.setResponseCode(status)
    if message is None:
        message = "System error"
    return json.dumps({
        'status': status,
        'message': message,
    })

def return_unauthorized(request, message=None, status=None):
    request.setHeader('Content-Type', 'application/json')
    if status is None:
        status = 401
    request.setResponseCode(status)
    if message is None:
        message = "Not authorized"
    return json.dumps({
        'status': status,
        'message': message,
        'redirect': "/?",
    })


def route_api_v1(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route('/ping')
        def api_v1_ping(webinterface, request):
            if webinterface.starting == True:
                return;
            request.setHeader("Access-Control-Allow-Origin", '*');
            return "y-pong-01"

        @webapp.route('/uptime')
        @require_auth(api=True)
        def api_v1_uptime(webinterface, request, session):
            if webinterface.starting == True:
                return;
            return str(webinterface._Atoms['running_since'])

        @webapp.route('/automation/list/items', methods=['GET'])
        @require_auth()
        def ajax_automation_list_items_get(webinterface, request, session):
            try:
                platform = request.args.get('platform')[0]
            except:
                return return_error(request, 'platform must be specified.')
            # try:
            #     type = request.args.get('type')[0]
            # except:
            #     return return_error('type must be specified.')
            webinterface._Automation.get_available_items(platform=platform)

            a = return_good(request, 'The list')
            request.setHeader('Content-Type', 'application/json')
            return json.dumps(a)

        @webapp.route('/devices/<string:device_id>/command/<string:command_id>', methods=['GET', 'POST'])
        @require_auth(api=True)
        def ajax_devices_command_get_post(webinterface, request, session, device_id, command_id):
            json_output = bytes_to_unicode(request.args.get('json_output', ["{}"])[0])
            print("json_output  %s" % json_output)
            print("json_output type: %s" % type(json_output))
            json_output = json.loads(json_output)
            inputs = json_output.get('inputs', {})

            if device_id in webinterface._Devices:
                device = webinterface._Devices[device_id]
            else:
                return return_not_found(request, 'device not found')

            try:
                device.command(
                    cmd=command_id,
                    requested_by={
                        'user_id': session['auth_id'],
                        'component': 'yombo.gateway.lib.WebInterface.api_v1.devices_get',
                        'gateway': webinterface.gwid
                    },
                    inputs=inputs,
                    )
                a = return_good(request, 'Command executed.')
                request.setHeader('Content-Type', 'application/json')
                return json.dumps(a)
            except KeyError as e:
                return return_not_found(request, 'Error with command: %s' % e)

        @webapp.route('/notifications', methods=['GET'])
        @require_auth()
        def api_v1_notifications_get(webinterface, request, session):
            return return_good(request, ''. webinterface.notifications.notifications)

        @webapp.route('/notifications/<string:notification_id>/ack', methods=['GET'])
        @require_auth()
        def api_v1_notifications_ack_get(webinterface, request, session, notification_id):
            try:
                webinterface._Notifications.ack(notification_id)
            except KeyError as e:
                return return_not_found(request)
            return return_good(request)

        @webapp.route('/web_notif', methods=['GET'])
        @require_auth()
        def api_v1_web_notif_get(webinterface, request, session):
            action = request.args.get('action')[0]
            results = {}
            if action == "closed":
                id = request.args.get('id')[0]
                # print "alert - id: %s" % id
                if id in webinterface.alerts:
                    del webinterface.alerts[id]
                    results = {"status": 200}
            request.setHeader('Content-Type', 'application/json')
            return json.dumps(results)

        @webapp.route('/statistics/names', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def api_v1_statistics_names(webinterface, request):
            records = yield webinterface._Libraries['localdb'].get_distinct_stat_names()
            request.setHeader('Content-Type', 'application/json')
            returnValue(json.dumps(records))

        @webapp.route('/statistics/echarts/buckets', methods=['GET', 'POST'])
        @require_auth()
        @inlineCallbacks
        def api_v1_statistics_echarts_buckets(webinterface, request, session):
            time_last = request.args.get('last', [None, ])[0]
            time_start = request.args.get('start', [None, ])[0]
            time_end = request.args.get('end', [None, ])[0]
            stat_type = request.args.get('type', [None, ])[0]
            stat_name = request.args.get('name', [None, ])[0]
            bucket_size = int(request.args.get('bucket_size', [3600, ])[0])

            if stat_name is None:
                returnValue(return_error(request, "'name' is required."))
            if not isinstance(stat_name, six.string_types):
                returnValue(return_error(request, "'name' Must be a string. Got: %s" % stat_name))

            if time_start is not None:
                if not isinstance(time_start, int) or time_start < 0:
                    returnValue(return_error(request, "'start' must be an int and must be greater than 0"))

            if time_end is not None:
                if not isinstance(time_end, int) or time_end < 0:
                    returnValue(return_error(request, "'end' must be an int and must be greater than 0"))

            if stat_type is not None:
                if stat_type is not isinstance(stat_type, six.string_types):
                    returnValue(return_error(request, "'type' Must be a string"))
                if stat_type not in ('counter', 'datapoint', 'average'):
                    returnValue(return_error(request, "'type' must be either: 'counter', 'datapoint', or 'average'"))

            if bucket_size is not None:
                if bucket_size < 0:
                    returnValue(return_error(request, "'bucket_size' must be an int and must be greater than 0."))

            if time_last is not None:
                time_last = int(time_last)
                if time_last < 0:
                    returnValue(return_error(request, "'last' must be an int and must be greater than 0."))
                time_start = int(time()) - time_last

            records = yield webinterface._Libraries['localdb'].get_stats_sums(stat_name, bucket_size=bucket_size,
                                                                              bucket_type=stat_type, time_start=time_start,
                                                                              time_end=time_end)
            labels = []
            data = []
            live_stats = webinterface._Statistics.get_stat(stat_name, stat_type)

            for record in records:
                labels.append(epoch_to_string(record['bucket'], '%Y/%-m/%-d %H:%M'))
                data.append(record['value'])

            for record in live_stats:
                labels.append(epoch_to_string(record['bucket'], '%Y/%-m/%-d %H:%M'))
                data.append(record['value'])

            results = {
                'title': {'text': 'Device Commands Sent'},
                'toolbox': {
                    'show': 'true',
                    'feature': {
                        'dataZoom': {
                            'show': 'true',
                            'title': {
                                'zoom': 'Select Zoom',
                                'back': 'Reset Zoom'
                            },
                        },
                        'dataView': {
                            'show': 'true',
                            'title': 'View',
                            'lang': ['View', 'Cancel', 'Save']
                        },
                        'restore': {
                            'show': 'true',
                            'title': 'Restore'
                        },
                        'saveAsImage': {
                            'show': 'true',
                            'title': 'Save as image',
                            'type': 'png',
                            'lang': ['Save as image']
                        },
                    },
                },
                'dataZoom': {
                    'show': 'true',
                },

                'tooltip': {'show': 'true'},
                'legend': {'data': ['Legend here']},
                'xAxis': [{'type': 'category', 'data': labels}],
                'yAxis': [{'type': 'value'}], 'series': [{'name': 'Commands Sent', 'type': 'bar', 'data': data}],

            }

            request.setHeader('Content-Type', 'application/json')
            returnValue(json.dumps(results))

        @webapp.route('/server/commands/index', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def api_v1_commands_index(webinterface, request, session):
            try:
                offset = request.args.get('offset')[0]
            except:
                offset = 0
            try:
                limit = request.args.get('limit')[0]
            except:
                limit = 50
            try:
                search = request.args.get('search')[0]
            except:
                search = None

            url = '/v1/command?_pagestart=%s&_pagelimit=%s' % (offset, limit)
            if search is not None:
                url = url + "&?_filters[label]*%s&_filters[description]*%s&_filters[machine_label]*%s&_filteroperator=or" % (search, search, search)

            results = yield webinterface._YomboAPI.request('GET', url)
            data = {
                'total': results['content']['pages']['total_items'],
                'rows': results['data'],
            }
            request.setHeader('Content-Type', 'application/json')
            returnValue(json.dumps(data))

        # @webapp.route('/server/dns/check_available/<string:dnsname>', methods=['GET'])
        # @require_auth()
        # @inlineCallbacks
        # def api_v1_dns_check_available(webinterface, request, session, dnsname):
        #     url = '/api/v1/dns/check_available/%s' % dnsname
        #     url = '/v1/device_type'
        #     results = yield webinterface._YomboAPI.request('GET', url)
        #     returnValue(results['content'])

        @webapp.route('/server/dns/check_available/<string:dnsname>', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def api_v1_dns_check_available(webinterface, request, session, dnsname):

            url = '/v1/dns/check_available/%s' % dnsname
            # url = '/v1/dns/check_available/sam'

            try:
                results = yield webinterface.get_api(request, "GET", url)
            except YomboWarning as e:
                returnValue(e.message)

            request.setHeader('Content-Type', 'application/json')
            returnValue(json.dumps(results['data']))

        @webapp.route('/server/devicetypes/index', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def api_v1_devicetypes_index(webinterface, request, session):
            try:
                offset = request.args.get('offset')[0]
            except:
                offset = 0
            try:
                limit = request.args.get('limit')[0]
            except:
                limit = 50
            try:
                search = request.args.get('search')[0]
            except:
                search = None

            url = '/v1/device_type?_pagestart=%s&_pagelimit=%s' % (offset, limit)
            if search is not None:
                url = url + "&?_filters[label]*%s&_filters[description]*%s&_filters[machine_label]*%s&_filteroperator=or" % (search, search, search)

            results = yield webinterface._YomboAPI.request('GET', url)
            data = {
                'total': results['content']['pages']['total_items'],
                'rows': results['data'],
            }
            request.setHeader('Content-Type', 'application/json')
            returnValue(json.dumps(data))

        @webapp.route('/server/input_type/index', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def api_v1_inputtypes_index(webinterface, request, session):
            try:
                offset = request.args.get('offset')[0]
            except:
                offset = 0
            try:
                limit = request.args.get('limit')[0]
            except:
                limit = 50
            try:
                search = request.args.get('search')[0]
            except:
                search = None

            url = '/v1/input_type?_pagestart=%s&_pagelimit=%s' % (offset, limit)
            if search is not None:
                url = url + "&?_filters[label]*%s&_filters[description]*%s&_filters[machine_label]*%s&_filteroperator=or" % (search, search, search)

            results = yield webinterface._YomboAPI.request('GET', url)
            data = {
                'total': results['content']['pages']['total_items'],
                'rows': results['data'],
            }
            request.setHeader('Content-Type', 'application/json')
            returnValue(json.dumps(data))

        @webapp.route('/server/modules/index', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def api_v1_modules_index(webinterface, request, session):
            try:
                offset = request.args.get('offset')[0]
            except:
                offset = 0
            try:
                limit = request.args.get('limit')[0]
            except:
                limit = 50
            try:
                search = request.args.get('search')[0]
            except:
                search = None

            url = '/v1/module?_pagestart=%s&_pagelimit=%s' % (offset, limit)
            if search is not None:
                url = url + "&?_filters[label]*%s&_filters[short_description]*%s&_filters[machine_label]*%s&_filteroperator=or" % (search, search, search)

            results = yield webinterface._YomboAPI.request('GET', url)
            data = {
                'total': results['content']['pages']['total_items'],
                'rows': results['data'],
            }
            request.setHeader('Content-Type', 'application/json')
            returnValue(json.dumps(data))

        @webapp.route('/server/modules/show/<string:module_id>', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def api_v1_modules_show_one(webinterface, request, session, module_id):
            # action = request.args.get('action')[0]
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            request.setHeader('Content-Type', 'application/json')
            returnValue(json.dumps(results['data']))

