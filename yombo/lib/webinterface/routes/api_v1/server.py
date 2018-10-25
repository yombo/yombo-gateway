# Import python libraries
import json

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_error
from yombo.constants import CONTENT_TYPE_JSON

def route_api_v1_server(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route('/server/commands/index', methods=['GET'])
        @require_auth(api=True)
        @inlineCallbacks
        def apiv1_server_commands_index(webinterface, request, session):
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

            try:
                results = yield webinterface._YomboAPI.request('GET', url, session=session['yomboapi_session'])
            except YomboWarning as e:
                return return_error(request, e.message, e.errorno)

            data = {
                'total': results['content']['pages']['total_items'],
                'rows': results['data'],
            }
            request.setHeader('Content-Type', CONTENT_TYPE_JSON)
            return json.dumps(data)

        @webapp.route('/server/dns/check_available/<string:dnsname>', methods=['GET'])
        @require_auth(api=True)
        @inlineCallbacks
        def apiv1_server_dns_check_available(webinterface, request, session, dnsname):

            url = '/v1/dns/check_available/%s' % dnsname
            # url = '/v1/dns/check_available/sam'

            try:
                results = yield webinterface._YomboAPI.request('GET', url, session=session['yomboapi_session'])
            except YomboWarning as e:
                return return_error(request, e.message, e.errorno)

            request.setHeader('Content-Type', CONTENT_TYPE_JSON)
            return json.dumps(results['data'])

        @webapp.route('/server/devicetypes/index', methods=['GET'])
        @require_auth(api=True)
        @inlineCallbacks
        def apiv1_server_devicetypes_index(webinterface, request, session):
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

            try:
                results = yield webinterface._YomboAPI.request('GET', url, session=session['yomboapi_session'])
            except YomboWarning as e:
                return return_error(request, e.message, e.errorno)

            data = {
                'total': results['content']['pages']['total_items'],
                'rows': results['data'],
            }
            request.setHeader('Content-Type', CONTENT_TYPE_JSON)
            return json.dumps(data)

        @webapp.route('/server/input_type/index', methods=['GET'])
        @require_auth(api=True)
        @inlineCallbacks
        def apiv1_server_inputtypes_index(webinterface, request, session):
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

            try:
                results = yield webinterface._YomboAPI.request('GET', url, session=session['yomboapi_session'])
            except YomboWarning as e:
                return return_error(request, e.message, e.errorno)
            data = {
                'total': results['content']['pages']['total_items'],
                'rows': results['data'],
            }
            request.setHeader('Content-Type', CONTENT_TYPE_JSON)
            return json.dumps(data)

        @webapp.route('/server/modules/index', methods=['GET'])
        @require_auth(api=True)
        @inlineCallbacks
        def apiv1_server_modules_index(webinterface, request, session):
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

            try:
                results = yield webinterface._YomboAPI.request('GET', url, session=session['yomboapi_session'])
            except YomboWarning as e:
                return return_error(request, e.message, e.errorno)
            data = {
                'total': results['content']['pages']['total_items'],
                'rows': results['data'],
            }
            request.setHeader('Content-Type', CONTENT_TYPE_JSON)
            return json.dumps(data)

        @webapp.route('/server/modules/show/<string:module_id>', methods=['GET'])
        @require_auth(api=True)
        @inlineCallbacks
        def apiv1_server_modules_show_one(webinterface, request, session, module_id):
            try:
                results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id,
                                                               session=session['yomboapi_session'])
            except YomboWarning as e:
                return return_error(request, e.message, e.errorno)

            request.setHeader('Content-Type', CONTENT_TYPE_JSON)
            return json.dumps(results['data'])
