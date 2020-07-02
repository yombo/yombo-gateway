# Import python libraries
import json
import re
from requests_toolbelt.multipart import MultipartDecoder
from urllib.parse import (ParseResultBytes, urlparse as _urlparse, unquote_to_bytes as unquote)

from yombo.constants import CONTENT_TYPE_JSON, CONTENT_TYPE_MSGPACK
from yombo.utils import random_string, bytes_to_unicode


def parse_www_form_urlencoded(qs, keep_blank_values=1, strict_parsing=0):
    """
    Parse application/x-www-form-urlencoded data into a dictionary.

    :param qs: The content to parse.
    """
    d = {}
    items = [s2 for s1 in qs.split(b"&") for s2 in s1.split(b";")]
    for item in items:
        try:
            k, v = item.split(b"=", 1)
        except ValueError:
            if strict_parsing:
                raise
            continue
        if v or keep_blank_values:
            k = unquote(k.replace(b"+", b" "))
            v = unquote(v.replace(b"+", b" "))
            if k in d:
                d[k].append(v)
            else:
                d[k] = [v]
    return d


def parse_form_data(content, content_type):
    """
    Parse multipart/form-data data into a dictionary.

    :param qs: The content to parse.
    """
    decoder = MultipartDecoder(content, content_type)
    splitregex = re.compile(';\\s*')

    results = {}
    for part in decoder.parts:
        disp = part.headers[b'Content-Disposition'].decode('utf-8')
        # split:            form-data; name="mykey"     - Gets the key: mykey
        results[splitregex.split(disp)[1].split('=')[1].strip('\"')] = part.text

    return results


def request_data(webinterface, request):
    """
    Attempts to look in various locations of the request to get the submitted data. The priority is:

      # Look in the body for JSON/MSGPACK. This requires the content-type to be properly set. This
        also requires the request method to be one of: POST, PATCH, or PUT
      # Look at the query string for values.
      # Attempt to decode x-www-form-urlencoded or form-data items.

    Once one method has found to contain data, will stop processing. Will return a dictionary of the key/values.

    :param webinterface:
    :param request:
    :return:
    """
    # method = request.method.decode().strip()
    # headers = request.requestHeaders
    # print(f"a 4: method: {method}")
    # print(f"a 4: method: {type(method)}")
    # print(f"a 4a: headers: {headers}")
    # print(f"a 4b: headers: {type(headers)}")

    results = {}
    method = request.method.decode().strip()
    headers = request.requestHeaders
    if method.lower() in ("post", "patch", "put"):
        if request.requestHeaders.hasHeader("content-type"):
            content_type = bytes_to_unicode(request.requestHeaders.getRawHeaders("content-type")[0])
            if content_type == CONTENT_TYPE_JSON:
                return webinterface._Tools.data_unpickle(request.content.read(), content_type="json")
            if content_type == CONTENT_TYPE_MSGPACK:
                return webinterface._Tools.data_unpickle(request.content.read(), content_type="msgpack")
            if content_type == "application/x-www-form-urlencoded":
                return parse_www_form_urlencoded(request.content.read(), 1)
            if content_type.startswith("multipart/form-data"):
                return parse_form_data(request.content.read(), content_type)

    for argument, value in request.args.items():
        value = value[0]
        if "[" in argument:
            name = argument[0:argument.find("[")]
            sub_name = argument[argument.find("[")+1: argument.find("]")]
            if name == sub_name:
                sub_name = None
        else:
            name = argument
            sub_name = None

        if name not in results:
            if sub_name is None:
                results[name] = []
            else:
                results[name] = {}

        if sub_name is None:
            results[name] = value
        else:
            results[name][sub_name] = value
    return results


