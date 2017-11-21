# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth

from yombo.utils import epoch_to_string, bytes_to_unicode

def return_good(request, message=None, payload=None, code=None):
    request.setHeader('Content-Type', 'application/json')
    if code is None:
        code = 200
    request.setResponseCode(code)
    if payload is None:
        payload = {}
    if message is None:
        message = "OK"
    return json.dumps({
        'code': code,
        'message': message,
        'payload': payload,
    })

def return_not_found(request, message=None, code=None):
    request.setHeader('Content-Type', 'application/json')
    if code is None:
        code = 404
    request.setResponseCode(code)
    if message is None:
        message = "Not found"
    return json.dumps({
        'code': code,
        'message': message,
    })

def return_error(request, message=None, code=None):
    request.setHeader('Content-Type', 'application/json')
    if code is None:
        code = 404
    request.setResponseCode(code)
    if message is None:
        message = "System error"
    return json.dumps({
        'code': code,
        'message': message,
    })

def return_unauthorized(request, message=None, code=None):
    request.setHeader('Content-Type', 'application/json')
    if code is None:
        code = 401
    request.setResponseCode(code)
    if message is None:
        message = "Not authorized"
    return json.dumps({
        'code': code,
        'message': message,
        'redirect': "/?",
    })

