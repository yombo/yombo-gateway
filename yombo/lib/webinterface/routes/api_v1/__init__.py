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


def args_to_dict(arguments):
    results = {}
    for argument, value in arguments.items():
        value = value[0]
        name = argument[0:argument.find('[')]
        sub_name = argument[argument.find('[')+1 : argument.find(']')]
        if name == sub_name:
            sub_name = None

        if name not in results:
            if sub_name is None:
                results[name] = []
            else:
                results[name] = {}

        if sub_name is None:
            results[name].append(value)
        else:
            results[name][sub_name] = value
    return results


def return_good(request, message=None, payload=None, comments=None, code=None):
    request.setHeader('Content-Type', 'application/json')
    if comments is None:
        comments = {}
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
        'comments': comments,
        'payload': payload,
    })


def return_not_found(request, message=None, code=None, comments=None):
    request.setHeader('Content-Type', 'application/json')
    if comments is None:
        comments = {}
    if code is None:
        code = 404
    request.setResponseCode(code)
    if message is None:
        message = "Not found"
    return json.dumps({
        'code': code,
        'message': message,
        'comments': comments,
    })


def return_error(request, message=None, code=None, comments=None):
    request.setHeader('Content-Type', 'application/json')
    if comments is None:
        comments = {}
    if code is None:
        code = 404
    request.setResponseCode(code)
    if message is None:
        message = "System error"
    return json.dumps({
        'code': code,
        'message': message,
        'comments': comments,
    })


def return_unauthorized(request, message=None, code=None, comments=None):
    request.setHeader('Content-Type', 'application/json')
    if comments is None:
        comments = {}
    if code is None:
        code = 401
    request.setResponseCode(code)
    if message is None:
        message = "Not authorized"
    return json.dumps({
        'code': code,
        'message': message,
        'comments': comments,
        'redirect': "/?",
    })

