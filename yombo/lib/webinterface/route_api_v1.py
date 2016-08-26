# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, returnValue
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

                device = webinterface._Devices.get_device(deviceid)
                device.do_command(cmd=commandid)
                a = return_good('Command executed.')
                return json.dumps(a)

        @webapp.route('/notifications', methods=['GET'])
        @require_auth()
        def api_v1_notifications_get(webinterface, request, session):
            action = request.args.get('action')[0]
            results = {}
            if action == "closed":
                id = request.args.get('id')[0]
                print "alert - id: %s" % id
                if id in webinterface.alerts:
                    del webinterface.alerts[id]
                    results = {"status": 200}
            return json.dumps(results)
    
        @webapp.route('/statistics/names', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def ajax_notifications_name_get(webinterface, request):
            records = yield webinterface._Libraries['localdb'].get_distinct_stat_names()
            print records
            returnValue(json.dumps(records))
    
        @webapp.route('/statistics/range', methods=['GET'])
        @require_auth()
        def api_v1_notifications_range_get(webinterface, request, session):
            name = request.args.get('name')[0]
            min = request.args.get('min')[0]
            max = request.args.get('max')[0]
            results = {}
            if action == "closed":
                id = request.args.get('id')[0]
                print "alert - id: %s" % id
                if id in webinterface.alerts:
                    del webinterface.alerts[id]
                    results = {"status": 200}
            return json.dumps(results)

        @webapp.route('/statistics/something', methods=['GET'])
        @require_auth()
        def api_v1_api_v1_statistics_something(webinterface, request, session):
            action = request.args.get('action')[0]
            results = {}
            if action == "closed":
                id = request.args.get('id')[0]
                print "alert - id: %s" % id
                if id in webinterface.alerts:
                    del webinterface.alerts[id]
                    results = {"status": 200}
            return json.dumps(results)

        @webapp.route('/statistics/echarts/buckets', methods=['GET', 'POST'])
        @require_auth()
        @inlineCallbacks
        def api_v1_statistics_test(webinterface, request, session):
            stat_name = action = request.args.get('name', [None,])[0]
            bucket_size = action = request.args.get('bucket_size', [3600,])[0]
            if stat_name is None:
                returnValue(return_error('name is required.'))
            # print "action = %s" % action

            records = yield webinterface._Libraries['localdb'].get_stats_sums(stat_name, bucket_size=bucket_size)
            # print "stat records: %s" % records
            labels = []
            data = []
            for record in records:
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

                'tooltip': {'show' : 'true'},
                'legend': {'data':['Legend here']},
                'xAxis': [{'type': 'category', 'data': labels}],
                'yAxis': [{'type': 'value'}], 'series': [{'name':'Commands Sent','type' : 'bar','data':data}],

            }

            returnValue(json.dumps(results))
