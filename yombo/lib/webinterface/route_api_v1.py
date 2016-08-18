# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, succeed, returnValue
from yombo.lib.webinterface.auth import require_auth_pin, require_auth

def return_error(message, status=500):
    return {
        'status': status,
        'message': message,
    }

def return_good(message, payload={}):
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
                return json.dumps(return_error('Action must be specified.'))

            if action == 'runcommand':
                try:
                    deviceid = request.args.get('deviceid')[0]
                    commandid = request.args.get('commandid')[0]
                except:
                    return json.dumps(return_error('deviceid and commandid must be specified for "runcommand".'))

                device = webinterface._DevicesLibrary.get_device(deviceid)
                msg = device.get_message(webinterface, cmd=commandid)
                msg.send()
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
                    results = {"status":200}
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
                    results = {"status":200}
            return json.dumps(results)
    
        @webapp.route('/statistics/something', methods=['GET'])
        @require_auth()
        def api_v1_notifications_something_get(webinterface, request, session):
            action = request.args.get('action')[0]
            results = {}
            if action == "closed":
                id = request.args.get('id')[0]
                print "alert - id: %s" % id
                if id in webinterface.alerts:
                    del webinterface.alerts[id]
                    results = {"status":200}
            return json.dumps(results)
        
