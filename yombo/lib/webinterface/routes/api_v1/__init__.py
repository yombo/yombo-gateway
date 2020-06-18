# Import python libraries
import json
from yombo.utils import random_string

from yombo.constants import CONTENT_TYPE_JSON


def request_args(request):
    """
    Accepts the request and returns the submitted arguments as an easy to consume dictionary. This
    can also handle one level deep nested dictionaries within the arguments. For example:
    http://localhost:8080/api/v1/system/backup/configs?password1=hello&argument2=hi&argument[inside]=nested

    This would return:
    {'password1': 'hello', 'argument2': 'hi', 'argument': {'inside': 'nested'}}

    :param request: The web request.
    :return:
    """
    results = {}
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