def request_args(webinterface, request):
    """
    Accepts the request and returns the submitted arguments as an easy to consume dictionary. This
    can also handle one level deep nested dictionaries within the arguments. For example:
    http://localhost:8080/api/v1/system/backup/configs?password1=hello&argument2=hi&argument[inside]=nested

    This would return:
    {'password1': 'hello', 'argument2': 'hi', 'argument': {'inside': 'nested'}}

    For POST/PATCH/PUT, this decodes JSON/MSGPACK contents to a dictionary. If there's not data, reverts to the
    query string.

    :param request: The web request.
    :return:
    """
    results = {}
    method = request.method.decode().strip()
    headers = request.requestHeaders
    # print(f"a 4: method: {method}")
    # print(f"a 4: method: {type(method)}")
    # print(f"a 4a: headers: {headers}")
    # print(f"a 4b: headers: {type(headers)}")
    if method.lower() in ("post", "patch", "put"):
        if "content-type" in headers:
            if request.requestHeaders.hasHeader("origin"):
                origin = request.requestHeaders.getRawHeaders("origin")[0]

            if headers["content-type"] == CONTENT_TYPE_JSON:
                return webinterface._Tools.data_unpickle(request.content.read(), content_type="json")
            if headers["content-type"] == CONTENT_TYPE_MSGPACK:
                return webinterface._Tools.data_unpickle(request.content.read(), content_type="msgpack")
    for argument, value in request.args.items():
        value = value[0]
        if "[" in argument:
            name = argument[0:argument.find("[")]
            sub_name = argument[argument.find("[")+1: argument.find("]")]
            if name == sub_name:
                sub_name = None
        else:
            name = argument
            sub_name = None

        if name not in results:
            if sub_name is None:
                results[name] = []
            else:
                results[name] = {}

        if sub_name is None:
            results[name] = value
        else:
            results[name][sub_name] = value
    return results


def return_json(request, payload, code=None):
    """
    Return an un-adulterated json response. Converts payload to json if needed.

    :param request:
    :param payload:
    :return:
    """
    request.setHeader("Content-Type", CONTENT_TYPE_JSON)
    if code is None:
        code = 200
    request.setResponseCode(code)
    if isinstance(payload, str):
        return payload
    return json.dumps(payload)


def return_good_base(request, data=None, included=None, code=None, meta=None):
    request.setHeader("Content-Type", CONTENT_TYPE_JSON)
    if data is None:
        data = []
    if code is None:
        code = 200
    request.setResponseCode(code)
    response = {
        "data": data,
    }
    if included is not None:
        response["included"] = included
    if meta is not None:
        response["meta"] = meta

    return json.dumps(response)


def return_good(request, data_type, id=None, attributes=None, included=None, code=None, meta=None):
    request.setHeader("Content-Type", CONTENT_TYPE_JSON)

    if id is None:
        id = random_string(length=15)
    if attributes is None:
        attributes = {}

    response = {
        "type": data_type,
        "id": id,
        "attributes": attributes,
    }
    if included is not None:
        response["included"] = included
    if meta is not None:
        response["meta"] = meta

    return return_good_base(request, data=response, included=included, code=code, meta=meta)


def return_error(request, errors=None, code=None, meta=None):
    request.setHeader("Content-Type", CONTENT_TYPE_JSON)
    if errors is None:
        errors = [{}]
    elif isinstance(errors, str):
        errors = [{}]
    if code is None:
        code = 400
    request.setResponseCode(code)

    print(f"return_error: {errors}")
    for error in errors:
        if "code" not in error:
            error["code"] = str(code)
        if "id" not in error:
            error["id"] = f"no_id_provided_{code}"
        if "title" not in error:
            error["title"] = "Unknown error"
        if "detail" not in error:
            error["detail"] = "No details about error was provided."
        if "links" not in error:
            error["links"] = {}
        if "about" not in error["links"]:
            error["links"]["about"] = f"https://yombo.net/GWAPI:Error_Responses"

    response = {
        "errors": errors,
    }

    if meta is not None:
        response["meta"] = meta

    return json.dumps(response)


def return_error_single(request, message=None, code=None, meta=None):
    if message is not None:
        errors = [{"message": message}]
    else:
        errors = None
    return return_error(request, errors=errors, code=code, meta=meta)


def return_not_found(request, message=None, code=None, meta=None):
    if message is not None:
        errors = [{"message": message}]
    else:
        errors = [{"title": "Not found", "message": "The requested item or path was not found."}]
    if code is None:
        code = 404
    return return_error(request, errors=errors, code=code, meta=meta)


def return_unauthorized(request, message=None, code=None, meta=None):
    if message is not None:
        errors = [{"message": message}]
    else:
        errors = [{"title": "Not authorized", "message": "The request has not been authorized."}]
    if code is None:
        code = 401
    return return_error(request, errors=errors, code=code, meta=meta)
