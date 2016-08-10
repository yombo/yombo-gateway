# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, succeed, returnValue

def api_v1(webapp):
    with webapp.subroute("/api") as webapp:
        @webapp.route('v1/notifications', methods=['GET'])
        def api_v1_notifications_get(webinterface, request):
            action = request.args.get('action')[0]
            results = {}
            if action == "closed":
                id = request.args.get('id')[0]
                print "alert - id: %s" % id
                if id in webinterface.alerts:
                    del webinterface.alerts[id]
                    results = {"status":200}
            return json.dumps(results)
    
        @webapp.route('v1/statistics/names', methods=['GET'])
        @inlineCallbacks
        def ajax_notifications_name_get(webinterface, request):
            records = yield webinterface._Libraries['localdb'].get_distinct_stat_names()
            print records
            returnValue(json.dumps(records))
    
        @webapp.route('v1/statistics/range', methods=['GET'])
        def api_v1_notifications_range_get(webinterface, request):
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
    
        @webapp.route('v1/statistics/something', methods=['GET'])
        def api_v1_notifications_something_get(webinterface, request):
            action = request.args.get('action')[0]
            results = {}
            if action == "closed":
                id = request.args.get('id')[0]
                print "alert - id: %s" % id
                if id in webinterface.alerts:
                    del webinterface.alerts[id]
                    results = {"status":200}
            return json.dumps(results)
        
