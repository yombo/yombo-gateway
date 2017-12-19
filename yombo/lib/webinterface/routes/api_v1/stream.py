# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

from twisted.internet import defer

from yombo.lib.webinterface.auth import require_auth
# from yombo.lib.webinterface.routes.api_v1.__init__ import return_good, return_not_found, return_error, return_unauthorized
from yombo.utils import epoch_to_string, bytes_to_unicode, unicode_to_bytes, random_string


def broadcast(webinterface, name, data):
    """
    Sends an event to all connected web event listeners

    :param webinterface:
    :param name:
    :param data:
    :return:
    """
    # print("broadcast: %s -> %s" % (name, data))
    output = EventMsg(data, name)
    for spectator_id in list(webinterface.api_stream_spectators):
        spectator = webinterface.api_stream_spectators[spectator_id]
        if not spectator.transport.disconnected:
            spectator.write(output)
        else:
            del webinterface.api_stream_spectators[spectator_id]

def hook_was_called(webinterface, hook_name, **kwargs):
    broadcast(webinterface, hook_name, kwargs['event'])

def route_api_v1_stream(webapp, webinterface_local):
    webinterface_local.register_hook('_device_status_', hook_was_called)
    webinterface_local.register_hook('_notification_add_', hook_was_called)
    webinterface_local.register_hook('_notification_delete_', hook_was_called)
    webinterface_local.register_hook('_notification_acked_', hook_was_called)

    with webapp.subroute("/api/v1") as webapp:
        @webapp.route('/stream', methods=['GET'])
        @require_auth(api=True)
        def apiv1_stream_get(webinterface, request, session):
            print("Got a new stream.  Request: %s" % request)
            request.setHeader('Content-type', 'text/event-stream')
            request.write(EventMsg(int(time()), 'ping'))

            # We'll want to write more things to this client later, so keep the request
            # around somewhere.
            webinterface.api_stream_spectators[random_string(length=10)] = request

            # Indicate we're not done with this request by returning a deferred.
            # (In fact, this deferred will never fire, which is kinda fishy of us.)
            return defer.Deferred()

def EventMsg(data, name=None):
    """Format a Sever-Sent-Event message.
    :param data: message data, will be JSON-encoded.
    :param name: (optional) name of the event type.
    :rtype: str
    """
    # We need to serialize the message data to a string.  SSE doesn't say that
    # we must use JSON for that, but it's a convenient choice.
    # print("sending sse data: %s" % data)
    if isinstance(data, int) or isinstance(data, float):
        jsonData = data
    else:
        try:
            jsonData = json.dumps(data)
            # print("sending sse jsonData1: %s" % jsonData)
            # assert '\n' not in jsonData
        except Exception as e:
            jsonData = unicode_to_bytes(data)
            # print("sending sse jsonData2: %s" % jsonData)
            # assert '\n' not in jsonData

    # Newlines make SSE messages slightly more complicated.  Fortunately for us,
    # we don't have any in the messages we're using.

    if name:
        output = 'event: %s\n' % (name,)
    else:
        output = ''

    output += 'data: %s\n\n' % (jsonData,)
    return unicode_to_bytes(output)