# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

# Import external libraries
import yombo.ext.six as six

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, returnValue

from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth


def return_error(message, status=500):
    return json.dumps({
        'status': status,
        'message': message,
    })


def return_good(message, payload=None):
    if payload is None:
        payload = {}
    return {
        'status': 200,
        'message': message,
        'payload': payload,
    }


def route_api_v1(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route('/ping')
        def api_v1_ping(webinterface, request):
            if webinterface.starting == True:
                return;
            request.setHeader("Access-Control-Allow-Origin", '*');
            return "y-pong-01"

        @webapp.route('/uptime')
        @require_auth()
        def api_v1_uptime(webinterface, request, session):
            if webinterface.starting == True:
                return;
            return str(webinterface._Atoms['running_since'])

        @webapp.route('/devices', methods=['GET'])
        @require_auth()
        def ajax_devices_get(webinterface, request, session):
            try:
                action = request.args.get('action')[0]
            except:
                return return_error('Action must be specified.')

            if action == 'runcommand':
                try:
                    deviceid = request.args.get('deviceid')[0]
                    commandid = request.args.get('commandid')[0]
                except:
                    return return_error('deviceid and commandid must be specified for "runcommand".')

                # print "making request for command...."
                device = webinterface._Devices.get(deviceid)
                device.command(
                    cmd=commandid,
                    requested_by={
                        'user_id': session['auth_id'],
                        'component': 'WebInterface',
                        'gateway': webinterface.gwid
                    }
                    )
                a = return_good('Command executed.')
                request.setHeader('Content-Type', 'application/json')
                return json.dumps(a)

        @webapp.route('/notifications', methods=['GET'])
        @require_auth()
        def api_v1_notifications_get(webinterface, request, session):
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
                returnValue(return_error("'name' is required."))
            if not isinstance(stat_name, six.string_types):
                returnValue(return_error("'name' Must be a string. Got: %s" % stat_name))

            if time_start is not None:
                if not isinstance(time_start, int) or time_start < 0:
                    returnValue(return_error("'start' must be an int and must be greater than 0"))

            if time_end is not None:
                if not isinstance(time_end, int) or time_end < 0:
                    returnValue(return_error("'end' must be an int and must be greater than 0"))

            if stat_type is not None:
                if stat_type is not isinstance(stat_type, six.string_types):
                    returnValue(return_error("'type' Must be a string"))
                if stat_type not in ('counter', 'datapoint', 'average'):
                    returnValue(return_error("'type' must be either: 'counter', 'datapoint', or 'average'"))

            if bucket_size is not None:
                if bucket_size < 0:
                    returnValue(return_error("'bucket_size' must be an int and must be greater than 0."))

            if time_last is not None:
                time_last = int(time_last)
                if time_last < 0:
                    returnValue(return_error("'last' must be an int and must be greater than 0."))
                time_start = int(time()) - time_last

            records = yield webinterface._Libraries['localdb'].get_stats_sums(stat_name, bucket_size=bucket_size,
                                                                              type=stat_type, time_start=time_start,
                                                                              time_end=time_end)
            # print "stat records: %s" % records
            labels = []
            data = []
            live_stats = webinterface._Statistics.get_stat(stat_name, stat_type)

            for record in records:
                labels.append(webinterface.epoch_to_human(record['bucket'], '%Y/%-m/%-d %H:%M'))
                data.append(record['value'])

            for record in live_stats:
                labels.append(webinterface.epoch_to_human(record['bucket'], '%Y/%-m/%-d %H:%M'))
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

            url = '/v1/command?offset=%s&limit=%s' % (offset, limit)
            if search is not None:
                url = url + "&label=%s" % search

            results = yield webinterface._YomboAPI.request('GET', url)
            data = {
                'total': results['content']['total'],
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
            except YomboWarning, e:
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

            url = '/v1/device_type?offset=%s&limit=%s' % (offset, limit)
            if search is not None:
                url = url + "&label=%s" % search

            results = yield webinterface._YomboAPI.request('GET', url)
            data = {
                'total': results['content']['total'],
                'rows': results['data'],
            }
            request.setHeader('Content-Type', 'application/json')
            returnValue(json.dumps(data))

        @webapp.route('/server/inputtypes/index', methods=['GET'])
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

            url = '/v1/input_type?offset=%s&limit=%s' % (offset, limit)
            if search is not None:
                url = url + "&label=%s" % search

            results = yield webinterface._YomboAPI.request('GET', url)
            data = {
                'total': results['content']['total'],
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

            url = '/v1/module?offset=%s&limit=%s' % (offset, limit)
            if search is not None:
                url = url + "&label=%s" % search

            results = yield webinterface._YomboAPI.request('GET', url)
            data = {
                'total': results['content']['total'],
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

