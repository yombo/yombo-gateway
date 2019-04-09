"""
Handles rendering content to browsers or API requests.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/webinterface/class_helpers/render.html>`_
"""
# Import python libraries
from glob import glob
import json
import msgpack
import os
import zlib

# Import Yombo libraries
from yombo.constants import CONTENT_TYPE_JSON
from yombo.core.log import get_logger
from yombo.lib.webinterface.routes.api_v1 import args_to_dict
from yombo.utils import random_string, sha256_compact

logger = get_logger("library.webinterface.render")


class Render:
    """
    Handles responses to web clients.
    """
    def get_idempotence(self, request, session):
        """
        Check if idempotence is in the request and if that key has already been processed for the given user. If it
        has, return the same response.

        :param self:
        :param request:
        :param session:
        :return:
        """
        request.setHeader("Content-Type", CONTENT_TYPE_JSON)
        idempotence = request.getHeader("x-idempotence")
        if idempotence is None:
            arguments = args_to_dict(request.args)
            idempotence = arguments.get("_idempotence", None)
        if idempotence is not None:
            request.idempotence = idempotence
            idempotence = sha256_compact(f"{session.auth_id}:{idempotence}")
            if idempotence in self.idempotence:
                results = msgpack.loads(zlib.uncompress(self.idempotence[idempotence]))
                print(f"get_idempotence results {results}")
                return False
                request.setHeader("Idempotence", "true")
                request.setResponseCode(results["response_code"])
                return results["data"]
        return False

    def render(self, request, session, template_path, **kwargs):
        """
        Render a page to the web browser, using a Jinja2 template. This adds common variables to the jinja2 engine.

        :param request:
        :param page:
        :param session:
        :param kwargs:
        :return:
        """
        self.webapp.templates.globals["_"] = self.i18n(request)  # set in auth.update_request.
        template = self.webapp.templates.get_template(template_path)
        kwargs["session"] = session
        files = glob(f"{self.working_dir}/frontend/_nuxt/*.js")
        nuxtpreload = sorted((os.path.getsize(s), s.split('/')[-1]) for s in files) if files else ''
        kwargs["nuxtpreload"] = nuxtpreload[-5:]
        # print(f"webinterface render {kwargs}")
        return template.render(**kwargs)

    def render_api(self, request, session, data_type, id=None, attributes=None, meta=None, included=None,
                   response_code=None):
        """
        Renders content to an API based client.
        :param request:
        :param session:
        :param data_type:
        :param id:
        :param attributes:
        :param meta:
        :param included:
        :param response_code:
        :return:
        """
        if id is None:
            id = random_string(length=20)
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

        if response_code is None:
            response_code = 200

        request.setResponseCode(response_code)
        request.setHeader("Content-Type", CONTENT_TYPE_JSON)
        idempotence = request.getHeader("x-idempotence")
        if idempotence is None:
            arguments = args_to_dict(request.args)
            idempotence = arguments.get("_idempotence", None)
        if idempotence is not None:
            idempotence = sha256_compact(f"{session.auth_id}:{idempotence}")
            self.idempotence[idempotence] = zlib.compress(msgpack.packb(json.dumps(
                {
                    "data": response,
                    "response_code": response_code,
                }
            )))
        return json.dumps(response)

    def render_api_raw(self, request, session, data, response_code=None):
        """
        Renders content to an API based client, however this takes the data input as a dictionary and will
        not be processed. THis shoulud be in JSON API format, but not always.

        :param request:
        :param session:
        :param data:
        :param response_code:
        :return:
        """
        if response_code is None:
            response_code = 200

        request.setResponseCode(response_code)
        request.setHeader("Content-Type", CONTENT_TYPE_JSON)
        return json.dumps(data)

    def render_api_errors(self, request, session, errors=None, meta=None, response_code=None):
        """
        Render multiple API errors.

        :param request:
        :param session:
        :param errors:
        :param meta:
        :param response_code:
        :return:
        """
        request.setHeader("Content-Type", CONTENT_TYPE_JSON)

        if response_code is None:
            response_code = 400

        # print(f"return_error: {errors}")
        for error in errors:
            if "code" not in error:
                error["code"] = str(response_code)
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

        request.setResponseCode(response_code)
        return json.dumps(response)

    def render_api_error(self, request, session, code=None, title=None, detail=None, link=None, meta=None,
                         response_code=None):
        """
        Render a single error to an API client.

        :param request:
        :param session:
        :param code:
        :param title:
        :param detail:
        :param link:
        :param meta:
        :param response_code:
        :return:
        """
        print("render_api_error")
        request.setHeader("Content-Type", CONTENT_TYPE_JSON)

        if response_code is None:
            response_code = 400

        error = {"links": {}}
        if code is None:
            error["code"] = str(response_code)
        error["code"] = code
        if title is None:
            error["title"] = "Unknown error"
        error["title"] = code
        if detail is None:
            error["detail"] = "No details about error was provided."
        error["detail"] = code
        if link is not None:
            error["links"]["about"] = link
        else:
            error["links"]["about"] = f"https://yombo.net/GWAPI:Error_Responses"

        response = {
            "errors": error,
        }

        if meta is not None:
            response["meta"] = meta

        request.setResponseCode(response_code)
        return json.dumps(response)
